# -*- coding: utf-8 -*-
"""Robô da ANM: baixa os arquivos de dados abertos, recorta Goiás como em `Squad 1/Dados brutos` e confere a forma.

Ordem: SIGMINE primeiro (o recorte do Cadastro Mineiro usa os processos com poligonal em Goiás), depois Cadastro Mineiro,
CFEM e Anuário Mineral. Para cada arquivo:
  1. baixa o arquivo nacional (ou o de Goiás, no SIGMINE);
  2. recorta Goiás pela regra registrada (robo/anm_recorte.py) — as linhas que ficam saem byte a byte como a ANM publica;
  3. confere a forma do recorte contra o arquivo atual: mesmas colunas na mesma ordem, mesma codificação e separador,
     tipos das colunas mantidos, nenhuma coluna esvaziada, número de linhas sem queda grande;
  4. igual ao atual → nada a fazer; diferente → grava, e registra a data em `datas_de_acesso.json`, o sha256 e o tamanho no
     LEIA-ME de `Dados brutos` e, no Cadastro, as contagens em `recorte_goias.json`.
Depois disso o pipeline da base consolidada (Squad 1/Bases consolidadas) precisa rodar para os números chegarem ao site: o
workflow do robô faz isso (ver robo/LEIA-ME.md).
"""
import json
import re
import shutil
from pathlib import Path

import anm_recorte
import forma
from comum import FalhaDownload, Resultado, baixar, digital_zip, sha256

BRUTOS_REL = Path("Squad 1") / "Dados brutos"


class ANM:
    def __init__(self, raiz, hoje, cfg, gravar=True, espelho=None, pasta_tmp=None, aceitar=()):
        self.raiz, self.hoje, self.cfg, self.gravar = Path(raiz), hoje, cfg, gravar
        self.espelho = espelho or {}
        self.aceitar = set(aceitar)  # fontes ou arquivos em que uma queda grande de linhas foi aceita por alguém
        self.tmp = Path(pasta_tmp)
        self.brutos = self.raiz / BRUTOS_REL
        self.datas_path = self.brutos / "datas_de_acesso.json"
        self.datas = json.loads(self.datas_path.read_text(encoding="utf-8"))
        self.leiame_path = self.brutos / "LEIA-ME.md"
        self.leiame = self.leiame_path.read_text(encoding="utf-8")
        self.recorte_path = self.brutos / "ANM - Cadastro Mineiro" / "recorte_goias.json"
        self.recorte_json = json.loads(self.recorte_path.read_text(encoding="utf-8"))
        self.mudou = False
        self.fontes_alteradas = set()

    def _url(self, url):
        return self.espelho.get(url, url)

    def _baixar(self, url, nome, r):
        destino = self.tmp / nome
        try:
            baixar(self._url(url), destino, limite_mb=self.cfg.get("limite_download_mb"))
            r.baixado = str(destino)
            return destino
        except FalhaDownload as e:
            r.situacao, r.motivo = "falhou", f"{url}: {e}"
            return None

    def _fracao(self, *nomes):
        """Fração mínima de linhas (ou registros) do arquivo atual; zero quando a queda foi aceita (`--aceitar-queda`)."""
        return 0.0 if self.aceitar & set(nomes) else self.cfg.get("fracao_minima", 0.9)

    # ----------------------------------------------------------------------------------------------------------- fontes
    def rodar(self, so=None):
        resultados = []
        for f in self.cfg["fontes"]:
            if so and f["id"] not in so:
                continue
            if f["tipo"] == "shapefile":
                resultados.append(self.shapefile(f))
            elif f["tipo"] == "cadastro":
                resultados += self.cadastro(f)
            else:
                resultados.append(self.csv(f))
        return resultados

    def shapefile(self, f):
        r = Resultado("ANM", f["nome"])
        atual = self.brutos / f["arquivo"]
        novo = self._baixar(f["url"], Path(f["arquivo"]).name, r)
        if novo is None:
            return r
        # o pipeline lê vários campos do SIGMINE: todos os campos de hoje são exigidos
        bloq, av = forma.checar_shapefile(novo, atual, todos_exigidos=True, fracao_minima=self._fracao(f["id"], atual.name))
        r.avisos += av
        if bloq:
            r.situacao, r.motivo = "bloqueada", "; ".join(bloq)
            return r
        if digital_zip(novo) == digital_zip(atual):
            r.situacao = "sem_mudanca"
            return r
        self._gravar(novo, atual, f, r)
        return r

    def csv(self, f):
        r = Resultado("ANM", f["nome"])
        atual = self.brutos / f["arquivo"]
        baixado = self._baixar(f["url"], Path(f["url"]).name, r)
        if baixado is None:
            return r
        dados = baixado.read_bytes()
        if forma.parece_html(dados):
            r.situacao, r.motivo = "bloqueada", "o servidor devolveu uma página HTML/XML em vez do CSV"
            return r
        if f.get("recorte"):
            try:
                dados, cont = anm_recorte.recortar_uf(dados, f["separador"], f["recorte"]["coluna"], f["recorte"]["valor"])
            except (ValueError, IndexError) as e:
                r.situacao, r.motivo = "bloqueada", f"não deu para recortar Goiás: {e}"
                return r
            r.detalhes = cont
        return self._conferir_e_gravar_csv(dados, atual, f, r)

    def cadastro(self, f):
        """Os 13 arquivos do Cadastro Mineiro (lista e regra de cada um em recorte_goias.json)."""
        pasta = self.brutos / f["pasta"]
        municipios = anm_recorte.municipios_goias(self.raiz / f["malha_municipal"])
        processos = anm_recorte.processos_sigmine(self.brutos / f["sigmine"])  # o SIGMINE já atualizado nesta execução
        saida = []
        for item in self.recorte_json["arquivos"]:
            nome = item["arquivo"]
            r = Resultado("ANM", f"Cadastro Mineiro — {nome}")
            saida.append(r)
            baixado = self._baixar(f["url_base"] + nome, nome, r)
            if baixado is None:
                continue
            dados = baixado.read_bytes()
            if forma.parece_html(dados):
                r.situacao, r.motivo = "bloqueada", "o servidor devolveu uma página HTML/XML em vez do CSV"
                continue
            try:
                goias, cont = anm_recorte.recortar_cadastro(dados, item["regra"], municipios, processos, f["separador"])
            except (ValueError, IndexError) as e:
                r.situacao, r.motivo = "bloqueada", f"não deu para recortar Goiás: {e}"
                continue
            r.detalhes = cont
            sub = {**f, "arquivo": f"{f['pasta']}/{nome}", "logico": f["logico"] + nome}
            self._conferir_e_gravar_csv(goias, pasta / nome, sub, r)
            if r.situacao == "atualizada":
                item.update(cont)
                item.update({"mb_nacional": round(len(dados) / 1e6, 2), "mb_goias": round(len(goias) / 1e6, 2),
                             "sha256_nacional": sha256(baixado), "sha256_goias": sha256(pasta / nome) if self.gravar else ""})
                self._linha_recorte_leiame(nome, item)
        return saida

    # ---------------------------------------------------------------------------------------------------------- comum
    def _conferir_e_gravar_csv(self, dados, atual, f, r):
        bloq, av = forma.checar_csv(dados, atual.read_bytes(), f["codificacao"], f["separador"],
                                    fracao_minima=self._fracao(f["id"], atual.name, atual.stem))
        r.avisos += av
        if bloq:
            r.situacao, r.motivo = "bloqueada", "; ".join(bloq)
            return r
        if dados == atual.read_bytes():
            r.situacao = "sem_mudanca"
            return r
        novo = self.tmp / ("recorte_" + atual.name)
        novo.write_bytes(dados)
        self._gravar(novo, atual, f, r)
        return r

    def _gravar(self, novo, atual, f, r):
        r.situacao = "atualizada"
        if not r.motivo:
            r.motivo = "conteúdo novo"
        if not self.gravar:
            return
        shutil.copyfile(novo, atual)
        r.arquivos.append(atual.relative_to(self.raiz).as_posix())
        self.datas[f["logico"]] = self.hoje
        self._linha_arquivo_leiame(atual)
        if f.get("src"):
            self._data_da_fonte_leiame(f["src"])
        self.fontes_alteradas.add(f.get("src") or f["nome"])
        self.mudou = True

    # ------------------------------------------------------------------------------------------------- LEIA-ME e índices
    def _linha_arquivo_leiame(self, caminho):
        """| `arquivo` | 1,9 MB | `sha256` | na lista de arquivos da pasta da fonte."""
        mb = f"{caminho.stat().st_size / 1e6:.1f}".replace(".", ",")
        padrao = re.compile(r"^(\| `" + re.escape(caminho.name) + r"` \| )[\d,]+ MB \| `[0-9a-f]{64}` \|$", re.M)
        self.leiame = padrao.sub(lambda m: f"{m.group(1)}{mb} MB | `{sha256(caminho)}` |", self.leiame, count=1)

    def _linha_recorte_leiame(self, nome, item):
        """| `arquivo` | regra | linhas nacionais | linhas aqui | `sha256 nacional` | na tabela do recorte do Cadastro."""
        num = lambda n: f"{n:,}".replace(",", ".")  # noqa: E731
        padrao = re.compile(r"^\| `" + re.escape(nome) + r"` \| (\w+) \| [\d.]+ \| [\d.]+ \| `[0-9a-f]{64}` \|$", re.M)
        self.leiame = padrao.sub(lambda m: f"| `{nome}` | {m.group(1)} | {num(item['linhas_nacional'])} | {num(item['linhas_goias'])} | "
                                           f"`{item['sha256_nacional']}` |", self.leiame, count=1)

    def _data_da_fonte_leiame(self, src):
        """A coluna 'Arquivo do dia' da linha da fonte na tabela de fontes."""
        linhas = self.leiame.split("\n")
        for i, ln in enumerate(linhas):
            if f"**{src}**" in ln and ln.startswith("| `"):
                cel = ln.split(" | ")
                if len(cel) >= 6 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", cel[4]):
                    cel[4] = self.hoje
                    linhas[i] = " | ".join(cel)
        self.leiame = "\n".join(linhas)

    def salvar(self):
        if not (self.gravar and self.mudou):
            return []
        # mesma forma de gravar dos arquivos de hoje (indentação 1, sem quebra de linha no fim)
        self.datas_path.write_text(json.dumps(dict(sorted(self.datas.items())), ensure_ascii=False, indent=1), encoding="utf-8")
        self.leiame_path.write_text(self.leiame, encoding="utf-8")
        self.recorte_path.write_text(json.dumps(self.recorte_json, ensure_ascii=False, indent=1), encoding="utf-8")
        return [p.relative_to(self.raiz).as_posix() for p in (self.datas_path, self.leiame_path, self.recorte_path)]

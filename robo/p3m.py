# -*- coding: utf-8 -*-
"""Robô do P3M: baixa cada camada do GeoServer do SGB, confere a forma, recorta por Goiás e grava como o repositório guarda.

Para cada camada do inventário (`Squad 1/P3M/inventario_p3m.csv`):
  1. baixa a URL de `url_download` (WFS do SGB, SHAPE-ZIP) — a mesma extensão do pedido original;
  2. confere a forma contra o zip original atual: geometria, sistema de coordenadas, campos (os que o mapa lê são
     obrigatórios), número de registros, caixa perto de Goiás;
  3. compara o conteúdo (não os bytes do zip, que o GeoServer refaz a cada pedido): igual → nada a fazer;
  4. recorta por Goiás (robo/recorte.py, as regras do Recortado) e confere o recorte contra o recortado atual;
  5. confere a chave de cada camada do mapa com todos os zips dela (o novo e os atuais dos outros): chave repetida barra
     todos os zips novos daquela camada, e só dela;
  6. grava o original e o recortado nos mesmos caminhos, atualiza `_indice_recorte.csv` e a `data_download` do inventário.
O resto do inventário (registros, tamanhos, classificação) é refeito por scripts/build_inventario_p3m.py, e o mapa por
scripts/build_mapa_base.py, na cadeia de scripts/atualizar_derivados.py.
"""
import csv
import io
import json
import shutil
import zipfile
from pathlib import Path

import anm_recorte
import forma
from comum import FalhaDownload, Resultado, baixar, digital_zip

P3M_REL = Path("Squad 1") / "P3M"
CAMPOS_INDICE = ["arquivo", "origem", "registros_originais", "registros_em_goias", "fiapos_de_divisa_removidos", "mb"]


class P3M:
    def __init__(self, raiz, hoje, cfg, gravar=True, espelho=None, pasta_tmp=None, aceitar=()):
        self.raiz, self.hoje, self.cfg, self.gravar = Path(raiz), hoje, cfg, gravar
        self.espelho = espelho or {}
        self.aceitar = set(aceitar)  # camadas em que uma queda grande de registros foi aceita por alguém
        self.pendentes = {}  # zip recortado (ou original) -> camada que passou na forma e espera a conferência da chave
        self.tmp = Path(pasta_tmp)
        self.p3m = self.raiz / P3M_REL
        self.rec_dir = self.p3m / "Recortado pelo polígono de Goiás"
        self.inv_path = self.p3m / "inventario_p3m.csv"
        self.ind_path = self.rec_dir / "_indice_recorte.csv"
        with open(self.inv_path, encoding="utf-8-sig", newline="") as f:
            leitor = csv.DictReader(f, delimiter=";")
            self.inv_campos, self.inventario = leitor.fieldnames, list(leitor)
        with open(self.ind_path, encoding="utf-8-sig", newline="") as f:
            self.indice = {r["arquivo"]: r for r in csv.DictReader(f, delimiter=";")}
        self.exigidos = campos_do_site(self.raiz)
        self._go = None
        self.mudou = False

    # ------------------------------------------------------------------------------------------------------------ escolha
    def alvos(self, escopo="mapa", so=None):
        """Linhas do inventário a atualizar: as camadas que o mapa usa (padrão), todas, ou as pedidas em `so`."""
        no_site = set(self.exigidos)
        linhas = []
        for ln in self.inventario:
            zips = {Path(a).name for col in ("arquivo_original", "arquivo_recortado") for a in ln[col].split(";") if a}
            if so:
                if ln["camada"] in so or zips & set(so):
                    linhas.append(ln)
            elif escopo == "todas" or zips & no_site:
                linhas.append(ln)
        return linhas

    # ---------------------------------------------------------------------------------------------------------- camada
    def limite(self):
        if self._go is None:
            import recorte
            self._go = recorte.limite(self.p3m / "Original" / "6- Cartografia" / "GO_UF_2024.zip")
        return self._go

    def atualizar(self, linha):
        r = Resultado("P3M", f"{linha['titulo_p3m']} ({linha['camada']})")
        originais = [a for a in linha["arquivo_original"].split(";") if a]
        recortados = [a for a in linha["arquivo_recortado"].split(";") if a]
        if not linha["url_download"]:
            r.situacao, r.motivo = "pulada", "sem URL de download (não vem do P3M)"
            return r
        if len(originais) != 1 or len(recortados) > 1:
            r.situacao, r.motivo = "pulada", "camada guardada em partes; atualizar à mão (ver Squad 1/P3M/LEIA-ME.md)"
            return r
        orig = self.p3m / originais[0]
        rec = self.p3m / recortados[0] if recortados else None
        novo = self.tmp / f"{linha['camada']}_original.zip"
        url = self.espelho.get(linha["url_download"], linha["url_download"])
        try:
            baixar(url, novo, limite_mb=self.cfg.get("limite_mb", 95))
        except FalhaDownload as e:
            r.situacao, r.motivo = "falhou", str(e)
            return r
        r.baixado = str(novo)
        exig = self.exigidos.get(orig.name, set()) | (self.exigidos.get(rec.name, set()) if rec else set())
        fracao = 0.0 if self.aceitar & {linha["camada"], orig.name} else self.cfg.get("fracao_minima", 0.5)
        bloq, av = forma.checar_shapefile(novo, orig, exigidos=exig, fracao_minima=fracao)
        r.avisos += av
        if bloq:
            r.situacao, r.motivo = "bloqueada", "; ".join(bloq)
            return r
        if digital_zip(novo) == digital_zip(orig):
            r.situacao = "sem_mudanca"
            return r
        import recorte
        go, crs = self.limite()
        novo_rec = self.tmp / f"{linha['camada']}_recortado.zip"
        n_orig, n_go, fiapos = recorte.recortar_zip(novo, novo_rec, go, crs_saida=crs, crs_area=self.cfg.get("crs_area", recorte.CRS_AREA),
                                                    fracao=self.cfg.get("fiapo_fracao", recorte.FIAPO_FRACAO),
                                                    m2=self.cfg.get("fiapo_km2", 10) * 1e6)
        if rec is not None:
            if not n_go:
                r.situacao, r.motivo = "bloqueada", f"o recorte ficou sem nenhuma feição em Goiás (o atual tem {self.indice.get(rec.name, {}).get('registros_em_goias', '?')})"
                return r
            bloq, av = forma.checar_shapefile(novo_rec, rec, exigidos=exig, fracao_minima=fracao)
            r.avisos += [f"recorte: {a}" for a in av if not a.startswith(("campos novos", "codificação"))]
            if bloq:
                r.situacao, r.motivo = "bloqueada", "recorte: " + "; ".join(bloq)
                return r
        r.situacao = "atualizada"
        r.detalhes = {"registros_original": n_orig, "registros_goias": n_go, "fiapos": fiapos}
        r.motivo = f"{n_orig} registros no original, {n_go} em Goiás"
        self.pendentes[(rec or orig).name] = {"r": r, "linha": linha, "orig": orig, "rec": rec, "novo": novo,
                                              "novo_rec": novo_rec if n_go else None, "n": (n_orig, n_go, fiapos)}
        return r

    # ------------------------------------------------------------------------------------------- chave de cada camada
    def conferir_chaves(self):
        """Uma camada do mapa que junta vários zips (os mapeamentos geológicos, um por escala) precisa de chave única no
        conjunto. Confere com os zips novos desta execução e os atuais dos outros; se repetir, barra todos os zips novos
        daquela camada — o mapa continua com a versão atual dela, e as outras camadas seguem."""
        barrados = []
        for camada, (zips, campo) in chaves_do_site(self.raiz).items():
            novos = [z for z in zips if z in self.pendentes]
            if not novos:
                continue
            valores = []
            for z in zips:
                p = self.pendentes.get(z)
                caminho = p["novo_rec"] if p else next(iter(self.rec_dir.glob(f"*/{glob_escape(z)}")), None)
                if caminho is not None:
                    valores += valores_do_campo(caminho, campo)
            problema = problema_de_chave(campo, valores)
            if problema:
                motivo = f"a camada {camada} do mapa ficaria com {problema}"
                for z in novos:
                    p = self.pendentes.pop(z)
                    p["r"].situacao, p["r"].motivo = "bloqueada", motivo
                    barrados.append(p["r"])
        return barrados

    def gravar_pendentes(self):
        """Grava as camadas que passaram em tudo: original, recortado, índice do recorte e data no inventário."""
        for p in self.pendentes.values():
            if not self.gravar:
                continue
            r, orig, rec = p["r"], p["orig"], p["rec"]
            n_orig, n_go, fiapos = p["n"]
            shutil.copyfile(p["novo"], orig)
            r.arquivos.append(orig.relative_to(self.raiz).as_posix())
            if n_go:
                if rec is None:  # camada que antes não tinha nada em Goiás
                    rec = self.rec_dir / orig.parent.name / orig.name
                    rec.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(p["novo_rec"], rec)
                r.arquivos.append(rec.relative_to(self.raiz).as_posix())
                self.indice[rec.name] = {"arquivo": rec.name, "origem": orig.relative_to(self.p3m).as_posix(),
                                         "registros_originais": str(n_orig), "registros_em_goias": str(n_go),
                                         "fiapos_de_divisa_removidos": str(fiapos), "mb": f"{rec.stat().st_size / 1e6:.2f}"}
            p["linha"]["data_download"] = self.hoje
            self.mudou = True

    # ---------------------------------------------------------------------------------------------------------- gravar
    def salvar(self):
        """Grava o índice do recorte e o inventário (só a data de download das camadas que mudaram)."""
        if not (self.gravar and self.mudou):
            return []
        s = io.StringIO()
        w = csv.DictWriter(s, fieldnames=CAMPOS_INDICE, delimiter=";", lineterminator="\r\n")
        w.writeheader()
        w.writerows(self.indice.values())
        self.ind_path.write_text(s.getvalue(), encoding="utf-8-sig", newline="")
        s = io.StringIO()
        w = csv.DictWriter(s, fieldnames=self.inv_campos, delimiter=";", lineterminator="\r\n")
        w.writeheader()
        w.writerows(self.inventario)
        self.inv_path.write_text(s.getvalue(), encoding="utf-8-sig", newline="")
        return [p.relative_to(self.raiz).as_posix() for p in (self.ind_path, self.inv_path)]


def campos_do_site(raiz):
    """{nome do zip recortado: campos da fonte que scripts/mapa_camadas.json lê dele}. É o que o site exige de cada arquivo."""
    cfg = json.loads((Path(raiz) / "scripts" / "mapa_camadas.json").read_text(encoding="utf-8"))
    saida = {}
    for camada in cfg["camadas"]:
        origem = camada.get("origem") or {}
        if origem.get("tipo") != "p3m":
            continue
        campos = set()
        for c in camada.get("campos", []):
            f = c.get("fonte")
            campos |= set(f) if isinstance(f, list) else ({f} if f else set())
        for v in (camada.get("titular") or {}).values():
            if isinstance(v, str):
                campos.add(v)
        for a in origem.get("arquivos", []):
            saida.setdefault(a["arquivo"], set()).update(campos)
    # cada zip só precisa dos campos da camada que existem nele hoje (camadas que juntam vários zips têm campos de um só)
    rec_dir = Path(raiz) / P3M_REL / "Recortado pelo polígono de Goiás"
    for nome in list(saida):
        achados = list(rec_dir.glob(f"*/{glob_escape(nome)}"))
        if achados:
            atuais = {c[0] for p in forma.ler_shapefile_zip(achados[0]) for c in p["campos"]}
            saida[nome] &= atuais
    return saida


def chaves_do_site(raiz):
    """{camada do mapa: (zips, campo da fonte que é a chave)} para as camadas do P3M em que cada feição é um registro (as que
    agrupam registros por um campo, como as minas por processo, repetem a chave na fonte de propósito)."""
    cfg = json.loads((Path(raiz) / "scripts" / "mapa_camadas.json").read_text(encoding="utf-8"))
    saida = {}
    for camada in cfg["camadas"]:
        origem = camada.get("origem") or {}
        if origem.get("tipo") != "p3m" or camada.get("agrupar_por"):
            continue
        campo = next((c.get("fonte") for c in camada.get("campos", []) if c["id"] == camada.get("chave")), None)
        if isinstance(campo, str):
            saida[camada["id"]] = ([a["arquivo"] for a in origem.get("arquivos", [])], campo)
    return saida


def problema_de_chave(campo, valores):
    """Texto do problema quando a chave tem valor repetido ou vazio (o mapa exige chave única e preenchida); senão None."""
    vistos, repetidos = set(), set()
    for v in valores:
        (repetidos if v in vistos else vistos).add(v)
    vazios = sum(1 for v in valores if v == "")
    repetidos.discard("")
    if not (repetidos or vazios):
        return None
    partes = ([f"repetida em {len(repetidos)} valores ({', '.join(sorted(repetidos)[:8])}…)"] if repetidos else []) + \
             ([f"vazia em {vazios} feições"] if vazios else [])
    return f"a chave {campo} " + " e ".join(partes)


def valores_do_campo(caminho_zip, campo):
    with zipfile.ZipFile(caminho_zip) as z:
        valores = []
        for nome in sorted(n for n in z.namelist() if n.lower().endswith(".dbf")):
            valores += [r.get(campo, "").strip() for r in anm_recorte.ler_dbf(z.read(nome), "utf-8")]
    return valores


def glob_escape(nome):
    return "".join(f"[{c}]" if c in "[]*?" else c for c in nome)

# -*- coding: utf-8 -*-
"""O registro de `Squad 1/Dados brutos`: `datas_de_acesso.json` e o LEIA-ME da pasta.

Toda fonte que o robô grava ali passa por aqui, para que ANM, IBGE e SGB não sobrescrevam as mudanças umas das outras:
  - a data de acesso do arquivo (chave lógica que a planilha consolidada cita);
  - a linha do arquivo na lista da pasta (tamanho e sha256);
  - na tabela de fontes, a coluna "Arquivo do dia" e, quando a fonte informa, "Período coberto";
  - na lista de URLs, a consulta que reproduz o arquivo (o SIDRA muda o ano na URL).
"""
import json
import re
from pathlib import Path

from comum import sha256

BRUTOS_REL = Path("Squad 1") / "Dados brutos"


class Registro:
    def __init__(self, raiz, hoje, gravar=True):
        self.raiz, self.hoje, self.gravar = Path(raiz), hoje, gravar
        self.brutos = self.raiz / BRUTOS_REL
        self.datas_path = self.brutos / "datas_de_acesso.json"
        self.datas = json.loads(self.datas_path.read_text(encoding="utf-8"))
        self.leiame_path = self.brutos / "LEIA-ME.md"
        self.leiame = self.leiame_path.read_text(encoding="utf-8")
        self.mudou = False

    def arquivo(self, caminho, logico=None, src=None):
        """Registra um arquivo que acabou de ser gravado."""
        if logico:
            self.datas[logico] = self.hoje
        self.linha_arquivo(caminho)
        if src:
            self.celula_da_fonte(src, 4, self.hoje)
        self.mudou = True

    def linha_arquivo(self, caminho):
        """| `arquivo` | 1,9 MB | `sha256` | na lista de arquivos da pasta da fonte."""
        mb = f"{Path(caminho).stat().st_size / 1e6:.1f}".replace(".", ",")
        padrao = re.compile(r"^(\| `" + re.escape(Path(caminho).name) + r"` \| )[\d,]+ MB \| `[0-9a-f]{64}` \|$", re.M)
        self.leiame = padrao.sub(lambda m: f"{m.group(1)}{mb} MB | `{sha256(caminho)}` |", self.leiame, count=1)

    def celula_da_fonte(self, src, coluna, valor):
        """Uma célula da linha da fonte na tabela de fontes: 3 = Período coberto, 4 = Arquivo do dia."""
        linhas = self.leiame.split("\n")
        for i, ln in enumerate(linhas):
            if f"**{src}**" in ln and ln.startswith("| `"):
                cel = ln.split(" | ")
                if len(cel) >= 6 and (coluna != 4 or re.fullmatch(r"\d{4}-\d{2}-\d{2}", cel[4])):
                    cel[coluna] = valor.replace("|", "/")
                    linhas[i] = " | ".join(cel)
        self.leiame = "\n".join(linhas)

    def url_da_fonte(self, src, url, nota=""):
        """- **SRC**: <url> (nota) (metadados: …) — troca a URL e a nota, mantém os metadados."""
        padrao = re.compile(r"^(- \*\*" + re.escape(src) + r"\*\*: )(.*?)( \(metadados: .*)?$", re.M)
        self.leiame = padrao.sub(lambda m: m.group(1) + url + (f" {nota}" if nota else "") + (m.group(3) or ""), self.leiame, count=1)

    def salvar(self):
        if not (self.gravar and self.mudou):
            return []
        # mesma forma de gravar dos arquivos de hoje (indentação 1, sem quebra de linha no fim)
        self.datas_path.write_text(json.dumps(dict(sorted(self.datas.items())), ensure_ascii=False, indent=1), encoding="utf-8")
        self.leiame_path.write_text(self.leiame, encoding="utf-8")
        return [p.relative_to(self.raiz).as_posix() for p in (self.datas_path, self.leiame_path)]

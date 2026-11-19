# -*- coding: utf-8 -*-
"""Peças comuns do robô: download, impressão digital do conteúdo e o registro do que aconteceu em cada fonte."""
import hashlib
import json
import shutil
import struct
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
AGENTE = "minera-goias-robo/1.0 (+https://github.com/mineragoias-rgb/minera-goias)"


class FalhaDownload(Exception):
    pass


def baixar(url, destino, limite_mb=None, tentativas=3, espera=5, timeout=300):
    """Grava `url` em `destino`. Repete em erro de rede; recusa arquivo acima de `limite_mb`.

    Aceita `file://` (o modo espelho dos testes usa isso)."""
    ultimo = None
    for t in range(1, tentativas + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENTE})
            with urllib.request.urlopen(req, timeout=timeout) as r, open(destino, "wb") as f:
                total = 0
                while True:
                    bloco = r.read(1 << 20)
                    if not bloco:
                        break
                    total += len(bloco)
                    if limite_mb and total > limite_mb * 1e6:
                        raise FalhaDownload(f"passou de {limite_mb} MB; não cabe no repositório")
                    f.write(bloco)
                tipo = (r.headers.get("Content-Type") or "") if hasattr(r, "headers") else ""
            return tipo
        except FalhaDownload:
            raise
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            ultimo = e
            if isinstance(e, urllib.error.HTTPError) and e.code in (400, 401, 403, 404, 410):
                break  # não adianta repetir
            if t < tentativas:
                time.sleep(espera * t)
    raise FalhaDownload(f"{type(ultimo).__name__}: {ultimo}")


def existe(url, timeout=60):
    """True se o servidor tem o arquivo (HEAD 200), False se responde 404/410; None se não deu para saber."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": AGENTE}, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status == 200
    except urllib.error.HTTPError as e:
        return False if e.code in (404, 410) else None
    except (urllib.error.URLError, OSError, TimeoutError):
        return None


def sha256(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def digital_zip(caminho):
    """Impressão digital do CONTEÚDO de um zip de shapefile.

    O GeoServer refaz o zip a cada pedido: muda a data dos membros e a data gravada no cabeçalho do .dbf (bytes 1 a 3).
    Comparar o zip byte a byte acusaria mudança a cada execução. Aqui entram só os bytes de .shp, .shx, .dbf (com a data
    zerada) e .prj, na ordem dos nomes; .cst e .cpg (codificação) também, porque mudam a leitura dos textos."""
    h = hashlib.sha256()
    with zipfile.ZipFile(caminho) as z:
        for nome in sorted(z.namelist()):
            ext = nome.lower().rsplit(".", 1)[-1]
            if ext not in ("shp", "shx", "dbf", "prj", "cst", "cpg"):
                continue
            dados = z.read(nome)
            if ext == "dbf" and len(dados) >= 4:
                dados = dados[:1] + b"\0\0\0" + dados[4:]
            h.update(Path(nome).name.lower().encode() + b"\0" + struct.pack("<Q", len(dados)) + dados)
    return h.hexdigest()


def pasta_temporaria(prefixo="robo_"):
    return Path(tempfile.mkdtemp(prefix=prefixo))


def mover(origem, destino):
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(origem), str(destino))


@dataclass
class Resultado:
    """O que aconteceu com uma fonte (ou camada) nesta execução."""
    fonte: str
    nome: str
    situacao: str = "pendente"  # sem_mudanca | atualizada | bloqueada | falhou | pulada
    motivo: str = ""
    avisos: list = field(default_factory=list)
    detalhes: dict = field(default_factory=dict)
    arquivos: list = field(default_factory=list)
    baixado: str = ""  # arquivo baixado nesta execução (guardado para inspeção quando a fonte é barrada)

    def como_dict(self):
        return {k: getattr(self, k) for k in ("fonte", "nome", "situacao", "motivo", "avisos", "detalhes", "arquivos")}


ROTULOS = {"atualizada": "atualizada", "sem_mudanca": "sem mudança", "bloqueada": "BLOQUEADA (forma)", "falhou": "FALHOU (download)",
           "pulada": "pulada"}


def relatorio_md(resultados, hoje):
    linhas = [f"Execução de {hoje}.", ""]
    contagem = {}
    for r in resultados:
        contagem[r.situacao] = contagem.get(r.situacao, 0) + 1
    linhas.append(" · ".join(f"{ROTULOS.get(k, k)}: {v}" for k, v in sorted(contagem.items())))
    linhas += ["", "| Fonte | Base | Situação | Motivo / avisos |", "|---|---|---|---|"]
    ordem = {"bloqueada": 0, "falhou": 1, "atualizada": 2, "pulada": 3, "sem_mudanca": 4}
    for r in sorted(resultados, key=lambda r: (ordem.get(r.situacao, 9), r.fonte, r.nome)):
        texto = "; ".join(x for x in [r.motivo] + r.avisos if x).replace("|", "/").replace("\n", " ")
        linhas.append(f"| {r.fonte} | {r.nome} | {ROTULOS.get(r.situacao, r.situacao)} | {texto} |")
    return "\n".join(linhas) + "\n"


def gravar_json(caminho, dado):
    Path(caminho).write_text(json.dumps(dado, ensure_ascii=False, indent=1), encoding="utf-8")

# -*- coding: utf-8 -*-
"""Filtra os CSVs nacionais do dataset PARCELA_CARGA_CONSUMO (CCEE) para Goiás e grava no repositório.

Fonte: https://dadosabertos.ccee.org.br/dataset/parcela_carga_consumo (Infomercado, CC-BY-4.0).
Baixe cada ano pelo botão de download do recurso (parcela_carga_consumo_2024/2025/2026) — o servidor de
download (pda-download.ccee.org.br) bloqueia requisições automatizadas (curl/fetch), então o download em
si precisa ser feito manualmente pelo navegador.

    python scripts/build_ccee_go.py --2024 <baixado_2024.csv> --2025 <baixado_2025.csv> --2026 <baixado_2026.csv>

Cada arquivo de entrada é o CSV nacional bruto (';' como separador, UTF-8, ponto como separador decimal).
O filtro mantém só ESTADO_UF == GO, remove o preenchimento de espaços à direita presente em alguns campos
de origem (ESTADO_UF, SIGLA_PARCELA_CARGA, CNPJ_CARGA, …) e grava com BOM UTF-8 + CRLF, no mesmo formato
que os arquivos já versionados em Squad 1/dados/CCEE/.
"""
import argparse
import csv
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEST = REPO / "Squad 1" / "dados" / "CCEE"

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--2024", dest="ano2024", help="CSV nacional baixado do recurso parcela_carga_consumo_2024")
ap.add_argument("--2025", dest="ano2025", help="CSV nacional baixado do recurso parcela_carga_consumo_2025")
ap.add_argument("--2026", dest="ano2026", help="CSV nacional baixado do recurso parcela_carga_consumo_2026")
args = ap.parse_args()

anos = {"2024": args.ano2024, "2025": args.ano2025, "2026": args.ano2026}
anos = {ano: caminho for ano, caminho in anos.items() if caminho}
assert anos, "informe pelo menos um --2024/--2025/--2026 com o caminho do CSV nacional baixado"

for ano, origem in sorted(anos.items()):
    origem = Path(origem)
    with open(origem, encoding="utf-8-sig", newline="") as f:
        r = csv.reader(f, delimiter=";")
        header = next(r)
        idx_uf = header.index("ESTADO_UF")
        linhas = [[c.strip() for c in row] for row in r if row and row[idx_uf].strip().upper() == "GO"]
    meses = sorted({row[header.index("MES_REFERENCIA")] for row in linhas})
    destino = DEST / f"parcela_carga_consumo_{ano}_GO.csv"
    with open(destino, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\r\n")
        w.writerow(header)
        w.writerows(linhas)
    print(f"{ano}: {len(linhas)} linhas GO de {origem.name} -> {destino.relative_to(REPO)}; meses {meses[0]}–{meses[-1]} ({len(meses)} meses)")

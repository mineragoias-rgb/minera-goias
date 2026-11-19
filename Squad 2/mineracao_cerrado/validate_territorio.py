#!/usr/bin/env python3
"""Verifica e resume os artefatos territoriais do Squad 2.

Este script não refaz o processamento geoespacial original. Ele torna
reproduzível a verificação dos artefatos publicados: relatório, tabelas
embutidas e camada GeoJSON de risco ambiental.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent
REPORT = FOLDER / "relatorio_mineracao_cerrado_GO.html"
RISK = FOLDER / "GO_radar_risco_ambiental.geojson"
PANEL = ROOT / "public" / "territorio.js"
CPF_PATTERN = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")


def fail(message: str) -> None:
    print(f"ERRO: {message}", file=sys.stderr)
    raise SystemExit(1)


def extract_embedded_data(html: str) -> dict:
    match = re.search(r"\bconst\s+D\s*=\s*\{", html)
    if not match:
        fail("o relatório não contém o objeto de dados 'const D = {...}'")

    try:
        data, _ = json.JSONDecoder().raw_decode(html, match.end() - 1)
    except json.JSONDecodeError as error:
        fail(f"o objeto D no relatório não é JSON válido: {error}")

    if not isinstance(data, dict):
        fail("o objeto D do relatório deveria ser um objeto JSON")

    return data


def fields_used_by_panel(code: str) -> set[str]:
    return set(re.findall(r"\bD\.([a-zA-Z_][a-zA-Z0-9_]*)", code))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verifica os artefatos territoriais do Squad 2."
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="exibe um resumo após as verificações",
    )
    args = parser.parse_args()

    for path in (REPORT, RISK, PANEL):
        if not path.is_file():
            fail(f"arquivo obrigatório ausente: {path.relative_to(ROOT)}")

    html = REPORT.read_text(encoding="utf-8")
    report_data = extract_embedded_data(html)

    panel_fields = fields_used_by_panel(PANEL.read_text(encoding="utf-8"))
    missing = panel_fields - set(report_data)
    if missing:
        fail(
            "o painel solicita tabelas ausentes no relatório: "
            + ", ".join(sorted(missing))
        )

    try:
        layer = json.loads(RISK.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        fail(f"GeoJSON inválido: {error}")

    features = layer.get("features")
    if layer.get("type") != "FeatureCollection" or not isinstance(features, list):
        fail("a camada de risco precisa ser uma FeatureCollection GeoJSON")

    if not features:
        fail("a camada de risco não contém projetos")

    if CPF_PATTERN.search(json.dumps(layer, ensure_ascii=False)):
        fail("a camada de risco contém uma sequência com formato de CPF")

    expected_projects = 1046
    if len(features) != expected_projects:
        fail(
            f"esperados {expected_projects} projetos na camada; "
            f"encontrados {len(features)}"
        )

    print("OK: relatório, tabelas do painel e camada de risco validados.")

    if args.summary:
        print(f"Projetos na camada: {len(features)}")
        print(f"Tabelas embutidas no relatório: {len(report_data)}")
        print(f"Tabelas usadas pelo painel: {len(panel_fields)}")
        print("Dados pessoais em formato CPF: não encontrados")


if __name__ == "__main__":
    main()

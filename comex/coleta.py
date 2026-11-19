# -*- coding: utf-8 -*-
"""Coleta o Comex Stat (MDIC/SECEX) para Goiás e grava o bruto em comex/bruto/.

    python3 comex/coleta.py                 # baixa tudo e regrava o bruto
    python3 comex/coleta.py --check         # só conversa com a API e diz até que mês ela publicou

Só a biblioteca padrão, como o agente de produção: isto roda numa máquina enxuta, por cron, sem instalar nada.

Duas armadilhas da API que este arquivo existe para não cair:

1. PERÍODO QUE CRUZA ANOS. Se o período vai de 2019-01 a 2026-10, a API devolve, para TODO ano, apenas janeiro-outubro —
   o acumulado comparável, não o ano cheio — e não avisa. Conferido: NCM 26030010 em 2024 dá US$ 378,6 mi nesse formato e
   US$ 500,3 mi quando 2024 é pedido sozinho; a diferença é exatamente novembro e dezembro. Por isso cada ano é um pedido.

2. DETALHE `economicBlock`. Um país pertence a mais de um bloco, então a mesma venda volta repetida e a soma dobra
   (conferido: 1.000,6 contra 500,3 no mesmo recorte). Não se usa esse detalhe aqui.

A UF de Goiás é 53 no código do Comex Stat, que não é o código do IBGE (52): foi lido da própria API, varrendo os códigos
e perguntando qual nome volta.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date, timezone, datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

API = "https://api-comexstat.mdic.gov.br"
UF_GOIAS = 53
ANO_INICIAL = 2019
CAPITULOS_MINERAIS = [25, 26, 28, 71, 72, 74, 75, 81]
RAIZ = Path(__file__).resolve().parent
BRUTO = RAIZ / "bruto"


def post(caminho, payload, tentativas=3, espera=5):
    corpo = json.dumps(payload).encode("utf-8")
    erro = None
    for tentativa in range(tentativas):
        requisicao = urllib.request.Request(API + caminho, data=corpo,
                                            headers={"Content-Type": "application/json",
                                                     "Accept": "application/json"})
        try:
            with urllib.request.urlopen(requisicao, timeout=300) as resposta:
                return json.loads(resposta.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
            erro = e
            if tentativa + 1 < tentativas:
                time.sleep(espera * (tentativa + 1))
    raise RuntimeError(f"{caminho} falhou depois de {tentativas} tentativas: {erro!r}")


def get(caminho, tentativas=3, espera=5):
    erro = None
    for tentativa in range(tentativas):
        requisicao = urllib.request.Request(API + caminho, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(requisicao, timeout=120) as resposta:
                return json.loads(resposta.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
            erro = e
            if tentativa + 1 < tentativas:
                time.sleep(espera * (tentativa + 1))
    raise RuntimeError(f"{caminho} falhou depois de {tentativas} tentativas: {erro!r}")


def ate_quando():
    """Último mês que o Comex Stat publicou, dito pela própria API — nunca suposto pelo calendário."""
    d = get("/general/dates/updated")["data"]
    return int(d["year"]), int(d["monthNumber"]), d["updated"]


def ncms_curados():
    curada = json.loads((RAIZ / "base_curada.json").read_text(encoding="utf-8"))
    return curada, sorted({int(n["codigo"]) for m in curada["minerais"] for n in m["ncms"]})


def serie_mensal(fluxo, ncms, ano_fim, mes_fim):
    """Um pedido por ano: período que cruza anos faz a API devolver só o acumulado até o mês final (ver o cabeçalho)."""
    linhas = []
    for ano in range(ANO_INICIAL, ano_fim + 1):
        fim = f"{ano}-{mes_fim:02d}" if ano == ano_fim else f"{ano}-12"
        d = post("/general", {"flow": fluxo, "monthDetail": True,
                              "period": {"from": f"{ano}-01", "to": fim},
                              "filters": [{"filter": "state", "values": [UF_GOIAS]},
                                          {"filter": "ncm", "values": ncms}],
                              "details": ["ncm"], "metrics": ["metricFOB", "metricKG"]})
        linhas.extend(d["data"]["list"])
        print(f"  {fluxo} {ano}: {len(d['data']['list'])} linhas", flush=True)
    return linhas


def destinos(ncms, ano_fim, mes_fim):
    linhas = []
    for ano in range(ANO_INICIAL, ano_fim + 1):
        fim = f"{ano}-{mes_fim:02d}" if ano == ano_fim else f"{ano}-12"
        d = post("/general", {"flow": "export", "monthDetail": False,
                              "period": {"from": f"{ano}-01", "to": fim},
                              "filters": [{"filter": "state", "values": [UF_GOIAS]},
                                          {"filter": "ncm", "values": ncms}],
                              "details": ["ncm", "country"], "metrics": ["metricFOB", "metricKG"]})
        linhas.extend(d["data"]["list"])
        print(f"  destinos {ano}: {len(d['data']['list'])} linhas", flush=True)
    return linhas


def municipios(ano_fim, mes_fim):
    """Município só existe por capítulo da NCM: a API recusa `ncm` como detalhe em /cities. A granularidade é essa, e a base diz isso."""
    linhas = []
    for ano in range(ANO_INICIAL, ano_fim + 1):
        fim = f"{ano}-{mes_fim:02d}" if ano == ano_fim else f"{ano}-12"
        d = post("/cities", {"flow": "export", "monthDetail": False,
                             "period": {"from": f"{ano}-01", "to": fim},
                             "filters": [{"filter": "state", "values": [UF_GOIAS]},
                                         {"filter": "chapter", "values": CAPITULOS_MINERAIS}],
                             "details": ["city", "chapter"], "metrics": ["metricFOB", "metricKG"]})
        linhas.extend(d["data"]["list"])
        print(f"  municípios {ano}: {len(d['data']['list'])} linhas", flush=True)
    return linhas


def grava(nome, obj):
    caminho = BRUTO / nome
    caminho.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"  → {caminho.relative_to(RAIZ.parent)} ({caminho.stat().st_size/1e3:.0f} kB)")


def main():
    ap = argparse.ArgumentParser(description="Baixa o Comex Stat de Goiás para comex/bruto/.")
    ap.add_argument("--check", action="store_true", help="só pergunta à API até quando ela publicou e sai")
    args = ap.parse_args()

    ano_fim, mes_fim, atualizado = ate_quando()
    print(f"Comex Stat publicado até {ano_fim}-{mes_fim:02d} (atualização declarada: {atualizado}).")
    if args.check:
        return 0

    curada, ncms = ncms_curados()
    fluxos = sorted({n["fluxo"] for m in curada["minerais"] for n in m["ncms"]})
    BRUTO.mkdir(exist_ok=True)
    print(f"{len(ncms)} NCMs curadas, fluxos {fluxos}.")

    for fluxo in fluxos:
        grava(f"mensal_{fluxo}.json", serie_mensal(fluxo, ncms, ano_fim, mes_fim))
    grava("destinos.json", destinos(ncms, ano_fim, mes_fim))
    grava("municipios.json", municipios(ano_fim, mes_fim))
    grava("coleta.json", {
        "baixado_em": datetime.now(timezone.utc).date().isoformat(),
        "api": API,
        "uf_comexstat": UF_GOIAS,
        "ano_inicial": ANO_INICIAL,
        "publicado_ate": {"ano": ano_fim, "mes": mes_fim},
        "atualizacao_declarada_pela_api": atualizado,
        "capitulos_dos_municipios": CAPITULOS_MINERAIS,
    })
    print("Pronto. Agora: python3 scripts/build_comex_base.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

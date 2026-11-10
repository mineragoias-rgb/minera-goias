# -*- coding: utf-8 -*-
"""Catálogo das bases de dados que o sistema usa (data/catalogo/catalogo.json), para a aba Base de dados do painel.

    python scripts/build_catalogo_bases.py

Cada base do repositório entra com nome, ORIGEM e ÚLTIMA ATUALIZAÇÃO — os três campos do cabeçalho pedido —, mais o período coberto, o
volume, onde ela vive, o que ela mede e o que ela deliberadamente não mede.

Nada aqui é digitado à mão: a última atualização de um pacote gerado vem do `built_on` que o próprio pacote grava, e a de um arquivo bruto
vem da data do último commit que o tocou. Volume e período são contados abrindo o arquivo. Assim o catálogo não envelhece sozinho enquanto
as bases mudam — se uma base sumir, a linha some com ela e o teste acusa.
"""
import argparse
import csv
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ap = argparse.ArgumentParser(description="Gera data/catalogo/catalogo.json com as bases que o sistema usa.")
ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
ap.add_argument("--saida")
args = ap.parse_args()
REPO = Path(args.repo)
SAIDA = Path(args.saida) if args.saida else REPO / "data" / "catalogo" / "catalogo.json"
VERSAO = "v1"


def commit_date(caminho):
    """Data do último commit que tocou o arquivo — a única 'última atualização' que não depende de alguém lembrar de digitar."""
    try:
        saida = subprocess.run(["git", "-C", str(REPO), "log", "-1", "--format=%cs", "--", str(caminho)],
                               capture_output=True, text=True, timeout=30)
        return saida.stdout.strip() or "NA"
    except (OSError, subprocess.SubprocessError):
        return "NA"


def carrega(rel):
    caminho = REPO / rel
    return json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else None


def conta(obj):
    """As seções dos pacotes ora são lista, ora tabela {cols, rows}, ora ausentes: uma contagem só serve para as três."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return len(obj.get("rows", ())) or None
    return len(obj)


def tamanho(rel):
    caminho = REPO / rel
    return round(caminho.stat().st_size / 1e6, 2) if caminho.exists() else None


panorama = carrega("data/panorama/panorama.json")
atlas = carrega("data/atlas/atlas.json")
producao = carrega("data/producao/producao.json")
empresas = carrega("data/empresas/empresas.json")
projetos = carrega("data/projetos/projetos.json")
mercado = carrega("public/data/mercado/mercado_v1.json")
noticias = carrega("public/data/noticias/latest.json")

bases = []


def base(**kw):
    kw.setdefault("periodo", "NA")
    kw.setdefault("volume", "NA")
    kw.setdefault("nao_mede", "NA")
    kw.setdefault("readme", None)
    bases.append(kw)


# ------------------------------------------------------------------------------------------------- bases de origem (dados brutos)
if panorama:
    p = panorama["meta"]["periods"]
    base(id="ccee", nome="CCEE — parcelas de carga em Goiás", familia="Energia", natureza="bruta",
         origem="Câmara de Comercialização de Energia Elétrica (CCEE), via arquivos versionados em Squad 1/dados/CCEE",
         atualizado_em=commit_date("Squad 1/dados/CCEE"),
         periodo=f"{p['ccee'][0]} a {p['ccee'][1]}", volume=f"{len(panorama['ccee']['rows'])} linhas agregadas",
         onde="Squad 1/dados/CCEE/*.csv · servida pelo pacote data/panorama/panorama.json",
         mede="Uma parcela de carga de um agente, em um mês, município e ramo de atividade, em MWh.",
         nao_mede="Consumo da mineração: a base mistura 16 ramos de atividade e o recorte mineral confiável exige critério revisado.",
         readme="data/panorama/README.md")
    base(id="cfem", nome="CFEM — arrecadação por processo e substância", familia="Mineração", natureza="bruta",
         origem="Agência Nacional de Mineração (ANM), via base consolidada do Squad 1",
         atualizado_em=commit_date("Squad 1/Dados brutos/ANM - CFEM"),
         periodo=f"{p['cfem'][0]} a {p['cfem'][1]}", volume=f"{len(panorama['cfem']['rows'])} linhas agregadas",
         onde="Squad 1/Dados brutos/ANM - CFEM · pacote data/panorama/panorama.json",
         mede="Recolhimento de CFEM por processo, substância, município e mês, em R$, e a quantidade comercializada declarada.",
         nao_mede="Produção: a quantidade é a comercializada declarada para fins de arrecadação.",
         readme="data/panorama/README.md")
    base(id="amb", nome="Anuário Mineral Brasileiro (AMB)", familia="Mineração", natureza="bruta",
         origem="Agência Nacional de Mineração (ANM)",
         atualizado_em=commit_date("Squad 1/Dados brutos/ANM - Anuário Mineral Brasileiro (AMB)"),
         periodo=f"{p['amb'][0]} a {p['amb'][1]}", volume=f"{len(panorama['amb_go']['rows'])} linhas de Goiás",
         onde="Squad 1/Dados brutos/ANM - Anuário Mineral Brasileiro (AMB)/*.csv",
         mede="Produção bruta e beneficiada por UF e substância, com o contido declarado e sua unidade.",
         nao_mede="Produção por empresa: o Anuário é por estado e substância, sem titular.",
         readme="data/panorama/README.md")
    base(id="investimento", nome="Investimento em pesquisa mineral", familia="Mineração", natureza="bruta",
         origem="Agência Nacional de Mineração (ANM)",
         atualizado_em=commit_date("Squad 1/Dados brutos/ANM - Investimento em pesquisa mineral"),
         periodo=f"{p['inv'][0]} a {p['inv'][1]}", volume=f"{len(panorama['inv_go']['rows'])} linhas de Goiás",
         onde="Squad 1/Dados brutos/ANM - Investimento em pesquisa mineral/",
         mede="Gasto declarado em pesquisa mineral por ano, substância e rubrica.",
         readme="data/panorama/README.md")
    base(id="rodadas", nome="Rodadas de disponibilidade de áreas", familia="Mineração", natureza="bruta",
         origem="Agência Nacional de Mineração (ANM)",
         atualizado_em=commit_date("Squad 1/dados"), periodo="Rodadas 1 a 8",
         volume=f"{len(panorama['rod']['rows'])} áreas em Goiás",
         onde="Squad 1/dados/ResultadoRodadaDisponibilidade*.csv",
         mede="Área oferecida em rodada, com situação, modalidade, município, lance e arrematante.",
         readme="data/panorama/README.md")
if atlas:
    base(id="sigmine", nome="Cadastro mineiro / SIGMINE — processos", familia="Mineração", natureza="bruta",
         origem="Agência Nacional de Mineração (ANM), shapefile do SIGMINE",
         atualizado_em=commit_date("Squad 1/Dados brutos/ANM - SIGMINE"),
         periodo="Extração de 10/09/2026",
         volume=f"{conta(atlas.get('processes')) or (conta(panorama['proc']) if panorama else 0) or 'NA'} processos",
         onde="Squad 1/Dados brutos/ANM - SIGMINE · pacote data/atlas/processes.json",
         mede="Polígono e atributos de cada processo minerário: fase, substância, titular, município e área.",
         nao_mede="Limite cadastral: as geometrias do atlas são simplificadas para o mapa.",
         readme="data/atlas/README.md")
    base(id="recmin", nome="RECMIN — ocorrências minerais", familia="Mineração", natureza="bruta",
         origem="Serviço Geológico do Brasil (SGB)",
         atualizado_em=commit_date("Squad 1/Dados brutos/SGB - RECMIN"),
         periodo="Baixado em 12/09/2026",
         volume=f"{conta(atlas.get('occurrences')) or 'NA'} ocorrências",
         onde="Squad 1/Dados brutos/SGB - RECMIN · pacote data/atlas/atlas.json",
         mede="Ocorrência mineral com substância, importância e coordenada.",
         nao_mede="Reserva ou recurso: ocorrência é registro geológico, não medida econômica.",
         readme="data/atlas/README.md")

# ---------------------------------------------------------------------------------------------------------- pacotes derivados
if atlas:
    base(id="atlas", nome="Atlas mineral de Goiás", familia="Pacote do painel", natureza="derivada",
         origem="Base consolidada do Squad 1 (v17), gerada por scripts/build_atlas_base.py",
         atualizado_em=atlas.get("meta", {}).get("built_on") or commit_date("data/atlas/atlas.json"),
         periodo="Ver README: cada camada tem período próprio",
         volume=f"{conta(atlas.get('municipalities')) or 'NA'} municípios · {tamanho('data/atlas/atlas.json')} MB",
         onde="data/atlas/atlas.json e processes.json · API /api/atlas",
         mede="Camadas do mapa: CFEM, quantidade comercializada, energia, intensidade, processos, projetos, ocorrências e barragens.",
         nao_mede="Comparação entre camadas: cada uma tem unidade e período próprios.",
         readme="data/atlas/README.md")
if panorama:
    base(id="panorama", nome="Panorama da mineração de Goiás", familia="Pacote do painel", natureza="derivada",
         origem="Base consolidada do Squad 1 e brutos do repositório, por scripts/build_panorama_base.py",
         atualizado_em=panorama.get("meta", {}).get("built_on") or commit_date("data/panorama/panorama.json"),
         periodo="2003 a 2026, conforme a fonte", volume=f"{tamanho('data/panorama/panorama.json')} MB",
         onde="data/panorama/panorama.json · API /api/panorama",
         mede="Gráficos e tabelas do Panorama, filtráveis por ano, mês, município, mineral, titular, fase e ramo.",
         readme="data/panorama/README.md")
if producao:
    m = producao["meta"]
    anos = sorted({r["periodo"][:4] for r in producao["registros"]})
    base(id="producao", nome="Produção por empresa", familia="Produção e energia", natureza="curada",
         origem="Declarações das próprias empresas: RI, relatórios anuais e o que imprensa e agregadores reproduzem deles",
         atualizado_em=m.get("atualizado_em") or m.get("built_on"),
         periodo=f"{anos[0]} a {anos[-1]}",
         volume=f"{len(producao['registros'])} registros de "
                f"{len({r['empresa'] for r in producao['registros']})} empresas",
         onde="producao/base_curada.json → data/producao/producao.json e .csv",
         mede="Um número de produção publicado por uma fonte, com medida, escopo, período, fonte e confiança.",
         nao_mede="Produção auditada: nenhuma linha foi conferida no documento de origem; todas nascem nao_validado.",
         readme="data/producao/README.md")
if empresas:
    anos = sorted({l["ano"] for l in empresas["linhas"]})
    base(id="empresas", nome="Empresas: produção, energia e coeficiente", familia="Produção e energia", natureza="derivada",
         origem="Cruzamento da base de produção com as parcelas de carga da CCEE, ligadas pelo CNPJ raiz",
         atualizado_em=empresas["meta"].get("built_on"),
         periodo=f"{anos[0]} a {anos[-1]}",
         volume=f"{len(empresas['linhas'])} linhas de "
                f"{len({l['empresa'] for l in empresas['linhas']})} empresas",
         onde="data/empresas/empresas.json · API /api/empresas",
         mede="Produção anualizada, carga de energia anualizada e o coeficiente entre as duas, por empresa, mineral e ano.",
         nao_mede="Intensidade medida na planta: a carga é do agente da CCEE e não inclui autoprodução.",
         readme="data/empresas/README.md")
if projetos:
    base(id="projetos", nome="Projetos minerais de Goiás", familia="Pipeline e mercado", natureza="curada",
         origem="Pesquisa em fontes públicas: RI, documentos regulatórios, órgãos públicos, associações e imprensa",
         atualizado_em=projetos["meta"].get("pesquisa_em"),
         periodo="Retrato da pesquisa; cada projeto traz a data da informação mais recente",
         volume=f"{len(projetos['projetos'])} projetos e {len(projetos['evidencias'])} evidências",
         onde="projetos/base_curada.json → data/projetos/projetos.json e Squad 1/entregas/projetos_minerais_goias.xlsx",
         mede="Projeto nomeado com empresa, mineral, município, fase, maturidade, capacidade, CAPEX, cronograma e evidência.",
         nao_mede="Pipeline cadastral: o universo de processos da ANM está no atlas, não aqui. Campo sem informação é NA.",
         readme="projetos/README.md")
if mercado:
    base(id="mercado", nome="Mercado de minerais críticos", familia="Pipeline e mercado", natureza="curada",
         origem="Fontes públicas: imprensa, resultados divulgados por empresas e estudos setoriais",
         atualizado_em=mercado.get("atualizado_em") or commit_date("public/data/mercado/mercado_v1.json"),
         periodo="Movimentos dos últimos doze meses",
         volume=f"{len(mercado.get('operacoes', []))} operações · {len(mercado.get('transacoes', []))} transações · "
                f"{len(mercado.get('referencias', []))} empresas de referência",
         onde="public/data/mercado/mercado_v1.json",
         mede="Quem produz em Goiás, valor dos ativos negociados e desempenho de mineradoras comparáveis.",
         nao_mede="Recomendação de investimento.", readme=None)
if noticias:
    itens = noticias.get("itens") or noticias.get("items") or []
    base(id="noticias", nome="Notícias do setor mineral", familia="Monitoramento", natureza="coletada",
         origem="Coletor de notícias do repositório, lendo feeds de veículos do setor",
         atualizado_em=commit_date("public/data/noticias/latest.json"),
         periodo="Acervo por mês em public/data/noticias/meses/",
         volume=f"{len(itens)} matérias na última coleta",
         onde="public/data/noticias/latest.json e meses/*.json",
         mede="Matéria do setor com título, veículo, data, substância e marca regional.",
         nao_mede="Preço de mercado: o que a imprensa publica não é cotação.", readme="news/README.md")

base(id="agente_producao", nome="Agente semanal de produção", familia="Monitoramento", natureza="coletada",
     origem="50 feeds configurados em producao/fontes.json: RI, imprensa setorial, Globo/g1, econômica, regional e internacional",
     atualizado_em=commit_date("producao/fontes.json"),
     periodo="Execução semanal, segunda-feira às 02:00",
     volume=f"{len(json.loads((REPO / 'producao' / 'fontes.json').read_text(encoding='utf-8'))['fontes'])} fontes",
     onde="producao/agente.py · banco em /var/lib/minera-goias-producao na VPS",
     mede="Candidatos de produção extraídos do texto, com a frase de evidência, confrontados com a base curada.",
     nao_mede="Nada é promovido sozinho: todo candidato nasce nao_validado.", readme="producao/README.md")

pacote = {
    "meta": {
        "built_on": date.today().isoformat(),
        "versao_base": VERSAO,
        "gerado_por": "scripts/build_catalogo_bases.py",
        "nota": ("Última atualização de pacote gerado vem do built_on que o próprio pacote grava; a de arquivo bruto vem da data do "
                 "último commit que o tocou. Volume e período são contados abrindo o arquivo, não digitados."),
    },
    "bases": bases,
}
SAIDA.parent.mkdir(parents=True, exist_ok=True)
with open(SAIDA, "w", encoding="utf-8", newline="\n") as f:
    json.dump(pacote, f, ensure_ascii=False, indent=1)
    f.write("\n")

familias = {}
for b in bases:
    familias.setdefault(b["familia"], []).append(b["nome"])
print(f"bases catalogadas: {len(bases)}")
for familia, nomes in familias.items():
    print(f"  {familia}: {len(nomes)} — {', '.join(n[:34] for n in nomes)}")
print(f"sem data de atualização: {[b['id'] for b in bases if b['atualizado_em'] in (None, 'NA')] or 'nenhuma'}")
print(f"SALVO: {SAIDA} ({SAIDA.stat().st_size / 1e3:.1f} kB)")

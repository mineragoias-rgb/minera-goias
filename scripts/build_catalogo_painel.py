# -*- coding: utf-8 -*-
"""Catálogo das bases de dados que o sistema usa (data/catalogo/catalogo.json), para a aba Base de dados do painel.

    python scripts/build_catalogo_painel.py

Cada base do repositório entra com nome, ORIGEM e ÚLTIMA ATUALIZAÇÃO — os três campos do cabeçalho pedido —, mais o período coberto, o
volume, onde ela vive, o que ela mede e o que ela deliberadamente não mede.

Nada aqui é digitado à mão: a última atualização de um pacote gerado vem do `built_on` que o próprio pacote grava, e a de um arquivo bruto
vem da data do último commit que o tocou. Volume e período são contados abrindo o arquivo. Assim o catálogo não envelhece sozinho enquanto
as bases mudam — se uma base sumir, a linha some com ela e o teste acusa.
"""
import argparse
import csv
import json
import re
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


def _fronteira_rasa():
    """Commits na borda de um clone raso (git clone --depth / actions/checkout sem fetch-depth: 0)."""
    try:
        caminho = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--git-path", "shallow"],
                                 capture_output=True, text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return set()
    arquivo = Path(caminho) if Path(caminho).is_absolute() else REPO / caminho
    return set(arquivo.read_text().split()) if arquivo.is_file() else set()


FRONTEIRA_RASA = _fronteira_rasa()


def commit_date(caminho):
    """Data do último commit que tocou o arquivo — a única 'última atualização' que não depende de alguém lembrar de digitar.

    Num clone raso, o commit da borda parece ter tocado todos os arquivos que existiam antes dele, e a data sairia errada
    (em 10/11/2026 todas as bases viraram 'atualizadas hoje' no GitHub Actions). Nesse caso o script para em vez de gravar.
    """
    try:
        saida = subprocess.run(["git", "-C", str(REPO), "log", "-1", "--format=%H %cs", "--", str(caminho)],
                               capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return "NA"
    partes = saida.stdout.split()
    if not partes:
        return "NA"
    if partes[0] in FRONTEIRA_RASA:
        raise SystemExit(f"histórico raso: a data de {caminho} não é confiável. Use um clone completo "
                         "(git fetch --unshallow, ou fetch-depth: 0 no actions/checkout).")
    return partes[1]


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
comex = carrega("data/comex/comex.json")
mercado = carrega("public/data/mercado/mercado_v1.json")
noticias = carrega("public/data/noticias/latest.json")

bases = []

# Seções dos READMEs que são instrução para a equipe (como rodar, atualizar, reproduzir), não descrição da base: ficam fora do
# quadro de documentação da aba. O resto do README vai como está escrito, sem resumo nem texto novo.
SECAO_DA_EQUIPE = re.compile(r"como (rodar|atualizar|se reconstr|funciona)|^atualiza|executar|rodar localmente|na vps|reprodu|"
                             r"verifica|o que o gerador faz|próximos passos|pendências|trabalho semanal|^no site|^estrutura|entre squads", re.I)


def documentacao(rel, secao=None, sem=()):
    """O texto do README da base, para o quadro de detalhes. Sem `secao`, vai o README inteiro menos o título, os blocos de
    código e as seções da equipe; com `secao`, só a seção de título que começa com ela. `sem` tira outras seções pelo título."""
    caminho = REPO / rel
    if not caminho.is_file():
        return None
    linhas, em_codigo = [], False
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if linha.lstrip().startswith("```"):
            em_codigo = not em_codigo
            continue
        if not em_codigo and not linha.startswith("Responsável:"):
            linhas.append(linha)
    partes, atual = [("", [])], None
    for linha in linhas:
        if linha.startswith("## "):
            partes.append((linha[3:].strip(), [linha]))
        elif linha.startswith("# ") and len(partes) == 1 and not partes[0][1]:
            continue  # o título do README: o quadro já mostra o nome da base
        else:
            partes[-1][1].append(linha)
    if secao:
        escolhidas = [p for p in partes[1:] if p[0].startswith(secao)]
    else:
        escolhidas = [partes[0]] + [p for p in partes[1:]
                                    if not SECAO_DA_EQUIPE.search(p[0]) and not any(p[0].startswith(x) for x in sem)]
    texto = "\n".join("\n".join(p[1]) for p in escolhidas).strip()
    return re.sub(r"\n{3,}", "\n\n", texto) or None


# O README fica como está no repositório, para a equipe. Para o site, o texto perde só o que é anotação interna:
# frases que mandam rodar script ou teste, e o crédito de squad no meio do texto. Caminhos de arquivo citados como fonte
# (entre crases) ficam, porque dizem de onde o dado veio.
FRASE_DA_EQUIPE = re.compile(r"python scripts/|tests/|Conferido por|Lido por scripts/|rode o gerador|rodar o gerador|"
                             r"para gerar (de novo|a base)|^O script |pode utilizar:$|\bEstudante \d", re.I)
CREDITO = [(re.compile(r"\s*\((?:do |da )?Squad [123]\)"), ""), (re.compile(r":\s*Squad [123]$", re.M), ""), (re.compile(r"\s*\(`eliel\.html`\)"), ""),
           (re.compile(r"\b(d|n|pel)([oa]) Squad [123]\b"), lambda m: {"d": "do", "n": "no", "pel": "pelo"}[m.group(1)] + " projeto"),
           (re.compile(r"\b([oa]) Squad [123]\b"), "o projeto"), (re.compile(r"\bao Squad [123]\b"), "ao projeto"),
           (re.compile(r"\s*/\s*Estudante \d+"), ""), (re.compile(r"\bSquad [123]\b"), "projeto")]


def para_o_site(texto):
    if not texto:
        return texto
    blocos, saida = texto.split("\n\n"), []
    for bloco in blocos:
        tabela_ou_titulo = bloco.lstrip().startswith(("|", "#"))
        if not tabela_ou_titulo:
            # frases inteiras, mesmo quebradas em várias linhas no README
            itens = bloco.split("\n- ") if bloco.lstrip().startswith("- ") else [bloco]
            limpos = []
            for item in itens:
                frases = re.split(r"(?<=[.;])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ`*(])", item)
                mantidas = [f for f in frases if not FRASE_DA_EQUIPE.search(f)]
                if mantidas:
                    limpos.append(" ".join(mantidas))
            bloco = "\n- ".join(limpos)
            if not bloco.strip() or bloco.strip() == "-":
                continue
        bloco = re.sub(r"\s*\(`eliel\.html`\)", "", bloco)  # arquivo com nome de aluno
        partes = re.split(r"(`[^`]*`)", bloco)
        for i in range(0, len(partes), 2):
            for padrao, troca in CREDITO:
                partes[i] = padrao.sub(troca, partes[i])
        saida.append("".join(partes))
    return "\n\n".join(saida).strip() or None


# O que cada base oferece para baixar (aba Base de dados, rota /api/catalogo/baixar/<id>, só com login). Pasta entra com os
# arquivos de dados que tem dentro; código, README e teste ficam de fora. A rota só entrega o que está nesta lista.
FORA_DO_DOWNLOAD = {".py", ".md", ".pyc", ".sh", ".ipynb"}
FORMATOS = {"csv", "json", "geojson", "xlsx", "ods", "zip", "html"}  # o que o cartão anuncia; o leia-me da fonte vai junto sem ser anunciado


def arquivos_para_baixar(caminhos):
    arquivos = []
    for rel in caminhos or ():
        caminho = REPO / rel
        if caminho.is_file():
            arquivos.append(caminho)
        elif caminho.is_dir():
            arquivos += sorted(p for p in caminho.rglob("*") if p.is_file() and p.suffix.lower() not in FORA_DO_DOWNLOAD
                               and not p.name.startswith(("test_", ".")))
    if not arquivos:
        return None
    return {"arquivos": [p.relative_to(REPO).as_posix() for p in arquivos],
            "tamanho_mb": round(sum(p.stat().st_size for p in arquivos) / 1e6, 1),
            "formatos": sorted({p.suffix.lower().lstrip(".") for p in arquivos} & FORMATOS)}


def base(**kw):
    kw.setdefault("periodo", "NA")
    kw.setdefault("volume", "NA")
    kw.setdefault("nao_mede", "NA")
    kw.setdefault("readme", None)
    secao, sem = kw.pop("secao", None), kw.pop("sem", ())
    kw["doc"] = para_o_site(documentacao(kw["readme"], secao, sem)) if kw["readme"] else None
    kw["download"] = arquivos_para_baixar(kw.pop("baixar", None))
    bases.append(kw)


# ------------------------------------------------------------------------------------------------- bases de origem (dados brutos)
if panorama:
    p = panorama["meta"]["periods"]
    base(id="ccee", baixar=['Squad 1/dados/CCEE'], nome="CCEE — parcelas de carga em Goiás", familia="Energia", natureza="bruta",
         origem="Câmara de Comercialização de Energia Elétrica (CCEE)",
         atualizado_em=commit_date("Squad 1/dados/CCEE"),
         periodo=f"{p['ccee'][0]} a {p['ccee'][1]}", volume=f"{len(panorama['ccee']['rows'])} linhas agregadas",
         onde="Squad 1/dados/CCEE/*.csv · servida pelo pacote data/panorama/panorama.json",
         mede="Uma parcela de carga de um agente, em um mês, município e ramo de atividade, em MWh.",
         nao_mede="Consumo da mineração: a base mistura 16 ramos de atividade e o recorte mineral confiável exige critério revisado.",
         readme="data/panorama/README.md")
    base(id="cfem", baixar=['Squad 1/Dados brutos/ANM - CFEM'], nome="CFEM — arrecadação por processo e substância", familia="Mineração", natureza="bruta",
         origem="Agência Nacional de Mineração (ANM), via base consolidada do projeto",
         atualizado_em=commit_date("Squad 1/Dados brutos/ANM - CFEM"),
         periodo=f"{p['cfem'][0]} a {p['cfem'][1]}", volume=f"{len(panorama['cfem']['rows'])} linhas agregadas",
         onde="Squad 1/Dados brutos/ANM - CFEM · pacote data/panorama/panorama.json",
         mede="Recolhimento de CFEM por processo, substância, município e mês, em R$, e a quantidade comercializada declarada.",
         nao_mede="Produção: a quantidade é a comercializada declarada para fins de arrecadação.",
         readme="data/panorama/README.md")
    base(id="amb", baixar=['Squad 1/Dados brutos/ANM - Anuário Mineral Brasileiro (AMB)'], nome="Anuário Mineral Brasileiro (AMB)", familia="Mineração", natureza="bruta",
         origem="Agência Nacional de Mineração (ANM)",
         atualizado_em=commit_date("Squad 1/Dados brutos/ANM - Anuário Mineral Brasileiro (AMB)"),
         periodo=f"{p['amb'][0]} a {p['amb'][1]}", volume=f"{len(panorama['amb_go']['rows'])} linhas de Goiás",
         onde="Squad 1/Dados brutos/ANM - Anuário Mineral Brasileiro (AMB)/*.csv",
         mede="Produção bruta e beneficiada por UF e substância, com o contido declarado e sua unidade.",
         nao_mede="Produção por empresa: o Anuário é por estado e substância, sem titular.",
         readme="data/panorama/README.md")
    base(id="investimento", baixar=['Squad 1/Dados brutos/ANM - Investimento em pesquisa mineral'], nome="Investimento em pesquisa mineral", familia="Mineração", natureza="bruta",
         origem="Agência Nacional de Mineração (ANM)",
         atualizado_em=commit_date("Squad 1/Dados brutos/ANM - Investimento em pesquisa mineral"),
         periodo=f"{p['inv'][0]} a {p['inv'][1]}", volume=f"{len(panorama['inv_go']['rows'])} linhas de Goiás",
         onde="Squad 1/Dados brutos/ANM - Investimento em pesquisa mineral/",
         mede="Gasto declarado em pesquisa mineral por ano, substância e rubrica.",
         readme="data/panorama/README.md")
    base(id="rodadas", baixar=['Squad 1/dados/ResultadoRodadaDisponibilidade (1).csv'], nome="Rodadas de disponibilidade de áreas", familia="Mineração", natureza="bruta",
         origem="Agência Nacional de Mineração (ANM)",
         atualizado_em=commit_date("Squad 1/dados"), periodo="Rodadas 1 a 8",
         volume=f"{len(panorama['rod']['rows'])} áreas em Goiás",
         onde="Squad 1/dados/ResultadoRodadaDisponibilidade*.csv",
         mede="Área oferecida em rodada, com situação, modalidade, município, lance e arrematante.",
         readme="data/panorama/README.md")
if atlas:
    base(id="sigmine", baixar=['Squad 1/Dados brutos/ANM - SIGMINE'], nome="Cadastro mineiro / SIGMINE — processos", familia="Mineração", natureza="bruta",
         origem="Agência Nacional de Mineração (ANM), shapefile do SIGMINE",
         atualizado_em=commit_date("Squad 1/Dados brutos/ANM - SIGMINE"),
         periodo="Extração de 24/10/2026",
         volume=f"{conta(atlas.get('processes')) or (conta(panorama['proc']) if panorama else 0) or 'NA'} processos",
         onde="Squad 1/Dados brutos/ANM - SIGMINE · pacote data/atlas/processes.json",
         mede="Polígono e atributos de cada processo minerário: fase, substância, titular, município e área.",
         nao_mede="Limite cadastral: as geometrias do atlas são simplificadas para o mapa.",
         readme="data/atlas/README.md")
    base(id="recmin", baixar=['Squad 1/Dados brutos/SGB - RECMIN'], nome="RECMIN — ocorrências minerais", familia="Mineração", natureza="bruta",
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
    base(id="atlas", baixar=['data/atlas'], nome="Atlas mineral de Goiás", familia="Pacote do painel", natureza="derivada",
         origem="Base consolidada do projeto (v19)",
         atualizado_em=atlas.get("meta", {}).get("built_on") or commit_date("data/atlas/atlas.json"),
         periodo="Ver README: cada camada tem período próprio",
         volume=f"{conta(atlas.get('municipalities')) or 'NA'} municípios · {tamanho('data/atlas/atlas.json')} MB",
         onde="data/atlas/atlas.json e processes.json · API /api/atlas",
         mede="Camadas do mapa: CFEM, quantidade comercializada, energia, intensidade, processos, projetos, ocorrências e barragens.",
         nao_mede="Comparação entre camadas: cada uma tem unidade e período próprios.",
         readme="data/atlas/README.md")
if panorama:
    base(id="panorama", baixar=['data/panorama'], nome="Panorama da mineração de Goiás", familia="Pacote do painel", natureza="derivada",
         origem="Base consolidada do projeto e dados brutos das fontes",
         atualizado_em=panorama.get("meta", {}).get("built_on") or commit_date("data/panorama/panorama.json"),
         periodo="2003 a 2026, conforme a fonte", volume=f"{tamanho('data/panorama/panorama.json')} MB",
         onde="data/panorama/panorama.json · API /api/panorama",
         mede="Gráficos e tabelas do Panorama, filtráveis por ano, mês, município, mineral, titular, fase e ramo.",
         readme="data/panorama/README.md")
if producao:
    m = producao["meta"]
    anos = sorted({r["periodo"][:4] for r in producao["registros"]})
    base(id="producao", baixar=['data/producao'], nome="Produção por empresa", familia="Produção e energia", natureza="curada",
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
    base(id="empresas", baixar=['data/empresas/empresas.json'], nome="Empresas: produção, energia e coeficiente", familia="Produção e energia", natureza="derivada",
         origem="Cruzamento da base de produção com as parcelas de carga da CCEE, ligadas pelo CNPJ raiz",
         atualizado_em=empresas["meta"].get("built_on"),
         periodo=f"{anos[0]} a {anos[-1]}",
         volume=f"{len(empresas['linhas'])} linhas de "
                f"{len({l['empresa'] for l in empresas['linhas']})} empresas",
         onde="data/empresas/empresas.json · API /api/empresas",
         mede="Produção anualizada, carga de energia anualizada e o coeficiente entre as duas, por empresa, mineral e ano.",
         nao_mede="Intensidade medida na planta: a carga é do agente da CCEE e não inclui autoprodução.",
         readme="data/empresas/README.md", sem=("Atlas Empresarial", "Mapa das empresas"))
if projetos:
    base(id="projetos", baixar=['data/projetos/projetos.json', 'Squad 1/entregas/projetos_minerais_goias.xlsx'], nome="Projetos minerais de Goiás", familia="Pipeline e mercado", natureza="curada",
         origem="Pesquisa em fontes públicas: RI, documentos regulatórios, órgãos públicos, associações e imprensa",
         atualizado_em=projetos["meta"].get("pesquisa_em"),
         periodo="Retrato da pesquisa; cada projeto traz a data da informação mais recente",
         volume=f"{len(projetos['projetos'])} projetos e {len(projetos['evidencias'])} evidências",
         onde="projetos/base_curada.json → data/projetos/projetos.json e Squad 1/entregas/projetos_minerais_goias.xlsx",
         mede="Projeto nomeado com empresa, mineral, município, fase, maturidade, capacidade, CAPEX, cronograma e evidência.",
         nao_mede="Pipeline cadastral: o universo de processos da ANM está no atlas, não aqui. Campo sem informação é NA.",
         readme="projetos/README.md")
if comex:
    mt = comex["meta"]
    anos = sorted({l["ano"] for l in comex["anual"]})
    base(id="comex_fonte", baixar=['comex/bruto'], nome="Comex Stat — despacho aduaneiro de Goiás", familia="Comércio exterior",
         natureza="coletada",
         origem=mt["fonte"]["nome"] + " — " + mt["fonte"]["portal"],
         atualizado_em=mt["coleta"]["atualizacao_declarada_pela_api"],
         periodo=f"{anos[0]} a {mt['publicado_ate']['ano']}/{mt['publicado_ate']['mes']:02d}",
         volume=f"{len(comex['serie'])} linhas mensais de {len(comex['minerais'])} minerais",
         onde="comex/bruto/*.json, baixado por comex/coleta.py",
         mede="Valor FOB em dólares e peso líquido em quilos, por NCM e por mês, com Goiás como UF da operação.",
         nao_mede="Produção: um embarque pode sair meses depois da lavra, e o peso é do produto, não do metal contido.",
         readme="data/comex/README.md")
    base(id="comex", baixar=['data/comex'], nome="Comércio exterior dos minerais de Goiás", familia="Comércio exterior",
         natureza="derivada",
         origem="Comex Stat ligado ao vocabulário mineral do projeto por comex/base_curada.json",
         atualizado_em=mt.get("built_on"),
         periodo=f"{anos[0]} a {mt['publicado_ate']['ano']}/{mt['publicado_ate']['mes']:02d}",
         volume=f"{len(comex['anual'])} linhas anuais · {len(comex['destinos'])} destinos · "
                f"{len(comex['municipios'])} linhas de município",
         onde="data/comex/comex.json e .csv · API /api/comex",
         mede="Exportação e importação por mineral, ano e mês, com país de destino e município de origem por capítulo da NCM.",
         nao_mede="Classificação federal de mineral crítico: o texto oficial não pôde ser lido, e a base marca NA em vez de atribuí-la.",
         readme="data/comex/README.md")
if mercado:
    base(id="mercado", baixar=['public/data/mercado/mercado_v1.json'], nome="Mercado de minerais críticos", familia="Pipeline e mercado", natureza="curada",
         origem="Fontes públicas: imprensa, resultados divulgados por empresas e estudos setoriais",
         atualizado_em=mercado.get("atualizado_em") or commit_date("public/data/mercado/mercado_v1.json"),
         periodo="Movimentos dos últimos doze meses",
         volume=f"{len(mercado.get('operacoes', []))} operações · {len(mercado.get('transacoes', []))} transações · "
                f"{len(mercado.get('referencias', []))} empresas de referência",
         onde="public/data/mercado/mercado_v1.json",
         mede="Quem produz em Goiás, valor dos ativos negociados e desempenho de mineradoras comparáveis.",
         nao_mede="Recomendação de investimento.", readme="public/data/mercado/README.md", secao="Leitura de mercado")
if noticias:
    itens = noticias.get("itens") or noticias.get("items") or []
    base(id="noticias", baixar=['public/data/noticias'], nome="Notícias do setor mineral", familia="Monitoramento", natureza="coletada",
         origem="Coletor de notícias do projeto, lendo feeds de veículos do setor",
         atualizado_em=commit_date("public/data/noticias/latest.json"),
         periodo="Acervo por mês",
         volume=f"{len(itens)} matérias na última coleta",
         onde="public/data/noticias/latest.json e meses/*.json",
         mede="Matéria do setor com título, veículo, data, substância e marca regional.",
         nao_mede="Preço de mercado: o que a imprensa publica não é cotação.", readme="news/README.md")

base(id="agente_producao", nome="Agente semanal de produção", familia="Monitoramento", natureza="coletada",
     origem="50 feeds: RI, imprensa setorial, Globo/g1, econômica, regional e internacional",
     atualizado_em=commit_date("producao/fontes.json"),
     periodo="Execução semanal, segunda-feira às 02:00",
     volume=f"{len(json.loads((REPO / 'producao' / 'fontes.json').read_text(encoding='utf-8'))['fontes'])} fontes",
     onde="producao/agente.py · banco em /var/lib/minera-goias-producao na VPS",
     mede="Candidatos de produção extraídos do texto, com a frase de evidência, confrontados com a base curada.",
     nao_mede="Nada é promovido sozinho: todo candidato nasce nao_validado.", readme="producao/README.md")

# ------------------------------------------------------------------------------------- bases que o painel usa e faltavam (26/11/2026)
carteira = carrega("public/data/mercado/projetos_go_v1.json")
if carteira:
    base(id="carteira_mercado", baixar=['public/data/mercado/projetos_go_v1.json'], nome="Carteira de projetos do Mercado", familia="Pipeline e mercado", natureza="curada",
         origem="Levantamento em relatórios corporativos, órgãos públicos e imprensa",
         atualizado_em=carteira["meta"]["consultado_ate"],
         periodo=f"Consulta até {carteira['meta']['consultado_ate']}",
         volume=f"{len(carteira['projetos'])} projetos e {len(carteira['noticias'])} notícias",
         onde="public/data/mercado/projetos_go_v1.json",
         mede="Carteira de projetos em Goiás, da pesquisa inicial à operação, classificada pela maturidade.",
         readme="public/data/mercado/README.md", secao="Carteira de projetos")

atlas_emp = carrega("data/empresas/atlas_empresas.json")
if atlas_emp:
    base(id="atlas_empresas", baixar=['data/empresas/atlas_empresas.json'], nome="Atlas empresarial", familia="Produção e energia", natureza="derivada",
         origem="SIGMINE, Cadastro Mineiro e CFEM (ANM), base de produção, carga da CCEE e radar de notícias",
         atualizado_em=atlas_emp["meta"].get("built_on") or commit_date("data/empresas/atlas_empresas.json"),
         volume=f"{len(atlas_emp['empresas'])} empresas · {len(atlas_emp['processos'])} processos",
         onde="data/empresas/atlas_empresas.json · API /api/empresas/atlas",
         mede="Uma linha por CNPJ raiz de titular com processo, CFEM ou carga da CCEE em Goiás, com processos, CFEM, projetos e notícias.",
         readme="data/empresas/README.md", secao="Atlas Empresarial")

mapa_emp = carrega("data/empresas/mapa_empresas.json")
if mapa_emp:
    base(id="mapa_empresas", baixar=['data/empresas/mapa_empresas.json'], nome="Mapa das empresas", familia="Produção e energia", natureza="derivada",
         origem="SIGMINE, CFEM e Cadastro Mineiro (ANM), carga da CCEE e radar de notícias",
         atualizado_em=mapa_emp["meta"].get("built_on") or commit_date("data/empresas/mapa_empresas.json"),
         volume=f"{len(mapa_emp['empresas'])} empresas · {len(mapa_emp['processos'])} processos",
         onde="data/empresas/mapa_empresas.json · API /api/empresas/mapa",
         mede=mapa_emp["meta"]["nota"].split(". ")[0] + ".",
         readme="data/empresas/README.md", secao="Mapa das empresas")

mapa_cat = carrega("data/mapa/catalogo.json")
if mapa_cat:
    base(id="mapa_camadas", baixar=['data/mapa'], nome="Camadas do Mapa mineral", familia="Pacote do painel", natureza="derivada",
         origem="Camadas do P3M (SGB), MapBiomas Coleção 11 e camadas do Atlas, recortadas para Goiás",
         atualizado_em=commit_date("data/mapa"),
         periodo="Cada camada tem data própria (ver documentação)",
         volume=f"{len(mapa_cat['camadas'])} camadas em {len(mapa_cat['grupos'])} grupos",
         onde="data/mapa/ · API /api/mapa",
         mede="Onde estão as feições de cada camada (pontos, linhas e polígonos) e seus atributos, com indicadores por município.",
         readme="data/mapa/README.md")

indicadores = carrega("data/indicadores/indicadores_municipais.json")
if indicadores:
    mi = indicadores["meta"]
    base(id="indicadores", baixar=['data/indicadores/indicadores_municipais.json'], nome="Indicadores municipais de mineração", familia="Pacote do painel", natureza="derivada",
         origem="ANM (CFEM, Cadastro Mineiro e rodadas) e IBGE",
         atualizado_em=commit_date("data/indicadores/indicadores_municipais.json"),
         periodo=f"Ano-base {mi['ano']}",
         volume=f"{mi['n_municipios']} municípios · {len(indicadores['indicadores'])} indicadores",
         onde="data/indicadores/indicadores_municipais.json · API /api/indicadores",
         mede="Indicadores de mineração por município de Goiás, usados no Ranking por Indicador.",
         readme="data/indicadores/README.md")

previsao = carrega("public/data/previsao/previsao_v1.json")
if previsao:
    base(id="previsao", baixar=['public/data/previsao', 'public/data/simulador'], nome="Previsão de demanda de energia da mineração", familia="Produção e energia", natureza="derivada",
         origem="Modelo econômico-energético do projeto, sobre a produção da ANM e a carga da CCEE",
         atualizado_em=previsao["data_versao"],
         periodo=f"Base {previsao['ano_base']}, projeção {previsao['horizonte']['inicio']} a {previsao['horizonte']['fim']}",
         volume=f"{len(previsao['minerais'])} minerais · {len(previsao['cenarios'])} cenários",
         onde="public/data/previsao/ e public/data/simulador/",
         mede="Energia projetada (MWh/TWh) por mineral e no total, nos cenários conservador, referência e expansão, com faixa baixa–alta.",
         nao_mede="Nióbio e outras substâncias: ficam de fora por falta de dados conciliáveis.",
         readme="Squad 2/modello_reale/README.md")

if (REPO / "Squad 2" / "intensidade_energetica" / "README.md").is_file():
    base(id="intensidade", baixar=['Squad 2/intensidade_energetica'], nome="Intensidade energética do setor mineral", familia="Produção e energia", natureza="derivada",
         origem="Carga da CCEE dividida pela produção da mesma entidade; referência externa quando não há carga",
         atualizado_em=commit_date("Squad 2/intensidade_energetica"),
         onde="Squad 2/intensidade_energetica/",
         mede="Energia por tonelada de cada mineral, usada pela Previsão de demanda.",
         readme="Squad 2/intensidade_energetica/README.md")

risco = carrega("Squad 2/mineracao_cerrado/GO_radar_risco_ambiental.geojson")
if risco:
    base(id="territorio", baixar=['Squad 2/mineracao_cerrado/GO_radar_risco_ambiental.geojson', 'Squad 2/mineracao_cerrado/relatorio_mineracao_cerrado_GO.html'], nome="Mineração e Cerrado em Goiás", familia="Território e emissões", natureza="derivada",
         origem="MapBiomas, SEEG, ANM, P3M (SGB) e Radar de Projetos",
         atualizado_em=commit_date("Squad 2/mineracao_cerrado"),
         periodo="1985 a 2025, com cenários até 2040",
         volume=f"{len(risco['features'])} projetos com risco ambiental",
         onde="Squad 2/mineracao_cerrado/ · API /api/territorio",
         mede="Área minerada e o uso anterior de cada pixel que vira mina; emissões de biomassa e de solo; efeito no entorno; impacto potencial de projetos novos.",
         nao_mede="Consumo de energia: mede impacto territorial e fica separado da Previsão de demanda.",
         readme="Squad 2/mineracao_cerrado/LEIA-ME.md")

pacote = {
    "meta": {
        "built_on": date.today().isoformat(),
        "versao_base": VERSAO,
        "gerado_por": "scripts/build_catalogo_painel.py",
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

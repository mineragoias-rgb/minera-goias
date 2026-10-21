# Radar de Projetos — projetos minerais de Goiás

Base consolidada dos projetos minerais de Goiás, da operação ao sinal inicial de investimento, para inteligência de mercado, análise de
investimentos e acompanhamento do pipeline mineral do estado. Completa a camada ANM do Radar de Projetos que a base consolidada do Squad 1
já traz na aba `04_dim_projetos` da v17, e substitui o levantamento inicial do aluno Lucas Maia
(`../Dados brutos/Aluno Lucas Maia/projetos_minerais_goias.xlsx`, 15 projetos, que continua publicado na aba Mercado do site).

| Arquivo | O que é |
|---|---|
| `projetos_minerais_goias.xlsx` | A entrega: abas **PROJETOS** (31 colunas), **NOTÍCIAS** (16 colunas, ligadas pelo ID do projeto) e **METODOLOGIA** |
| `curadoria_web.json` | A pesquisa na web, editável: projetos (com campos internos `_` de deduplicação) e as fontes de cada um |

Gerar de novo (precisa de `openpyxl` e `pyshp`):

    python scripts/build_projetos_minerais_goias.py            # escreve a planilha
    python scripts/build_projetos_minerais_goias.py --checar   # só controle de qualidade e contagens
    python -m unittest discover -s tests -p test_radar_projetos.py -v

## Versão de 21/10/2026

1.040 projetos e 1.328 notícias/evidências, em 177 municípios, por maturidade: 88 em operação, 2 em expansão, 192 prováveis, 253 possíveis
e 505 sinais (nenhum projeto de Goiás tinha, nas fontes, construção iniciada ou viabilidade concluída com decisão de investimento).

| Origem das linhas | Linhas | O que entra |
|---|---:|---|
| Pesquisa na web (`curadoria_web.json`) | 37 | Projetos com notícia, documento da empresa, de governo ou regulatório — 100 fontes. Únicos com capacidade, CAPEX e cronograma |
| Operações com CFEM em 2025 (ANM) | 71 | Titular PJ que recolheu CFEM; agregados para construção só a partir de R$ 300 mil; água mineral fora |
| Carteira ANM (aba 04 da v17) | 678 | Projetos que ainda não produzem, com a classificação do Squad 1 (teto PROVÁVEL); pessoa física agregada por mineral e município |
| Portfólios de pesquisa (Cadastro Mineiro) | 254 | Titular PJ com 5+ títulos de pesquisa de um mineral crítico ou estratégico (SINAL) |

Registros da ANM do mesmo empreendimento de um projeto pesquisado (mesmo processo, ou mesmo titular, mineral e município) não viram linha
nova: entram como evidência dele na aba NOTÍCIAS (44 registros absorvidos).

## Cuidados

- **Nenhum documento foi aberto um a um.** O ambiente de coleta bloqueia o acesso direto aos sites; as fontes foram localizadas e lidas
  pelo buscador. Números de capacidade, produção e CAPEX não foram conferidos no PDF de origem.
- **Nada é estimado.** O que a fonte não traz é `NA`. Valor de aquisição, financiamento e anúncio político de investimento não são CAPEX.
- **Pessoa física sem nome.** Empresário individual e espólio aparecem como "Titular individual (nome não publicado)"; os projetos de
  pessoa física da aba 04 entram agregados por mineral e município, sem nome. Nenhum CPF é publicado.
- **Título de pesquisa não é depósito.** Os portfólios são sinal de interesse, não de projeto econômico.
- **IDs** (`GO-0001`) valem para esta versão; uma nova coleta da ANM pode renumerar as linhas derivadas.

Critérios completos (inclusão, exclusão, maturidade, deduplicação, CAPEX, capacidade, previsão, confiança, conflitos e limitações) na aba
METODOLOGIA da planilha.

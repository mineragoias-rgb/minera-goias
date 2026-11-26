# Mercado de minerais críticos

Os dois arquivos da aba **Mercado** do painel: a leitura do mercado de minerais críticos em torno de Goiás, montada com fontes públicas,
e a carteira de projetos minerais do estado. A aba lê os dois direto do navegador (`public/mercado.js`).

| Arquivo | Conteúdo |
|---|---|
| `mercado_v1.json` | Leitura de mercado: 4 indicadores, 6 operações, 3 transações, preço de referência, 4 mineradoras de referência, 3 normas, 6 notícias, 5 oportunidades, 5 riscos e as 9 fontes com link |
| `projetos_go_v1.json` | Carteira de 15 projetos minerais de Goiás, com 5 notícias ligadas aos projetos e a metodologia do levantamento (14 itens) |

## Leitura de mercado (`mercado_v1.json`)

Montada com imprensa especializada, resultados divulgados por empresas de capital aberto e estudos setoriais. **Não vem da base
consolidada do projeto**: serve para contextualizar o que os dados da ANM e da CCEE mostram, não para substituí-los. Os valores
financeiros são os últimos publicados até setembro de 2026 (`atualizado_em`: 2026-09-17) e podem já ter sido revisados.

Não tem gerador: o arquivo é a própria curadoria, editado à mão.

| Seção | O que traz |
|---|---|
| `indicadores` | Os 4 números do topo da aba (empresas com pesquisa mineral ativa, área sob requerimento na ANM, fatia de Goiás no PIB da cadeia até 2050, CFEM de terras raras na arrecadação do estado), cada um com rótulo e detalhe |
| `operacoes` | Operações em Goiás: mineral, local, situação e nota |
| `transacoes` | Ativos negociados: ativo, comprador, ano e valor em milhões de dólares |
| `preco_referencia` | Série de preço de referência, com rótulo e nota |
| `referencias` | Mineradoras de referência no mundo: empresa, praça (bolsa), mineral, onde opera, receita e resultado |
| `regulacao` | Normas e marcos: sigla, nome e descrição |
| `noticias` | Notícias com data (ano e mês), título, resumo, fonte e link |
| `oportunidades` e `riscos` | Listas de texto |
| `fontes` | As 9 fontes usadas, cada uma com nome e link |

### Regras que o arquivo não quebra

- **Nada é recalculado.** Cada valor fica na moeda e no período em que foi divulgado, sem conversão; por isso os valores não se somam entre si.
- **Linguagem especulativa não vira número**: não vira capacidade nem CAPEX.
- **Todo texto vem em português e inglês**, e todo link é `https`.
- **Toda transação tem um número comparável** (`valor_usd_milhoes`), para as barras da aba terem a mesma escala.

### Quem mais usa

O gerador do Comércio exterior (`scripts/build_comex_base.py`) lê as `operacoes` deste arquivo para conferir se a curadoria do Comércio
exterior continua presa às outras bases, e o catálogo do painel (`scripts/build_catalogo_painel.py`) lê a data de atualização.

### Como atualizar

1. Editar `mercado_v1.json`, mantendo os dois idiomas e o link de cada fonte, e mudar `atualizado_em`.
2. Rodar `python -m unittest discover -s tests -p test_mercado.py`.
3. Rodar `python scripts/build_catalogo_painel.py`, para o catálogo do painel registrar a nova data.

## Carteira de projetos (`projetos_go_v1.json`)

Projetos minerais de Goiás, da pesquisa inicial à operação, levantados em relatórios corporativos, órgãos públicos e imprensa. Gerada por
`python scripts/build_projetos_go.py` a partir da planilha do levantamento, versionada em `Squad 1/Dados brutos/`, com consulta até
04/10/2026. O pacote guarda o `sha256` da planilha de origem.

O gerador publica as três abas da planilha (PROJETOS, NOTÍCIAS e METODOLOGIA) **sem reescrever nada**: o texto de cada célula sai como está,
e `NA` vira ausência (`null`), que é o que a própria metodologia diz que `NA` significa.

| Parte | O que traz |
|---|---|
| `meta` | Origem, `sha256` da planilha, data da consulta, as 7 maturidades, os 3 graus de confiança e o gerador |
| `metodologia` | Os 14 itens da metodologia do levantamento |
| `projetos` | Os 15 projetos, com empresa, controladora, parceiros, mineral, município, fase, maturidade, estágio, status, capacidade, produção, CAPEX, ano previsto, datas, confiança, evidência, fonte e links |
| `noticias` | As 5 notícias, cada uma ligada a um projeto da carteira |

### As maturidades e a confiança

Sete maturidades, nesta hierarquia: **OPERAÇÃO > EXPANSÃO > CONSTRUÇÃO > DEFINIDO > PROVÁVEL > POSSÍVEL > SINAL**. Confiança em três graus:
**ALTO** (fontes primárias ou regulatórias), **MÉDIO** (imprensa confiável) e **BAIXO** (indícios difusos).

### Regras que o gerador não deixa quebrar

O gerador **recusa** a planilha quando ela sai do próprio vocabulário: ID fora do padrão `GO-000` ou repetido, maturidade fora das sete
etiquetas, confiança fora de ALTO/MÉDIO/BAIXO, data que não é AAAA-MM-DD, projeto fora de Goiás, notícia que aponta para projeto inexistente,
ou "Previsão de entrada" diferente de "Ano previsto".

- **Capacidade e produção ficam em texto**, com a unidade original (t/ano, oz/ano, t/ano de TREO…): unidades diferentes não se somam nem
  viram barra na mesma escala.
- **O CAPEX sai em número** só porque a planilha declara a moeda e o ano de cada valor. Valores de anos diferentes continuam não somáveis,
  e a aba não os soma.

### Metodologia do levantamento

Os 14 itens estão no próprio pacote (`metodologia`): objetivo, abrangência, período da pesquisa, fontes, critérios de inclusão, critérios
de exclusão, critérios de maturidade, regras de deduplicação, regras de tratamento de CAPEX, regras de capacidade, regras para previsão de
entrada, critérios de confiança, significado de NA e limitações da pesquisa. Dois deles, nas palavras da planilha:

- **Significado de NA:** "Not Available" (não disponível); indica ausência da informação, sem extrapolação.
- **Limitações da pesquisa:** o cenário de empresas júnior pode mudar com rapidez; o mapeamento reflete só o que as exploradoras declararam
  publicamente.

### Relação com a base de projetos do catálogo

Esta carteira (15 projetos) **não é** a base "Projetos minerais de Goiás" de `projetos/` (37 projetos): são levantamentos diferentes, em
arquivos diferentes.

### Como atualizar

1. Trocar a planilha do levantamento em `Squad 1/Dados brutos/`.
2. Rodar `python scripts/build_projetos_go.py`. Ele recusa a planilha que quebre as regras acima.
3. Rodar `python -m unittest discover -s tests -p test_mercado.py`.

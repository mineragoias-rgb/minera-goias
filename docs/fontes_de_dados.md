# Fontes de dados do Minera Goiás

Levantamento de 23/10/2026: todas as bases que o site usa, de onde vêm, como se baixam e o que falta para um robô atualizá-las.
A tabela completa, uma linha por fonte, está em [`fontes_de_dados.csv`](fontes_de_dados.csv) (`;`, UTF-8), pensada para o robô ler.

Os links vêm do que o repositório já registra (aba `07_dim_fontes` da base consolidada v17, `Squad 1/Dados brutos/LEIA-ME.md`,
`Squad 1/P3M/inventario_p3m.csv`, `Squad 1/dados/CCEE/Read.me` e os geradores em `scripts/`). **Não foram testados hoje**: a rede do
ambiente onde o levantamento foi feito não alcança os portais do governo. Antes de automatizar, cada URL precisa de um teste. A ANM
anunciou em 05/02/2026 que trocou os links dos seus dados abertos, então as URLs de `dadosabertos.anm.gov.br` merecem atenção especial.

## Como os dados chegam ao site

```
fontes externas ──► Squad 1/Dados brutos, Squad 1/dados, Squad 1/P3M      (cópia do arquivo baixado, sem correção)
                       │
                       ├─► base consolidada v17 (Squad 1/Bases consolidadas, rodar_pipeline.py) ─► Atlas, Panorama, Mapa, Radar, Simulador
                       ├─► inventário do P3M ─► Mapa mineral
                       └─► CCEE, rodadas, investimento ─► Panorama, Empresas, Squad 2
curadoria da equipe ──► Radar de Projetos, Mercado, Empresas (produção), parâmetros do Squad 2
robôs que já existem ──► notícias (todo dia) e agente de produção (toda segunda)
```

Depois que um arquivo bruto muda na `main`, o workflow `atualizar-derivados.yml` já refaz e publica sozinho tudo o que sai dele:
inventário do P3M, Mapa, pacote do Squad 2, Panorama, Produção, Empresas, intensidade energética, carteira do Mercado e Simulador.
**O que falta automatizar é o primeiro passo** (baixar da fonte) e duas etapas que ainda rodam fora da cadeia: a base consolidada
(`rodar_pipeline.py`, que gera a v17) e o Atlas (`build_atlas_base.py`, que precisa do GeoPackage gerado pelo pipeline).

## Por aba do site

| Aba | Fontes |
|---|---|
| Atlas e panorama | ANM (AMB, CFEM, Cadastro Mineiro, SIGMINE, investimento em pesquisa, rodadas, SIGBM), IBGE (malha, população, PIB), SGB (RECMIN), CCEE |
| Mapa mineral | P3M/SGB (39 camadas), limite estadual do IBGE, e pelo Atlas: municípios, processos (SIGMINE), barragens (SIGBM), projetos ANM, ocorrências (RECMIN) |
| Mercado | leitura de mercado da equipe, carteira de projetos do Lucas Maia, produção declarada pelas empresas |
| Empresas | produção declarada pelas empresas + CCEE |
| Radar | Radar de Projetos (curadoria na web + CFEM, carteira ANM e Cadastro Mineiro) e notícias (22 feeds) |
| Simulador | modelo do Squad 2 (AMB pela base consolidada, CCEE, parâmetros de cenário) |

## Por facilidade de automatizar

### Prontas para o robô: link direto ou serviço de dados

| Fonte | Download | Observação |
|---|---|---|
| ANM — AMB produção bruta e beneficiada | `https://dadosabertos.anm.gov.br/AMB/Producao_Bruta.csv` e `…/Producao_Beneficiada.csv` | arquivo nacional |
| ANM — CFEM | `https://dadosabertos.anm.gov.br/CFEM/CFEM_Arrecadacao_2022_2026.csv` | o nome muda com a faixa de anos: listar a pasta `CFEM/` e escolher o mais recente; recortar Goiás |
| ANM — Cadastro Mineiro (13 arquivos) | `https://dadosabertos.anm.gov.br/SCM/<arquivo>.csv` | nacional (~72 MB); recortar pela regra de `recorte_goias.json` |
| ANM — SIGMINE Goiás | `https://dadosabertos.anm.gov.br/SIGMINE/PROCESSOS_MINERARIOS/GO.zip` | já vem só Goiás |
| IBGE — malha municipal | `https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2025/UFs/GO/GO_Municipios_2025.zip` | anual: trocar o ano no caminho |
| IBGE — limite de Goiás | `…/municipio_2024/UFs/GO/GO_UF_2024.zip` | pelo padrão do geoftp; conferir |
| IBGE — população e PIB | `https://apisidra.ibge.gov.br/values/t/6579/n6/all/v/9324/p/last` e `…/t/5938/n6/all/v/37/p/last` | API; `p/last` traz o último ano |
| SGB — RECMIN | WFS `geoservicos.sgb.gov.br` (URL completa no CSV) | GeoJSON pela caixa de Goiás |
| SGB — P3M (157 camadas) | uma URL WFS por camada na coluna `url_download` de `Squad 1/P3M/inventario_p3m.csv` | a melhor candidata: URL pronta, catálogo com API e o resto da cadeia já automático |
| ANEEL — SIGA; ONS — linhas e subestações | portais CKAN (`dadosabertos.aneel.gov.br`, `dados.ons.org.br`) | falta registrar a URL do recurso; ainda não usadas pelo site |
| Notícias | `news/feeds.json` | **já automático** (todo dia às 04:00 UTC) |

### Exigem navegador ou um link que ainda não foi registrado

| Fonte | Situação |
|---|---|
| CCEE — parcela de carga e consumo | o servidor de download (`pda-download.ccee.org.br`) recusa `curl`; hoje se baixa à mão e se filtra com `scripts/build_ccee_go.py`. Testar a API CKAN do portal ou um navegador automatizado |
| ANM — investimento em pesquisa (DIPEM) | URL não registrada; procurar o conjunto da ANM em dados.gov.br |
| ANM — rodadas de disponibilidade | URL não registrada; a ANM publica a base de oferta pública e leilão de áreas (SOPLE) |
| ANM — SIGBM (barragens) | o Atlas usa um retrato congelado; o SIGBM Público não tem exportação conhecida. Alternativa automática: a camada de barragens do P3M |
| Energia por município no Atlas | retrato congelado do `eliel.html`; dá para refazer a partir da CCEE |
| EPE — BEN e PDE | publicações anuais ou por edição, com nomes que mudam; ainda não usadas |
| IMB — Goiás em Dados | exportação manual sem parâmetros registrados; só validação |
| SGB — pacotes de geoquímica do GeoSGB | levantamentos encerrados: não mudam |

### Curadoria humana (o robô pode ajudar, não substituir)

Radar de Projetos (`curadoria_web.json`), carteira do Lucas Maia, leitura de mercado (`mercado_v1.json`), produção declarada
(`producao/base_curada.json`, que já tem o agente semanal `producao/agente.py` propondo candidatos) e os parâmetros do Squad 2.
Pela `METODOLOGIA.md`, importar não é validar: aqui o robô sugere e uma pessoa aprova.

## O robô (primeira versão, 23/10/2026)

O P3M e a ANM (Anuário Mineral, CFEM, Cadastro Mineiro e SIGMINE) já são atualizados toda semana pelo robô em [`robo/`](../robo/LEIA-ME.md):
ele baixa, confere a forma contra o arquivo que o site usa, aplica os mesmos recortes de Goiás, refaz a base consolidada, o atlas e
os derivados quando a ANM muda, roda os testes e publica. As demais fontes desta página continuam manuais.

## Sugestão para o robô

1. **Começar pelo P3M e pela ANM.** São as fontes com link direto e as que mais mudam (CFEM e Cadastro Mineiro são diárias). O robô
   baixa, compara o sha256 com o do repositório e só segue quando mudou.
2. **Recortar e gravar no mesmo lugar e formato de hoje** (o LEIA-ME de `Dados brutos` descreve cada recorte), registrar a data em
   `datas_de_acesso.json` e abrir um commit ou PR. A cadeia `atualizar-derivados.yml` faz o resto.
3. **Pôr a base consolidada na cadeia** (`rodar_pipeline.py` → v18), senão um arquivo da ANM novo não chega ao Atlas e ao Panorama.
4. **Guardas**: CPF e nome de pessoa física continuam mascarados; arquivo vazio, muito menor que o anterior ou com cabeçalho diferente
   para a execução em vez de publicar.
5. **Registrar as URLs que faltam** (DIPEM, rodadas, ANEEL, ONS, recurso da CCEE) na coluna `url_download` do CSV.

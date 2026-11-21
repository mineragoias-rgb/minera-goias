# Pipeline da planilha consolidada — MINERA Goiás (Squad 1 / Estudante 1)

Gera `documentacao/prototipo_bases_consolidadas_v18.xlsx` e as camadas de mapa em `outputs/mapas/` a partir dos arquivos
em `dados/`. Nenhum número é digitado: tudo sai destes scripts.

## O que precisa existir

A pasta do projeto — a que contém este `base_consolidada_work/` — com:

- `documentacao/modelo_demo/prototipo_bases_consolidadas_v0.xlsx`: modelo da planilha. É ENTRADA, não apagar (também vale direto em
  `documentacao/`);
- os dados brutos, em um de dois arranjos, que `caminhos.py` reconhece sozinho:
  - **GitHub:** `Squad 1/Dados brutos/<fonte>/`, ao lado de `Squad 1/Bases consolidadas/`, que é a pasta do projeto (catálogo em
    `Dados brutos/LEIA-ME.md`);
  - **cópia de trabalho:** `dados/` dentro da pasta do projeto, com a organização original dos downloads.

`outputs/mapas/` é criada na primeira execução.

## Como rodar

Python 3.11 (a planilha atual foi gerada com 3.11.3, no Windows 11). A partir da pasta do projeto:

```bash
pip install -r base_consolidada_work/requirements.txt
```

```bash
python base_consolidada_work/scripts/rodar_pipeline.py
```

O comando funciona a partir de qualquer pasta (use o caminho do script). Leva cerca de 12 minutos; a etapa de mapas
sozinha leva uns 4. Cada etapa roda num processo separado. Se uma falhar, o script mostra o fim do log e para: corrija e
retome com `--de <etapa>`. `--lista` mostra os nomes das etapas.

## Caminhos

`caminhos.py` calcula tudo a partir da própria posição — não há caminho de máquina nos scripts:

- `BASE` = dois níveis acima de `scripts/`, ou seja, a pasta do projeto — ou a pasta indicada na variável de ambiente `MINERA_BASE`;
- `TMP` = JSONs intermediários entre as etapas, em `<pasta temporária do sistema>/minera_goias_pipeline` (fora do OneDrive e do
  git). Para usar outra pasta, defina a variável de ambiente `MINERA_TMP`;
- `arquivo("dados/…")` = acha um arquivo bruto pelo **caminho lógico** que a planilha cita (abas 07 e 08). Na cópia de trabalho ele
  está em `BASE/dados/`; no GitHub, em `../Dados brutos/<pasta da fonte>/`, pela tabela `PASTAS_BRUTOS`. A variável
  `MINERA_BRUTOS` aponta outra pasta no formato de `Dados brutos`. Como o caminho citado não muda, a planilha sai igual nos dois arranjos.

O log de cada etapa fica em `<TMP>/logs/`. A primeira linha da execução mostra qual arranjo foi usado.

Do GitHub, a partir da raiz do repositório:

```bash
python "Squad 1/Bases consolidadas/base_consolidada_work/scripts/rodar_pipeline.py"
```

## Etapas

| # | Script | O que faz |
|---|---|---|
| 1 | `build_base1_mineral_ano` | mineral × ano: AMB, CFEM, Cadastro Mineiro e SIGMINE; crosswalk de minerais, rochas por tipo de uso, tratamento da quantidade da CFEM |
| 2 | `build_base2_municipio_ano` | município × ano: malha, população e PIB do IBGE, CFEM, Cadastro Mineiro |
| 3 | `build_base3_empresa_mineral_ano` | empresa × mineral × ano: identidade do titular pela raiz do CNPJ, ponte CFEM → processo, máscara de CPF |
| 4 | `build_base4_mapas` | camadas de mapa (GeoPackage, GeoJSON, PMTiles) e a tabela de processos da aba 03 |
| 5 | `build_fato_08` | fato longo: uma linha por célula numérica do AMB e da CFEM |
| 6 | `build_interface_12` | entrega ao Squad 2, nos níveis estado e operação |
| 7 | `build_projetos_04` | projetos: camada ANM do Radar de Projetos |
| 8 | `build_ocorrencias_06` | ocorrências minerais do RECMIN |
| 9 | `build_mapas_04_06` | camadas de mapa dos projetos (04) e das ocorrências (06), no GeoPackage e em GeoJSON |
| 10–17 | `write_base1` … `write_fato_08` | montam a planilha aba por aba a partir do modelo v0, passando pelos arquivos intermediários `v1_base1`, `v3`, `v4`, `v5`, `v5a_ocorrencias`, `v5b_projetos`, `v5c_interface` e `v5d_fato` em `documentacao/` |
| 18 | `write_governanca_into_workbook` | nomes do Contrato de Dados, catálogo de fontes (07), dicionário (14), validações (14b), 00_LEIA-ME e o arquivo final |

## Conferir o resultado

Abra a aba `14b_validacoes_governanca`. Hoje ela tem 3 ALERTAs esperados, que são alertas de dado sinalizados de
propósito: plausibilidade CFEM × AMB, processos com quantidade implausível na CFEM (09c) e produção repetida no AMB. Qualquer outro
ALERTA indica problema.

A ANM republica os arquivos com frequência, e um `dados/` diferente gera números diferentes. Para reproduzir exatamente
uma planilha, os arquivos precisam ter o sha256 registrado na aba 07 dela.

Três scripts resumem a planilha em documentos, sem digitar número (rode depois de gerar uma versão nova):

- `gerar_relatorio_qualidade.py` grava `documentacao/relatorio_qualidade.md`: faltantes, duplicidades, divergências entre fontes e
  unidades, a partir das abas 14b, 14, 08, 09b, 09c, 13b e dos crosswalks;
- `gerar_nota_sem_coordenadas.py` grava `documentacao/nota_squad2_operacoes_sem_coordenadas.md` e `operacoes_sem_coordenadas.csv`:
  a produção estimada por operação que não tem coordenadas na aba 12;
- `gerar_pacote_squad2.py` grava `documentacao/pacote_squad2/`: a aba 12 em CSV no formato dos exemplos do Squad 2, o dicionário dos
  campos com a correspondência para o contrato do motor, um LEIA-ME e o rascunho da mensagem pedindo a confirmação do formato.

## Cuidados ao mexer nos scripts

- Os scripts executam trechos uns dos outros com `exec`: as Bases 2 e 3, a 06 e a governança usam as definições da
  Base 1 até o marcador `# 2) Carregar as fontes`; a Base 4 e a 08 executam a Base 3 inteira.
- Ordene antes de cortar ou juntar conjuntos (`sorted(...)[:n]`) e não use `hash()` do Python em IDs: a ordem de um `set`
  de texto e o `hash()` mudam a cada execução.
- Nome de aba do Excel tem no máximo 31 caracteres. Ao renomear um cabeçalho, renomeie também a coluna da Tabela do Excel.
- Aba nova precisa de descrição em `ABA_DESC` (governança) e as colunas novas, em `D`/`DA`: a governança acusa o que faltar.

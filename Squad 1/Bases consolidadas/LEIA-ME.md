# Base consolidada do Squad 1 — Estudante 1 (Eliel)

Base Mineral de Goiás — versão 1: minerais, empresas, processos e projetos da ANM, municípios, ocorrências geológicas do SGB,
produção mineral e CFEM de Goiás, com ID estável, fonte e unidade em cada número, como pede o Contrato de Dados.

| O quê | Onde |
|---|---|
| **Entregável** (25 abas, versão 18) | `documentacao/prototipo_bases_consolidadas_v18.xlsx` — comece pela aba `00_LEIA-ME` |
| Dados brutos usados, uma pasta por fonte | [`../Dados brutos/`](../Dados%20brutos/) — catálogo em `Dados brutos/LEIA-ME.md` e na aba `07_dim_fontes` |
| Entrega ao Squad 2 | aba `12_interface_squad1_squad2` |
| Dicionário de dados e validações automáticas | abas `14_dicionario_dados` e `14b_validacoes_governanca` |
| Relatório de qualidade (faltantes, duplicidades, divergências e unidades) | `documentacao/relatorio_qualidade.md` |
| Nota ao Squad 2 sobre a produção estimada sem coordenadas | `documentacao/nota_squad2_operacoes_sem_coordenadas.md` e `operacoes_sem_coordenadas.csv` |
| Pacote da aba 12 para o Squad 2 (CSV, dicionário, correspondência com o contrato do motor e rascunho de mensagem) | `documentacao/pacote_squad2/` |
| Decisão pendente do grupo (basaltos declarados como revestimento) | `documentacao/nota_decisao_basaltos.md` |
| Quadro de entradas e saídas do Squad 1 | [`../QUADRO_ENTRADAS_SAIDAS.md`](../QUADRO_ENTRADAS_SAIDAS.md) |
| Código que gera a planilha e os mapas | `base_consolidada_work/scripts/` (instruções no `LEIA-ME.md` de lá) |
| Modelo da planilha (entrada do pipeline) | `documentacao/modelo_demo/prototipo_bases_consolidadas_v0.xlsx` |

## Entrada e saída

- **Entrada:** o Contrato de Dados V1 e a lista oficial de minerais, definidos pelo gestor do projeto (IDs, nomes de campo e
  unidades), e os arquivos oficiais de [`../Dados brutos/`](../Dados%20brutos/).
- **Saída para o Squad 2:** aba `12_interface_squad1_squad2` — `production_t` por mineral e ano, observada em Goiás (AMB, 2010–2025)
  e aberta por operação com coordenadas (2022–2025, estimativa com método e intervalo na própria linha).
- **Saída para o Squad 3:** a planilha, carregada pelo importador no banco do site, e o atlas do site (`data/atlas/`), gerado da
  planilha por `scripts/build_atlas_base.py`.

## Campos de governança (Entrega Avaliativa, seção 3)

Todas as abas de dados (01 a 06 e 08 a 13) têm, em cada linha: fonte (`source_id` ou `source_ids`), `source_url`, `data_acesso`,
`periodo_referencia`, `tipo_fonte`, `valor_observado_estimado`, `metodo_estimacao` (preenchido quando o valor não é observado),
`status_validacao` e `responsavel_validacao`, além de `operation_id` e `project_id` onde há operação ou projeto. A aba 14b confere, a
cada geração, que os campos existem, estão preenchidos e têm URL e data iguais às do catálogo 07.

- **04, 06, 08 e 12:** preenchidos na origem de cada linha (na 08, até o arquivo, a linha e a coluna da fonte).
- **01, 02, 03, 05 e 13:** fontes em que o registro aparece; URL, data e tipo vêm da aba 07, na ordem das fontes da linha.
- **09, 10 e 11:** o período é o ano (2026 parcial) e o status herda os alertas das linhas da 08 que entram na soma.

## O que não está aqui

- **Camadas de mapa** (`outputs/mapas/`, cerca de 200 MB) e as planilhas intermediárias `v1_base1` … `v5d_fato`: são geradas de
  novo a cada execução do pipeline.
- **Fontes catalogadas que não alimentam as abas de dados** (IMB, água mineral, malha municipal de 2024, SIG geológico, geoquímica
  da Folha Nazário e mapas em PDF): ficam só na cópia de trabalho, com link e sha256 na aba 07.

## Site e importador

O importador da VPS (`ingestion/`) carrega os CSV e XLSX do `main` no banco do site: a planilha v18 e os CSV e XLSX de
`../Dados brutos/` entram como fonte `source_unvalidated` (as versões anteriores da planilha ficam só no histórico do git, para não
serem carregadas em dobro). O modelo v0 fica em `modelo_demo/` para não ser carregado: ele só tem dados ilustrativos. O atlas do site
(`data/atlas/`) é um retrato separado e não é atualizado por esta pasta.

## LGPD

Na planilha, o CPF que aparece dentro do nome de um titular (empresário individual) sai mascarado (`***456789**`), e a aba 14b
confere a cada geração que não há CPF completo em nenhum campo de texto. Os arquivos de `../Dados brutos/` são publicados como a
ANM os divulga e trazem, em algumas linhas, nome e CPF de titulares pessoa física.

## Como rodar

A partir da raiz do repositório, com Python 3.11:

```bash
pip install -r "Squad 1/Bases consolidadas/base_consolidada_work/requirements.txt"
```

```bash
python "Squad 1/Bases consolidadas/base_consolidada_work/scripts/rodar_pipeline.py"
```

O pipeline encontra sozinho os arquivos de `../Dados brutos/` e leva cerca de 14 minutos. A aba 14b da planilha gerada mostra se algo
saiu do esperado.

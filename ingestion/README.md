# Importação automática das bases

O script `import_repository.py` percorre as pastas do repositório, cataloga arquivos e importa CSV, TSV e todas as abas dos arquivos XLSX para uma camada de dados de origem. Pode usar MySQL na VPS ou criar um SQLite local. Aceita outros repositórios já baixados através de `--root` e `--repo-id`, mantendo as origens separadas.

## O que é armazenado

| Tabela | Conteúdo |
|---|---|
| `ingest_files` | Caminho, classificação, hash, estado da importação e versão ativa de cada arquivo |
| `ingest_versions` | Histórico de conteúdos importados, commit de origem e versão das regras |
| `ingest_datasets` | Abas/tabelas, cabeçalhos, codificação, contagens e alertas |
| `ingest_rows` | Valores originais por coluna, linha de origem e fórmulas do Excel |
| `ingest_runs` | Histórico das execuções e relatório por arquivo |
| `ingest_current_rows` | Visão SQL com os registros das versões atuais, já ligados à origem |

As linhas são classificadas em `data`, `header` e `context`. Cabeçalhos duplicados recebem sufixos únicos; rótulos originais e posições ficam em `columns_json`. Cabeçalhos das planilhas atuais estão configurados em `policy.json`. Em novos formatos, o cabeçalho é inferido e marcado para revisão. Abas de resumo e QA são preservadas como contexto.

## Regras de integridade

- Dados em pastas/arquivos `demo` ou `mock` são catalogados e excluídos da carga. Os demais dados são marcados `source_unvalidated`, pois importação não equivale a validação científica.
- Arquivos de código, SQL, HTML e notebooks são apenas catalogados: nunca executados.
- Não há conversão presumida de unidades, CFEM para produção, energia para intensidade, ou associação automática de empresas por nomes parecidos.
- CSV preserva textos, decimais e identificadores exatamente como lidos. Excel preserva os valores armazenados. Zeros reais permanecem zeros; ausências permanecem ausências.
- Fórmulas não são calculadas: ficam preservadas em `formulas_json`, junto do valor em cache quando disponível. Falta de cache e erros do Excel aparecem como alertas.
- CPF/CNPJ em notação científica ou armazenados como número geram alertas. Dígitos perdidos na origem não são inventados nem recuperados por aproximação.
- Hashes evitam reimportação de arquivos iguais. Uma alteração cria versão histórica nova e substitui a referência atual só após importar todas as abas daquele arquivo.
- Arquivos removidos são desativados; seu histórico não é apagado. Uma falha mantém a última versão válida daquele arquivo e marca o erro no catálogo. A execução pode terminar parcial, com outros arquivos atualizados.
- CSVs e planilhas corrigidas continuam como fontes separadas. **Não some todas as linhas da visão como se fossem observações independentes:** há bases sobrepostas, agregados e diferentes unidades.
- As tabelas existentes `tb_projetos`, `tb_projecoes` e demais `tb_*` não são sobrescritas. Transformações para essas tabelas exigem mapeamento validado de chaves, unidades, períodos e fontes.

## Execução local

```sh
python -m pip install -r ingestion/requirements.txt
python ingestion/import_repository.py --root . \
  --sqlite /tmp/minera-goias.sqlite --report /tmp/minera-goias-report.json
```

O banco e o relatório devem ficar fora da pasta inspecionada. `--commit` permite informar o SHA do Git; sem esse argumento a origem é identificada como `working-tree`.

## VPS

O timer `minera-goias-ingestion.timer` verifica a versão publicada a cada cinco minutos. O deploy do código verifica o GitHub a cada dois minutos. Depois de uma atualização validada da `main`, o importador processa as mudanças e grava o relatório em `/var/lib/minera-goias-ingestion/latest.json`.

```sh
systemctl status minera-goias-ingestion.timer
journalctl -u minera-goias-ingestion.service -n 50
systemctl start minera-goias-ingestion.service
```

O usuário de importação tem acesso somente às cinco tabelas de ingestão. As credenciais ficam em `/etc/minera-goias-ingestion.env`. O programa e a política usados pelo serviço ficam instalados como arquivos pertencentes a root: mudar o importador ou a política no GitHub requer reinstalação administrativa. Os dados acompanham a `main` automaticamente. Para reprocessar após atualização do importador, remover apenas `/var/lib/minera-goias-ingestion/last-successful-commit` e iniciar o serviço novamente; o histórico permanece.

## Consultas

```sql
-- Tabelas/abas ativas, contagens e alertas
SELECT f.path, d.sheet_name, d.data_row_count, d.warnings_json
FROM ingest_files f JOIN ingest_datasets d ON d.version_id=f.current_version
WHERE f.active=1;

-- Linhas de uma fonte; os nomes das colunas estão em columns_json
SELECT source_row, values_json
FROM ingest_current_rows
WHERE path='Squad 1/dados/CCEE/parcela_carga_consumo_2025_GO.csv'
  AND row_role='data'
ORDER BY source_row LIMIT 20;

-- Exemplo MySQL: consultar período e município preservados da CCEE
SELECT JSON_UNQUOTE(JSON_EXTRACT(values_json,'$.mes_referencia')) AS periodo,
       JSON_UNQUOTE(JSON_EXTRACT(values_json,'$.cidade')) AS cidade
FROM ingest_current_rows
WHERE path='Squad 1/dados/CCEE/parcela_carga_consumo_2025_GO.csv'
  AND row_role='data'
LIMIT 20;
```

Os testes em `tests/test_ingestion.py` verificam atualização sem duplicatas, histórico, retirada de arquivos, isolamento de demos, codificação/decimais/identificadores, cabeçalhos repetidos e preservação da versão anterior quando uma atualização falha.

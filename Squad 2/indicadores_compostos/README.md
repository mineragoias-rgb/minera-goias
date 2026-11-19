# Indicadores compostos e cenários (Frente 8)

Responsável: Lucas. Apresentação em 12/11/2026. Metodologia reproduzível dos índices (IRMM, IVFM, IPMM, IPES), validação, cenários e o banco de 20 indicadores por município (2025).

**Esta pasta não faz parte do site.** Não fica em `public/` e não dispara a publicação nem os testes da plataforma.

## Conteúdo

| Arquivo | Função |
|---|---|
| `indices_compostos.py` | Motor: normalização, pesos, agregação, sensibilidade |
| `run_indices.py` | IRMM e IPES (lê `data/panorama/panorama.json`) |
| `run_extra.py` | IVFM, IPMM, tipologia e cenários |
| `cenarios.py` | Choques de preço e retirada de titular |
| `validacao.py` | Protocolo de validação (limiares fixados antes de rodar) |
| `build_xlsx.py` | Banco de 20 indicadores por município, 2025 |
| `test_indices.py`, `test_extra.py` | Testes (18/19 e 10/10; D06 falha de propósito, é a reprovação do IPES) |
| `registro_metodologico.md` | Fontes, decisões, validação e pendências |
| `resultados/` | Saídas geradas (CSV e JSON) |
| `entregas/` | xlsx, pptx e html entregues |

## Como rodar

Da raiz do repositório, dentro desta pasta, nesta ordem (as saídas vão para a pasta atual):

```
cd "Squad 2/indicadores_compostos"
python3 run_indices.py && python3 run_extra.py
python3 test_indices.py && python3 test_extra.py
python3 validacao.py        # depois dos testes: lê o resultado deles
python3 build_xlsx.py       # precisa de openpyxl; gera indicadores_2025_raw.xlsx
```

Dependências: numpy, pandas, scipy, openpyxl. Semente fixa 20261112.

## Pendências

- Regerar o PPT e o HTML de `entregas/` com o IPMM corrigido (o IPMM já foi refeito em `resultados/`; ver o registro).
- Trocar população e PIB pelos dados do IBGE (população estimada 2022–2025 e PIB 2022).
- Os arquivos `.pptx` e `.html` em `entregas/` foram gerados por scripts que não estão aqui.

## No site

O banco de 20 indicadores aparece no painel em Atlas · Território · Visão do mapa · Indicadores. O pacote de dados é gerado por `scripts/build_indicadores_municipais.py` a partir de `entregas/MINERA_Goias_Indicadores_2025.xlsx` e sai por `/api/indicadores`, atrás do login.

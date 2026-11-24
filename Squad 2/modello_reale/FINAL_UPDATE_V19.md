# Fechamento da atualização v19

Este roteiro fecha a última atualização solicitada após a entrega da base v19 do Squad 1 e da curadoria ampliada de projetos.

Regra central: dados novos de produção não são convertidos automaticamente em TWh sem uma intensidade energética compatível.

## O que a v19 efetivamente adiciona

- Produção observada estadual para 33 minerais, de 2010 a 2025.
- Abertura estimada por operação de 2022 a 2025 para 931 processos.
- Curadoria com 37 projetos, em vez de uma carteira restrita aos cinco minerais do modelo.

O modelo elétrico continua com cinco minerais porque o arquivo de coeficientes contém somente cobre, bauxita, níquel, fosfato e amianto.

A execução com a v19 mantém o cenário de referência de 2040 em **4,84 TWh**. Não houve mudança numérica apenas por substituir a base de produção.

## Resultado da auditoria da carteira atual

Rodar:

```bash
cd "Squad 2/modello_reale"
python src/audit_project_readiness.py

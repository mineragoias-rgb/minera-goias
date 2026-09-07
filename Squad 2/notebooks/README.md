# Notebooks da Squad 2

## Motor Econômico-Energético

O notebook `Motor_Economico_Energetico_MINERA_Goias.ipynb` implementa o motor de projeção econômico-energética do projeto MINERA Goiás.

Ele projeta a produção mineral e a demanda de energia elétrica de Goiás entre 2027 e 2040, por mineral e cenário.

## Dados de entrada

O notebook lê os dados demo diretamente do repositório:

```text
Squad 2/data/demo/
```

Não há carregamento manual de arquivos. Para executar o notebook, essa estrutura de pastas deve ser mantida.

## Resultados

Os resultados são gerados em:

```text
Squad 2/outputs/demo/
```

A execução produz projeções por mineral, total de Goiás, contribuição dos projetos e análises de sensibilidade.

## Execução

O notebook é executado automaticamente pelo GitHub Actions através do workflow:

```text
.github/workflows/validate-squad2-model.yml
```

Também pode ser executado localmente a partir da raiz do repositório, após instalar as dependências de `requirements.txt`.

## Dados reais

A versão atual utiliza dados sintéticos. Quando os dados reais forem disponibilizados, eles deverão substituir os arquivos demo mantendo os mesmos nomes de colunas, IDs estáveis e a mesma `production_basis`.

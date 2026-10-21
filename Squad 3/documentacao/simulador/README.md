# Simulador de Demanda Energética e Rastreabilidade

Squad 3 · Henrique Falci

Página web que recalcula a demanda de energia do setor mineral de Goiás entre 2027 e 2040
conforme o cenário, a hipótese de eficiência e o ajuste de intensidade escolhidos, mostrando
a origem de cada parâmetro. O simulador não consulta nenhuma fonte externa: lê um único
arquivo de parâmetros versionado do repositório.

Desde a versão 1.0.0 dos parâmetros, os números vêm do modelo econômico-energético do
Squad 2 (`Squad 2/modello_reale`), que projeta a produção histórica consolidada pelo Squad 1.

## Arquivos

| Arquivo | Função |
|---|---|
| `public/simulador.html` | Estrutura da página |
| `public/simulador.css` | Estilo, seguindo o guia visual azul/dourado |
| `public/simulador-engine.js` | Cálculo, isolado da interface e sem acesso à tela |
| `public/simulador.js` | Controles, gráficos e painel de fontes |
| `public/data/simulador/parametros_v1.json` | Parâmetros em uso, com campo `versao` |
| `public/data/simulador/parametros_v0.json` | Primeira versão, marcada como substituída |
| `scripts/build_simulador_base.py` | Gera o pacote v1 a partir do modelo do Squad 2 |
| `tests/simulador.test.js` | 55 verificações do cálculo |
| `tests/test_simulador.py` | Contrato dos parâmetros, rastreabilidade e ausência de segredos |

## Como rodar

O projeto não tem build. A página é servida como arquivo estático:

```sh
cd public
python3 -m http.server 8000
```

Abra `localhost:8000/simulador.html` no navegador. Em produção o Nginx já serve a página em
`/simulador.html`, junto com o resto de `public/`.

## Como testar

```sh
python3 -m unittest discover -s tests -p test_simulador.py -v
node tests/simulador.test.js
```

Ambos rodam no GitHub Actions, pelo workflow `validate-web.yml`.

## As equações

O núcleo é o método do projeto — produção física × intensidade energética — sem camada
estatística intermediária. São as mesmas equações do modelo do Squad 2:

```
Produção(m,t)    = producao_base_t(m) × (1 + crescimento_historico(m) + growth_adjustment(s))^(t − ano_base)
Intensidade(m,t) = energy_intensity_mwh_t(m) × (1 + ajuste_pct(m)/100) × (1 − g)^(t − ano_base)
Energia(m,t)     = Produção(m,t) × Intensidade(m,t)
```

- `ano_base` é 2025, o último ano observado pelo Squad 1; `t` vai de 2027 a 2040.
- `crescimento_historico` é a taxa composta da série histórica de cada mineral, calculada
  pelo modelo do Squad 2.
- `growth_adjustment` é o ajuste do cenário, em pontos percentuais: −2, 0 e +2.
- `g` é o ganho anual de eficiência, controlado pelo usuário entre 0% e 3%.
- `ajuste_pct` é o ajuste de sensibilidade por mineral, entre −10% e +10%.
- As três curvas comparadas usam a **mesma** hipótese de eficiência e o mesmo ajuste de
  intensidade, para que a diferença entre elas isole o efeito do cenário de crescimento.

**Só a energia é agregada.** As toneladas não são somadas entre minerais: o cobre usa
conteúdo mineral e os demais usam produção beneficiada.

## De onde vêm os dados

| Camada | Origem | Natureza |
|---|---|---|
| Produção histórica | Squad 1, séries consolidadas 2010–2025 (bauxita desde 2014) | observado |
| Intensidade energética | Coeficiente estadual do Squad 2 (`Squad 2/intensidade_energetica/coeficiente_estadual_para_modelo_v1.csv`): energia CCEE 2025 ÷ produção 2025; a bauxita, sem carga na CCEE, segue com o benchmark FGV Energia-EPGE | estimado |
| Crescimento e eficiência dos cenários | Hipóteses do Squad 2, em `scenarios.csv` | ilustrativo |
| Faixa de sensibilidade | Contrato `intensity_sensitivity_contract.json` do Squad 2 | — |

As intensidades são as que o modelo do Squad 2 carrega (`load_parameters()` em
`Squad 2/modello_reale/src/common.py`), lidas pela mesma função — o simulador não aponta para
um arquivo próprio. Desde 23/09/2026 são coeficientes calculados com a carga observada na CCEE
em 2025 dividida pela produção do mesmo ano; a bauxita, sem carga identificada, segue com
benchmark. São coeficientes por mineral, não medição de cada planta. Os resultados são cenários
condicionais, não previsão oficial.

### Cobertura e limites

Cinco minerais: cobre, bauxita, níquel, fosfato e amianto. O **nióbio ficou de fora** porque
o Squad 2 não conseguiu conciliar com segurança as unidades e o conceito de produção
disponíveis com o coeficiente energético.

O erro do backtest do Squad 2 aparece no painel de fontes, por mineral. A **bauxita** tem
44,3%: a produção caiu em 2024 depois de anos de crescimento, e uma projeção de tendência não
antecipa interrupções operacionais nem decisões de mercado. Com as intensidades da CCEE, a bauxita
passou a ser o **maior** consumidor projetado (o níquel caiu de 45,55 para 11,67 MWh/t), então
esse número pesa ainda mais ao interpretar o total.

O modelo ainda **não inclui carteira física de projetos**. As bases atuais não trazem
capacidade, ano de entrada e grau de certeza de forma estruturada e validada.

## Como atualizar e versionar os parâmetros

O pacote v1 é gerado, não escrito à mão. Os outputs do modelo do Squad 2 saem apenas como
artefato do GitHub Actions, que não fica versionado; por isso o simulador precisa de um
pacote próprio no repositório.

```sh
python3 -m venv .venv
.venv/bin/pip install -r "Squad 2/modello_reale/requirements.txt"
.venv/bin/python scripts/build_simulador_base.py
```

O script executa os três scripts do modelo do Squad 2, lê os outputs e extrai as primitivas
de cada mineral. Antes de gravar, ele confere que a fórmula que o navegador executa devolve a
mesma energia do modelo em todos os minerais, anos e cenários, e falha se a diferença passar
de 10⁻⁶ MWh. A diferença encontrada fica registrada em `conferencia_modelo`.

Para publicar uma versão nova:

1. Rode o build acima depois que o Squad 2 atualizar o modelo ou os parâmetros.
2. Confira o campo `versao` e ajuste `data_versao`.
3. Rode os dois comandos de teste. Eles falham se o pacote divergir dos arquivos de
   parâmetros do Squad 2, se faltar fonte em alguma medida ou se algum valor estimado não
   declarar o método.
4. Faça o commit e marque a versão no GitHub:

```sh
git tag params-v1.0 -m "Parâmetros do simulador v1.0.0"
git push origin params-v1.0
```

A tag congela o par arquivo + código que produziu um resultado, então qualquer número
apresentado pode ser reproduzido depois. A página mostra a versão carregada no canto
superior direito e no painel de fontes.

Versões anteriores permanecem no repositório com `situacao: substituido` e um ponteiro para
a versão que as substituiu.

## Integração

**Entrada recebida.** Do Squad 2 (Federico Castro): o modelo `modello_reale`, os parâmetros de
intensidade e cenário, o backtest e o contrato de sensibilidade. Do Squad 1, por meio do
modelo do Squad 2: as séries de produção consolidadas.

**Saída entregue.** `public/data/simulador/parametros_v1.json` — o pacote que a página lê,
com as primitivas do modelo, os campos de governança e a conferência contra o modelo de
origem. O Squad 3 (Kayo) pode servi-lo por API no lugar do arquivo estático: é um ponto único
de troca, em `CAMINHO_PARAMETROS` no início de `simulador.js`. O motor de cálculo é um módulo
de funções puras e pode ser chamado por qualquer outra tela do painel.

**O que ainda depende de terceiros.** Quando o Squad 1 estruturar capacidade, ano de entrada e
grau de certeza dos projetos, o Squad 2 poderá acrescentar a camada física de oferta; o
simulador então ganha um controle de ano de entrada de projeto. O nióbio volta quando as
unidades forem conciliadas.

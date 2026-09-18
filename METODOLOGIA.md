# Metodologia de medição

Este documento fixa **o que o Minera Goiás mede, a partir de qual fonte, em qual unidade e em qual período** — e, com o mesmo cuidado, o que ele ainda não mede. Vale para o painel CCEE, o atlas mineral, o perfil de município, a carga das tabelas de negócio e o radar de notícias.

Atualizado em 18/09/2026. Ao mudar uma regra de cálculo, atualize este arquivo na mesma alteração.

---

## 1. Cinco princípios que valem para tudo

**Contagem não é consumo, nem produção.** Um registro é uma linha de uma fonte. Quando o painel mostra "8.072 registros", isso é o número de linhas da CCEE no recorte — não é número de empresas, nem de minas, nem de MWh.

**Unidade nunca é convertida por inferência.** A CFEM declara quantidade em sete unidades diferentes (t, m³, kg, l, g, m², ct). Nada é somado entre unidades e nada é convertido sem regra revisada. Ouro aparece em kg; energia em MWh ou GWh; coeficientes em kWh/t.

**Fontes sobrepostas não se somam.** As planilhas corrigidas e as originais descrevem o mesmo fenômeno. O acervo guarda as duas como fontes separadas; somar suas linhas produziria dupla contagem.

**Importar não é validar.** Toda linha carregada nasce com `status_validacao = nao_validado`. A validação técnica é ato humano, registrado em `responsavel_validacao`.

**Quando a fonte não diz, o sistema não inventa.** Sem CNPJ na origem, o titular fica sem documento. Sem detalhamento anual, o município fica sem série. Sem substância cadastrada, o campo guarda o texto cru `DADO NÃO CADASTRADO`.

---

## 2. Unidade de observação, por fonte

| Fonte | Uma linha é… | Volume | Período |
|---|---|---|---|
| CCEE — parcelas de carga | Uma parcela de carga de um agente, em um mês, município e ramo | 4.241 (2024) · 8.072 (2025) · 8.245 (2026) | 2024–2026 |
| CFEM — arrecadação | Um recolhimento por processo, substância, município e mês | 38.854 | 2022–2026 |
| Cadastro mineiro (shapefile) | Um polígono de um processo minerário | 17.428 polígonos em 16.656 processos | Data de extração não informada |
| Rodadas de disponibilidade | Uma área oferecida em uma rodada | 31.841 no Brasil · **3.632 em Goiás** | Rodadas 1 a 8 |
| Dicionário de substâncias | Uma substância da ANM | 862 | Sem data declarada |
| Produção por empresa (`data/producao`) | Um número de produção publicado por uma fonte, para uma empresa, mineral, período e medida | 32 registros de 10 empresas | 2024–2027 (realizado, guidance, capacidade e meta) |
| Atlas (base consolidada do Squad 1, v17) | Retrato gerado da planilha por `scripts/build_atlas_base.py`; energia e barragens seguem do artefato recebido | 246 municípios · 16.656 processos · 3.377 projetos · 1.796 ocorrências · 23 barragens | Ver §3.2 e `data/atlas/README.md` |

O acervo importado hoje soma **189.785 linhas em 14 arquivos**, cada uma rastreável até arquivo, aba, linha de origem e commit.

---

## 3. Como cada indicador é calculado

### 3.1 Painel CCEE (visão geral)

Mede **cobertura do acervo**, não energia.

- **Registros no recorte** — contagem de linhas da CCEE do ano selecionado, filtradas por ramo de atividade quando escolhido.
- **Municípios representados** — contagem de valores distintos de `CIDADE` no recorte.
- **Meses com registros** — contagem de valores distintos de `MES_REFERENCIA`.
- **Cobertura ao longo do ano** e **municípios com mais registros** — as mesmas contagens, agrupadas.

**O que existe e deliberadamente não é usado:** o arquivo traz `CONSUMO_ACL`, `CONSUMO_CATIVO_PARC_LIVRE` e `CONSUMO_TOTAL` em MWh. Somados, dariam 6,84 milhões de MWh em 2024, 11,63 em 2025 e 11,33 em 2026. **O painel não publica esses totais** porque a base mistura 16 ramos de atividade — alimentícios, comércio, serviços — e um recorte "mineral" confiável exige critério de classificação revisado, não o campo autodeclarado `RAMO_ATIVIDADE`. Publicar MWh hoje sugeriria uma medição de consumo mineral que a base ainda não sustenta.

### 3.2 Atlas mineral

Cada camada tem unidade própria e período próprio; elas **não** se comparam entre si.

| Camada | Unidade | Período |
|---|---|---|
| CFEM por município | R$ | Intervalo escolhido entre 2022 e 2026, somando os anos cobertos (2026 parcial: jan.–início de ago.) |
| Quantidade comercializada | t (ou kg, para ouro) | 2025 |
| Energia da cadeia mineral | GWh | 2025 (artefato recebido) |
| Intensidade energética | kWh/t (MWh/kg para ouro) | 2025 (artefato recebido) |
| Polígonos de processos | ha declarados (calculados quando a declaração falta) | Arquivo do SIGMINE de 10/09/2026 |
| Projetos que ainda não produzem (aba 04) | Contagem, por classificação (provável, possível, sinal) | Situação no SIGMINE de 10/09/2026 |
| Ocorrências minerais (aba 06, RECMIN) | Contagem, por importância | RECMIN baixado em 12/09/2026 |
| Barragens | Classificação categórica | Extração sem data (artefato recebido) |

**Escala de cores:** faixas de quantis dos valores positivos. Cinza significa **sem registro ou zero** — e são coisas distintas que a fonte não separa.

**A CFEM anual cobre os 246 municípios.** O período é um intervalo com início e fim escolhidos; o valor de cada município é a soma dos anos dentro dele. Cinza significa que não houve arrecadação no intervalo. O intervalo completo reproduz o acumulado: para os 246 municípios, a soma dos cinco anos é idêntica ao total acumulado, sem uma divergência sequer.

**Gráficos das séries.** Além das séries anuais (CFEM, CFEM de janeiro a julho, energia mensal, produção beneficiada e investimento em pesquisa), o atlas traz sete gráficos calculados da base: CFEM de 2025 por substância; CFEM por substância e ano; concentração da CFEM de 2025 nos maiores municípios e titulares; produção bruta por mineral no ano mais recente do Anuário (as barras não se somam: co-produtos repetem a mesma tonelagem); parcela da produção bruta atribuída a operações (aba 12); projetos por mineral e classificação; ocorrências por substância e importância (uma ocorrência com mais de uma substância conta em cada uma). `tests/test_atlas.py` confere que os gráficos de CFEM somam o total de cada ano e que as contagens batem com as abas 04 e 06.

**Reconciliação feita:** a soma dos acumulados municipais bate com o total dos cinco anos em R$ 867.578.398,91.

### 3.3 Perfil do município

- **Processos minerários** — processos do SIGMINE que tocam o município (base consolidada).
- **CFEM acumulada** — CFEM da base consolidada, 2022 a 2026 (2026 parcial).
- **Participação no estado** — CFEM acumulada do município ÷ soma dos 246 municípios, em %.
- **Energia · 2025** — MWh do artefato convertidos para GWh (divisão por 1.000, única operação aritmética aplicada).
- **Substâncias declaradas · 2025** — quantidade comercializada (t), CFEM e titulares distintos por substância, da base consolidada, sem as quantidades excluídas na aba 09b.
- **Projetos (ANM)** e **Ocorrências (RECMIN)** — contagem dos pontos das abas 04 e 06 com o município.
- **Evolução ao longo do tempo** — CFEM por ano para qualquer um dos 246 municípios; 2026 aparece como parcial.

### 3.4 Carga das tabelas de negócio (`load_anm.py`)

- **Substância** resolvida contra o dicionário da ANM por nome normalizado (maiúsculas, sem acento). Todos os nomes reais resolvem; 381 processos trazem `DADO NÃO CADASTRADO` na origem e ficam sem `mineral_id`.
- **Titular** chaveado pelo nome normalizado, porque nenhuma fonte atual fornece documento utilizável.
- **Área do processo** preenchida **somente** quando há um único polígono. Com mais de um, a área fica por polígono e nenhum total é declarado: polígonos podem se sobrepor e a soma criaria superfície inexistente.
- **Polígono** tem chave própria. O identificador do shapefile se repete entre processos e até dentro de um mesmo processo, então é atributo de origem.

### 3.5 Produção por empresa (`data/producao`)

Mede **o que a empresa publicou**, não o que a mina produziu — e a diferença entre as duas coisas é o assunto desta seção.

Cada linha é um número de uma fonte, com quatro qualificadores obrigatórios, porque sem eles o número não é comparável com nenhum outro:

- **`medida`** — `minerio_rom`, `contido`, `metal_em_concentrado`, `produto_acabado`, `embarque`, `capacidade` ou `meta`. Níquel contido em ferroníquel e níquel contido no minério lavrado são grandezas diferentes da mesma mina.
- **`escopo`** — `operacao_goias`, `consolidado_brasil` ou `consolidado_global`. Os 4,2 Mt de rocha fosfática da Mosaic e o 1,21 Mt de fertilizantes da CMOC são do Brasil, não de Goiás, e por isso não entram em nenhum total do estado.
- **`tipo_valor`** — `realizado`, `guidance`, `capacidade` ou `meta`. Guidance carrega faixa (`valor`–`valor_max`) e nunca aparece como realização.
- **`periodo`** — ano, semestre ou trimestre, lido da própria publicação.

**Nada é convertido e nada é somado.** Onça troy, tonelada e quilo convivem sem fator; `kt`, `Mt` e `koz` são lidos como prefixo da mesma grandeza, que é definição e não conversão. Trimestres publicados não somam para formar o ano: a empresa revisa número no fechamento.

**Toda linha nasce `nao_validado`.** Nenhuma foi conferida no documento original: a coleta da v1 saiu de busca na web, num ambiente cujo proxy de egresso bloqueia os sites de RI, e `fonte_url` é o endereço que a busca atribuiu ao número. Conferir cada um é a primeira tarefa do agente semanal.

**Só entra o que a empresa declarou.** Release de resultados, relatório anual, ou o que imprensa e agregadores de mercado reproduzem dessas publicações. Estatística de agência não entra, e `agencia_oficial` não existe no vocabulário de `fonte_tipo`: a curadoria que o declarar é recusada na geração. O motivo é de medida, não de confiança — em 2025, para Goiás, o Anuário Mineral registra 35.487,71 t de Ni contido no minério lavrado enquanto a Anglo American publica 39.700 t de níquel contido no ferroníquel; 51.937,85 t de Cu contido contra 43.974 t de metal pago no concentrado de Chapada; 62.626,53 t de Nb₂O₅ contido contra 10.348 t de produto de nióbio da CMOC. Entre uma coluna e outra estão a recuperação metalúrgica e a estequiometria do óxido. Publicar as duas lado a lado sugeriria que uma corrige a outra, e nenhuma corrige: a visão do estado por substância continua sendo a do Anuário, no atlas e no panorama.

**O agente semanal (`producao/agente.py`) não escreve na base.** Ele lê fontes públicas, extrai candidatos com a frase de evidência, confronta com a curadoria (`confirma`, `diverge`, `unidade_divergente`, `novo`, `sem_periodo`) e propõe crescimento da própria metodologia — padrão, unidade ou termo de mineral que faltaram. Promoção automática existe e nasce desligada. Quem promove candidato a registro assina em `responsavel_validacao`.

### 3.6 Radar de notícias (protótipo)

Mede **o que a imprensa está dizendo**, não preço.

- Uma frase que cite uma substância **e** traga palavra de direção vira um sinal, guardando a frase como evidência.
- `score = (altas − baixas) ÷ total de sinais`, por substância e semana ISO.
- Veredito só com **3 ou mais matérias distintas**; abaixo disso fica `evidencia_insuficiente`, por mais extremo que seja o score.
- Preço citado no texto é extraído com moeda, unidade e escala — e permanece um **preço citado**, não cotação de mercado.

---

## 4. O que ainda não é medido

Declarar isto é parte da metodologia.

- **Consumo de energia da mineração em MWh.** Depende de um critério revisado para separar carga mineral das demais na base CCEE (§3.1).
- **Intensidade energética por operação.** Os coeficientes do atlas são razões municipais — energia do município ÷ produção do município —, não medidas de planta.
- **Projeções.** `tb_projecoes` está vazia. O motor da Squad 2 roda sobre dados sintéticos identificados como `estimated_demo` e não alimenta o portal.
- **Série de energia no perfil municipal.** A base CCEE do banco é mensal e cobre todos os municípios; ligá-la ao perfil municipal é o caminho natural, e ainda não foi feito.
- **Produção mineral física por empresa, medida e auditada.** A CFEM dá quantidade comercializada declarada para fins de arrecadação, que não equivale a produção. Desde 18/09/2026 há a base `data/producao`, que publica o que as próprias empresas declaram (§3.5) — mas ela é **o que foi publicado**, não o que foi medido: nenhuma linha foi conferida no documento de origem, a cobertura é de dez empresas e a série de cada operação tem buracos declarados. Não serve para fechar balanço de massa nem para calibrar intensidade energética por planta sem validação humana registro a registro.

---

## 5. Precisão e incerteza declaradas

- **Geometrias do atlas:** municípios da malha IBGE 2025 simplificados como cobertura (tolerância de 0,003°); processos do SIGMINE simplificados (~45 m) e quantizados em UInt16. Projetos são o ponto representativo dos seus processos (73 caem fora de Goiás porque os processos cruzam a divisa); ocorrências usam a coordenada do RECMIN, 83% posicionada em carta 1:250.000. Servem para localizar e comparar; **não são limites cadastrais**.
- **Identificadores em notação científica:** 34.212 registros da CFEM trazem CPF/CNPJ como número em notação científica. Dígitos perdidos na origem não são recuperados por aproximação — são sinalizados como alerta.
- **CPF de pessoa física** vem mascarado da ANM (`***370285**`). CNPJ de pessoa jurídica vem íntegro, e é dado público.
- **Fórmulas de planilha** não são recalculadas: 2.358 células da base consolidada estão sem valor em cache e aparecem como alerta, não como zero.
- **Barragens** trazem classificação de risco, dano potencial e nível de emergência como categorias de uma extração sem data. **Não servem para avaliar condição atual.**

---

## 6. Divergência aberta

**Período da CFEM de 2026.** O arquivo `CFEM_Arrecadacao_2022_2026_GO.csv` contém registros nos meses 1 a **8** de 2026. O artefato recebido rotulava o mesmo conjunto — 9.569 registros — como "janeiro a julho". Desde 13/09/2026 o atlas é gerado da base consolidada, que usa o `Mês` do arquivo (2026-01 a 2026-08) e a maior `DataCriacao` (04/08/2026): 2026 aparece como parcial, "jan.–início de ago.".

Hipótese a verificar: o campo `Mês` pode ser o mês do recolhimento, e não o da competência, o que deslocaria o rótulo em um mês. A pendência continua aberta até alguém confirmar na ANM se o `Mês` é de competência ou de recolhimento. Quem for verificar: comparar `Mês` com `DataCriacao` em uma amostra e confrontar com a documentação da CFEM.

---

## 7. Reprodutibilidade

Toda medição do portal pode ser refeita a partir do repositório:

```sh
# Acervo: reconstrói as tabelas de origem a partir dos arquivos
python3 ingestion/import_repository.py --root . --sqlite /tmp/acervo.sqlite --report /tmp/acervo.json

# Tabelas de negócio: carga direta das fontes da ANM, sem tocar no MySQL
python3 "Squad 3/database/load_anm.py" --root . --sqlite /tmp/negocio.sqlite

# Atlas: gera o pacote a partir da base consolidada do Squad 1 (planilha, GeoPackage e dados/ locais do Squad 1)
python3 scripts/build_atlas_base.py --base "<pasta do projeto do Squad 1>"

# Radar: executa sem rede, sobre as fixtures
python3 news/radar.py --db /tmp/radar.sqlite --offline-dir tests/fixtures/news
```

Cada arquivo importado guarda hash do conteúdo, commit de origem e versão das regras de leitura. Uma alteração cria versão nova e preserva a anterior; um arquivo removido é desativado sem apagar o histórico.

---

## 8. Como mudar esta metodologia

Uma regra de cálculo só muda junto com três coisas: o código que a implementa, o teste que a fixa e este documento. Os testes que hoje travam decisões metodológicas:

| Decisão | Teste |
|---|---|
| Nenhum polígono se perde pela chave do processo | `tests/test_load_anm.py` |
| Área não é somada quando polígonos podem se sobrepor | `tests/test_load_anm.py` |
| Documento de titular não é inventado | `tests/test_load_anm.py` |
| Nome de pessoa não sai no endpoint público | `tests/test_load_anm.py` · `tests/test_web.py` |
| Semana sem matérias suficientes não recebe veredito | `tests/test_news.py` |
| Preço citado preserva moeda, unidade e escala | `tests/test_news.py` |
| Demos e mocks ficam fora da carga | `tests/test_ingestion.py` |
| Versão anterior sobrevive a uma importação que falha | `tests/test_ingestion.py` |
| Gráficos do atlas somam a CFEM de cada ano; projetos e ocorrências batem com as abas 04 e 06 | `tests/test_atlas.py` |

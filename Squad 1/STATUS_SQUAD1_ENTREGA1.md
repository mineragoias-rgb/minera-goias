# Squad 1 — Situação da Entrega Avaliativa 1

**MINERA Goiás · Squad 1 — Mineral & Data Intelligence · prazo da entrega: 21/09/2026**
Levantamento de 13/09/2026, atualizado em 14/09/2026. As exigências vêm do guia `Squads (1).docx` (seção "Entrega Avaliativa 1"), do
`Contrato de Dados V1` e do `SQUAD1_PLANEJAMENTO.md`. A situação foi conferida no repositório `mineragoias-rgb/minera-goias` e na pasta de
trabalho do Estudante 1. O trabalho dos Estudantes 2 e 3 foi avaliado pelo que está no GitHub; o que existir fora dele não aparece aqui.

---

## 1. Resumo

| Componente | Responsável | Produto esperado (guia) | Situação em 14/09 |
|---|---|---|---|
| S1-E1 — Bases públicas e diagnóstico mineral | Eliel Pelegrino | Base Mineral de Goiás — versão 1 | **Completa.** Planilha v19, dados brutos no GitHub, pipeline que gera a mesma planilha a partir do repositório, relatório de qualidade e atlas no site. Restam duas confirmações com o grupo (seção 3.1). |
| S1-E2 — Projetos minerais e inteligência de mercado | Lucas Maia (a divisão do squad cita também Gabriel Gonçalves em "projetos já existentes") | Radar de Projetos Minerais de Goiás — versão 1 | **Parcial.** No GitHub há três planilhas "CORRIGIDA LUCAS V1" (AMB e CFEM); o radar estruturado com evidências ainda não está no repositório. A camada ANM do radar (aba 04 do E1) já existe. |
| S1-E3 — Dados faltantes e estimativas | Não nomeado na seção do guia (a lista do squad inclui Gabriel Gonçalves e Giovana Dodero) | Método de Tratamento e Estimação de Dados Faltantes — versão 1 | **Não encontrado no GitHub.** Os insumos estão prontos: dicionário com % de vazio, flags de estimativa na aba 12 e arquivos da CCEE. |

Rubrica individual (vale para as nove entregas técnicas):

| Critério | Pontos |
|---|---:|
| Produto técnico | 4,0 |
| Qualidade e consistência | 2,0 |
| Rastreabilidade | 1,5 |
| Integração ao MINERA Goiás | 1,5 |
| Organização e GitHub | 1,0 |

Faixas: 9–10 pronta para incorporação; 7–8,9 completa com ajustes; 5–6,9 parcial; abaixo de 5 insuficiente. Regras gerais: contribuição
identificável no GitHub; uma **entrada** recebida e uma **saída** usada por outro componente; toda variável rastreável até a fonte ou marcada
como estimativa, com método, erro e status observado/estimado.

---

## 2. O que já foi feito

### 2.1 Estudante 1 — Base Mineral de Goiás (Eliel)

**Produto:** `prototipo_bases_consolidadas_v19.xlsx`, com 31 abas, gerado por um pipeline de 19 etapas em Python.
- **No GitHub:** `Squad 1/Bases consolidadas/` (planilha, código e documentação) e `Squad 1/Dados brutos/` (arquivos das fontes).
- **Localmente:** a pasta de trabalho, com todas as fontes catalogadas e as camadas de mapa.

#### Conferência com a "Entrega completa até 21/09" do guia

| Exigência do guia | Situação | Evidência |
|---|---|---|
| Base bruta preservada e base tratada versão 1 | ✅ | `Squad 1/Dados brutos/`: 11 pastas, uma por fonte, cerca de 50 MB, byte a byte como as fontes publicam (o `.gitattributes` da pasta impede a conversão de fim de linha pelo git), com sha256 e data de acesso de cada arquivo. O Cadastro Mineiro vai recortado para Goiás (21.048 das 309.950 linhas), com o sha256 do arquivo nacional registrado. A base tratada é a v17. |
| Principais operações e substâncias de Goiás identificadas | ✅ | 16.656 processos do SIGMINE, 807 operações ativas, 67 minerais, produção do AMB 2010–2025 e CFEM de jan/2022 a ago/2026 |
| Campos mínimos: mineral, titular, operação/processo, município, produção, unidade, ano, coordenadas/geometria e fonte | ✅ | Abas 01–06, 08, 09 e 12; geometria no GeoPackage e no GeoJSON (aba 13) |
| Dicionário de dados e relatório de qualidade | ✅ | Dicionário na aba 14 (439 campos). Relatório de qualidade em `Bases consolidadas/documentacao/relatorio_qualidade.md`: faltantes, duplicidades, divergências e unidades, gerado da planilha. |
| Rotina reproduzível de tratamento | ✅ | `rodar_pipeline.py` (19 etapas, cerca de 13 min). Rodado a partir do layout do GitHub, gera as mesmas abas de dados que a cópia de trabalho (conferido célula a célula). |

#### Fontes exigidas pelo guia

| Fonte | Tipo no guia | Situação |
|---|---|---|
| ANM — AMB/RAL, Cadastro Mineiro, SIGMINE | obrigatórias | ✅ em uso e publicadas em `Dados brutos/` |
| SGB — GeoSGB / RECMIN | obrigatória | ✅ em uso e publicada |
| ANM — CFEM · IBGE — Malhas Municipais | complementares | ✅ em uso e publicadas |
| IMB — Goiás em Dados | complementar | ✅ usada como checagem cruzada da produção do AMB (validação na 14b) e publicada |

#### Contrato de Dados e governança (seção 3 do guia)

- **Campos por linha em todas as abas de dados (01 a 06 e 08 a 13):** fonte, `source_url`, `data_acesso`, `periodo_referencia`,
  `tipo_fonte`, `valor_observado_estimado`, `metodo_estimacao` (quando não observado), `status_validacao` e `responsavel_validacao`, além de
  `operation_id` e `project_id` onde há operação ou projeto. A aba 14b confere isso a cada geração: 36 validações, 33 OK e 3 alertas de dado.
- **IDs estáveis:** `MIN_###`, `COM_CNPJ_<raiz>`, `OPE_<processo>`, `PRJ_<processo-âncora>`, `OCC_<id do SGB>`, `municipality_id` = código IBGE.
- **Divergências registradas, não corrigidas:** 164 linhas do AMB com tonelagem repetida, 89 quantidades da CFEM fora da soma de toneladas,
  45 processos na 09c e 33 mineral-anos em que a CFEM não bate com o AMB.
- **LGPD:** a base mascara o CPF dentro do nome de empresário individual. Os brutos são publicados como a ANM divulga (decisão do Eliel,
  13/09).

#### Integração

- **Entrada e saída declaradas** no `LEIA-ME.md` de `Squad 1/Bases consolidadas/`.
- **Squad 2:** aba 12 (produção por mineral e ano, observada no estado e estimada por operação) e a nota
  `nota_squad2_operacoes_sem_coordenadas.md`, com a lista dos 112 processos sem poligonal. O pacote `pacote_squad2/` traz a aba em CSV no
  formato dos exemplos do Squad 2, o dicionário dos campos e a correspondência com o `production_history` do motor.
- **Squad 3:** a planilha e os brutos em CSV/XLSX entram no banco do site pelo importador; o atlas é gerado da planilha. A aba Panorama do painel (`data/panorama/`) refaz os gráficos e tabelas do Panorama da Mineração de Goiás com a base e os brutos do repositório.
- **Squad 1:** `Squad 1/QUADRO_ENTRADAS_SAIDAS.md` com as chaves compartilhadas e as entradas e saídas do E1, E2 e E3.

#### GitHub

| Commit | Conteúdo |
|---|---|
| `949d2b4` | base v13 e pipeline |
| `c612aa1` | v14 e atlas |
| `66b4f69`, `3bb85da` | v15, camadas de projetos e ocorrências, atlas com novos gráficos, METODOLOGIA |
| `99048e8` | `Dados brutos` por fonte, `Bases consolidadas`, v16 com governança em todas as abas, `load_anm.py` do Squad 3 com o caminho novo |
| `b6e3e3b` | relatório de qualidade, nota ao Squad 2, nota de decisão sobre os basaltos, quadro de entradas e saídas |
| `fead9d0` | este documento de situação |
| `56df030` | v17 (IMB como checagem cruzada na 14b) e dados brutos guardados byte a byte |

#### Versões da planilha

| Versão | O que entrou |
|---|---|
| v0 (10/09) | protótipo do schema com as 15 abas planejadas |
| v1–v5 | Bases 1 a 4: mineral × ano, município × ano, empresa × mineral × ano, mapas |
| v6 | nomes de campo do Contrato de Dados, catálogo de fontes, dicionário e validações |
| v7 | rochas classificadas pelo tipo de uso; aba 09c de alertas |
| v8 | fato longo (aba 08), rastreável até a célula da fonte |
| v9 | aba 12, a interface com o Squad 2 |
| v10 | aba 04, camada ANM do Radar de Projetos (3.377 projetos) |
| v11 | aba 06, ocorrências do RECMIN |
| v12 | LGPD (máscara de CPF), reprodutibilidade e LEIA-ME reescrito |
| v13 | catálogo com 20 fontes e pipeline que roda em outra máquina; primeira publicação no GitHub |
| v14 | regra da 09c corrigida para ouro e prata |
| v15 | camadas de mapa dos projetos (04) e das ocorrências (06); atlas com essas camadas e 7 gráficos novos |
| v16 | campos de governança em todas as abas de dados; dados brutos no GitHub e pipeline que roda a partir deles |
| v17 | IMB como checagem cruzada da produção do estado no AMB (aba 14b); abas de dados iguais às da v16 |

### 2.2 Estudante 2 — Projetos minerais (Lucas Maia)

No GitHub (`Squad 1/dados/`), enviados em 03/09 pela conta compartilhada `mineragoias-rgb`: `PRODUCAO CORRIGIDA LUCAS V1.xlsx` (AMB,
beneficiada), `PRODUCAO BRUTA CORRIGIDA LUCAS V1.xlsx` (AMB, bruta) e `ARRECADAÇÃO CORRIGIDA LUCAS V1.xlsx` (CFEM 2022–2026). O repositório
não documenta que correções foram feitas.

O Estudante 1 deixou pronta a camada ANM do radar (aba 04 e camada `projetos_futuros`): `project_id` estável, processos contíguos agrupados,
classificação por evidência na ANM (provável, possível, sinal), estágio, brownfield e último evento. Capacidade, CAPEX e ano previsto
ficaram vazios de propósito, porque dependem de evidência corporativa e ambiental.

### 2.3 Estudante 3 — Dados faltantes e estimativas

Nenhum artefato no GitHub até 14/09. Insumos disponíveis: `pct_vazio` por campo (aba 14), flags de estimativa (aba 12) e consumo da CCEE
para Goiás, 2024–2026 (`Squad 1/dados/CCEE/`).

### 2.4 Outros arquivos em `Squad 1/dados/`

As cópias idênticas de brutos que estavam ali (AMB, CFEM, investimento, SIGMINE, Panorama e Mineradoras) foram movidas para
`Squad 1/Dados brutos/`. Continuam em `Squad 1/dados/`:

| Arquivo | Observação |
|---|---|
| `CCEE/parcela_carga_consumo_2024–2026_GO.csv` | lidos pelo painel do site (`Squad 3/backend/dashboard.py`) — não mover |
| `ResultadoRodadaDisponibilidade (1).csv` | lido pelo radar do Squad 3 (`radar_api.py`) — não mover |
| `Substancia.txt` | dicionário de substâncias lido por `Squad 3/database/load_anm.py` — não mover |
| planilhas "CORRIGIDA LUCAS V1" | do Estudante 2 |
| `Base_Mineracao_Goias_Producao_Energia_2023_2026.xlsx`, `Panorama Mineracao Goias.html`, `GO.kmz`, `SQUAD1_PLANEJAMENTO.md` | versões exploratórias e planejamento |

O que é cada um, quem usa e o que propomos está em `Squad 1/PROPOSTA_ORGANIZACAO_DADOS.md` (nada foi movido).

---

## 3. O que falta para a Entrega 1 (até 21/09)

### 3.1 Estudante 1 — ajustes finais

- [x] **a.** v15 e atlas no `main` (13/09).
- [x] **b.** Entrada e saída de integração declaradas no LEIA-ME de `Bases consolidadas` (14/09).
- [x] **c.** Base bruta acessível: `Squad 1/Dados brutos/` (14/09).
- [x] **d.** Relatório de qualidade num documento único (14/09).
- [x] **e.** IMB — Goiás em Dados como checagem cruzada (v17, 14/09). A 14b compara a produção do estado com a produção beneficiada do
  AMB em 14 minerais, 2010–2016; o IMB não traz produção mineral depois de 2016. Iguais em todos os anos só amianto e saibro; fosfato,
  manganês, ouro e prata são iguais em parte dos anos; cobre, nióbio e níquel ficam sempre abaixo (o IMB parece publicar metal contido).
  A divergência fica registrada e a base segue o AMB. Os quatro CSVs estão em `Dados brutos/IMB - Goiás em Dados/`.
- [x] **f.** Nota ao Squad 2 sobre as operações sem coordenadas (14/09). Enviar ao Squad 2 fica com o Eliel.
- [ ] **g. Basaltos:** nota de decisão publicada (`nota_decisao_basaltos.md`); falta a decisão do grupo.
- [x] **h.** LGPD dos brutos: publicar como a ANM divulga (decisão do Eliel, 13/09).
- [ ] **i. Confirmar com o Squad 2** que a aba 12 atende a intensidade e o motor. O pacote está em `Bases consolidadas/documentacao/pacote_squad2/`
  (14/09): aba 12 em CSV no formato do motor, dicionário, correspondência com o `production_history` e cinco pontos a confirmar. Falta o
  Eliel enviar o rascunho de mensagem e o Squad 2 responder.
- [x] **j.** Campos de governança em todas as abas de dados (v16, 14/09).

### 3.2 Estudante 2 — Radar de Projetos v1 (exigências do guia)

- [ ] Radar estruturado e deduplicado, partindo da aba 04 para manter o `project_id`.
- [ ] Evidências por projeto (SEMAD, CVM, RI das empresas), com fonte rastreável e data; imprensa nunca como única evidência de "definido".
- [ ] Critério de maturidade completo e documentado: operação, expansão, construção, definido, provável, possível e sinal.
- [ ] Campos mínimos: `project_id`, projeto, empresa, mineral, município, estágio, capacidade, ano previsto, fonte, data, classificação e
  status de validação.
- [ ] Lista dos projetos que podem afetar a produção e a demanda de energia até 2040.
- [ ] Documentar as correções das planilhas "LUCAS V1".
- [ ] Contribuição identificável no GitHub (os envios saíram pela conta compartilhada).

### 3.3 Estudante 3 — Método de dados faltantes v1 (exigências do guia)

- [ ] Matriz de completude das variáveis das bases dos Estudantes 1 e 2.
- [ ] Escolher pelo menos uma variável material para a projeção de energia.
- [ ] Método base simples; machine learning só com amostra suficiente, com validação e comparação com o método simples.
- [ ] Base com flags `valor_observado_estimado`, `metodo_estimacao` e erro/confiança, mantendo o valor original.
- [ ] CCEE: demonstrar o pareamento entre agente/ativo de carga e operação mineral.
- [ ] Notebook ou código reproduzível no GitHub.

### 3.4 Squad 1 como um todo

- [x] Quadro de entradas e saídas (`Squad 1/QUADRO_ENTRADAS_SAIDAS.md`, 14/09).
- [ ] Mesmas chaves em todas as entregas (depende do E2 e do E3 usarem as chaves da base do E1).
- [ ] Organizar o que sobrou em `Squad 1/dados/`. Proposta publicada em `Squad 1/PROPOSTA_ORGANIZACAO_DADOS.md` (14/09), sem mover nada;
  faltam a decisão do Lucas sobre as planilhas "LUCAS V1", a confirmação do Squad 3 sobre a base exploratória e a origem do `GO.kmz`.
- [ ] Insumos para o E2 (modelo do radar a partir da aba 04) e o E3 (matriz de completude): script pronto na cópia local, aguardando o ok do
  Eliel para gerar e publicar.

---

## 4. Depois da Entrega 1 (roadmap do `SQUAD1_PLANEJAMENTO.md`)

Tabelas `evidence` e `sources` com histórico; Evidence Score com pesos validados pela equipe; entity resolution assistida por IA com fusão
validada por humano; fila de revisão verde / amarelo / vermelho; coletores por fonte; detecção de mudanças entre versões de documentos;
consulta da base pelo Squad 3 via banco e API.

---

## 5. Riscos e limitações conhecidas

- **AMB/RAL é declaratório;** as divergências estão registradas (09c, 14b, relatório de qualidade), não corrigidas.
- **A ANM republica os arquivos com frequência:** reproduzir uma versão exige os arquivos com o sha256 da aba 07 (os publicados em
  `Dados brutos/` são os usados na v17).
- **CFEM:** a quantidade comercializada não serve como proxy de produção; o `CPF_CNPJ` veio em notação científica; 2026 é parcial.
- **Produção sem coordenadas:** 457 linhas da aba 12 (112 processos, sobretudo ouro em Crixás) não têm localização — ver a nota ao Squad 2.
- **RECMIN** é evidência geológica, não projeto nem mina. **Processo não é mina em operação.**
- **Brutos com dados pessoais:** alguns arquivos da ANM trazem nome e CPF de pessoas físicas, publicados como a ANM divulga.
- **Prazo:** o E2 e o E3 dependem da base do E1, que está pronta; o risco maior está nas evidências corporativas (E2) e no pareamento com a
  CCEE (E3).

---

## 6. Onde encontrar

| O quê | Local |
|---|---|
| Planilha entregável | `Squad 1/Bases consolidadas/documentacao/prototipo_bases_consolidadas_v19.xlsx` (comece pela aba `00_LEIA-ME`) |
| Dados brutos, por fonte | `Squad 1/Dados brutos/` (catálogo no `LEIA-ME.md` de lá) |
| Código do pipeline | `Squad 1/Bases consolidadas/base_consolidada_work/scripts/` |
| Relatório de qualidade | `Squad 1/Bases consolidadas/documentacao/relatorio_qualidade.md` |
| Nota ao Squad 2 e lista de processos sem coordenadas | `Squad 1/Bases consolidadas/documentacao/nota_squad2_operacoes_sem_coordenadas.md` e `operacoes_sem_coordenadas.csv` |
| Pacote da aba 12 para o Squad 2 | `Squad 1/Bases consolidadas/documentacao/pacote_squad2/` |
| Nota de decisão sobre os basaltos | `Squad 1/Bases consolidadas/documentacao/nota_decisao_basaltos.md` |
| Quadro de entradas e saídas | `Squad 1/QUADRO_ENTRADAS_SAIDAS.md` |
| Proposta de organização de `Squad 1/dados/` | `Squad 1/PROPOSTA_ORGANIZACAO_DADOS.md` |
| Entrega ao Squad 2 | aba `12_interface_squad1_squad2` |
| Atlas do site | `data/atlas/` (README com as limitações) |
| Guias | `Squads (1).docx`, `📄 MINERA Goiás — Contrato de Dados.txt` e `SQUAD1_PLANEJAMENTO.md` |

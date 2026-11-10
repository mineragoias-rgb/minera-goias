# Projetos minerais de Goiás

Base consolidada de **projetos nomeados** — da operação em curso ao indício de investimento —, com empresa, mineral, município, fase,
maturidade, capacidade, CAPEX, cronograma e a evidência que sustenta cada linha.

| Arquivo | Conteúdo |
|---|---|
| `base_curada.json` | A curadoria: projetos e evidências. É aqui que se edita |
| `../Squad 1/entregas/projetos_minerais_goias.xlsx` | Entrega em três abas: PROJETOS, NOTÍCIAS e METODOLOGIA |
| `../data/projetos/projetos.json` | O mesmo conteúdo para a aba Base de dados do painel |

Gerado por `python scripts/build_projetos_base.py`. Conferido por `tests/test_projetos.py`.

## O que esta base não é

**Não é o pipeline cadastral da ANM.** Esse universo já está no atlas deste repositório: 3.377 processos da aba 04 da base do Squad 1,
com titular, substância, fase e polígono. Lá está *tudo* o que tem título minerário; aqui está o que virou **projeto com nome, empresa e
cronograma**. As duas se complementam e não se somam.

## As sete maturidades

`OPERAÇÃO > EXPANSÃO > CONSTRUÇÃO > DEFINIDO > PROVÁVEL > POSSÍVEL > SINAL`

**Maturidade mede o grau de comprovação econômica, não a etapa administrativa** — por isso `Fase` e `Maturidade` são colunas separadas.
Uma pesquisa mineral com sondagem financiada e cronograma de implantação é `PROVÁVEL`; a mesma fase sem nada disso é `POSSÍVEL`.

Dois exemplos do que a distinção resolve nesta base:

- **Pilar de Goiás** reiniciou a lavra subterrânea em outubro de 2026, mas ainda não fez o primeiro vazamento de ouro. Fase é
  *Reativação*; maturidade é `CONSTRUÇÃO`, não `OPERAÇÃO`, porque `OPERAÇÃO` exige produção comercial.
- **Carina** tem estudo de pré-viabilidade publicado e reservas declaradas em NI 43-101, mas nenhum comunicado de decisão final de
  investimento foi localizado. Fica `PROVÁVEL`, não `DEFINIDO`.

## Regras que a base não quebra

**NA é declaração, não lacuna.** Significa que a informação não foi encontrada em fonte pública — não zero, não ausência do atributo.
O gerador recusa campo vazio.

**Linguagem especulativa não vira fato.** "A expansão poderia dobrar a produção" ficou como texto em Observações, não como capacidade
anunciada. "Um fundo chinês tem interesse em aportar R$ 1 bilhão" entrou como `SINAL` em linha própria, não como CAPEX do projeto.

**CAPEX e capacidade só quando divulgados**, na moeda e na unidade de origem, sem conversão e sem estimativa a partir de outro projeto.
Um CAPEX declarado tem de vir com moeda e ano; uma capacidade, com unidade. Há teste para os dois.

**Divergência entre fontes é registrada, não resolvida em silêncio.** O CAPEX do Carina aparece como US$ 582,3 milhões, US$ 599 milhões,
US$ 680 milhões e US$ 780,9 milhões conforme a fonte e a data: ficou o valor atribuído à própria empresa, e os outros três estão em
Observações. O prazo do fim do amianto em Minaçu tem duas leituras da mesma decisão do STF, e as duas estão registradas.

**Deduplicação por empreendimento, não por notícia.** Saúva está separado de Chapada porque tem cava e decisão de investimento próprias;
Barro Alto está separado de Codemin porque são plantas em municípios diferentes, ainda que a produção seja publicada em conjunto.

## Limitações desta versão (v1)

A coleta foi feita por busca na web num ambiente cujo proxy de egresso bloqueia o acesso direto a páginas: **nenhum documento foi aberto e
lido na origem**. Não houve leitura de EIA/RIMA, de relatório NI 43-101, de formulário da CVM ou de processo de licenciamento — apenas do
que buscadores e veículos reproduzem deles. Em consequência:

- **A cobertura não é exaustiva.** Uma reportagem de agosto de 2026 cita pelo menos 18 empresas estrangeiras com processos de terras raras
  no Brasil sem nomeá-las; esta base não as alcança.
- **Titânio e manganês entram sem empresa**, como `SINAL`, vindos de um mapeamento estadual cujo documento não foi lido e cuja data não
  foi estabelecida.
- **Areia, brita, argila, rochas ornamentais, quartzito e água mineral estão sub-representados**, porque raramente geram projeto nomeado
  na imprensa — ainda que respondam por muitos títulos minerários no estado.
- **Nenhum processo de licenciamento ambiental foi consultado** no sistema estadual.

O caminho para fechar essas lacunas é a consulta direta ao SIGMINE/ANM, ao sistema de licenciamento da SEMAD e aos arquivos da SEC, da CVM
e do SEDAR+ — todos alcançáveis da VPS, que tem rede aberta.

## Como atualizar

1. Editar `base_curada.json`: acrescentar o projeto, ou corrigir o existente, e **sempre** acrescentar a evidência correspondente.
2. Rodar `python scripts/build_projetos_base.py`. Ele recusa a curadoria que quebre as regras: maturidade fora das sete categorias,
   projeto sem evidência, evidência órfã, ID repetido, campo vazio, CAPEX sem moeda.
3. Rodar `python -m unittest discover -s tests -p test_projetos.py`.
4. Rodar `python scripts/build_catalogo_bases.py`, para o catálogo do painel registrar a nova data.

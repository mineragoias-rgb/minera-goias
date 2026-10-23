# Robô de atualização das bases (P3M e ANM)

Primeira versão, de 23/10/2026. Toda segunda-feira, às 06:17 de Brasília, o workflow
[`robo-bases.yml`](../.github/workflows/robo-bases.yml) baixa de novo as bases do P3M e da ANM. Em seguida ele:

1. confere se cada arquivo novo tem a forma que o site usa;
2. trata o arquivo como o repositório guarda (recorte de Goiás);
3. refaz tudo o que sai dele, até o site;
4. roda os testes e publica na `main`.

A VPS baixa a `main` em até 2 minutos.

O robô **não inventa nem corrige dado**:

- arquivo igual ao atual não gera commit;
- arquivo com forma diferente é **barrado** e o atual continua no ar. Só aquele arquivo (ou aquela camada do mapa) fica de
  fora; os outros seguem;
- o que passou vai como a fonte publicou, com o mesmo recorte de antes.

## O que ele atualiza

| Fonte | O que baixa | Tratamento (o mesmo de antes) | Onde grava |
|---|---|---|---|
| P3M (SGB) | as camadas que o mapa usa (`--p3m-escopo todas`: as 157 com URL), pela URL de cada uma no inventário | recorte pelo limite de Goiás (`recorte.py`) | `Squad 1/P3M/Original` e `Recortado pelo polígono de Goiás` |
| ANM — SIGMINE | `SIGMINE/PROCESSOS_MINERARIOS/GO.zip` | nenhum (já vem só Goiás) | `Squad 1/Dados brutos/ANM - SIGMINE` |
| ANM — Cadastro Mineiro | os 13 CSV nacionais de `SCM/` | linha com município de Goiás ou processo com poligonal em Goiás | `ANM - Cadastro Mineiro` |
| ANM — CFEM | `CFEM/CFEM_Arrecadacao_2022_2026.csv` | linhas com UF = GO, no formato antigo (ver abaixo) | `ANM - CFEM` |
| ANM — Anuário Mineral | `AMB/Producao_Bruta.csv` e `Producao_Beneficiada.csv` | nenhum (arquivo nacional) | `ANM - Anuário Mineral Brasileiro (AMB)` |

As URLs e a forma esperada de cada fonte da ANM ficam em [`fontes.json`](fontes.json). As do P3M ficam na coluna
`url_download` de [`inventario_p3m.csv`](../Squad%201/P3M/inventario_p3m.csv).

Ficam de fora:

- as camadas do P3M guardadas em partes (SIGEF), que precisam ser atualizadas à mão;
- o limite de Goiás (`GO_UF_2024`), que é do IBGE.

## Os tratamentos são os mesmos de antes, conferidos

- **Recorte do P3M** (`recorte.py`). Segue as regras do LEIA-ME do Recortado:
  - ponto dentro ou na divisa fica;
  - linha ou polígono que cruza a divisa é cortado;
  - polígono inválido é corrigido (`make_valid`);
  - fiapo de divisa sai (menos de 1% da área e menos de 10 km², medidos em EPSG:5880);
  - a saída vai em SIRGAS 2000 com `.cpg` UTF-8.

  Refeito sobre os originais do repositório, o recorte reproduziu 155 das 156 camadas recortadas em 21/10/2026:
  - 154 saíram com os mesmos bytes em `.shp`, `.shx`, `.dbf` e `.prj` (fora a data que o `.dbf` grava no cabeçalho);
  - em 1 (Uso Sustentável), um polígono saiu com as partes em outra ordem, com as mesmas coordenadas e a mesma área;
  - os 1.416 fiapos removidos nessas camadas são os mesmos do índice.

  A que falta é o SIGEF Público, guardado em duas partes, que o robô não atualiza.
- **Recorte da ANM** (`anm_recorte.py`). As linhas que ficam são gravadas byte a byte como a ANM publica. A regra do Cadastro
  Mineiro é a do pipeline (`go_municipio_id`): um município com sufixo de outra UF, como "BARRO ALTO - BA", não casa pelo nome.
  Refeito sobre os arquivos do repositório, o recorte reproduziu as contagens que o Eliel registrou a partir dos arquivos
  nacionais em `recorte_goias.json`: linhas, linhas com município de Goiás e processos do SIGMINE, nos 13 arquivos.
- **CFEM no formato antigo** (`formato_csv.py`). Em outubro de 2026 a ANM passou a publicar a CFEM separada por vírgula e com
  aspas. O pipeline do Squad 1 e o Radar leem o formato antigo: ponto e vírgula, sem aspas, cp1252, CRLF. A conversão muda só a
  escrita:
  - separador, aspas, codificação e quebra de linha voltam a ser os do arquivo atual;
  - o separador decimal volta a ser a vírgula. O Radar tira os pontos como milhar, então `41474.14` viraria 4.147.414;
  - a data volta a `dd/mm/aaaa hh:mm`, que é como a governança da planilha lê.

  O resto do valor fica como a ANM publicou, inclusive o que ela tiver corrigido. A CFEM do repositório reescrita no formato
  novo volta byte a byte. Um valor que o formato antigo não representa (com `;`, aspas ou quebra de linha) barra o arquivo.
  O mesmo vale para uma coluna com dois estilos de número.

  O log da execução mostra a forma de cada coluna (dígito vira 9, letra vira a), sem nenhum valor. Mostra também quantas
  linhas do arquivo atual reaparecem iguais. A conversão vale só para fonte com `converter_formato` em `fontes.json`; hoje,
  só a CFEM. Em qualquer outra, formato novo é barrado.

## Checagem de forma (`forma.py`)

O padrão é o arquivo que está no repositório, porque é dele que os geradores e o site dependem, mais o que o site exige por
escrito. Um **bloqueio** impede o arquivo de entrar; um **aviso** só vai para o relatório.

| | Bloqueia | Avisa |
|---|---|---|
| CSV (ANM) | página HTML ou XML de erro no lugar do arquivo; arquivo vazio; não decodifica na codificação esperada (cp1252); separador trocado; colunas diferentes (nome ou ordem); linhas com número de campos errado; menos de 90% das linhas atuais; coluna numérica ou de data que deixou de ser; número com um separador que a coluna não tinha (`41474.14` onde era `41474,14`); data com outra escrita (`2026-08-31` onde era `31/08/2026`); coluna que estava preenchida e esvaziou | linhas a mais ou a menos |
| Shapefile (P3M e SIGMINE) | não é zip (erro do GeoServer); falta `.shx`, `.dbf` ou `.prj`; geometria mudou; sistema de coordenadas mudou; caixa fora do Brasil (coordenadas trocadas) ou longe de Goiás; menos de 50% dos registros (90% no SIGMINE); sumiu ou mudou de tipo um campo que o mapa lê (`scripts/mapa_camadas.json`; no SIGMINE, qualquer campo) | registros a mais ou a menos; campos novos; campo que o site não usa sumiu |
| Recorte do P3M | ficou sem nenhuma feição em Goiás; o recortado novo falha nas mesmas regras acima | |
| Chave das camadas do mapa | a chave da camada (`chave` em `scripts/mapa_camadas.json`) ficaria repetida ou vazia no conjunto dos zips dela, contando os novos e os atuais. Barra só os zips novos daquela camada | |
| Planilha consolidada | ALERTA novo na aba 14b. São exceção os listados em `fontes.json` (`planilha.alertas_esperados`), cada um com o motivo | |

`python robo/robo_bases.py --checar` faz a checagem inversa, sem rede: confere se os arquivos que **estão** no repositório seguem o
padrão. Olha o recorte de Goiás refeito sobre cada arquivo, o sha256 e o tamanho no LEIA-ME de `Dados brutos`, as datas em
`datas_de_acesso.json`, o `.cpg`, o `.prj` e as contagens dos recortados do P3M, e os campos que o mapa lê. O
`tests/test_robo.py` roda essa checagem e também execuções completas contra um portal falso.

## Como a base nova chega ao site

```
robo_bases.py ──► dados brutos (P3M, ANM) ──────────────────────────────── commit 1
   └ ANM mudou ──► pipeline do Squad 1 (rodar_pipeline.py, ~15 min) ─► planilha v17 refeita
                   ├ trava: nenhum ALERTA novo na aba 14b
                   ├ relatório de qualidade e nota do Squad 2
                   ├ atlas (scripts/build_atlas_base.py)
                   └ Radar de Projetos (troca só se os valores mudaram) ──── commit 2
scripts/atualizar_derivados.py ──► inventário do P3M, mapa, panorama, Squad 2, simulador… ── commit 3
testes do site e do robô ──► push para a main ──► VPS
```

Rodar o pipeline em cima dos dados do repositório, sem nada novo, reproduz **todas as abas de dados da v17 célula por célula**.
Também reproduz `data/atlas` (o `processes.json` byte a byte; no `atlas.json`, só a data e o sha256 da planilha mudam). Mudam
só as abas de catálogo e governança (07, 14 e 14b), porque o GitHub guarda o recorte de Goiás do Cadastro Mineiro e não guarda
algumas fontes do catálogo. A primeira vez que o robô refizer a planilha, essas abas passam a descrever o arranjo do GitHub, e o
00_LEIA-ME registra a data em que o robô atualizou os dados (`MINERA_DATA_DADOS`).

## Rodar à mão

```bash
pip install geopandas==1.1.3 pyogrio==0.12.1 shapely==2.2.0 pyshp==3.1.6    # o P3M precisa; a ANM roda só com a biblioteca padrão
python robo/robo_bases.py --sem-gravar                    # baixa e confere tudo, sem gravar
python robo/robo_bases.py --fontes anm --so CFEM          # só a CFEM
python robo/robo_bases.py --fontes p3m --so mvw_minas_ativas_grp
python robo/robo_bases.py --checar                        # o repositório está no padrão?
```

No GitHub: **Actions → Robô das bases (P3M e ANM) → Run workflow**. Dá para escolher as fontes, o escopo do P3M e se publica.
O resumo de cada execução fica na página dela: o que mudou, o que foi barrado e por quê, a aba 14b e os derivados.

### Arquivo barrado

O que a fonte publicou e foi barrado sobe como artefato da execução, **robo-bases**, junto com `robo.md` e `robo.json`. O
`LEIA-ME.txt` do artefato diz o motivo de cada arquivo. Arquivo acima de 60 MB vai só com os primeiros 2 MB, que bastam para
ver o cabeçalho.

Às vezes a queda de linhas é real: a fonte limpou registros, ou mudou a regra do que publica. Quem conferir isso na fonte pode
rodar o workflow com **aceitar_queda** (ou `--aceitar-queda`). O campo leva:

- o id da ANM em `fontes.json` (`CFEM`, `CADASTRO`…);
- ou o nome do arquivo (`Alvara_de_Pesquisa.csv`);
- ou a camada do P3M (código `vw_…` ou nome do zip).

Separe por vírgula. Só a trava de quantidade sai, e só nessa execução. As outras checagens continuam.

Saída do robô:

- 0: tudo certo;
- 1: alguma fonte foi barrada ou não baixou. O que passou foi gravado, e o job fica vermelho para alguém olhar;
- 3: `--checar` ou `--conferir-planilha` acharam problema.

## Limites desta primeira versão

- **Rede.** Nos testes de 23/10/2026, os servidores do GitHub baixaram da ANM e do SGB todas as URLs de `fontes.json` e do
  inventário. Mesmo assim, um portal pode recusar ou cair. Nesse caso, a fonte aparece como "não baixou" no resumo e o resto
  segue. Se a recusa continuar, o robô pode rodar na VPS (`python robo/robo_bases.py`) e o commit seguir por lá.
- **O GeoServer do SGB oscila.** No teste das 17:40 de 23/10/2026, seis camadas voltaram com erro do GeoServer, e os
  mapeamentos geológicos vieram com `objectid` repetido entre as escalas. Quarenta minutos depois, as 53 camadas vieram iguais
  às do repositório. A conferência da chave de cada camada do mapa existe por causa disso.
- **Nome de arquivo que muda.** A CFEM traz a faixa de anos no nome (`2022_2026`). Quando a ANM publicar `2022_2027`, a URL
  antiga falha e alguém precisa trocar a URL e o nome do arquivo, no robô e no pipeline.
- **Uma planilha só.** O robô refaz a v17 no lugar e não cria v18: a estrutura é a mesma e os dados são os do dia.
- **Catálogo do P3M.** Só é baixado de novo, com a data de atualização de cada camada no SGB, quando alguma camada mudou.
- **Encontrado no teste de 23/10/2026, ainda sem solução:**
  - a **CFEM** passou a vir separada por vírgula e com aspas em todos os campos (`"Ano","Mês","Processo",…`). Antes vinha
    com `;` e sem aspas. O pipeline e o Radar leem o formato antigo, então o robô barra o arquivo. Falta decidir entre
    converter o arquivo novo para o formato antigo no recorte ou ensinar os leitores o formato novo. Antes, é preciso ver no
    artefato se os números também mudaram de formato;
  - quatro arquivos nacionais do **Cadastro Mineiro** encolheram na ANM:

    | Arquivo | Linhas antes | Linhas em 23/10/2026 |
    |---|---|---|
    | Portaria de Lavra | 15.493 | 549 |
    | Requerimento de Lavra | 21.371 | 2.748 |
    | Relatório de Pesquisa Aprovado | 15.695 | 4.686 |
    | Alvará de Pesquisa | 111.614 | 81.479 |

    O robô barrou os quatro, e o site segue com os arquivos anteriores. Antes de usar `aceitar_queda`, confira na ANM se a
    queda é real.
- **Ainda à mão:** CCEE (o portal recusa download automatizado), investimento em pesquisa e rodadas de disponibilidade (sem URL
  registrada), SIGBM e as fontes de energia. Ver `docs/fontes_de_dados.md`.

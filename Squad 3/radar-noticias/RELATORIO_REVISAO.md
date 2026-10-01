# Revisão do `news/radar.py`

Revisão feita em 18–19/09/2026 sobre `news/radar.py` (371 linhas, versão `0.1-prototype`), para decidir se o código existente servia ou se era preciso escrever outro.

## Veredito

**Aproveitar, não refazer.** A arquitetura é boa e foi mantida inteira. Foram encontrados **quatro defeitos**, todos localizados e todos corrigidos em `radar.py` nesta pasta. Nada foi reescrito do zero.

O que já estava certo e foi preservado:

- Matéria identificada pelo hash do link, então reexecutar no mesmo dia não duplica.
- Feed fora do ar não derruba a rodada: a execução vira `partial` e o erro fica registrado na fonte.
- Cada sinal guarda a frase que o originou, então dá para auditar de onde veio.
- O veredito de tendência espera um mínimo de matérias distintas antes de se pronunciar.
- O README do módulo antigo é honesto sobre os limites do protótipo.

Isso é desenho maduro. Jogar fora seria desperdício.

---

## Defeito 1 — substância casada por trecho, não por palavra inteira

**Onde:** `news/radar.py:173`, dentro de `analyse()`.

O código usava `fold(term) in folded`, um teste de substring. A função `mentions()`, que faz o casamento por palavra inteira, já existia logo acima em `news/radar.py:139` — mas só era usada na marca regional, não na detecção de substância.

**Evidência**, rodando o próprio código antigo:

```
'Tesouro Direto tem alta de 2%...'          -> SINAL: ouro | up
'Governo anuncia queda do tesouro...'       -> SINAL: ouro | down
'A nova regra cobre 30% dos contratos...'   -> SINAL: cobre | up
```

"Tes**ouro**" vira sinal de ouro. O README do módulo antigo afirma que a comparação é por palavra inteira: a proteção existia, só não tinha sido aplicada aqui.

**Gravidade: alta.** Contamina direto a tabela `news_trends`, que é o produto final. E piora com as fontes de economia da lista nova — Folha Mercado, InfoMoney, G1 Economia — que é justamente onde "tesouro" aparece toda hora.

**Correção:** `analyse()` passou a usar o `mentions()` que já existia.

**Resultado, comparando os dois lado a lado:**

| Frase | Antigo | Novo |
|---|---|---|
| Tesouro Direto tem alta de 2% | `ouro/up` | — |
| Governo anuncia queda do tesouro | `ouro/down` | — |
| Preço do níquel sobe 4% | `niquel/up` | `niquel/up` |
| Ouro recua após decisão do Fed | `ouro/down` | `ouro/down` |

Falso positivo eliminado, verdadeiro positivo preservado. Sem regressão.

**O que a correção não resolve:** "a regra **cobre** 30% dos contratos" continua virando sinal de cobre, nos dois. Aí `cobre` é palavra inteira mesmo — é o verbo. Resolver isso exige classe gramatical, não lista de palavras. Fica registrado como limite conhecido no README.

---

## Defeito 2 — user-agent recusada, e recusada nos dois sentidos

**Onde:** `news/radar.py:69`, em `fetch()`.

A UA declarada era `minera-goias-news-radar/0.1`. O `mining.com` responde **403** para ela.

**Evidência**, com a função de rede do próprio radar antigo:

```
FALHA  HTTPError: HTTP Error 403: Forbidden  https://www.mining.com/feed/
FALHA  HTTPError: HTTP Error 403: Forbidden  https://www.mining.com/commodity/nickel/feed/
```

No `--check` da lista nova rodado com o código antigo, isso derrubou **8 fontes**: Mining.com, suas 6 fontes por substância e a Australian Mining.

**A descoberta que complicou a correção:** trocar para UA de navegador conserta essas 8 e **quebra outras duas**. Medido em 19/09/2026:

| Site | UA de robô | UA de navegador |
|---|---|---|
| mining.com | **403** | 200 |
| mining-technology.com | 200 | **403** |
| power-technology.com | 200 | **403** |

Não existe UA única que atenda a lista toda.

**Correção:** `fetch()` tenta a UA de navegador e, se levar 401/403/406/429, repete com a de robô. As seis URLs do teste passam agora, nos dois sentidos.

---

## Defeito 3 — gzip não tratado, e o efeito é intermitente

**Onde:** `news/radar.py:69`, em `fetch()`.

O G1 devolve o corpo compactado em parte das requisições, sem que se peça. O parser recebia bytes gzip e estourava `ParseError`.

**Evidência**, três tentativas seguidas na mesma URL:

```
tentativa 1: FALHA ParseError: not well-formed (invalid token): line 1, column 0   bytes=96001
tentativa 2: FALHA ParseError: not well-formed (invalid token): line 1, column 0   bytes=96001
tentativa 3: OK 100 itens                                                         bytes=310316
```

Duas de três vieram com os bytes mágicos `\x1f\x8b`.

**Gravidade: alta, e sorrateira.** Não é falha estável: o feed funciona num dia e some no outro, sem explicação no log. Afeta G1 Goiás, G1 Economia e G1 Brasil — três das fontes de maior volume da lista.

**Correção:** `read_once()` decide pelos bytes mágicos, não pelo cabeçalho, porque o cabeçalho pode vir ausente.

---

## Defeito 4 — metadado da fonte nunca atualiza

**Onde:** `news/radar.py:210` e `news/radar.py:239`, as duas cópias do mesmo `INSERT`.

O `ON CONFLICT(source_id) DO UPDATE` mexia só em `last_status` e `last_seen`. Nome, idioma, `tipo` e `escopo` ficavam congelados no valor da primeira inserção.

**Evidência:**

```
1a rodada  escopo = nacional
2a rodada  escopo = nacional   (esperado: setorial, após editar o config)
```

**Gravidade: alta para o que foi pedido.** É exatamente o defeito que mataria o filtro por `tema`: o campo novo só chegaria ao banco em fonte nova; nas já cadastradas, nunca. A página filtraria por um valor desatualizado sem ninguém perceber.

**Correção:** as duas cópias do `INSERT` viraram uma função só, `remember_source()`, que atualiza todos os metadados a cada rodada. A `url` fica de fora do `UPDATE` de propósito: o `source_id` é o hash dela, então não pode divergir numa linha existente.

Além disso, `news_sources` ganhou a coluna `tema`, com migração por `ALTER TABLE` para bancos escritos pela versão antiga — `CREATE TABLE IF NOT EXISTS` não adicionaria a coluna sozinho.

**Verificação:**

```
1a rodada tema = mineracao
2a rodada tema = energia   (esperado: energia)
```

---

## Efeito das correções na lista de 63 fontes

Mesma lista de 63 fontes, mesmo comando `--check`, só mudando o código:

| Versão | Fontes que responderam |
|---|---|
| `news/radar.py` (antigo) | 53 / 63 |
| `radar.py` desta pasta, só com a UA de navegador | 58 / 63 |
| `radar.py` desta pasta, versão final | **63 / 63** |

Das 10 falhas do código antigo, 9 eram culpa dos defeitos 2 e 3 — não da lista de fontes. A décima era a Resource World, que é servidor lento de verdade e passou na rodada final.

O passo intermediário está registrado de propósito: trocar a UA para navegador consertou 8 fontes e quebrou 2 (Mining Technology e Power Technology). Só a tentativa com as duas UAs fecha a lista inteira.

## Observações menores, não corrigidas

- `response.read(MAX_FEED_BYTES)` trunca em 8 MB sem avisar. Um feed maior que isso vira XML cortado e cai como `ParseError`. Nenhum feed da lista chega perto, então ficou como está.
- `report['signals']` incrementa mesmo quando o `INSERT OR IGNORE` não insere nada. É contagem de relatório, não afeta dado gravado.

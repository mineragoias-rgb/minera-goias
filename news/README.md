# Radar de notícias — protótipo

Coleta diária de notícias sobre **energia** e **terras raras** (e outras substâncias configuradas), guarda cada matéria com sua origem e data, e lê no texto a **direção** que a imprensa está dando aos preços. Roda todo dia às **01:00** pelo `minera-goias-news.timer`.

## O que ele é e o que ele não é

O radar **não produz série de preços**. Ele não cota commodity, não consulta bolsa e não substitui fonte de mercado. O que ele entrega é **evidência sobre o que está sendo publicado**: quantas matérias falaram de cada substância na semana, quantas usaram linguagem de alta e quantas de baixa, e quais preços apareceram citados no texto — sempre com o trecho que originou cada sinal.

Isso é um indício antecedente, não um dado de preço. Uma semana com muita notícia de alta pode refletir repercussão de um mesmo fato. Use como alerta para investigar, nunca como número para relatório.

## Como funciona

1. **Coleta** — lê os feeds RSS/Atom de `feeds.json`. Cada matéria é identificada pelo hash do link, então reexecutar no mesmo dia não duplica nada. Um feed fora do ar não derruba os outros: a execução termina como `partial` e registra o erro na fonte.
2. **Leitura de sinais** — quebra título e resumo em frases. Numa frase que cite uma substância **e** traga palavra de direção (alta/queda, surge/plunge…), grava um sinal com a frase como evidência. Frase sem palavra de direção não vira sinal. Empate entre palavras de alta e de baixa também não vira sinal.
3. **Preço citado** — quando a mesma frase traz moeda e valor, o número é extraído com unidade e escala (`USD 9 thousand per tonne` vira 9000, `R$ 61/MWh` vira 61). A presença de preço aumenta a confiança do sinal.
4. **Tendência semanal** — por substância e semana ISO, soma altas e baixas e calcula `score = (alta − baixa) / total`. O veredito só sai com um mínimo de matérias distintas (`min_items_for_trend`, hoje 3); abaixo disso fica `evidencia_insuficiente`, mesmo que o score seja extremo.

| Veredito | Quando |
|---|---|
| `pressao_de_alta` | score ≥ +0,34 com matérias suficientes |
| `pressao_de_baixa` | score ≤ −0,34 com matérias suficientes |
| `sem_direcao_clara` | matérias suficientes, mas equilibradas |
| `evidencia_insuficiente` | menos matérias que o mínimo configurado |

## Tabelas

| Tabela | Conteúdo |
|---|---|
| `news_runs` | Histórico das execuções, versão do radar e relatório completo |
| `news_sources` | Feeds configurados, último status e última leitura |
| `news_items` | Matérias com título, link, resumo, data de publicação e execução de origem |
| `news_signals` | Um sinal por substância e frase: direção, confiança, evidência e preço citado |
| `news_trends` | Balanço semanal por substância, com score e veredito |

## Executar localmente

```sh
# Com rede, usando os feeds reais
python3 news/radar.py --db /tmp/radar.sqlite --report /tmp/radar.json

# Sem rede, com as fixtures dos testes
python3 news/radar.py --db /tmp/radar.sqlite --offline-dir tests/fixtures/news
```

Só biblioteca padrão do Python — nenhuma dependência para instalar.

## Na VPS

```sh
systemctl status minera-goias-news.timer
systemctl list-timers minera-goias-news.timer
journalctl -u minera-goias-news.service -n 50 --no-pager
cat /var/lib/minera-goias-news/latest.json
```

A instalação segue o padrão dos outros serviços: o programa e o `feeds.json` ficam em `/usr/local/lib/minera-goias-news/` como arquivos de root, e o banco em `/var/lib/minera-goias-news/`. Mudar `feeds.json` no GitHub **não** altera a VPS sozinho — exige reinstalação administrativa, como no importador.

## Limites conhecidos deste protótipo

- **Léxico fixo.** Direção é detectada por lista de palavras, sem modelo de linguagem. Ironia, negação ("não deve subir") e citação indireta passam batido.
- **Título e resumo apenas.** O radar não abre a matéria; o RSS do Google News costuma trazer resumo curto, o que reduz o material analisado.
- **Uma matéria replicada por vários veículos** conta como várias, inflando o score. O mínimo de matérias reduz o efeito, mas não elimina.
- **Preço citado não é preço de mercado.** Pode ser valor de contrato, de projeção ou de outro período. Nada é convertido entre moedas ou unidades.
- **Sem recorte de Goiás.** As fontes são nacionais e internacionais; o radar não filtra por estado.

Para virar produção, o caminho é: rotular uma amostra à mão para medir acerto do léxico, deduplicar matérias por similaridade de título, e só então comparar os sinais com uma série de preço de verdade para ver se antecipam alguma coisa.

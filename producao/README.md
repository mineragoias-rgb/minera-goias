# Agente de produção — busca semanal

Procura, uma vez por semana, números de produção mineral por empresa nas fontes públicas, confronta cada um com a base curada e registra o que
achou **com a frase que originou o número**. Roda segunda-feira às 02:00 pelo `minera-goias-producao.timer`.

## O que ele é e o que ele não é

O agente **não atualiza a base sozinho**. Ele produz candidatos `nao_validado`, aponta divergências contra o que já está curado e propõe
melhorias da própria metodologia. Promover candidato a registro e aceitar proposta de metodologia são atos humanos — é o que o
`METODOLOGIA.md` fixa em "importar não é validar" e "quando a fonte não diz, o sistema não inventa".

Ele também **não lê o documento inteiro**: trabalha sobre título e resumo do feed. Um release de RI com a tabela de produção em PDF passa
batido; o que chega é a manchete que fala dela.

## O ciclo de uma execução

1. **Coleta** — lê os feeds de `fontes.json`: buscas por empresa, feeds setoriais (ANM, IBRAM, Brasil Mineral, Mining.com, Mining Weekly) e uma
   busca geral de produção mineral em Goiás. Matéria é identificada pelo hash do link, então reexecutar não duplica. Feed fora do ar não derruba
   os outros: a execução termina como `partial`.
2. **Extração** — quebra o texto em frases e aplica os padrões ativos. Um candidato só nasce com **número, unidade e mineral** legíveis; período
   sai do próprio texto e nunca da data da matéria.
3. **Confronto** — compara com `base_curada.json` por empresa, mineral e período.
4. **Propostas** — o que claramente falava de produção e escapou vira proposta de metodologia.
5. **Decisões** — o que o agente promoveria e o que promoveu, sempre com o motivo.

## Leitura de número: a armadilha da notação

`43,974` vale 43.974 em inglês e 43,974 em português — errar isso erra por mil, em silêncio. O agente decide pela **grafia** sempre que ela
fecha o caso: separador repetido (`1.234.567`) é milhar; os dois separadores juntos definem o decimal pelo último; uma casa, duas ou quatro ou
mais depois do separador é decimal. Sobra um caso genuinamente ambíguo — separador único com exatamente três casas —, e só aí o idioma
declarado da fonte decide. Esse candidato sai marcado `ambigua_pelo_idioma`, e o texto original do número viaja junto em `valor_bruto`.

## Vereditos do confronto

| Veredito | Significa |
|---|---|
| `confirma` | Bate com a base dentro da tolerância (2%, que cobre `39,7 kt` contra `39.700 t`) |
| `diverge` | Mesma empresa, mineral, período e unidade, valor fora da tolerância — é o alerta que importa |
| `unidade_divergente` | A base tem esse recorte em outra unidade. **Nada é convertido**: a divergência é o resultado |
| `novo` | Recorte que a base ainda não cobre — candidato a virar registro |
| `sem_periodo` | O texto não disse o período, então não há o que confrontar |

Quando o valor confere mas a **medida** não — um embarque confirmando um número de produção —, o veredito continua `confirma` e a medida da
base viaja junto em `medida_base`, com `medida_confere = 0`.

## As três lacunas que ele sabe apontar

O agente não inventa metodologia: ele mede onde a metodologia atual falhou e propõe o conserto, com assinatura, contagem, fontes distintas e
até cinco exemplos.

| Proposta | Quando | O que sugere |
|---|---|---|
| `padrao` | Frase com produção, número, unidade e mineral conhecidos que nenhuma expressão cobriu | Uma expressão nova, montada do contexto da frase |
| `unidade` | O token depois do número não está no léxico | Acrescentar a unidade — com o fator decidido por gente |
| `mineral` | Número e unidade conhecidos, nenhum termo de mineral | Mapear o termo para uma substância da ANM |

Padrão que atravessa oito execuções sem capturar nada vira proposta de aposentadoria. O agente **não apaga** nada.

### Promoção automática

`auto_promocao` nasce **desligada**. Ligada, ela promove proposta que bateu o mínimo de ocorrências, em fontes distintas e em execuções
distintas — e toda promoção fica em `prod_decisoes` com os exemplos que a sustentaram. Ligar isso é decisão de quem responde pela base; com ela
desligada, a proposta elegível só muda de status para `elegivel_aguardando_revisao` e espera.

## Tabelas

| Tabela | Conteúdo |
|---|---|
| `prod_runs` | Execuções, versão do agente, versão da metodologia e relatório completo |
| `prod_fontes` | Fontes configuradas, último status e última leitura |
| `prod_itens` | Matérias com título, link, resumo e data |
| `prod_candidatos` | Um número por padrão e frase: valor, texto original do número, notação, unidade, medida, tipo, período, evidência, veredito e referência na base |
| `prod_propostas` | Lacunas da metodologia, com contagem, fontes, execuções e exemplos |
| `prod_padroes` | Aproveitamento de cada padrão e execuções seguidas sem uso |
| `prod_decisoes` | O que foi promovido ou proposto para aposentadoria, e por quê |

## Rodar localmente

```sh
# Com rede, fontes reais
python3 producao/agente.py --db /tmp/producao.sqlite --report /tmp/producao.json

# Sem rede, com as fixtures dos testes
python3 producao/agente.py --db /tmp/producao.sqlite --offline-dir tests/fixtures/producao

# Só testar quais fontes respondem, sem gravar nada
python3 producao/agente.py --check
```

Só biblioteca padrão do Python — nenhuma dependência para instalar.

> **Os endereços de `fontes.json` não foram testados contra a rede.** Foram montados a partir dos padrões de RSS de cada veículo, num ambiente
> cujo proxy de egresso bloqueia esses domínios. Rode `--check` na primeira instalação e remova os que não responderem.

## Na VPS

```sh
systemctl status minera-goias-producao.timer
systemctl list-timers minera-goias-producao.timer
journalctl -u minera-goias-producao.service -n 50 --no-pager
cat /var/lib/minera-goias-producao/latest.json
```

Instalação no padrão dos outros serviços: programa, `fontes.json` e `base_curada.json` em `/usr/local/lib/minera-goias-producao/` como arquivos
de root, banco em `/var/lib/minera-goias-producao/`. Mudar `fontes.json` no GitHub **não** altera a VPS sozinho — exige reinstalação
administrativa, como no importador e no radar.

## O trabalho semanal de quem revisa

1. Abrir `latest.json` e olhar **divergências** primeiro: é ali que a base pode estar errada.
2. Conferir os `novo` que tenham fonte de RI — são os candidatos a virar registro.
3. Ler as propostas com mais ocorrências e decidir o que entra em `fontes.json`.
4. Editar `producao/base_curada.json`, rodar `python scripts/build_producao_base.py`, rodar `tests/test_producao.py` e enviar para `main`.

Quem valida um número assina: preencha `status_validacao` e `responsavel_validacao` no registro promovido.

## Limites conhecidos

- **Título e resumo apenas.** O número que só existe na tabela do PDF não é alcançado.
- **Atribuição de empresa é lexical.** "Anglo American" numa matéria sobre cobre no Chile seria atribuída à operação de níquel de Goiás; o
  confronto por mineral e período reduz o estrago, não o elimina.
- **Uma matéria replicada** por vários veículos gera candidatos repetidos, com evidências diferentes.
- **Escopo não é lido do texto.** O agente não distingue sozinho produção da operação em Goiás de consolidado da empresa — quem promove o
  candidato decide o `escopo`.
- **Léxico fixo.** Mineral, unidade e período saem de listas. É justamente o que as propostas existem para fazer crescer.

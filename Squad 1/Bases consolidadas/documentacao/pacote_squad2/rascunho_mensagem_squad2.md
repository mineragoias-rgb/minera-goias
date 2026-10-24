# Rascunho — mensagem ao Squad 2 sobre a aba 12

> Rascunho preparado para o Eliel (Squad 1 / Estudante 1) revisar e enviar. **Não foi enviado.** Os números saem da planilha v17.

**Assunto:** Squad 1 → Squad 2: produção por mineral, ano e operação (aba 12) — confirmar o formato

Oi, pessoal do Squad 2!

A base do Squad 1 (v17) já tem a entrega para vocês: a aba `12_interface_squad1_squad2`. Para facilitar, deixamos um pacote em
`Squad 1/Bases consolidadas/documentacao/pacote_squad2/`, com a aba em CSV (no mesmo formato dos exemplos de `Squad 2/data/demo/`), o
dicionário dos campos e a correspondência com o `production_history` do motor.

Em resumo:
- **Nível estado** (745 linhas, 2010–2025): produção observada de Goiás no AMB, por mineral, ano e base.
- **Nível operação** (4.831 linhas, 2022–2025, 931 processos): estimativa, o total do estado rateado pela CFEM
  recolhida por processo. Os dois níveis não se somam.

Para fechar o formato antes da Entrega 1 (21/09), precisamos que vocês confirmem:

1. **Nível:** o motor vai usar a produção estimada por operação ou o total observado do estado?
2. **`operation_id` vazio:** 457 linhas estimadas (18,3% da produção estimada) são de processos sem
   poligonal no SIGMINE. Podemos usar o número do processo (`processo_anm`) como identificador, ou vocês preferem agrupar ou deixar essas linhas
   de fora?
3. **Base de produção:** a aba usa `ROM` e `beneficiada`, e 29 dos 33 minerais têm as duas. Qual base vocês
   querem para cada mineral? A intensidade energética precisa estar na mesma base. Podemos escrever em minúsculas (`rom`), como no contrato.
4. **Incerteza:** o contrato não tem campo de erro. Querem receber junto a faixa `erro_estimativa_intervalo` e a sensibilidade
   `production_t_rateio_por_t`?
5. **Entrega:** CSV no GitHub serve, ou vocês preferem ler direto do banco do site?

Com a resposta, passamos a gerar o `production_history` no formato do motor a cada versão nova da base.

Abraço,
Eliel — Squad 1 / Estudante 1

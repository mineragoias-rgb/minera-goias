# -*- coding: utf-8 -*-
"""Pacote da aba 12 para o Squad 2: a aba em CSV, o dicionário dos campos, a correspondência com o contrato do motor e o rascunho de
mensagem pedindo a confirmação do formato.

    python base_consolidada_work/scripts/gerar_pacote_squad2.py                 # usa a planilha mais recente de documentacao/
    python base_consolidada_work/scripts/gerar_pacote_squad2.py <planilha.xlsx>

Grava documentacao/pacote_squad2/: interface_squad1_squad2.csv, dicionario_interface_squad1_squad2.csv, LEIA-ME.md e
rascunho_mensagem_squad2.md. Os CSV seguem a convenção dos exemplos do Squad 2 (Squad 2/data/demo/: vírgula, UTF-8 com BOM, ponto
decimal). Todos os números saem da planilha (abas 12 e 14). O rascunho não é enviado a ninguém: fica para o Estudante 1 revisar e mandar.
"""
import csv
import glob
import os
import re
import sys
from collections import Counter, defaultdict

import openpyxl

sys.stdout.reconfigure(encoding="utf-8")
from caminhos import BASE  # caminhos relativos ao projeto — ver caminhos.py

ABA = "12_interface_squad1_squad2"
if len(sys.argv) > 1:
    PLANILHA = sys.argv[1]
else:
    PLANILHA = max((int(m.group(1)), p) for p in glob.glob(os.path.join(BASE, "documentacao", "prototipo_bases_consolidadas_v*.xlsx"))
                   if (m := re.search(r"_v(\d+)\.xlsx$", p)))[1]
VERSAO = "v" + re.search(r"_v(\d+)\.xlsx$", PLANILHA).group(1)
PASTA = os.path.join(os.path.dirname(PLANILHA), "pacote_squad2")
os.makedirs(PASTA, exist_ok=True)
wb = openpyxl.load_workbook(PLANILHA, read_only=True)


def ler(aba):
    it = wb[aba].iter_rows(min_row=4, values_only=True)
    cab = [c for c in next(it) if c is not None]
    return cab, [dict(zip(cab, r)) for r in it if r and r[0] is not None]


inteiro = lambda x: f"{x:,}".replace(",", ".")
pct = lambda x: f"{x:.1f}".replace(".", ",")
mi = lambda t: f"{t / 1e6:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ---------------------------------------------------------------------------------------------------------------- aba 12 em CSV
cab12, linhas = ler(ABA)
with open(os.path.join(PASTA, "interface_squad1_squad2.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(cab12 + ["versao_base"])
    for d in linhas:
        w.writerow(["" if d.get(c) is None else d[c] for c in cab12] + [VERSAO])

# ---------------------------------------------------------------------------------------------------------------- dicionário
# campo da aba 12 -> (campo no contrato do motor do Squad 2, nota)
MAPA = {
    "mineral_id": ("production_history.mineral_id", "MIN_### do catálogo (aba 01)"),
    "mineral_name": ("minerals.mineral_name", "catálogo completo na aba 01"),
    "company_id": ("production_history.company_id", "vazio no nível estado"),
    "operation_id": ("production_history.operation_id", "vazio no nível estado e nos processos sem poligonal no SIGMINE (usar processo_anm?)"),
    "project_id": ("projects.project_id", "vazio até o Radar de Projetos (Estudante 2)"),
    "year": ("production_history.year", ""),
    "production_t": ("production_history.production_t", ""),
    "production_basis": ("production_history.production_basis", "ROM e beneficiada; o motor escreve rom, beneficiada, conteudo_mineral"),
    "valor_observado_estimado": ("production_history.data_nature", "observado no nível estado; estimado no nível operação"),
    "source_id": ("production_history.source_id", "uma fonte no nível estado; várias, separadas por ';', no nível operação"),
    "source_url": ("sources.source_url", "catálogo completo na aba 07"),
}
cab14, dic = ler("14_dicionario_dados")
dic12 = {d["campo"]: d for d in dic if d["aba"] == ABA}
faltam = [c for c in cab12 if c not in dic12]
assert not faltam, f"campos da aba 12 sem linha no dicionário (14): {faltam}"
COLS_DIC = ["campo", "contrato_de_dados", "descricao", "unidade_ou_dominio", "fonte_ou_derivacao", "tipo", "pct_vazio", "n_distintos",
            "exemplo", "observacao"]
with open(os.path.join(PASTA, "dicionario_interface_squad1_squad2.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(COLS_DIC + ["campo_no_motor_squad2", "nota_correspondencia"])
    for c in cab12:
        d = dic12[c]
        w.writerow(["" if d.get(k) is None else d[k] for k in COLS_DIC] + list(MAPA.get(c, ("", ""))))
    w.writerow(["versao_base", "", "Versão da planilha de onde o CSV saiu (acrescentada ao exportar).", "vNN", "pacote_squad2", "texto", "0", "1",
                VERSAO, "", "", ""])

# ---------------------------------------------------------------------------------------------------------------- números
est = [d for d in linhas if d["nivel_agregacao"] == "estado"]
ope = [d for d in linhas if d["nivel_agregacao"] == "operacao"]
assert len(est) + len(ope) == len(linhas), Counter(d["nivel_agregacao"] for d in linhas)
anos = lambda L: f"{min(d['year'] for d in L)}–{max(d['year'] for d in L)}"
nat = lambda L: "; ".join(f"{k}: {inteiro(v)}" for k, v in Counter(d["valor_observado_estimado"] for d in L).most_common())
proc_ope = {d["processo_anm"] for d in ope if d.get("processo_anm")}
t_ope = sum(d["production_t"] or 0 for d in ope)
sem_op = [d for d in ope if not d.get("operation_id")]
t_sem_op = sum(d["production_t"] or 0 for d in sem_op)
proc_sem_op = {d["processo_anm"] for d in sem_op}
nao_ident = [d for d in ope if d.get("company_id") == "COM_NAO_IDENTIFICADO"]
t_nao_ident = sum(d["production_t"] or 0 for d in nao_ident)
minerais = {d["mineral_id"] for d in linhas}
bases_mineral = defaultdict(set)
for d in est:
    bases_mineral[d["mineral_name"]].add(d["production_basis"])
duas_bases = sorted(m for m, b in bases_mineral.items() if len(b) > 1)
contagem_bases = Counter(d["production_basis"] for d in linhas)
status = Counter((d["nivel_agregacao"], d["status_validacao"]) for d in linhas)

chave = lambda d: (d["mineral_id"], d["year"], d["production_basis"])
tot_est = defaultdict(float)
n_chave_est = Counter(chave(d) for d in est)
for d in est:
    tot_est[chave(d)] += d["production_t"] or 0
soma_ope = defaultdict(float)
for d in ope:
    soma_ope[chave(d)] += d["production_t"] or 0
anos_ope = {d["year"] for d in ope}
grupos = [k for k in tot_est if k[1] in anos_ope and tot_est[k] > 0]
iguais = [k for k in grupos if k in soma_ope and abs(soma_ope[k] - tot_est[k]) <= 0.001 * tot_est[k]]
sem_abertura = [k for k in grupos if k not in soma_ope]
diferentes = [k for k in grupos if k in soma_ope and k not in iguais]
ope_sem_estado = [k for k in soma_ope if k not in tot_est]
t_grupos = sum(tot_est[k] for k in grupos)
t_sem_abertura = sum(tot_est[k] for k in sem_abertura)
nome_mineral = {d["mineral_id"]: d["mineral_name"] for d in linhas}

print(f"{VERSAO}: {len(linhas)} linhas ({len(est)} estado, {len(ope)} operação), {len(cab12)} colunas, {len(minerais)} minerais")
print(f"chaves repetidas no nível estado: {sum(1 for v in n_chave_est.values() if v > 1)}")
print(f"mineral-ano-base com operação ({sorted(anos_ope)}): {len(grupos)} — iguais {len(iguais)}, sem abertura {len(sem_abertura)}, "
      f"diferentes {len(diferentes)}, operação sem total do estado {len(ope_sem_estado)}")
for k in diferentes[:10]:
    print("  diferente:", k, round(soma_ope[k], 3), round(tot_est[k], 3))
for k in sem_abertura[:10]:
    print("  sem abertura:", k, round(tot_est[k], 3))
print(f"sem operation_id: {len(sem_op)} linhas, {len(proc_sem_op)} processos, {pct(100 * t_sem_op / t_ope)}% da produção estimada")
print(f"COM_NAO_IDENTIFICADO: {len(nao_ident)} linhas, {pct(100 * t_nao_ident / t_ope)}% da produção estimada")
print(f"minerais com as duas bases: {duas_bases}")
print(f"status: {dict(status)}")

# ---------------------------------------------------------------------------------------------------------------- textos
def lista(itens):
    itens = list(itens)
    return ", ".join(itens[:-1]) + " e " + itens[-1] if len(itens) > 1 else "".join(itens)


obs_est = {chave(d): (d.get("observacao") or "").strip() for d in est}
motivos = Counter(obs_est.get(k) or "(sem observação)" for k in sem_abertura)
mineral_sem_abertura = Counter(nome_mineral[k[0]] for k in sem_abertura)
print("motivos sem abertura:", dict(motivos))
fechamento = (f"Em {inteiro(len(iguais))} das {inteiro(len(grupos))} combinações de mineral, ano e base de {min(anos_ope)}–{max(anos_ope)} "
              "com produção no estado, a soma das operações é igual ao total do estado (diferença até 0,1%)")
if sem_abertura:
    fechamento += (f"; em {inteiro(len(sem_abertura))} não há abertura por operação ({pct(100 * t_sem_abertura / t_grupos)}% da produção "
                   f"do estado nesses anos — {'; '.join(f'{m}: {q}' for m, q in mineral_sem_abertura.most_common())}"
                   + ("; o motivo fica em `observacao` na linha do estado" if "(sem observação)" not in motivos else "") + ")")
if diferentes:
    fechamento += f"; em {inteiro(len(diferentes))} a soma difere do total"
fechamento += "."
if ope_sem_estado:
    fechamento += f" Há {inteiro(len(ope_sem_estado))} combinações com operações e sem total do estado."

status_txt = "; ".join(f"`{s}` ({n}): {inteiro(q)}" for (n, s), q in sorted(status.items()))
uma_base = sorted(m for m, b in bases_mineral.items() if len(b) == 1)
duas_txt = (f"{len(duas_bases)} dos {len(bases_mineral)} minerais têm as duas bases no nível estado, e cada série deve usar uma só"
            + (f" (só uma base: {lista(f'{m} ({min(bases_mineral[m])})' for m in uma_base)})" if uma_base else "")
            if duas_bases else "nenhum mineral tem as duas bases no nível estado")

leiame = f"""# Pacote da aba 12 para o Squad 2 — produção por mineral, ano e operação ({VERSAO})

Squad 1 / Estudante 1 → Squad 2. Gerado por `gerar_pacote_squad2.py` a partir de `prototipo_bases_consolidadas_{VERSAO}.xlsx`, aba
`{ABA}`. Todos os números abaixo saem da planilha; rodar o script de novo depois de uma versão nova atualiza o pacote.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `interface_squad1_squad2.csv` | a aba 12 inteira: {inteiro(len(linhas))} linhas, as {len(cab12)} colunas da aba e `versao_base` |
| `dicionario_interface_squad1_squad2.csv` | um campo por linha (descrição, unidade, fonte, % vazio, exemplo) e o campo correspondente no contrato do motor |
| `rascunho_mensagem_squad2.md` | rascunho da mensagem pedindo a confirmação do formato — **não enviado** |

Os CSV seguem a convenção dos exemplos do Squad 2 em `Squad 2/data/demo/`: vírgula como separador, UTF-8 com BOM e ponto decimal. Campos
vazios ficam vazios (nada foi preenchido com zero).

## Dois níveis que não se somam

| `nivel_agregacao` | Linhas | Anos | `valor_observado_estimado` | O que é |
|---|---:|---|---|---|
| `estado` | {inteiro(len(est))} | {anos(est)} | {nat(est)} | produção de Goiás no AMB por mineral, ano e base (ROM ou beneficiada), em t |
| `operacao` | {inteiro(len(ope))} | {anos(ope)} | {nat(ope)} | o total do estado rateado entre {inteiro(len(proc_ope))} processos pela participação de cada um na CFEM recolhida (R$) do mineral no ano |

- {fechamento}
- **Sem `operation_id`:** {inteiro(len(sem_op))} linhas do nível operação ({inteiro(len(proc_sem_op))} processos, {pct(100 * t_sem_op / t_ope)}% da
  produção estimada) são de processos que recolhem CFEM mas não têm poligonal no SIGMINE de Goiás. O `processo_anm` identifica essas
  linhas; a lista está em `../operacoes_sem_coordenadas.csv` e a explicação em `../nota_squad2_operacoes_sem_coordenadas.md`.
- **Titular não identificado:** {inteiro(len(nao_ident))} linhas do nível operação têm `company_id = COM_NAO_IDENTIFICADO`
  ({pct(100 * t_nao_ident / t_ope)}% da produção estimada).
- **Base de produção:** {inteiro(contagem_bases.get('ROM', 0))} linhas em `ROM` e {inteiro(contagem_bases.get('beneficiada', 0))} em `beneficiada`; {duas_txt}.
- **Estimativa:** a ANM não publica produção por operação. As linhas de operação trazem `metodo_estimacao` e a faixa
  `erro_estimativa_intervalo` (rateio por R$ × rateio pela quantidade comercializada da CFEM, que também está em `production_t_rateio_por_t`).
- **Status de validação:** {status_txt}.
- `project_id` fica vazio até o Radar de Projetos (Estudante 2). Consumo de energia não vem do Squad 1.

## Correspondência com o contrato do motor

Contrato em `Squad 2/README (1).md`, seção "Produção histórica (`production_history`)":

| Campo do motor | Obrigatório | Campo da aba 12 | Situação |
|---|---|---|---|
| `mineral_id` | Sim | `mineral_id` | pronto ({len(minerais)} minerais, catálogo na aba 01) |
| `company_id` | Sim | `company_id` | pronto no nível operação; vazio no nível estado |
| `operation_id` | Sim | `operation_id` | vazio em {inteiro(len(sem_op))} linhas do nível operação; `processo_anm` pode servir de identificador |
| `year` | Sim | `year` | pronto |
| `production_t` | Sim | `production_t` | pronto |
| `production_basis` | Sim | `production_basis` | a aba usa `ROM` e `beneficiada`; o motor escreve `rom`, `beneficiada` e `conteudo_mineral` |
| `data_nature` | Sim | `valor_observado_estimado` | `observado` no nível estado, `estimado` no nível operação |
| `source_id` | Sim | `source_id` | uma fonte no nível estado; várias, separadas por `;`, no nível operação |

Os catálogos `minerals` e `sources` do motor correspondem às abas 01 e 07 da planilha. `projects` depende do Radar de Projetos (a aba 04 é a
camada ANM). `energy_intensity` não vem do Squad 1.

## Pontos a confirmar com o Squad 2

1. **Nível:** o motor usa a produção estimada por operação ({anos(ope)}) ou o total observado do estado ({anos(est)})?
2. **`operation_id` vazio:** usar `processo_anm` como identificador dessas {inteiro(len(sem_op))} linhas, agrupar ou deixar de fora?
3. **Base:** qual base (`rom` ou `beneficiada`) por mineral, compatível com a intensidade energética; e se o valor vai em minúsculas, como no contrato.
4. **Incerteza:** receber `erro_estimativa_intervalo` e `production_t_rateio_por_t` junto, já que o contrato não tem campo de erro?
5. **Entrega:** CSV no GitHub, como este pacote, ou leitura direta do banco do site?
"""
open(os.path.join(PASTA, "LEIA-ME.md"), "w", encoding="utf-8", newline="\n").write(leiame)

mensagem = f"""# Rascunho — mensagem ao Squad 2 sobre a aba 12

> Rascunho preparado para o Eliel (Squad 1 / Estudante 1) revisar e enviar. **Não foi enviado.** Os números saem da planilha {VERSAO}.

**Assunto:** Squad 1 → Squad 2: produção por mineral, ano e operação (aba 12) — confirmar o formato

Oi, pessoal do Squad 2!

A base do Squad 1 ({VERSAO}) já tem a entrega para vocês: a aba `12_interface_squad1_squad2`. Para facilitar, deixamos um pacote em
`Squad 1/Bases consolidadas/documentacao/pacote_squad2/`, com a aba em CSV (no mesmo formato dos exemplos de `Squad 2/data/demo/`), o
dicionário dos campos e a correspondência com o `production_history` do motor.

Em resumo:
- **Nível estado** ({inteiro(len(est))} linhas, {anos(est)}): produção observada de Goiás no AMB, por mineral, ano e base.
- **Nível operação** ({inteiro(len(ope))} linhas, {anos(ope)}, {inteiro(len(proc_ope))} processos): estimativa, o total do estado rateado pela CFEM
  recolhida por processo. Os dois níveis não se somam.

Para fechar o formato antes da Entrega 1 (21/09), precisamos que vocês confirmem:

1. **Nível:** o motor vai usar a produção estimada por operação ou o total observado do estado?
2. **`operation_id` vazio:** {inteiro(len(sem_op))} linhas estimadas ({pct(100 * t_sem_op / t_ope)}% da produção estimada) são de processos sem
   poligonal no SIGMINE. Podemos usar o número do processo (`processo_anm`) como identificador, ou vocês preferem agrupar ou deixar essas linhas
   de fora?
3. **Base de produção:** a aba usa `ROM` e `beneficiada`{f", e {len(duas_bases)} dos {len(bases_mineral)} minerais têm as duas" if duas_bases else ""}. Qual base vocês
   querem para cada mineral? A intensidade energética precisa estar na mesma base. Podemos escrever em minúsculas (`rom`), como no contrato.
4. **Incerteza:** o contrato não tem campo de erro. Querem receber junto a faixa `erro_estimativa_intervalo` e a sensibilidade
   `production_t_rateio_por_t`?
5. **Entrega:** CSV no GitHub serve, ou vocês preferem ler direto do banco do site?

Com a resposta, passamos a gerar o `production_history` no formato do motor a cada versão nova da base.

Abraço,
Eliel — Squad 1 / Estudante 1
"""
open(os.path.join(PASTA, "rascunho_mensagem_squad2.md"), "w", encoding="utf-8", newline="\n").write(mensagem)
print(f"SALVO: {PASTA} (interface_squad1_squad2.csv, dicionario_interface_squad1_squad2.csv, LEIA-ME.md, rascunho_mensagem_squad2.md)")

# Rateio da energia entre coprodutos (Frente 1): refeito junto com o pacote, porque lê a aba 12 que acabou de ser gravada.
import runpy  # noqa: E402

runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "gerar_coprodutos.py"), run_name="__main__")

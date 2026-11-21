# -*- coding: utf-8 -*-
"""Repositório de erros das bases do Squad 1 (Frente 1 — Eliel): catálogo ERR_### e as análises que o sustentam.

    python "Squad 1/Bases consolidadas/base_consolidada_work/scripts/gerar_repositorio_erros.py"

Grava em Squad 1/Auditoria e qualidade/:
  repositorio_erros.xlsx — abas 00_leia_me, erros, bario_niobio, bario_niobio_processos, contido_vs_bruto, tonelagens_repetidas, amb_x_cfem;
  REPOSITORIO_ERROS.md   — o resumo para ler no GitHub.
Todo número citado é recalculado a cada execução: dos brutos (Squad 1/Dados brutos, via caminhos.arquivo) e da planilha consolidada
de versão mais alta. Só lê; nada é corrigido (regra do projeto: divergência é registrada, não corrigida).
Os poucos números que não dá para recalcular daqui (medidos num arquivo que não está no repositório ou num momento do pipeline)
estão marcados em onde_foi_conferido como "registro do projeto", com a data.
"""
import datetime
import json
import os
import re
import sys
from collections import Counter

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

sys.stdout.reconfigure(encoding="utf-8")
from caminhos import BASE, arquivo
from repositorio_erros_analises import (aba, amb_x_cfem, bario_niobio, load_amb, load_cfem, planilha, repetidas, teor_df)

SAIDA = os.path.join(os.path.dirname(BASE), "Auditoria e qualidade")
# PLAN e MODO podem vir de quem executa este arquivo com runpy.run_path(..., init_globals=...): a etapa do pipeline
# write_repositorio_erros_into_workbook.py passa a planilha intermediária e MODO="pipeline" (não grava os arquivos à parte).
PLAN = globals().get("PLAN") or planilha()
MODO = globals().get("MODO") or "arquivo"
VERSAO = (re.search(r"_(v\d+)\.xlsx$", PLAN) or re.search(r"_(v\w+)\.xlsx$", PLAN)).group(1)
HOJE = datetime.date.today().isoformat()


def br(x, d=0):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(a, b, d=1):
    return br(100 * a / b, d) if b else "—"


# =============================================================================================== dados
a = load_amb()
cf = load_cfem()
d09, dmin = aba("09_cons_mineral_ano", PLAN), aba("01_dim_minerais", PLAN)
b13 = aba("13b_auditoria_mapas", PLAN)
c9 = aba("09c_alertas_cfem_processo", PLAN)
n09b = len(aba("09b_auditoria_cfem_quantidade", PLAN))
d11 = aba("11_cons_empresa_ano_mineral", PLAN)
d06 = aba("06_dim_ocorrencias_geologicas", PLAN)
d01c = aba("01c_rochas_por_tipo_de_uso", PLAN)
d04b = aba("04b_eventos_anm_classificados", PLAN)
d06b = aba("06b_crosswalk_recmin", PLAN)
d02 = aba("02_dim_empresas", PLAN)

go = a[a.uf == "GO"]
teor = teor_df(go)
rep = repetidas(a)
axc = amb_x_cfem(a, d09, dmin)
bn, bnproc = bario_niobio(a, cf)


def v13(trecho):
    x = b13[b13.iloc[:, 1].astype(str).str.startswith(trecho)]
    return int(x.n.iloc[0]) if len(x) else None


def re1(padrao, texto, conv=lambda s: s):
    m = re.search(padrao, texto)
    if not m:
        raise SystemExit(f"padrão não encontrado: {padrao} em {texto[:120]}")
    return conv(m.group(1))


inteiro = lambda s: int(s.replace(",", "").replace(".", ""))

# --- AMB
rep_go = rep[rep.uf == "GO"]
b23 = bn[bn.rom_identico]
nb = bn.set_index("ano")
z = a[a.unid_contido == "-"]
contido_traco = (len(z), int((z.contido.fillna(0) == 0).sum()), int((z.contido.fillna(0) != 0).sum()))
al = teor[teor.alertas.fillna("") != ""]
n_cod = lambda c: int(al.alertas.str.contains(c + " ").sum())
ouro = teor[(teor.substancia == "Ouro") & (teor.base == "bruta_rom")].dropna(subset=["teor_pct"])
ouro_pior = ouro.loc[(ouro.teor_pct / ouro.teor_mediano_pct).idxmax()]
ouro_rom = go[(go.substancia == "Ouro") & (go.base == "bruta_rom") & (go.qtd > 0)].qtd
ouro_ben = go[(go.substancia == "Ouro") & (go.base == "beneficiada") & (go.qtd > 0)]
ouro_ben_t = ouro_ben.qtd * ouro_ben.unid.map({"kg": 1e-3, "g": 1e-6, "t": 1.0})
nb_axc = axc[axc.substancia == "Nióbio"]
cls = axc.classificacao.str[:2]
nR = {k: int((cls == k).sum()) for k in ("R1", "R2", "R4", "R5", "R6")}
n_compat = int(axc.classificacao.str.startswith("compatível").sum())


def lista(k):
    x = axc[cls == k]
    return "; ".join(f"{s} {int(y)}" for s, y in zip(x.substancia, x.ano))


# --- CFEM
u = cf.unid.str.lower().value_counts()
subs_unid = cf.groupby("Substância").unid.nunique()
cpf = cf.CPF_CNPJ.fillna("")
cpf_cient = int(cpf.str.contains(r"E\+").sum())
cpf_mask = int(cpf.str.contains("*", regex=False).sum())
qtd_cient = int(cf.QuantidadeComercializada.str.contains(r"E\+").sum())
s96 = cf.Processo.str.startswith("96")
ouro_cf = cf[cf["Substância"].str.strip().str.upper().isin(["OURO", "MINÉRIO DE OURO"]) & (cf.ano <= 2025)]
crixas = ouro_cf[ouro_cf.Processo.isin(["960658", "960657"])].groupby("ano").valor.sum() / ouro_cf.groupby("ano").valor.sum()
v11 = pd.to_numeric(d11.cfem_recolhido_brl, errors="coerce")
ni11 = v11[d11.company_id == "COM_NAO_IDENTIFICADO"].sum()
k_grao = ["Ano", "Mês", "Processo", "AnoDoProcesso", "Substância", "CodigoMunicipio", "unid", "CPF_CNPJ"]
cf_ult = f"{cf.ano.max()}-{cf[cf.ano == cf.ano.max()]['Mês'].astype(int).max():02d}"
cf_criacao = pd.to_datetime(cf.DataCriacao, dayfirst=True, errors="coerce").max().date().isoformat()
sev = c9.severidade.value_counts()
c9n = c9.copy()
c9n["razao"] = pd.to_numeric(c9n.razao, errors="coerce")
nb9 = c9n[(c9n.mineral_name == "Nióbio")].sort_values("razao", ascending=False)
ti9 = c9n[(c9n.mineral_name == "Titânio")].sort_values("razao", ascending=False)
p567 = c9n[c9n.processo_anm == "860567/2021"]
p567_rpt = pd.to_numeric(p567.r_por_t, errors="coerce")
_ro = d01c[d01c.fonte == "CFEM (GO)"].groupby("regra").valor_recolhido_brl.sum()
rochas = "; ".join(f"{k}: {br(100 * v / _ro.sum(), 1)}%" for k, v in _ro.sort_values(ascending=False).items())
n_lgpd = int(d02.razao_social.astype(str).str.contains(r"\*\*\*\d{6}\*\*").sum())
n_terminais = int(pd.to_numeric(d04b[d04b.classe_evento == "encerramento"].processos).sum())
sem_cat_06b = ", ".join(d06b[d06b.tipo_correspondencia == "sem_categoria_anm"].substancia_original)

# --- Cadastro Mineiro (o arquivo do repositório é o recorte de Goiás: processos com município ou poligonal em GO)
import csv
import glob
import io
import unicodedata

nomes_go = {unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode().upper() for n in aba("05_dim_municipios", PLAN).municipality_name}
sit_tot = sit_sim = homon = linhas_ruins = 0
homon_set = set()
for f in sorted(glob.glob(arquivo("dados/ANM/cadastro_mineiro/*.csv"))):
    texto = open(f, encoding="cp1252", errors="replace").read()
    linhas = texto.splitlines()
    cab = next(csv.reader([linhas[0]]))
    for l in linhas[1:]:
        try:
            linhas_ruins += len(next(csv.reader([l], strict=True))) != len(cab)
        except csv.Error:
            linhas_ruins += 1
    d = pd.read_csv(io.StringIO(texto), dtype=str, keep_default_na=False, engine="python", on_bad_lines="skip")
    if "Situação" in d:
        sit_tot += len(d)
        sit_sim += int((d["Situação"] == "Sim").sum())
    for v in d.get("Municipio(s)", []):
        for tok in str(v).split(","):
            m = re.match(r"(.*) - ([A-Z]{2})$", tok.strip())
            if m and m.group(2) != "GO":
                n = unicodedata.normalize("NFKD", m.group(1)).encode("ascii", "ignore").decode().upper().strip()
                if n in nomes_go:
                    homon += 1
                    homon_set.add(f"{n}-{m.group(2)}")

# --- RECMIN (só os pontos que a 06 manteve em Goiás) e SIDRA
gj = json.load(open(arquivo("dados/SGB_GeoSGB/recmin/ocorrencias_recursos_minerais_GO.geojson"), encoding="utf-8"))
rp = pd.DataFrame([x["properties"] for x in gj["features"]])
rp = rp[rp.id_ocorrencia.astype(str).isin(set(d06.occurrence_id.str.replace("OCC_", "")))]
rec_loc = 100 * (rp.localizacao_mina == "Mina subterrânea (GPS sem sinal)").mean()
rec_gar = 100 * (rp.situacao_garimpo.fillna("") == rp.situacao_mina.fillna("")).mean()
anos_cad = rp.data_cadastro.astype(str).str[:4].value_counts(normalize=True)
sidra = {}
for nome in ("populacao_municipal_goias_ultimo_ano.json", "pib_municipal_goias_ultimo_ano.json"):
    j = json.load(open(arquivo(f"dados/IBGE/{nome}"), encoding="utf-8"))[1:]
    sidra[nome] = (sum(1 for r in j if len(r.get("D1C", "")) == 7), sum(1 for r in j if len(r.get("D1C", "")) != 7),
                   sorted({r.get("MN") for r in j}))

# =============================================================================================== catálogo
E = []


def e(fonte, arq, tipo, descricao, exemplo, medido, conferido, impacto, regra, checagem, onde, status):
    E.append(dict(codigo=f"ERR_{len(E) + 1:03d}", fonte=fonte, arquivo_ou_campo=arq, tipo=tipo, descricao=descricao, exemplo=exemplo,
                  numero_medido=medido, onde_foi_conferido=conferido, impacto=impacto, regra_adotada=regra, checagem_que_detecta=checagem,
                  onde_aparece=onde, status=status))


BRUTO = f"bruto (recalculado em {HOJE})"
PL = lambda abas: (f"esta planilha ({abas})" if MODO == "pipeline" else f"planilha {VERSAO} ({abas})")
AMBf = "ANM — AMB (Produção Bruta/Beneficiada)"
ba23 = (f"GO {int(b23.ano.iloc[0])}, produção bruta: Nióbio e Bário com exatamente {br(b23.nb_rom_t.iloc[0], 2)} t "
        f"(linhas {b23.nb_rom_linha_csv.iloc[0]} e {b23.ba_rom_linha_csv.iloc[0]} do Producao_Bruta.csv)") if len(b23) else "—"
e(AMBf, "Producao_Bruta.csv / Producao_Beneficiada.csv — quantidade", "duplicidade (co-produto)",
  "A mesma tonelagem aparece em linhas de minerais diferentes da mesma UF e ano (co-produto que sai do mesmo minério: Chumbo+Zinco, Ouro+Prata, Bário+Nióbio).",
  ba23 + ". Fora de 2023 os números diferem, mas o ROM do bário (5–6 Mt/ano, com poucos milhares de t beneficiadas) é a rocha lavrada para nióbio e fosfato.",
  f"{rep.grupo.nunique()} grupos / {len(rep)} linhas no Brasil; {rep_go.grupo.nunique()} grupos em GO", BRUTO,
  "Somar ROM entre minerais conta o mesmo minério duas vezes; na intensidade energética, o denominador fica inflado.",
  "Linha mantida; status alerta_producao_repetida na 08. O ROM de subproduto sem valor próprio (bário de Catalão, cobalto, prata) tem status rom_minerio_associado e não é aberto por operação. Não somar ROM entre minerais. "
  "Bário × Nióbio no ROM de 2023: o alerta fica, SEM correção por inferência (não se sabe qual dos dois números está certo; a decisão é do grupo).",
  "14b — 'mesma tonelagem de produção em linhas diferentes…' (ALERTA)", "08 (status_validacao), 12, 14b; aba tonelagens_repetidas", "sinalizado")
x2 = rep_go[rep_go.tipo.str.startswith("entre") & rep_go.substancia.str.startswith("Rochas Ornamentais")]
e(AMBf, "Producao_Beneficiada.csv — categoria", "duplicidade (mesma declaração em 2 categorias)", "A mesma declaração aparece em duas categorias do mesmo grupo.",
  ("GO " + ", ".join(f"{int(y)} ({b}): {q} t" for y, b, q in x2[["ano", "base", "qtd_txt"]].drop_duplicates().itertuples(index=False))
   + " em Rochas Ornamentais e Rochas Ornamentais - Outras") if len(x2) else "—",
  f"{x2.grupo.nunique()} grupo(s) em GO", BRUTO, "Infla a soma de rochas ornamentais.", "Igual ao ERR_001 (sinalizado, não corrigido).",
  "14b (mesma checagem do ERR_001)", "08, 14b", "sinalizado")
e(AMBf, "Unidade de Medida - Contido", "unidade", "Contido com unidade '-': quase sempre zero (não se aplica), mas às vezes com valor.", "—",
  f"{br(contido_traco[0])} células com unidade '-' (todas as UFs): {br(contido_traco[1])} zero e {br(contido_traco[2])} diferentes de zero", BRUTO,
  "Valor sem unidade não pode virar tonelada.", "Zero com '-' não vira linha na 08; diferente de zero com '-' fica registrado sem conversão.",
  "contido_vs_bruto (alerta C2 em GO)", "08", "tratado")
e(AMBf, "Producao_Bruta.csv — Quantidade Contido (ouro)", "valor implausível",
  f"Contido do ouro na produção bruta de GO em {int(ouro_pior.ano)} implica teor de {br(ouro_pior.teor_pct * 1e4, 1)} g/t, contra mediana de "
  f"{br(ouro_pior.teor_mediano_pct * 1e4, 2)} g/t nos outros anos.",
  f"GO {int(ouro_pior.ano)}: {br(ouro_pior.qtd_t / 1e6, 1)} Mt de minério com {br(ouro_pior.contido)} kg de ouro contido ({br(ouro_pior.contido_t)} t — "
  f"o estado produz {br(ouro_ben_t.min(), 1)}–{br(ouro_ben_t.max(), 1)} t de ouro por ano).",
  f"1 mineral-ano ({br(ouro_pior.teor_pct / ouro_pior.teor_mediano_pct)}× a mediana)", BRUTO,
  "Usar o contido como limite ou proxy de metal daria milhares de t de ouro.", "O contido do AMB não é usado como limite na 09c (usa a beneficiada em kg).",
  "contido_vs_bruto (alerta C4)", "09c (coluna amb_base)", "sinalizado")
e(AMBf, "Producao_Beneficiada.csv — Nióbio", "quebra de série / conceito",
  "A produção beneficiada de nióbio muda de ordem de grandeza em 2024, com o teor caindo de ~50% para ~1,4% Nb2O5: passou a declarar a massa que entra na usina, não o concentrado.",
  f"Nióbio beneficiada GO: {br(nb.nb_benef_t[2023])} t (2023) → {br(nb.nb_benef_t[2024])} t (2024) e {br(nb.nb_benef_t[2025])} t (2025); "
  f"contido {br(nb.nb_benef_contido_t[2023])} → {br(nb.nb_benef_contido_t[2024])} t de Nb2O5.",
  "2 mineral-anos", BRUTO, "Série da beneficiada do nióbio não comparável antes/depois de 2024; intensidade energética por t beneficiada muda ~70×.",
  "DECIDIDO (Eliel, 19/11/2026) e aplicado na v18: a série do nióbio beneficiado é o contido em Nb2O5. A 09 ganhou contido_beneficiada_t, contido_indicacao "
  "e serie_beneficiada; na 12 o nióbio beneficiado vai como production_basis = conteudo_mineral. Regra em regras_series.py.",
  "14b — conciliação 08 → 09 (inclui contido_beneficiada_t) e 12 estado = 08", "09, 12, bario_niobio", "tratado (v18)")
e(AMBf, "Unidade de Medida - Produção (metais)", "unidade",
  "Para ouro e prata, a bruta é tonelada de MINÉRIO e a beneficiada é kg de METAL; misturar as duas dá limites absurdos.",
  f"Ouro GO: {br(ouro_rom.min() / 1e6)}–{br(ouro_rom.max() / 1e6)} Mt/ano de minério (bruta) × {br(ouro_ben_t.min(), 1)}–{br(ouro_ben_t.max(), 1)} t/ano de metal (beneficiada, em kg).",
  "2 minerais (ouro, prata)", PL("09c, regra METAL_KG"), "Sem a regra, nenhum processo de ouro era sinalizado na 09c.",
  "METAL_KG: para esses metais o limite é a beneficiada convertida para t, e a mediana de R$/t é ponderada pelo R$.", "09c (coluna criterio)", "09c", "tratado (v14)")
ba_lac = [int(y) for y in nb.index if not (nb.ba_rom_t.get(y) > 0)]
e(AMBf, "Linhas por ano", "cobertura (lacuna)", "Minerais somem do AMB em alguns anos (sem linha) ou vêm com zero entre anos com produção.",
  f"Bário GO: produção bruta zero ou sem linha em {', '.join(map(str, ba_lac))}.",
  f"{n_cod('C8')} mineral-base-anos sem linha e {n_cod('C7')} com zero após ano produtivo, em GO", BRUTO,
  "Zero não é 'não produziu': a série pode ter buraco de declaração.", "Nenhuma correção; vazio fica vazio na 09.", "contido_vs_bruto (C7, C8)", "09", "sinalizado")
e(AMBf, "Quantidade Contido / Indicação Contido", "conceito", "Contido informado sem dizer o que é (óxido, metal ou o próprio produto).",
  "Vermiculita, amianto, diamante, gemas: contido igual à quantidade ou sem indicação.", f"{n_cod('C3')} mineral-base-anos em GO", BRUTO,
  "Não se sabe se o contido é teor ou produto.", "Contido com a indicação original na 08 e na 09 (contido_indicacao).", "contido_vs_bruto (C3, informativo)",
  "08, 09", "sinalizado")
e(AMBf, "Valores de venda × consumo/transferência", "conceito",
  "Em minas integradas (nióbio, fosfato) a venda da produção bruta é zero: o valor está em consumo/transferência para a usina.",
  f"Nióbio GO {min(ANOS := list(nb_axc.ano.astype(int)))}–{max(ANOS)}: vendas R$ {br(nb_axc.vendas_brl.sum() / 1e6, 1)} mi no período; "
  f"consumo + transferência R$ {br(nb_axc.vendas_consumo_transf_brl.min() / 1e6)}–{br(nb_axc.vendas_consumo_transf_brl.max() / 1e6)} mi por ano.",
  "Nióbio, fosfato", BRUTO, "Comparar a CFEM só com a venda dá razão infinita ou absurda.",
  "No AMB × CFEM, comparar também com venda + consumo + transferência.", "amb_x_cfem (duas razões)", "amb_x_cfem", "tratado")
e(AMBf, "Arquivo inteiro", "versão da fonte", "A ANM republica produção e CFEM com frequência (dados preliminares).", "—", "—", "registro do projeto",
  "Rodar de novo com arquivo novo muda números sem aviso.", "sha256 e data de acesso de cada arquivo na 07; o robô (robo-bases.yml) só publica se a 14b não ganhar ALERTA novo.",
  "07 (sha256); robo_bases.py --conferir-planilha", "07", "tratado")

CF = "ANM — CFEM (arrecadação GO)"
e(CF, "QuantidadeComercializada / UnidadeDeMedida", "unidade", "Unidades misturadas para a mesma substância (t, kg, g, ct, m³, l, m²).",
  "Amianto em kg e t; areia em t e m³.",
  f"{int((subs_unid > 1).sum())} de {len(subs_unid)} substâncias com mais de uma unidade; linhas por unidade: " + ", ".join(f"{k} {br(v)}" for k, v in u.items()),
  BRUTO, "Somar quantidade sem converter mistura grandezas.", "Massa → t; m³, l e m² somados à parte (cfem_qtd_outras_unidades). Lista de suspeitas de unidade trocada em auditoria_unidades_anm.md.",
  "14b — 'Quantidade comercializada da CFEM…'; auditoria_unidades_anm.py", "09 (cfem_qtd_*), 09b", "tratado")
e(CF, "QuantidadeComercializada", "valor corrompido", "Quantidade em notação científica ou inflada ~1000× (R$/unidade absurdo).", "No download de 09/2026 havia valores como 7,23824E+12; as infladas ~1000× continuam.",
  f"{qtd_cient} linhas em notação científica; {n09b} linhas fora da soma de t na 09b",
  BRUTO + " e " + PL("09b"), "Uma linha destrói a soma do ano.", "Excluir da soma de t (nunca do R$) se notação científica ou R$/unidade < mediana/1000.",
  "08 status quantidade_excluida_da_soma_09b", "09b, 08", "tratado")
e(CF, "CPF_CNPJ", "identificação",
  "No arquivo baixado em 09/2026, o CNPJ vinha como número em notação científica (34.212 de 38.854 linhas) e não identificava a empresa. CPF de PF vem mascarado.",
  "'9,69944E+11'; '***370285**'.",
  f"arquivo atual: {br(cpf_cient)} de {br(len(cf))} linhas em notação científica; {br(cpf_mask)} mascaradas",
  BRUTO + "; 09/2026 = registro do projeto", "Sem CNPJ, a CFEM só liga à empresa pelo processo.",
  "Ponte pelo número do processo (canon_processo) com Cadastro Mineiro e SIGMINE; company_id = raiz do CNPJ; CNPJ pagador quando o processo não tem titular.",
  "02b (crosswalk) e soma da 11 = bruto", "02, 02b, 11",
  "resolvido na fonte (download atual com CNPJ completo)" if cpf_cient == 0 else "tratado")
e(CF, "Processo (série 96xxxx)", "cobertura (identificação)", "Processos da série 96xxxx não existem no Cadastro Mineiro nem no SIGMINE (sem titular e sem poligonal).",
  f"Ouro em Crixás: 960658/1987 e 960657/1987 levam {pct(crixas.min(), 1, 0)}–{pct(crixas.max(), 1, 0)}% do R$ de ouro de GO por ano.",
  f"série 96: {br(int(s96.sum()))} linhas, R$ {br(cf[s96].valor.sum() / 1e6, 1)} mi ({pct(cf[s96].valor.sum(), cf.valor.sum())}% da CFEM); "
  f"sem empresa no fim (COM_NAO_IDENTIFICADO na 11): R$ {br(ni11 / 1e3, 1)} mil ({pct(ni11, v11.sum(), 2)}%)",
  BRUTO + " e " + PL("11"), "Parte da produção fica sem coordenada (sem poligonal).",
  "Empresa pelo CNPJ pagador; o que sobra vai para COM_NAO_IDENTIFICADO, e a soma continua igual ao bruto.", "Soma da 11 = bruto", "11, 12, 03", "sinalizado")
nbx = nb9.iloc[0] if len(nb9) else None
tix = ti9.iloc[0] if len(ti9) else None
e(CF, "Quantidade por processo", "valor implausível", "Processo declara mais toneladas que o estado inteiro produziu no AMB, ou R$/t incompatível.",
  "; ".join(f"{r.mineral_name} {r.processo_anm} em {int(r.year)}: {br(float(r.cfem_t_processo) / (1e6 if float(r.cfem_t_processo) > 1e6 else 1), 1)}"
            f"{' Mt' if float(r.cfem_t_processo) > 1e6 else ' t'} na CFEM contra {br(float(r.amb_total_uf_t) / (1e6 if float(r.amb_total_uf_t) > 1e6 else 1), 1)}"
            f"{' Mt' if float(r.amb_total_uf_t) > 1e6 else ' t'} no AMB do estado ({br(r.razao, 1)}×)" for r in (nbx, tix) if r is not None),
  f"{len(c9)} processo-anos ({int(sev.get('alta', 0))} alta, {int(sev.get('moderada', 0))} moderada)", PL("09c"), "Rateio por t ficaria distorcido.",
  "Sinalizar, não corrigir; rateio da 12 por R$ e não por t.", "14b — 'Processos com quantidade na CFEM implausível…'", "09c, 08, 12", "sinalizado")
e(CF, "Substância = OURO", "conceito", "Minério declarado como ouro (t de minério com preço de minério).",
  f"860567/2021: R$ {br(p567_rpt.min() / 1e3)}–{br(p567_rpt.max() / 1e3)} mil/t (ouro vale milhões de R$/t)." if len(p567) else "—",
  f"{len(p567)} processo-anos desse processo", PL("09c"), "Toneladas de ouro infladas.", "Mediana de R$/t ponderada pelo R$ e alerta de preço.",
  "09c (criterio)", "09c", "sinalizado")
e(CF, "Linhas com mesmo (ano, mês, processo, substância, município, unidade, CPF_CNPJ)", "duplicidade aparente",
  "Linhas iguais no grão são recolhimentos distintos, não duplicatas.", "—", f"{br(int(cf.duplicated(k_grao, keep=False).sum()))} linhas", BRUTO,
  "Deduplicar apagaria arrecadação real.", "Manter o grão da linha.", "Soma 08 = bruto", "08", "tratado")
e(CF, "Substância (rochas)", "conceito", "A CFEM não traz o uso; a categoria ANM de rocha depende do uso (brita × ornamental).",
  "Granito para brita × granito para revestimento.", f"R$ de rochas por origem da categoria: {rochas}", PL("01c"),
  "Sem a regra, Rochas Ornamentais chegavam a 35–191× o AMB.", "Uso pelo número do processo (Cadastro → SIGMINE → outra rocha do processo).",
  "14b — 'Rochas na CFEM…'", "01c", "tratado (v7)")
e(CF, "Último ano", "cobertura", "O último ano da CFEM é parcial.", f"Último mês: {cf_ult}; última DataCriacao: {cf_criacao}.", "—", BRUTO,
  "Comparar o ano corrente com anos cheios subestima.", "Rótulo '(parcial)' em periodo_referencia e no site.", "periodo_referencia", "09, 10, 11", "tratado")
e(CF, "Substância (nomes)", "conceito", "A CFEM usa nomes próprios, diferentes das categorias do AMB.",
  "BARITA (= Bário), NIÓBIO e MINÉRIO DE NIÓBIO (= Nióbio); subitens de calcário.", "—", BRUTO, "Cruzar por nome perde ou duplica minerais.",
  "Crosswalk de substâncias para mineral_id.", "01b e 14b (integridade)", "01b", "tratado")

CM = "ANM — Cadastro Mineiro"
e(CM, "Municipio(s)", "recorte territorial", "Campo multivalorado e nacional; municípios de outros estados têm o mesmo nome de municípios goianos.",
  "'CACHOEIRA DOURADA - GO, CACHOEIRA DOURADA - MG'; " + ", ".join(sorted(homon_set)[:6]) + ".",
  f"no recorte de Goiás do repositório: {br(homon)} citações de {len(homon_set)} homônimos de outra UF (no nacional de 09/2026: 1.186 citações, 24 homônimos)",
  BRUTO + "; nacional = registro do projeto", "Filtrar pelo nome puxa processos de outros estados.",
  "go_municipio_id(): cada token, rejeitando sufixo de UF ≠ GO.", "05b (crosswalk de municípios)", "05b", "tratado")
e(CM, "Situação", "campo sem informação", "'Situação' = 'Sim' em todas as linhas (os dados abertos só têm processos ativos).", "—",
  f"{br(sit_sim)} de {br(sit_tot)} linhas", BRUTO, "Não serve para separar processo vivo de morto.", "Usar o último evento do SIGMINE (04b).", "04b",
  "04, 04b", "tratado")
e(CM, "Superintendência", "recorte territorial", "Jurisdição regional da ANM não segue a fronteira do estado.", "—", "—", "registro do projeto",
  "Filtrar por superintendência erra o recorte.", "Nunca filtrar por Superintendência.", "—", "—", "tratado")
e(CM, "Arquivos CSV (aspas)", "formato",
  "Aspas dentro de campos sem escape quebram a linha; o leitor do pipeline (on_bad_lines='skip') descarta essas linhas sem aviso.",
  "Alvara_de_Pesquisa.csv nacional, linha 6430: 'Área Operacional \"Lagoa Mirim\" - RS'.",
  f"nos arquivos nacionais de 09/2026: 1.184 linhas (nenhuma com município de GO); no recorte de Goiás do repositório: {br(linhas_ruins)}",
  "registro do projeto (19/11/2026) e " + BRUTO, "Hoje sem impacto em GO; numa base nova pode perder processos goianos em silêncio.",
  "Nenhuma ainda. Proposta: contar as linhas descartadas e falhar se alguma citar '- GO' (no recorte do robô e no pipeline).", "nenhuma (proposta)", "—",
  "pendente — novo")
e(CM, "Titular", "LGPD", "Titular pessoa física aparece com CPF no nome.", "—",
  f"{n_lgpd} titulares na 02 com CPF mascarado no nome", PL("02"),
  "Exposição de CPF no site.", "mascarar_cpf() na exibição; o company_id não muda.", "14b — 'LGPD…'", "02, 03, 04", "tratado (v12)")
e(CM, "Municipio(s) em processo de divisa", "recorte territorial", "Processo que cruza a divisa às vezes só cita o município do outro estado.",
  "2 linhas da 04 mudavam no recorte só por município.", "2 linhas", "registro do projeto (v16)", "Recorte só por município perde processos com área em GO.",
  "Recorte = município de GO OU processo com poligonal no SIGMINE de GO.", "Comparação dos dois arranjos (v16)", "04", "tratado (v16)")

SG = "ANM — SIGMINE"
e(SG, "UF", "recorte territorial", "Campo UF não é recorte territorial (processos com UF=MG parcialmente em GO, UF=PA 100% em GO).", "—",
  f"{br(v13('Processos com menos de 50%'))} processos com menos de 50% da área em GO", PL("13b"), "Filtrar por UF erra o universo.",
  "Recorte pela geometria, com fracao_area_em_go.", "13b", "03, 13b", "tratado")
e(SG, "Geometria", "formato", "Polígonos com autointerseção e processos fragmentados em várias feições.", "—",
  f"{v13('Polígonos inválidos')} inválidos; {v13('Processos fragmentados')} fragmentados", PL("13b"), "Área e interseção erradas.",
  "make_valid + dissolve por processo.", "13b", "03, 13b", "tratado")
n_disc = int(b13.iloc[:, 1].astype(str).str.startswith("Discordância espacial").sum())
e(SG, "Município", "cobertura", "SIGMINE não tem município; processos discordam do Cadastro (desmembramentos, ex.: Jussara → Santa Fé de Goiás).", "806139/1973",
  f"{n_disc} discordâncias; {br(v13('Processos sem município no Cadastro'))} sem município no Cadastro", PL("13b"),
  "Município textual pode ser o da época do registro.", "Junção espacial (maior área).", "13b", "03, 13b", "tratado")
e(SG, "Último evento", "conceito", "SIGMINE mantém processos encerrados (indeferimento, caducidade, renúncia…).", "—",
  f"{br(n_terminais)} processos do universo com evento terminal", PL("04b"), "Contar projeto morto como vivo.",
  "Cada tipo de evento classificado na 04b.", "14b — '04: cada processo vivo…'", "04, 04b", "tratado")
e(SG, "Geometria (web)", "formato", "Simplificar poligonais de título deforma polígonos pequenos.", "125 polígonos < 2 ha deformam > 10% (teste de 09/2026).", "—",
  PL("13b"), "Mapa com área legal errada.", "Sem simplificação; GeoJSON por grupo + PMTiles.", "13b", "13, 13b", "tratado")

RM = "SGB — RECMIN (ocorrências)"
e(RM, "localizacao_mina / situacao_garimpo / data_cadastro", "campo sem informação",
  "Campos preenchidos com valor padrão: localização genérica, situação do garimpo copiada da mina, data de cadastro = data da carga.",
  "'Mina subterrânea (GPS sem sinal)'; 'Mina Ativo(a)' de 2001 (Cana Brava, hoje em pesquisa).",
  f"nos {br(len(rp))} pontos de GO: localização genérica {br(rec_loc, 1)}%; situacao_garimpo = situacao_mina {br(rec_gar, 1)}%; "
  f"data de cadastro em {anos_cad.index[0]} {br(anos_cad.iloc[0] * 100, 1)}%", BRUTO,
  "'Ativo' do RECMIN não significa ativo hoje.", "Campos fora da aba; cruzamento com a ANM informa o status atual.", "14b — '06: campos do RECMIN fora da aba…'",
  "06, 06b", "tratado")
e(RM, "substancias", "conceito", "Substâncias em ordem alfabética, sem principal; algumas sem categoria ANM.",
  sem_cat_06b or "—", f"{len(d06b)} nomes na 06b", PL("06b"), "Não dá para escolher 'o' mineral do ponto.",
  "mineral_ids multivalorado; crosswalk 06b.", "14b — '06: substâncias → mineral_ids…'", "06, 06b", "tratado")

IB = "IBGE — SIDRA e malha"
p_, f_ = sidra["populacao_municipal_goias_ultimo_ano.json"], sidra["pib_municipal_goias_ultimo_ano.json"]
e(IB, "JSON municipais do SIDRA", "duplicidade (linha agregada)", "Os JSON 'municipais' trazem também a linha da UF (D1C=52).", "NN = 'Unidade da Federação'.",
  f"população: {br(p_[0])} municípios + {p_[1]} UF; PIB: {br(f_[0])} + {f_[1]} UF", BRUTO, "A soma de GO dobra.", "Filtrar código de 7 dígitos.",
  "07 confere população da UF = soma dos 246", "05, 10", "tratado")
e(IB, "PIB municipal", "unidade", "PIB vem em mil reais.", f"Unidade no arquivo: {', '.join(map(str, f_[2]))}.", "—", BRUTO, "PIB 1.000× menor.",
  "Converter para R$ (pib_total_brl).", "dicionário (14)", "10", "tratado")
e(IB, "Malha municipal", "geometria", "Centro da caixa envolvente cai fora do município.", "—", f"{v13('Ponto ')} de 246", PL("13b"),
  "Ponto do município no lugar errado.", "representative_point.", "13b", "05, 13b", "tratado")
e("IMB — Goiás em Dados", "Produção mineral do estado", "conceito", "Produção do IMB parece contido para cobre, nióbio e níquel (sempre abaixo do AMB); só vai até 2016.",
  "—", "comparação mineral a mineral em 2010–2016 (o IMB não traz produção depois)", PL("14b, checagem 'IMB × AMB'"), "Misturar IMB e AMB troca minério por metal.", "IMB só como validação cruzada.",
  "14b — 'IMB × AMB'", "07, 14b", "tratado (v17)")
e("CCEE — consumo de energia", "RAMO_ATIVIDADE", "conceito",
  "Cargas sem ramo são as distribuidoras (mercado cativo), não um setor; CONSUMO_CATIVO_PARC_LIVRE ≈ 0.", "Equatorial Goiás e CHESP, ≈ 1,1 TWh/mês.",
  "29,8 TWh medidos, 10,8 TWh livres (36%) em 2024-08 a 2026-07", "registro do projeto (Panorama, 14/09/2026)",
  "'% livre' dava 100%; rankings misturavam cativo.", "Ramo 'DISTRIBUIDORA (MERCADO CATIVO)'; rankings só com o livre.", "—", "site (Panorama)", "tratado")

RP = "Pipeline (reprodutibilidade)"
e(RP, "Base 3 — municipios_atuacao", "reprodutibilidade", "A ordem de um set muda a cada execução do Python; cortar antes de ordenar dava resultados diferentes.",
  "list(muns)[:6]", "~660 de 10.199 linhas mudavam por execução (v11)", "registro do projeto", "Mesma entrada, planilhas diferentes.",
  "Sempre ordenar antes de cortar ou juntar.", "2 execuções = mesmo sha256", "03, 11", "tratado")
e(RP, "Fim de linha no GitHub", "reprodutibilidade", "core.autocrlf trocava CRLF↔LF nos brutos e o sha256 deixava de bater.",
  "13 CSVs do Cadastro, 3 JSON do IBGE.", "—", "registro do projeto (v17)", "sha256 da 07 não confere com o arquivo do GitHub.",
  ".gitattributes '* -text' em Dados brutos; conferir git ls-files --eol.", "—", "07", "tratado")
e(RP, "%TEMP% e datas de arquivo", "reprodutibilidade",
  "Windows apaga de %TEMP% arquivos com data antiga; clonar muda a data de modificação (usada como data_acesso).", "—", "—", "registro do projeto (v16)",
  "Arquivos somem; data_acesso muda ao clonar.", "Não usar cp -p em %TEMP%; Dados brutos/datas_de_acesso.json no arranjo GitHub.", "caminhos.data_acesso()",
  "07, 08", "tratado")
e(RP, "Excel", "formato", "Nome de aba > 31 caracteres e cabeçalho renomeado sem atualizar a Tabela corrompem o xlsx.", "06b_crosswalk_substancias_recmin (32).",
  "2 ocorrências", "registro do projeto", "Excel repara ou recusa o arquivo.", "Contar caracteres; atualizar tableColumns junto.", "14b (estrutura)", "todas", "tratado")

AX = "Cruzamento AMB × CFEM"
e(AX, f"mineral × ano {ANOS[0]}–{ANOS[-1]}", "cobertura (royalty)", "Produção no AMB sem nenhuma CFEM no ano.", lista("R1"), f"{nR['R1']} mineral-anos",
  BRUTO + " e " + PL("09"), "Ou a CFEM foi paga com outro nome de substância, ou não foi paga.", "Sinalizado; não estimar CFEM.", "amb_x_cfem (R1)",
  "amb_x_cfem", "sinalizado")
e(AX, f"mineral × ano {ANOS[0]}–{ANOS[-1]}", "cobertura (royalty)", "CFEM paga sem produção no AMB.", lista("R2"), f"{nR['R2']} mineral-anos",
  BRUTO + " e " + PL("09"),
  "Água mineral está em outro arquivo da ANM (Agua_Mineral_Producao.csv), não no AMB; potássio e 'minerais industriais' não têm linha no AMB de GO.",
  "Sinalizado.", "amb_x_cfem (R2)", "amb_x_cfem", "sinalizado")
e(AX, f"mineral × ano {ANOS[0]}–{ANOS[-1]}", "valor implausível (royalty)",
  "CFEM incompatível com o valor declarado no AMB e a alíquota legal (Lei 8.001/1990, Anexo, redação da Lei 13.540/2017).",
  lista("R4") + (" | abaixo: " + lista("R5") if nR["R5"] else "") + (" | AMB sem valor: " + lista("R6") if nR["R6"] else ""),
  f"{nR['R4']} acima de 2× a alíquota, {nR['R5']} abaixo de 1/4, {nR['R6']} com valor do AMB menor que a CFEM", BRUTO + " e " + PL("09"),
  "Valor do AMB subdeclarado, CFEM em outra base (ex.: níquel pago sobre o minério e AMB com valor do ferroníquel) ou erro de classificação (basaltos).",
  "Sinalizado; não corrigido.", "amb_x_cfem (R4, R5, R6)", "amb_x_cfem", "sinalizado")
cat = pd.DataFrame(E)

# =============================================================================================== abas de análise
SEV = {"C1": "verificar", "C2": "verificar", "C4": "verificar", "C6": "verificar", "C3": "informativo", "C5": "lacuna", "C7": "lacuna", "C8": "lacuna"}
t = teor.copy()
t["codigos"] = t.alertas.fillna("").str.findall(r"C\d").map(lambda l: ", ".join(dict.fromkeys(l)))
t["severidade"] = t.codigos.map(lambda s: next((n for n in ("verificar", "lacuna", "informativo") if any(SEV.get(c) == n for c in s.split(", "))), ""))
t = t[["substancia", "base", "ano", "qtd", "unid", "contido", "unid_contido", "indicacao", "teor_pct", "teor_mediano_pct", "codigos", "severidade", "alertas",
       "arquivo", "linha_csv"]]
t.columns = ["mineral_amb", "base", "ano", "quantidade", "unidade", "contido", "unidade_contido", "indicacao_contido", "teor_implicito_pct",
             "teor_mediano_mineral_pct", "codigos", "severidade", "alertas", "arquivo_fonte", "linha_csv"]
r = rep[["uf", "ano", "base", "grupo", "tipo", "substancia", "classe", "qtd_txt", "unid", "minerais_do_grupo", "arquivo", "linha_csv"]]
r.columns = ["uf", "ano", "base", "grupo", "tipo", "mineral_amb", "classe", "quantidade_texto_original", "unidade", "minerais_do_grupo", "arquivo_fonte", "linha_csv"]
x = axc[["substancia", "ano", "qtd_bruta_rom", "qtd_beneficiada", "unid_beneficiada", "valor_venda_bruta_rom", "valor_venda_beneficiada", "valor_consumo_bruta_rom",
         "valor_consumo_beneficiada", "valor_transf_bruta_rom", "valor_transf_beneficiada", "vendas_brl", "vendas_consumo_transf_brl", "cfem_brl", "subitens",
         "cfem_pct_vendas", "cfem_pct_vendas_consumo_transf", "aliquota_legal_pct", "aliquota_legal_texto", "classificacao"]]
x.columns = ["mineral_amb", "ano", "producao_bruta_t", "producao_beneficiada", "unidade_beneficiada", "amb_venda_bruta_brl", "amb_venda_beneficiada_brl",
             "amb_consumo_bruta_brl", "amb_consumo_beneficiada_brl", "amb_transferencia_bruta_brl", "amb_transferencia_beneficiada_brl", "amb_vendas_brl",
             "amb_vendas_consumo_transf_brl", "cfem_recolhido_brl", "minerais_cfem_somados", "cfem_pct_das_vendas", "cfem_pct_de_vendas_consumo_transf",
             "aliquota_legal_pct", "aliquota_legal", "classificacao"]

LEIA = [
    ("Repositório de erros e análises — Squad 1 / Estudante 1", ""),
    ("Gerado em", f"{HOJE} por base_consolidada_work/scripts/gerar_repositorio_erros.py"),
    ("Entrada", f"Squad 1/Dados brutos (AMB, CFEM, Cadastro Mineiro, RECMIN, SIDRA) e {os.path.basename(PLAN)} (abas 01, 05, 06, 08, 09, 09b, 09c, 11, 13b, 14b). "
                "Nada foi alterado nessas fontes."),
    ("erros", f"Catálogo único: {len(cat)} erros (ERR_001…). Para cada um: fonte, tipo, exemplo, número medido, onde foi conferido, impacto, regra adotada "
              "no pipeline, checagem que detecta, onde aparece e status (tratado / sinalizado / pendente)."),
    ("bario_niobio", "Bário × Nióbio em Goiás: produção bruta e beneficiada com contido (BaSO4 / Nb2O5), teor implícito, a série adotada para o nióbio "
                     "beneficiado (contido, desde a v18) e a CFEM por substância (BARITA, NIÓBIO, MINÉRIO DE NIÓBIO)."),
    ("bario_niobio_processos", "CFEM de bário e nióbio por processo e ano: os mesmos processos pagam as duas substâncias."),
    ("contido_vs_bruto", "Todos os minerais de GO, nas duas bases do AMB: teor implícito (contido ÷ quantidade, em t) e alertas C1…C8."),
    ("tonelagens_repetidas", "Mesma quantidade (texto e unidade iguais, ≠ 0) em linhas diferentes da mesma UF, ano e base — todas as UFs."),
    ("amb_x_cfem", f"GO {ANOS[0]}–{ANOS[-1]} por mineral do AMB: produção, valores do AMB, CFEM (subitens somados ao mineral-pai), razão CFEM ÷ valor e alíquota legal."),
    ("", ""), ("Alertas contido_vs_bruto", ""),
    ("C1", "contido maior que a quantidade (verificar)"), ("C2", "contido ≠ 0 com unidade '-' (verificar)"),
    ("C3", "contido sem indicação: óxido, metal ou o próprio produto? (informativo)"), ("C4", "teor fora de 1/3–3× a mediana do mineral naquela base (verificar)"),
    ("C5", "contido zerado num ano com produção, e o mineral informa contido em ≥ 3 anos (lacuna)"), ("C6", "quantidade > 5× ou < 1/5 do ano anterior (verificar)"),
    ("C7", "produção zero logo após ano com produção (lacuna)"), ("C8", "ano sem linha no AMB entre anos com linha (lacuna)"),
    ("", ""), ("Classificação amb_x_cfem", ""),
    ("Alíquotas", "Lei 8.001/1990, Anexo (redação da Lei 13.540/2017): 1% rochas, areias, cascalhos, saibros e demais substâncias para uso imediato na construção "
                  "civil, rochas ornamentais, águas minerais e termais; 1,5% ouro; 2% diamante e demais substâncias; 3% bauxita, manganês, nióbio e sal-gema; 3,5% ferro. "
                  "Base: receita bruta de venda menos tributos; no consumo, preço corrente. Argilas e calcário: 1% ou 2% conforme o uso."),
    ("Razões", "cfem_pct_das_vendas = CFEM ÷ vendas (bruta + beneficiada); cfem_pct_de_vendas_consumo_transf = CFEM ÷ (vendas + consumo + transferência). "
               "A verdade fica entre as duas: vendas sozinhas ignoram minas integradas; somar tudo pode contar o mesmo minério na bruta e na beneficiada."),
    ("R1", "produção no AMB sem CFEM no ano"), ("R2", "CFEM sem produção no AMB no ano"), ("R3", "produção sem valor comercial no AMB e sem CFEM"),
    ("R4", "CFEM > 2× a alíquota mesmo sobre o maior denominador"), ("R5", "CFEM < 1/4 da alíquota mesmo sobre o menor denominador"),
    ("R6", "valor comercial do AMB menor que a própria CFEM (AMB sem valor ou incompleto)"),
    ("", ""), ("Regra do projeto", "Divergência é registrada, não corrigida. Este arquivo não muda nenhum número da base consolidada."),
]

wb = Workbook()
ws = wb.active
ws.title = "00_leia_me"
for i, (k, v) in enumerate(LEIA, 1):
    ws.cell(i, 1, k).alignment = Alignment(vertical="top")
    ws.cell(i, 2, v).alignment = Alignment(wrap_text=True, vertical="top")
    if i == 1 or (k and not v):
        ws.cell(i, 1).font = Font(bold=True, size=12 if i == 1 else 11)
ws.column_dimensions["A"].width = 26
ws.column_dimensions["B"].width = 140


def add(nome, df, titulo, nota, larguras=None, quebra=False):
    ws = wb.create_sheet(nome)
    ws.cell(1, 1, titulo).font = Font(bold=True, size=12)
    ws.cell(2, 1, nota)
    df = df.replace({np.nan: None})
    for j, c in enumerate(df.columns, 1):
        ws.cell(4, j, c).font = Font(bold=True)
    for i, row in enumerate(df.itertuples(index=False), 5):
        for j, v in enumerate(row, 1):
            v = v.item() if isinstance(v, np.generic) else v
            c = ws.cell(i, j, v)
            if quebra:
                c.alignment = Alignment(wrap_text=True, vertical="top")
    tab = Table(displayName="t_" + nome, ref=f"A4:{get_column_letter(len(df.columns))}{4 + max(len(df), 1)}")
    tab.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True)
    ws.add_table(tab)
    ws.freeze_panes = "B5"
    for j, c in enumerate(df.columns, 1):
        w = (larguras or {}).get(c) or min(max(10, max([len(str(c))] + [len(str(v)) for v in df[c].head(200) if v is not None]) + 2), 60)
        ws.column_dimensions[get_column_letter(j)].width = w


st = Counter(s.split(" ")[0] for s in cat.status)
add("erros", cat, "Repositório de erros por base", f"{len(cat)} erros. status: " + ", ".join(f"{k} {v}" for k, v in st.items()),
    larguras={"descricao": 60, "exemplo": 60, "numero_medido": 45, "impacto": 50, "regra_adotada": 55, "checagem_que_detecta": 40, "onde_aparece": 22,
              "arquivo_ou_campo": 30, "fonte": 30, "onde_foi_conferido": 28}, quebra=True)
add("bario_niobio", bn, "Bário × Nióbio em Goiás (AMB e CFEM)",
    "Quantidades em t; contido em t de BaSO4 (bário) e Nb2O5 (nióbio). Série do nióbio beneficiado = contido Nb2O5 (decisão de 19/11/2026, ERR_005). "
    "linha_csv = linha no CSV do AMB.")
add("bario_niobio_processos", bnproc, "CFEM de bário e nióbio por processo", "Mesmos processos pagam BARITA e NIÓBIO / MINÉRIO DE NIÓBIO.")
add("contido_vs_bruto", t, "Contido × quantidade no AMB — Goiás",
    f"{len(t)} linhas mineral-base-ano; com alerta: {int((t.codigos != '').sum())} (verificar {int((t.severidade == 'verificar').sum())}, "
    f"lacuna {int((t.severidade == 'lacuna').sum())}, informativo {int((t.severidade == 'informativo').sum())}).")
add("tonelagens_repetidas", r, "Mesma tonelagem em linhas diferentes (todas as UFs)", f"{r.grupo.nunique()} grupos, {len(r)} linhas.")
add("amb_x_cfem", x, f"AMB × CFEM por mineral — Goiás {ANOS[0]}–{ANOS[-1]}", "Valores em R$ correntes. Classificação na 00_leia_me.")
XLSX = os.path.join(SAIDA, "repositorio_erros.xlsx")
if MODO != "pipeline":
    os.makedirs(SAIDA, exist_ok=True)
    wb.save(XLSX)

# =============================================================================================== REPOSITORIO_ERROS.md
def tab_md(cab, linhas):
    return "\n".join(["| " + " | ".join(cab) + " |", "|" + "|".join("---" for _ in cab) + "|"] + ["| " + " | ".join(map(str, l)) + " |" for l in linhas])


b23r = b23.iloc[0] if len(b23) else None
cf_ano = cf[cf.ano.isin(ANOS)].groupby("ano").valor.sum()
md = f"""# Repositório de erros — bases do Squad 1

Squad 1 / Estudante 1 (Frente 1). Gerado em {HOJE} por `Squad 1/Bases consolidadas/base_consolidada_work/scripts/gerar_repositorio_erros.py`,
a partir de `Squad 1/Dados brutos/` e da planilha `{os.path.basename(PLAN)}`. Planilha completa: [`repositorio_erros.xlsx`](repositorio_erros.xlsx).
Todo número abaixo é recalculado a cada execução. **Regra do projeto:** divergência é registrada, não corrigida.

| Aba | O que tem |
|---|---|
| `erros` | catálogo com {len(cat)} erros (ERR_001…), com fonte, exemplo, número medido, impacto, regra adotada, checagem e status |
| `bario_niobio`, `bario_niobio_processos` | bário × nióbio em Goiás: AMB (bruta, beneficiada, contido) e CFEM por substância e processo |
| `contido_vs_bruto` | todos os minerais de Goiás: teor implícito e alertas C1…C8 |
| `tonelagens_repetidas` | mesma tonelagem em linhas diferentes, todas as UFs ({rep.grupo.nunique()} grupos, {len(rep)} linhas) |
| `amb_x_cfem` | Goiás {ANOS[0]}–{ANOS[-1]}: produção e valor no AMB × CFEM, comparados com a alíquota legal |

Lista de suspeitas de unidade trocada no AMB e na CFEM: [`auditoria_unidades_anm.md`](auditoria_unidades_anm.md).

## 1. Bário × nióbio: dá para separar?

| O que | Separa? | Por quê |
|---|---|---|
| Produção bruta (ROM) no AMB | **Não de verdade** | Cada mineral tem sua linha, mas o ROM do bário é a rocha lavrada para nióbio e fosfato. {('Em ' + str(int(b23r.ano)) + ' os dois têm exatamente **' + br(b23r.nb_rom_t, 2) + ' t** (linhas ' + str(b23r.nb_rom_linha_csv) + ' e ' + str(b23r.ba_rom_linha_csv) + ' do `Producao_Bruta.csv`).') if b23r is not None else ''} Na base, esse ROM tem status `rom_minerio_associado` e não é aberto por operação. |
| Contido | **Sim** | BaSO₄ para o bário e Nb₂O₅ para o nióbio. |
| Produção beneficiada | **Sim**, com cuidado | O nióbio mudou de conceito em 2024 (ver abaixo). |
| CFEM | **Sim** | `BARITA` × `NIÓBIO` / `MINÉRIO DE NIÓBIO`; os mesmos processos pagam as duas. |

**Nióbio beneficiado:** {br(nb.nb_benef_t[2023])} t em 2023 → {br(nb.nb_benef_t[2024])} t em 2024 → {br(nb.nb_benef_t[2025])} t em 2025, com o teor
caindo de ~50% para ~1,4% Nb₂O₅ (a ANM passou a registrar a massa que entra na usina). **Decidido em 19/11/2026 e aplicado na v18:** a série é o contido
em Nb₂O₅ — {br(nb.nb_benef_contido_t[2023])} t (2023), {br(nb.nb_benef_contido_t[2024])} t (2024), {br(nb.nb_benef_contido_t[2025])} t (2025). Na aba 09,
`serie_beneficiada = contido`; na 12, `production_basis = conteudo_mineral`.

## 2. "O contido é sempre verdadeiro?" — Não

{len(t)} linhas mineral-base-ano de Goiás; {int((t.codigos != '').sum())} com alerta (verificar {int((t.severidade == 'verificar').sum())},
lacuna {int((t.severidade == 'lacuna').sum())}, informativo {int((t.severidade == 'informativo').sum())}). Os principais: ERR_004 (ouro {int(ouro_pior.ano)}:
{br(ouro_pior.contido_t)} t de ouro contido no ROM), ERR_005 (nióbio), ERR_003 (contido com unidade '-'), ERR_008 (contido sem indicação), ERR_007 (lacunas).

## 3. Royalties: CFEM paga num mineral e não em outro

CFEM somada por ano ({ANOS[0]}–{ANOS[-1]}): {'; '.join(f'{y}: R$ {br(v / 1e6, 1)} mi' for y, v in cf_ano.items())}. A CFEM foi dividida pelo valor do AMB de
duas formas (só vendas; vendas + consumo + transferência) e comparada com a alíquota da Lei 8.001/1990 (redação da Lei 13.540/2017).

""" + tab_md(["Classe", "Mineral-anos", "Quais"], [
    ["Compatível com a alíquota", n_compat, "—"],
    ["**R1** — produção no AMB sem CFEM", nR["R1"], lista("R1") or "—"],
    ["**R2** — CFEM sem produção no AMB", nR["R2"], lista("R2") or "—"],
    ["**R4** — CFEM acima de 2× a alíquota", nR["R4"], lista("R4") or "—"],
    ["**R5** — CFEM abaixo de 1/4 da alíquota", nR["R5"], lista("R5") or "—"],
    ["**R6** — AMB com valor menor que a CFEM", nR["R6"], lista("R6") or "—"]]) + f"""

## 4. Catálogo ({len(cat)} erros)

""" + tab_md(["Código", "Fonte", "Erro", "Status"], [[c.codigo, c.fonte, c.descricao.split(";")[0].split(". ")[0], c.status] for c in cat.itertuples()]) + f"""

Por status: {', '.join(f'{k} {v}' for k, v in st.items())}. A coluna `onde_foi_conferido` diz de onde veio cada número; os marcados
"registro do projeto" foram medidos num arquivo ou momento que não está no repositório (com a data).

**Pendente:** ERR_024 — os CSV nacionais do Cadastro Mineiro têm aspas sem escape, e o leitor com `on_bad_lines="skip"` descarta essas linhas sem aviso
(1.184 no download nacional de 09/2026, nenhuma de Goiás; {linhas_ruins} no recorte do repositório). Proposta: contar as descartadas e falhar se alguma citar "- GO".
"""
if MODO != "pipeline":
    open(os.path.join(SAIDA, "REPOSITORIO_ERROS.md"), "w", encoding="utf-8", newline="\n").write(md)
    print(f"SALVO: {XLSX} ({len(cat)} erros; status {dict(st)}) e REPOSITORIO_ERROS.md")

# =============================================================================================== checagens para a 14b
# Cada erro com assinatura automática vira uma checagem: as ocorrências de hoje são comparadas com a lista conhecida (erros_conhecidos.json,
# revisada à mão). Ocorrência nova = ALERTA, para uma base nova acusar o mesmo tipo de erro de novo; a que sumiu só é relatada.
#   python gerar_repositorio_erros.py --atualizar-conhecidos   (grava a lista de hoje, depois de revisar as novas)
CONHECIDOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "erros_conhecidos.json")


def _chaves(codigos):
    x = teor[teor.alertas.fillna("").str.contains("|".join(c + " " for c in codigos))]
    return sorted({f"{s_}|{b_}|{int(y_)}|{c}" for s_, b_, y_, al_ in zip(x.substancia, x.base, x.ano, x.alertas)
                   for c in codigos if c + " " in al_})


linhas_go_descartadas = []
for f in sorted(glob.glob(arquivo("dados/ANM/cadastro_mineiro/*.csv"))):
    _l = open(f, encoding="cp1252", errors="replace").read().splitlines()
    _cab = next(csv.reader([_l[0]]))
    for i, l in enumerate(_l[1:], start=2):
        try:
            ok_ = len(next(csv.reader([l], strict=True))) == len(_cab)
        except csv.Error:
            ok_ = False
        if not ok_ and re.search(r"- GO\b", l):
            linhas_go_descartadas.append(f"{os.path.basename(f)}:{i}")
OCORRENCIAS = {
    "contido_incoerente": _chaves(["C1", "C2", "C4"]),
    "quebra_de_serie": _chaves(["C6"]),
    "lacuna_amb": _chaves(["C7", "C8"]),
    "amb_x_cfem": sorted(f"{s_}|{int(y_)}|{c[:2]}" for s_, y_, c in zip(axc.substancia, axc.ano, axc.classificacao) if c[:2] in ("R1", "R2", "R4", "R5", "R6")),
    "cfem_cnpj_notacao_cientifica": [f"{cpf_cient} linhas"] if cpf_cient else [],
    "cadastro_go_descartado": linhas_go_descartadas,
}
CHECAGENS_DEF = [
    ("contido_incoerente", "Repositório de erros (ERR_003/004): contido do AMB de GO incoerente com a quantidade (C1, C2, C4) — ocorrências fora da lista conhecida"),
    ("quebra_de_serie", "Repositório de erros (ERR_005): quebra de série maior que 5× no AMB de GO (C6) — ocorrências fora da lista conhecida"),
    ("lacuna_amb", "Repositório de erros (ERR_007): lacunas no AMB de GO, ano sem linha ou zero depois de ano produtivo (C7, C8) — fora da lista conhecida"),
    ("amb_x_cfem", "Repositório de erros (ERR_043–045): AMB × CFEM sem par ou fora da alíquota legal (R1, R2, R4, R5, R6) — fora da lista conhecida"),
    ("cfem_cnpj_notacao_cientifica", "Repositório de erros (ERR_013): CPF_CNPJ da CFEM em notação científica (CNPJ que não identifica a empresa)"),
    ("cadastro_go_descartado", "Repositório de erros (ERR_024): linhas do Cadastro Mineiro com município de GO que o leitor descartaria (aspas sem escape)"),
]
if "--atualizar-conhecidos" in sys.argv:
    # alertas_aceitos (lidos por travas.py) são revisados à mão: ficam como estão
    _aceitos = json.load(open(CONHECIDOS, encoding="utf-8")).get("alertas_aceitos") if os.path.exists(CONHECIDOS) else None
    json.dump({**OCORRENCIAS, **({"alertas_aceitos": _aceitos} if _aceitos else {})},
              open(CONHECIDOS, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    print(f"SALVO: {CONHECIDOS} ({sum(map(len, OCORRENCIAS.values()))} ocorrências conhecidas)")
_conh = json.load(open(CONHECIDOS, encoding="utf-8")) if os.path.exists(CONHECIDOS) else {}
CHECAGENS = []
for chave, nome in CHECAGENS_DEF:
    hoje, antes = set(OCORRENCIAS[chave]), set(_conh.get(chave, []))
    novas, sumiram = sorted(hoje - antes), sorted(antes - hoje)
    res = (f"{len(hoje)} ocorrências hoje, {len(hoje & antes)} já conhecidas" + (f"; NOVAS ({len(novas)}): " + "; ".join(novas[:12]) if novas else "; nenhuma nova")
           + (f"; deixaram de ocorrer ({len(sumiram)}): " + "; ".join(sumiram[:6]) if sumiram else ""))
    CHECAGENS.append(dict(verificacao=nome, n=len(novas), resultado=res, ok=not novas))

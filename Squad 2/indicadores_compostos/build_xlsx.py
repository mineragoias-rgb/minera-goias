# -*- coding: utf-8 -*-
"""Banco de 20 indicadores por município (Goiás, 2025). Uso: python3 build_xlsx.py  -> indicadores_2025.xlsx"""
import json, numpy as np, pandas as pd, openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter as L
from pathlib import Path
REPO=str(Path(__file__).resolve().parents[2])
P=json.load(open(f"{REPO}/data/panorama/panorama.json")); D=P["dims"]
mun=pd.DataFrame(D["mun"],columns=["cod","nome","pop","pib"]); mun.index.name="mun"
cf=pd.DataFrame(P["cfem"]["rows"],columns=P["cfem"]["cols"])
pr=pd.DataFrame(P["proc"]["rows"],columns=P["proc"]["cols"])
rd=pd.DataFrame(P["rod"]["rows"],columns=P["rod"]["cols"]); rd=rd[rd.mun>=0]
# área territorial (km²) da aba 10 do repositório
wb=openpyxl.load_workbook(f"{REPO}/Squad 1/Bases consolidadas/documentacao/prototipo_bases_consolidadas_v17.xlsx",read_only=True,data_only=True)
it=wb["10_cons_municipio_ano"].iter_rows(min_row=4,values_only=True); cab=list(next(it)); ix={c:i for i,c in enumerate(cab)}
ar={}
for r in it:
    if r and r[0] is not None and r[ix["area_km2"]] is not None: ar[int(r[0])]=float(r[ix["area_km2"]])
mun["area_km2"]=mun.cod.astype(int).map(ar)
N=len(mun)
# ---------- receita (2025)
c25=cf[cf.ano==2025]; c24=cf[cf.ano==2024]
mm=c25.groupby(["mun","mes"]).valor.sum().unstack(fill_value=0).reindex(index=mun.index,columns=range(1,13),fill_value=0)
R1=mm.sum(axis=1); R1_24=c24.groupby("mun").valor.sum().reindex(mun.index).fillna(0)
R2=(R1/R1_24-1).where(R1_24>0)
sd=mm.std(axis=1,ddof=1); sdl=np.log1p(mm).std(axis=1,ddof=1)
act=(mm>0).sum(axis=1)
R5=sdl.where(act>0); R6=(mm.mean(axis=1)/sd).where((act>0)&(sd>0))
# ---------- processos (todos com ano_processo <= 2025)
p=pr[pr.ano_processo<=2025].drop_duplicates(["processo","mun"])
cnt=p.groupby(["mun","status"]).size().unstack(fill_value=0).reindex(index=mun.index,columns=range(8),fill_value=0)
P1=cnt[0]+cnt[1]; P2=cnt[3]; P3=cnt[4]; P4=cnt[5]
A1=(p[p.status==4].groupby("mun").area_ha.sum()).reindex(mun.index).fillna(0)
r=rd.copy(); r["ha"]=r.area_ha/100.0  # correção de unidade
arr=r[r.situacao.isin([0,3])].drop_duplicates("processo"); ofe=r[r.situacao.isin([1,2])&~r.processo.isin(arr.processo)].drop_duplicates("processo")
A2=arr.groupby("mun").ha.sum().reindex(mun.index).fillna(0); A3=ofe.groupby("mun").ha.sum().reindex(mun.index).fillna(0)
# ---------- substâncias e titulares (todos os processos do município; parcela = área)
def hhi(g):
    t=g.sum()
    return float(((g/t)**2).sum()) if t>0 else np.nan
S1=p.groupby("mun")["min"].nunique().reindex(mun.index).fillna(0)
S2=p.groupby(["mun","min"]).area_ha.sum().groupby(level=0).apply(hhi).reindex(mun.index)
T1=p.groupby("mun")["emp"].nunique().reindex(mun.index).fillna(0)
T2=p.groupby(["mun","emp"]).area_ha.sum().groupby(level=0).apply(hhi).reindex(mun.index)
# ---------- tabela
df=pd.DataFrame({"cod":mun.cod,"nome":mun.nome,"R1":R1,"R2":R2,"R3":R1/mun["pop"],"R4":R1/mun.pib,"R5":R5,"R6":R6,
 "P1":P1,"P2":P2,"P3":P3,"P4":P4,"A1":A1,"A2":A2,"A3":A3,"A4":A1/100/mun.area_km2,"A5":A2/100/mun.area_km2,"A6":A3/100/mun.area_km2,
 "S1":S1,"S2":S2,"T1":T1,"T2":T2,"meses":act})
df.to_pickle("/tmp/ind.pkl"); mun.to_pickle("/tmp/mun.pkl")
# ---------- planilha
NAMES=[("R1","CFEM 2025 (R$)","Receita","R$","Σ CFEM recolhida jan–dez 2025"),
("R2","Crescimento da CFEM (2025 vs 2024)","Receita","%","CFEM₂₀₂₅ ÷ CFEM₂₀₂₄ − 1; vazio se CFEM₂₀₂₄ = 0"),
("R3","CFEM per capita (R$/hab.)","Receita","R$/hab.","R1 ÷ população (Insumos)"),
("R4","CFEM/PIB","Receita","razão","R1 ÷ PIB (Insumos)"),
("R5","Volatilidade da CFEM","Receita","desvio-padrão","desvio-padrão amostral de ln(1 + CFEM mensal), 12 meses de 2025; vazio sem CFEM"),
("R6","Sharpe da CFEM","Receita","razão","média mensal ÷ desvio-padrão amostral mensal (2025), sem taxa livre de risco; vazio se desvio = 0"),
("P1","Processos de lavra","Processos","nº","status 0 (operação ativa) + 1 (lavra autorizada sem CFEM recente)"),
("P2","Processos em pré-lavra","Processos","nº","status 3"),
("P3","Processos em pesquisa","Processos","nº","status 4"),
("P4","Requerimentos","Processos","nº","status 5 (requerimento de licenciamento ou lavra garimpeira)"),
("A1","Área em pesquisa (ha)","Área","ha","Σ área dos processos únicos em status 4"),
("A2","Área arrematada (ha)","Área","ha","Σ área de processos únicos das rodadas com situação Conquistada ou Arrematada (área ÷ 100, corrigida)"),
("A3","Área ofertada (ha)","Área","ha","Σ área de processos únicos das rodadas Livre ou Aguardando Leilão, exceto os já arrematados"),
("A4","% da área do município em pesquisa","Área","%","A1 ÷ 100 ÷ área territorial (km²) — pode ultrapassar 100% por sobreposição"),
("A5","% da área do município arrematada","Área","%","A2 ÷ 100 ÷ área territorial (km²)"),
("A6","% da área do município ofertada","Área","%","A3 ÷ 100 ÷ área territorial (km²)"),
("S1","Quantidade de substâncias","Substâncias","nº","substâncias distintas nos processos do município"),
("S2","HHI por substância","Substâncias","0–1","Σ(parcela²) da área por substância; direto: alto = concentrado; vazio sem processo"),
("T1","Quantidade de titulares","Titulares","nº","titulares distintos nos processos do município"),
("T2","HHI por titular","Titulares","0–1","Σ(parcela²) da área por titular; direto: alto = concentrado; vazio sem processo")]
out=openpyxl.Workbook(); H=PatternFill("solid",fgColor="1F3A2E"); HF=Font(bold=True,color="FFFFFF"); B=Font(bold=True)
def head(ws,row=1):
    for c in ws[row]: c.fill=H; c.font=HF; c.alignment=Alignment(wrap_text=True,vertical="center")
# Insumos
wi=out.active; wi.title="Insumos"
wi.append(["cod_ibge","município","população (repositório)","PIB R$ (repositório)","área territorial km²","CFEM 2025 R$","CFEM 2024 R$"])
for i,(k,m) in enumerate(mun.iterrows()):
    wi.append([int(m.cod),m.nome,int(m["pop"]) if pd.notna(m["pop"]) else None,float(m.pib) if pd.notna(m.pib) else None,m.area_km2,float(R1[k]),float(R1_24[k])])
head(wi)
wi.append([]); 
# Indicadores
ws=out.create_sheet("Indicadores",0)
ws.append(["cod_ibge","município"]+[f"{k} · {n}" for k,n,*_ in NAMES]+["meses com CFEM em 2025"])
fm={"R3":lambda r:f'=IF(AND(ISNUMBER(Insumos!C{r}),Insumos!C{r}>0),Insumos!F{r}/Insumos!C{r},"")',
    "R4":lambda r:f'=IF(AND(ISNUMBER(Insumos!D{r}),Insumos!D{r}>0),Insumos!F{r}/Insumos!D{r},"")',
    "R1":lambda r:f"=Insumos!F{r}",
    "A4":lambda r:f'=IF(Insumos!E{r}>0,K{r}/100/Insumos!E{r},"")',"A5":lambda r:f'=IF(Insumos!E{r}>0,L{r}/100/Insumos!E{r},"")',"A6":lambda r:f'=IF(Insumos!E{r}>0,M{r}/100/Insumos!E{r},"")'}
keys=[k for k,*_ in NAMES]
for i,(k,row) in enumerate(df.iterrows()):
    r=i+2; vals=[int(row.cod),row.nome]
    for kk in keys:
        if kk in fm: vals.append(fm[kk](r))
        else:
            v=row[kk]; vals.append(None if pd.isna(v) else float(v))
    vals.append(int(row.meses)); ws.append(vals)
# colunas A1..A3 são K..M? calcula posição real
pos={kk:2+keys.index(kk)+1 for kk in keys}
for i in range(N):
    r=i+2
    ws.cell(r,pos["A4"]).value=f'=IF(Insumos!E{r}>0,{L(pos["A1"])}{r}/100/Insumos!E{r},"")'
    ws.cell(r,pos["A5"]).value=f'=IF(Insumos!E{r}>0,{L(pos["A2"])}{r}/100/Insumos!E{r},"")'
    ws.cell(r,pos["A6"]).value=f'=IF(Insumos!E{r}>0,{L(pos["A3"])}{r}/100/Insumos!E{r},"")'
head(ws); ws.freeze_panes="C2"; ws.row_dimensions[1].height=60
for j in range(1,len(keys)+4): ws.column_dimensions[L(j)].width=16
ws.column_dimensions["B"].width=26
fmt={"R1":"#,##0","R2":"0.0%","R3":"#,##0.00","R4":"0.00%","R5":"0.000","R6":"0.00","A1":"#,##0","A2":"#,##0","A3":"#,##0","A4":"0.0%","A5":"0.0%","A6":"0.0%","S2":"0.000","T2":"0.000"}
for kk,f in fmt.items():
    for r in range(2,N+2): ws.cell(r,pos[kk]).number_format=f
# Dicionário
wd=out.create_sheet("Dicionário"); wd.append(["código","indicador","família","unidade","fórmula / regra","universo","origem","nova ou antiga"])
antigas={"R1","R3","R4","P1","P2","A1"}  # já existentes no site/entregas anteriores
for k,n,f,u,d in NAMES:
    wd.append([k,n,f,u,d,"246 municípios de Goiás","ANM (CFEM, cadastro, rodadas) + IBGE via repositório","antiga (versão anual)" if k in("R1","R3","R4") else "nova"])
head(wd)
for j,w in zip("ABCDEFGH",(8,38,14,12,80,22,40,20)): wd.column_dimensions[j].width=w
# Estatísticas
we=out.create_sheet("Estatísticas"); we.append(["código","indicador","n válidos","n vazios","média","mediana","P25","P75","mínimo","máximo","soma"])
for k,n,*_ in NAMES:
    s=df[k].astype(float) if k not in("R3","R4","A4","A5","A6") else df[k].astype(float)
    s=s.replace([np.inf,-np.inf],np.nan)
    we.append([k,n,int(s.notna().sum()),int(s.isna().sum()),s.mean(),s.median(),s.quantile(.25),s.quantile(.75),s.min(),s.max(),float(s.sum())])
head(we)
for j in "ABCDEFGHIJK": we.column_dimensions[j].width=16
we.column_dimensions["B"].width=38
# Mapeamento
wm=out.create_sheet("Mapeamento_fases"); wm.append(["status (código)","descrição no painel","entra em"])
mp={0:"P1 lavra",1:"P1 lavra",2:"nenhum indicador de fase (conta em S e T)",3:"P2 pré-lavra",4:"P3 pesquisa; A1",5:"P4 requerimentos",6:"nenhum (conta em S e T)",7:"nenhum (conta em S e T)"}
for i,s in enumerate(D["status"]): wm.append([i,s,mp[i]])
wm.append([]); wm.append(["situação da rodada","","entra em"])
for i,s in enumerate(D["sit"]): wm.append([i,s,"A2 arrematada" if i in(0,3) else ("A3 ofertada" if i in(1,2) else "nenhum")])
head(wm); wm.column_dimensions["B"].width=60; wm.column_dimensions["C"].width=44
# Leia-me
wl=out.create_sheet("LEIA-ME",0)
txt=["MINERA Goiás · Frente 8 · Banco de 20 indicadores por município · ano-base 2025","",
"Estrutura: 1 linha por município (246) × 20 indicadores. Sem painel temporal e sem índice composto: cada indicador é independente.",
"HHI (S2, T2) é direto: valor alto = concentração alta. Nenhum indicador foi invertido.",
"Células vazias = indicador indefinido (ex.: crescimento com base zero; HHI sem processos; Sharpe sem variação).",
"","RESSALVAS (leia antes de usar)",
"1) População: o repositório traz um único valor por município (rótulo ano 2026). Não é a série 2022–2025 do IBGE. Para trocar, edite a aba Insumos, coluna C; R3 recalcula.",
"2) PIB: o repositório traz o PIB de 2023, não o de 2022 pedido. Para trocar, edite a aba Insumos, coluna D; R4 recalcula. R4 mistura CFEM 2025 com PIB defasado.",
"3) Não foi possível baixar os arquivos do IBGE: o ambiente bloqueia o acesso externo (erro 403 do proxy). Anexe a tabela de população estimada e o PIB 2022 para substituir os insumos.",
"4) Processos e áreas são o estoque atual (fase = status atual) de processos abertos até 2025. Não há histórico de fase.",
"5) % de área usa a área territorial (aba 10 do repositório). Áreas de processos se sobrepõem, então o valor pode passar de 100%.",
"6) Áreas de rodadas (A2, A3) corrigidas: área ÷ 100 e um registro por processo. Isso difere dos valores usados no IPMM entregue antes (que estavam inflados).",
"7) HHI com parcela por área (ha). Substâncias e titulares = todos os processos do município, qualquer fase.",
"8) CFEM em R$ correntes. R5 e R6 usam os 12 meses de 2025; veja a coluna 'meses com CFEM em 2025' para avaliar a confiança.",
"9) Nenhum indicador aqui foi validado por testes de índice; são medidas descritivas."]
for t in txt: wl.append([t])
wl["A1"].font=Font(bold=True,size=13); wl.column_dimensions["A"].width=150
for rr in (6,): wl.cell(rr,1).font=B
out.save("indicadores_2025_raw.xlsx")
print(df.describe().T[["count","mean","max"]].to_string())
print("área nula:",mun.area_km2.isna().sum(),"pop nula:",mun['pop'].isna().sum(),"pib nulo:",mun.pib.isna().sum())
print("A2 total",A2.sum(),"A3 total",A3.sum(),"R1 total",R1.sum())

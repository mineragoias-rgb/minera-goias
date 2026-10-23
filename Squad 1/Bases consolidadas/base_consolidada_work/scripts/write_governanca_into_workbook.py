# -*- coding: utf-8 -*-
"""Etapa final de governança do protótipo (v5 -> v6). Roda DEPOIS de write_base4_into_workbook.py.

1. Padroniza nomes de coluna: aplica os nomes FIXADOS no Contrato de Dados V1 (year, mineral_name,
   municipality_name, production_t, energy_mwh, energy_intensity_mwh_t) e unifica nomes diferentes para a
   mesma informação entre abas (ex.: 'cnpj_raiz (8 díg.)' e 'cnpj_raiz').
2. Reconstrói 07_dim_fontes como catálogo mestre real: URLs oficiais (metadados .ods da ANM, SIDRA, geoftp
   do IBGE), arquivo local, sha256, tamanho, período efetivamente coberto, abas que citam cada fonte e as
   limitações encontradas no pente fino.
3. Reconstrói 14_dicionario_dados a partir das colunas REAIS da planilha (e não de definições antigas), com
   tipo inferido, % vazio, domínio e origem de cada campo.
4. 14b_validacoes_governanca: resultado das checagens (nomes, descrições, fontes, tipos, IDs, integridade).
"""
import contextlib, glob, hashlib, io, json, os, re, sys, warnings
from collections import Counter, defaultdict

import openpyxl
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
from caminhos import ARRANJO, BASE, TMP, arquivo, arquivos_brutos, data_acesso  # caminhos relativos ao projeto — ver caminhos.py
import qualidade_cfem
SRC = f"{BASE}/documentacao/prototipo_bases_consolidadas_v5d_fato.xlsx"  # v5 + 06/06b + 04/04b + 12 + 08 (write_ocorrencias_06 → write_projetos_04 → write_interface_12 → write_fato_08)
OUT = f"{BASE}/documentacao/prototipo_bases_consolidadas_v17.xlsx"
VERSAO = "v17"
NAVY, TEAL, LBLUE, WHITE, AMBER = "17365D", "1F6D7A", "DCE6F1", "FFFFFF", "C65911"
HDR = 4

ABAS_REAIS = ["01_dim_minerais", "02_dim_empresas", "03_dim_operacoes", "04_dim_projetos", "05_dim_municipios", "06_dim_ocorrencias_geologicas", "08_fato_producao_energia",
              "09_cons_mineral_ano", "10_cons_municipio_ano", "11_cons_empresa_ano_mineral", "12_interface_squad1_squad2", "13_mapas_camadas"]
ABAS_AUDITORIA = ["01b_crosswalk_pente_fino", "01c_rochas_por_tipo_de_uso", "02b_crosswalk_empresas", "04b_eventos_anm_classificados", "05b_crosswalk_municipios",
                  "06b_crosswalk_recmin",
                  "09b_auditoria_cfem_quantidade", "09c_alertas_cfem_processo", "13b_auditoria_mapas"]
ABAS_MAQUETE = []  # desde a v11 todas as abas são reais

# ---------------------------------------------------------------------------
# Padrão de nomes
# ---------------------------------------------------------------------------
RENAME = {
    # nomes fixados no Contrato de Dados V1 ("não alterar sem avisar o grupo")
    "ano": "year", "mineral_nome": "mineral_name", "mineral_nome_padronizado": "mineral_name",
    "municipio_nome": "municipality_name", "producao_t": "production_t", "consumo_energia_mwh": "energy_mwh",
    "intensidade_mwh_t": "energy_intensity_mwh_t",
    "producao_rom_t": "production_t_rom", "producao_beneficiada": "production_beneficiada",
    "unidade_beneficiada": "production_beneficiada_unit",
    # mesma informação com nomes diferentes entre abas
    "cnpj_raiz (8 díg.)": "cnpj_raiz", "identificacao": "identificacao_empresa",
    "identificacao (como o ID foi atribuído)": "identificacao_empresa",
    "principais_minerais_cadastro (snapshot)": "principais_minerais",
    # abas de auditoria e catálogo: nome de campo sem espaço, acento ou parêntese
    "valor_original (bruto na fonte)": "valor_original", "valor_normalizado (sem acento/maiúsculo)": "valor_normalizado",
    "mineral_id / nome atribuído": "atribuido_a", "municipio_id / nome atribuído": "atribuido_a", "atribuído a": "atribuido_a",
    "tipo_correspondência": "tipo_correspondencia", "tipo_correspondência / achado": "tipo_correspondencia",
    "verificação": "verificacao", "decisão": "decisao",
    "arquivo_geojson (web)": "arquivo", "tamanho_MB": "tamanho_mb", "camada_gpkg (QGIS)": "camada_gpkg",
}
CONTRATO = {"mineral_id", "company_id", "operation_id", "project_id", "municipality_id", "source_id", "source_ids",
            "mineral_name", "production_t", "energy_mwh", "energy_intensity_mwh_t", "year", "municipality_name",
            "latitude", "longitude", "production_basis", "scenario", "projected_production_t", "energy_demand_mwh"}
SNAKE = re.compile(r"^[a-z][a-z0-9_]*$")


def style_header(ws, title, note, ncol, h=60):
    last = get_column_letter(ncol)
    ws.merge_cells(f"A1:{last}1")
    ws["A1"] = title
    ws["A1"].font = Font(bold=True, color=WHITE, size=14)
    ws["A1"].fill = PatternFill("solid", fgColor=NAVY)
    ws.row_dimensions[1].height = 26
    ws.merge_cells(f"A2:{last}2")
    ws["A2"] = note
    ws["A2"].font = Font(italic=True, color="404040", size=10)
    ws["A2"].fill = PatternFill("solid", fgColor=LBLUE)
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[2].height = h


def write_table(ws, columns, rows, table_name, wrap=()):
    for i, c in enumerate(columns, start=1):
        cell = ws.cell(row=HDR, column=i, value=c["key"])
        cell.font = Font(bold=True, color=WHITE)
        cell.fill = PatternFill("solid", fgColor=TEAL)
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    ws.row_dimensions[HDR].height = 30
    for r_i, row in enumerate(rows, start=HDR + 1):
        for c_i, c in enumerate(columns, start=1):
            v = row.get(c["key"])
            v = None if v == "" else v
            cell = ws.cell(row=r_i, column=c_i, value=v)
            if c.get("fmt") and v is not None:
                cell.number_format = c["fmt"]
            if c["key"] in wrap:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
    if rows:
        t = Table(displayName=table_name, ref=f"A{HDR}:{get_column_letter(len(columns))}{HDR + len(rows)}")
        t.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
        ws.add_table(t)
    for i, c in enumerate(columns, start=1):
        ws.column_dimensions[get_column_letter(i)].width = c.get("width", 16)
    ws.freeze_panes = ws.cell(row=HDR + 1, column=min(3, len(columns))).coordinate


wb = openpyxl.load_workbook(SRC)

# descrições da maquete v0 (reaproveitadas só para as abas que ainda são maquete)
desc_v0 = {}
_it = wb["14_dicionario_dados"].iter_rows(min_row=HDR, values_only=True)
_h = next(_it)
for _r in _it:
    if _r and _r[0]:
        _d = dict(zip(_h, _r))
        desc_v0[(str(_d["aba"]).split(" — ")[0], _d["campo"])] = (_d.get("descricao_regra") or "", _d.get("unidade_ou_dominio") or "")

# ---------------------------------------------------------------------------
# 1) renomeação de cabeçalhos (célula E coluna da Tabela do Excel, senão o arquivo corrompe)
# ---------------------------------------------------------------------------
renomeados, nome_original = [], {}
for aba in ABAS_REAIS + ABAS_AUDITORIA + ABAS_MAQUETE:
    ws = wb[aba]
    for cell in ws[HDR]:
        if isinstance(cell.value, str) and cell.value in RENAME:
            renomeados.append((aba, cell.value, RENAME[cell.value]))
            nome_original[(aba, RENAME[cell.value])] = cell.value
            cell.value = RENAME[cell.value]
    for t in ws.tables.values():
        for tc in t.tableColumns:
            if tc.name in RENAME:
                tc.name = RENAME[tc.name]
print(f"Cabeçalhos renomeados: {len(renomeados)}")


def ler(aba):
    ws = wb[aba]
    cab = [c.value for c in ws[HDR]]
    linhas = [dict(zip(cab, r)) for r in ws.iter_rows(min_row=HDR + 1, values_only=True) if any(v is not None for v in r)]
    return [c for c in cab if c is not None], linhas


# ---------------------------------------------------------------------------
# 1b) v16: fontes por linha nas dimensões de minerais (01) e titulares (02), antes do catálogo contar as citações
# ---------------------------------------------------------------------------
from copy import copy as _copy
from openpyxl.worksheet.table import TableColumn


def acrescentar_colunas(aba, valores):
    """Acrescenta colunas no fim da tabela da aba: célula de cabeçalho com o mesmo estilo, valores linha a linha e coluna da Tabela do Excel."""
    ws = wb[aba]
    cab = [c.value for c in ws[HDR]]
    n = max(i for i, v in enumerate(cab, start=1) if v is not None)
    novas = [k for k in dict.fromkeys(k for v in valores for k in v) if k not in cab]
    assert ws.cell(row=HDR + len(valores), column=1).value is not None and ws.cell(row=HDR + len(valores) + 1, column=1).value is None, aba
    modelo = ws.cell(row=HDR, column=n)
    for j, nome in enumerate(novas, start=n + 1):
        h = ws.cell(row=HDR, column=j, value=nome)
        h._style = _copy(modelo._style)
        ws.column_dimensions[get_column_letter(j)].width = 30
        for i, v in enumerate(valores, start=HDR + 1):
            if v.get(nome) not in (None, ""):
                ws.cell(row=i, column=j, value=v[nome])
    for t in ws.tables.values():
        ini, fim = t.ref.split(":")
        t.ref = ini + ":" + get_column_letter(n + len(novas)) + re.sub(r"[A-Z]+", "", fim)
        for nome in novas:
            t.tableColumns.append(TableColumn(id=len(t.tableColumns) + 1, name=nome))
        if t.autoFilter is not None:
            t.autoFilter.ref = t.ref
    return novas


ORDEM_SRC = ["SRC_ANM_PROD_BRUTA", "SRC_ANM_PROD_BENEF", "SRC_ANM_CFEM", "SRC_ANM_CADASTRO", "SRC_ANM_SIGMINE", "SRC_SGB_RECMIN", "SRC_IBGE_MALHA_2025"]
_vazio = lambda v: v in (None, "", 0)
_fmin, _femp = defaultdict(set), defaultdict(set)
for r in ler("09_cons_mineral_ano")[1]:
    m = r["mineral_id"]
    if not _vazio(r.get("production_t_rom")):
        _fmin[m].add("SRC_ANM_PROD_BRUTA")
    if not _vazio(r.get("production_beneficiada")) or not _vazio(r.get("valor_venda_beneficiada_brl")):
        _fmin[m].add("SRC_ANM_PROD_BENEF")
    if not _vazio(r.get("cfem_recolhido_brl")):
        _fmin[m].add("SRC_ANM_CFEM")
    if not _vazio(r.get("qtd_processos_cadastro_mineiro")):
        _fmin[m].add("SRC_ANM_CADASTRO")
    if not _vazio(r.get("qtd_processos_sigmine")):
        _fmin[m].add("SRC_ANM_SIGMINE")
for r in ler("06_dim_ocorrencias_geologicas")[1]:
    for m in str(r.get("mineral_ids") or "").split(";"):
        if m.strip():
            _fmin[m.strip()].add("SRC_SGB_RECMIN")
for r in ler("03_dim_operacoes")[1]:
    if r.get("company_id"):
        _femp[r["company_id"]].add("SRC_ANM_SIGMINE")
for r in ler("11_cons_empresa_ano_mineral")[1]:
    if not _vazio(r.get("cfem_recolhido_brl")):
        _femp[r["company_id"]].add("SRC_ANM_CFEM")
_sem_fonte_min = 0
_v01 = []
for r in ler("01_dim_minerais")[1]:
    ids = sorted(_fmin.get(r["mineral_id"], ()), key=ORDEM_SRC.index)
    if not ids:  # categoria oficial sem dado em nenhuma fonte: a lista de categorias vem do AMB
        ids, _sem_fonte_min = ["SRC_ANM_PROD_BRUTA", "SRC_ANM_PROD_BENEF"], _sem_fonte_min + 1
    _v01.append(dict(source_ids="; ".join(ids)))
_v02 = []
for r in ler("02_dim_empresas")[1]:
    ids = set(_femp.get(r["company_id"], ()))
    if not _vazio(r.get("qtd_processos")) or str(r.get("identificacao_empresa") or "").startswith("raiz_cnpj"):
        ids.add("SRC_ANM_CADASTRO")
    _v02.append(dict(source_ids="; ".join(sorted(ids or {"SRC_ANM_CADASTRO"}, key=ORDEM_SRC.index))))
acrescentar_colunas("01_dim_minerais", _v01)
acrescentar_colunas("02_dim_empresas", _v02)
print(f"v16: source_ids na 01 ({len(_v01)} minerais; {_sem_fonte_min} sem dado em nenhuma fonte citam o AMB) e na 02 ({len(_v02)} titulares)")

DADOS = {aba: ler(aba) for aba in ABAS_REAIS + ABAS_AUDITORIA + ABAS_MAQUETE}

# ---------------------------------------------------------------------------
# 2) catálogo mestre de fontes (07)
# ---------------------------------------------------------------------------
citacoes, citacao_invalida = defaultdict(Counter), Counter()
for aba in ABAS_REAIS:
    cab, linhas = DADOS[aba]
    col_src = "source_ids" if "source_ids" in cab else ("source_id" if "source_id" in cab else None)  # a 08 cita uma fonte por linha
    if not col_src:
        continue
    for r in linhas:
        for s in str(r[col_src] or "").split(";"):
            s = s.strip()
            if not s:
                continue
            if re.fullmatch(r"SRC_[A-Z0-9_]+", s):
                citacoes[s][aba] += 1
            else:
                citacao_invalida[(aba, s)] += 1


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def info_arquivos(padroes):
    arqs = sorted({a for p in padroes for a in glob.glob(arquivo(p))})
    if not arqs:
        return dict(arquivos=0, tamanho_mb=None, sha256="", data_arquivo_local="")
    hs = [sha256(a) for a in arqs]
    return dict(arquivos=len(arqs), tamanho_mb=round(sum(os.path.getsize(a) for a in arqs) / 1e6, 2),
                sha256=hs[0] if len(hs) == 1 else "conjunto:" + hashlib.sha256("".join(hs).encode()).hexdigest(),
                data_arquivo_local=data_acesso(padroes))


def separador(p):
    with open(p, encoding="cp1252", errors="replace") as f:
        l = f.readline()
    return ";" if l.count(";") > l.count(",") else ","


def csv_local(p):
    s = separador(arquivo(p))
    return pd.read_csv(arquivo(p), sep=s, encoding="cp1252", encoding_errors="replace", dtype=str,
                       keep_default_na=False, engine="python", on_bad_lines="skip"), s


def periodo_ano(p, col_re=r"^ano"):
    try:
        df, _ = csv_local(p)
        col = next(c for c in df.columns if re.match(col_re, c.strip(), re.I))
        anos = sorted(int(a) for a in df[col] if str(a).strip().isdigit())
        return f"{anos[0]}–{anos[-1]}"
    except Exception as e:
        return f"(não calculado: {e})"


def formato_csv_local(p):
    try:
        _, s = csv_local(p)
        return f"CSV separado por {'ponto e vírgula' if s == ';' else 'vírgula'}; lido como Windows-1252"
    except Exception as e:
        return f"(não verificado: {e})"


try:
    _cf, _ = csv_local("dados/ANM/cfem/CFEM_Arrecadacao_2022_2026_GO.csv")
    _comp = (_cf["Ano"].astype(int) * 100 + _cf["Mês"].astype(int))
    _dc = pd.to_datetime(_cf["DataCriacao"].str.strip(), format="%d/%m/%Y %H:%M", errors="coerce")
    periodo_cfem = f"{_comp.min() // 100}-{_comp.min() % 100:02d} a {_comp.max() // 100}-{_comp.max() % 100:02d} (registros criados até {_dc.max():%Y-%m-%d})"
except Exception as e:
    _cf, periodo_cfem = None, f"(não calculado: {e})"
# qualidade do CPF_CNPJ contada no arquivo em uso (a ANM passou a publicar o CNPJ completo em out/2026) e cobertura da ponte do
# processo (build_base3): os textos da fonte SRC_ANM_CFEM e o aviso das contagens de titulares saem daqui
_q_cfem = qualidade_cfem.contar(_cf["CPF_CNPJ"]) if _cf is not None else None
try:
    _q_ponte = json.load(open(f"{TMP}/_cfem_qualidade.json", encoding="utf-8"))
except (OSError, ValueError):
    _q_ponte = None
_cob = qualidade_cfem.cobertura_ponte(_q_ponte)
if _q_cfem is None:
    _lim_cpf, _conf_cfem, AVISO_CNPJ = "CPF_CNPJ não verificado", "alta (oficial) para valores", "Contado pelo CPF_CNPJ da CFEM."
else:
    _lim_cpf, AVISO_CNPJ = qualidade_cfem.limitacao_catalogo(_q_cfem), qualidade_cfem.aviso_titulares(_q_cfem)
    _conf_cfem = "alta (oficial) para valores; " + ("baixa para identificação do titular" if qualidade_cfem.corrompido(_q_cfem)
                                                   else "média para identificação do titular (CNPJ completo, sem nome)")


def periodo_json(p):
    try:
        d = json.load(open(arquivo(p), encoding="utf-8"))
        anos = sorted({r["D3N"] for r in d[1:]})
        niveis = Counter(r["NN"] for r in d[1:])  # o arquivo de população traz também a linha da UF: não contar como município
        n_mun = niveis.pop("Município", 0)
        extra = "; " + ", ".join(f"mais {n} linha(s) de nível {k}" for k, n in niveis.items()) if niveis else ""
        return f"{', '.join(anos)} ({n_mun} municípios do Brasil no arquivo{extra})"
    except Exception as e:
        return f"(não calculado: {e})"


try:
    import pyogrio
    _gq = pyogrio.read_dataframe(f"{BASE}/outputs/mapas/minera_goias_mapas_v1.gpkg", layer="amostras_geoquimicas_sgb_go",
                                 columns=["projeto_sgb", "data_visita"], read_geometry=False)
    _gq["a"] = _gq["data_visita"].astype(str).str[:4]
    _gq = _gq[_gq["a"].str.isdigit()]
    periodo_sgb = "; ".join(f"{k}: coleta {g['a'].min()}–{g['a'].max()}" for k, g in _gq.groupby("projeto_sgb"))
except Exception as e:
    periodo_sgb = f"(não calculado: {e})"

try:  # RECMIN: URL exata da requisição e período vêm do próprio download (não duplicar à mão)
    _META_RECMIN = json.load(open(arquivo("dados/SGB_GeoSGB/recmin/ocorrencias_recursos_minerais_GO.metadados.json"), encoding="utf-8"))
    _rc = json.load(open(arquivo("dados/SGB_GeoSGB/recmin/ocorrencias_recursos_minerais_GO.geojson"), encoding="utf-8"))
    _dts = sorted(str(f["properties"]["data_cadastro"])[:10] for f in _rc["features"] if f["properties"].get("data_cadastro"))
    _ano_top, _n_top = Counter(x[:4] for x in _dts).most_common(1)[0]
    periodo_recmin = (f"cadastros no GeoSGB de {_dts[0]} a {_dts[-1]} ({100 * _n_top / len(_dts):.0f}% em {_ano_top}, carga do banco); "
                      f"baixado em {_META_RECMIN['data_download_utc'][:10]}")
except Exception as e:
    _META_RECMIN, periodo_recmin = {}, f"(não calculado: {e})"


def periodo_imb():
    partes = []
    for p in sorted(glob.glob(arquivo("dados/IMB/consulta*.csv"))):
        try:
            df = pd.read_csv(p, sep=";", encoding="cp1252", encoding_errors="replace", dtype=str, keep_default_na=False)
            anos = [c for c in df.columns if re.fullmatch(r"\d{4}", str(c).strip())]
            com = [a for a in anos if (df[a].str.strip().replace({"-": ""}) != "").any()]
            partes.append(f"{os.path.basename(p)}: colunas {anos[0]}–{anos[-1]}, último ano com valor {com[-1] if com else '—'}")
        except Exception as e:
            partes.append(f"{os.path.basename(p)}: (não calculado: {e})")
    return " | ".join(partes)


def periodo_zip(padroes):
    """Data de publicação do Leia-me.txt do pacote (quando existe) e faixa de datas dos arquivos internos do zip."""
    import zipfile
    partes = []
    for p in padroes:
        for a in sorted(glob.glob(arquivo(p))):
            try:
                with zipfile.ZipFile(a) as z:
                    datas = sorted("%04d-%02d" % i.date_time[:2] for i in z.infolist() if not i.is_dir())
                    leia = [n for n in z.namelist() if n.lower().endswith("leia-me.txt")]
                    pub = re.search(r"Data da Publica\w*o:\s*([\d/]+)", z.read(leia[0]).decode("utf-8", errors="replace")) if leia else None
                partes.append(f"{os.path.basename(a)}: " + (f"publicado em {pub.group(1)}; " if pub else "") + f"arquivos internos de {datas[0]} a {datas[-1]}")
            except Exception as e:
                partes.append(f"{os.path.basename(a)}: (não calculado: {e})")
    return " | ".join(partes)


def periodo_nazario(p):
    try:
        wbn = openpyxl.load_workbook(arquivo(p), read_only=True)
        datas, n, abas = [], 0, len(wbn.sheetnames)
        for ws in wbn.worksheets:
            it = ws.iter_rows(values_only=True)
            cab = [str(c).strip() if c is not None else "" for c in next(it)]
            i = cab.index("DATA_DE_ANÁLISE")
            for r in it:
                if any(v is not None for v in r):
                    n += 1
                    if r[i]:
                        datas.append(str(r[i])[:10])
        wbn.close()
        return f"análises de {min(datas)} a {max(datas)} ({n} linhas em {abas} abas)"
    except Exception as e:
        return f"(não calculado: {e})"


def periodo_mineradoras(p):
    try:
        wbm = openpyxl.load_workbook(arquivo(p), read_only=True)
        it = wbm["Operacao_atual"].iter_rows(min_row=4, values_only=True)
        cab = list(next(it))
        ini, fim = cab.index("CFEM_Ano_inicio"), cab.index("CFEM_Ano_fim")
        anos = [int(v) for r in it for v in (r[ini], r[fim]) if str(v or "").strip().isdigit()]
        wbm.close()
        return f"CFEM de {min(anos)} a {max(anos)} nas colunas da planilha; 'operação atual' = CFEM positiva em 2025 ou 2026 (critério da própria planilha)"
    except Exception as e:
        return f"(não calculado: {e})"


def periodo_json_uf(p):
    try:
        d = json.load(open(arquivo(p), encoding="utf-8"))
        return "; ".join(f"{r['D3N']} ({r['D1N']}: " + f"{int(r['V']):,}".replace(",", ".") + f" {r['MN'].lower()})" for r in d[1:])
    except Exception as e:
        return f"(não calculado: {e})"


def checagem_pop_uf():
    """O total estadual deve ser a soma dos municípios de GO na mesma tabela e ano — conferido a cada geração."""
    try:
        uf = json.load(open(arquivo("dados/IBGE/populacao_goias_ultimo_ano.json"), encoding="utf-8"))[1]
        mun = json.load(open(arquivo("dados/IBGE/populacao_municipal_goias_ultimo_ano.json"), encoding="utf-8"))[1:]
        # só código de município (7 dígitos): o arquivo "municipal" também traz a linha da UF (D1C = 52), que dobraria a soma
        go = [r for r in mun if len(str(r["D1C"])) == 7 and str(r["D1C"]).startswith("52") and r["D3N"] == uf["D3N"] and str(r["V"]).isdigit()]
        soma, total = sum(int(r["V"]) for r in go), int(uf["V"])
        s_soma, s_total = f"{soma:,}".replace(",", "."), f"{total:,}".replace(",", ".")
        return (f"Soma dos {len(go)} municípios de Goiás em {uf['D3N']} na população municipal (SRC_IBGE_POP) = {s_soma} pessoas: "
                f"{'igual ao' if soma == total else 'DIFERENTE do'} total estadual ({s_total}).")
    except Exception as e:
        return f"(checagem com a população municipal não calculada: {e})"


FONTES = [
    dict(source_id="SRC_ANM_PROD_BRUTA", nome_fonte="ANM — Anuário Mineral Brasileiro (AMB): produção bruta (minério ROM)", orgao="ANM", tipo_fonte="oficial",
         url_catalogo="https://dadosabertos.anm.gov.br/AMB/", url_recurso="https://dadosabertos.anm.gov.br/AMB/Producao_Bruta.csv",
         metadados_oficiais="https://dadosabertos.anm.gov.br/AMB/metadados-amb.ods (cópia em dados/ANM/producao_amb_ral/)",
         padroes=["dados/ANM/producao_amb_ral/Producao_Bruta.csv"], granularidade="UF × classe × substância × ano",
         formato_declarado="CSV separado por ponto e vírgula; Windows-1252", frequencia_atualizacao="diária (metadados ANM)",
         periodo=lambda: periodo_ano("dados/ANM/producao_amb_ral/Producao_Bruta.csv"), confiabilidade="alta (oficial), porém declaratória",
         limitacoes="Declaratório (RAL): a ANM alerta para inconsistências — divergências são registradas, não corrigidas. Não identifica empresa, operação nem município. "
                    "A cópia local (993.159 bytes) difere da publicada em 11/09/2026 (993.642 bytes; atualização diária): reprodutibilidade pelo sha256. "
                    "O separador local (vírgula) difere do declarado nos metadados (ponto e vírgula): um novo download pode quebrar os scripts."),
    dict(source_id="SRC_ANM_PROD_BENEF", nome_fonte="ANM — Anuário Mineral Brasileiro (AMB): produção beneficiada", orgao="ANM", tipo_fonte="oficial",
         url_catalogo="https://dadosabertos.anm.gov.br/AMB/", url_recurso="https://dadosabertos.anm.gov.br/AMB/Producao_Beneficiada.csv",
         metadados_oficiais="https://dadosabertos.anm.gov.br/AMB/metadados-amb.ods (cópia local)",
         padroes=["dados/ANM/producao_amb_ral/Producao_Beneficiada.csv"], granularidade="UF × classe × substância × ano × unidade",
         formato_declarado="CSV separado por ponto e vírgula; Windows-1252", frequencia_atualizacao="diária (metadados ANM)",
         periodo=lambda: periodo_ano("dados/ANM/producao_amb_ral/Producao_Beneficiada.csv"), confiabilidade="alta (oficial), porém declaratória",
         limitacoes="Declaratório (RAL). Unidade varia por substância (t, kg, ct, m³…): não somar entre minerais. "
                    "Cópia local (678.640 bytes) difere da publicada em 11/09/2026 (678.427 bytes). Separador local difere do declarado."),
    dict(source_id="SRC_ANM_CFEM", nome_fonte="ANM — CFEM: arrecadação (recorte Goiás de CFEM_Arrecadacao_2022_2026)", orgao="ANM", tipo_fonte="oficial",
         url_catalogo="https://dadosabertos.anm.gov.br/CFEM/", url_recurso="https://dadosabertos.anm.gov.br/CFEM/CFEM_Arrecadacao_2022_2026.csv",
         metadados_oficiais="https://dadosabertos.anm.gov.br/CFEM/metadados-cfem.ods (cópia em dados/ANM/cfem/)",
         padroes=["dados/ANM/cfem/CFEM_Arrecadacao_2022_2026_GO.csv"], granularidade="mês × processo × substância × município × titular",
         formato_declarado="CSV separado por ponto e vírgula; Windows-1252", frequencia_atualizacao="diária (metadados ANM)",
         periodo=lambda: periodo_cfem, confiabilidade=_conf_cfem,
         limitacoes="Recorte UF=GO do arquivo nacional feito antes de chegar em dados/ (passo não documentado — registrar no GitHub). "
                    f"{_lim_cpf}; sem nome do titular. "
                    "Empresa só pela ponte do número do processo" + (f" ({_cob.replace(' das linhas e ', ' das linhas; ')})" if _cob else "")
                    + ". Quantidade comercializada ≠ produção. 2026 parcial."),
    dict(source_id="SRC_ANM_CADASTRO", nome_fonte="ANM — Cadastro Mineiro (SCM): títulos e requerimentos", orgao="ANM", tipo_fonte="oficial",
         url_catalogo="https://dadosabertos.anm.gov.br/SCM/",
         url_recurso="https://dadosabertos.anm.gov.br/SCM/<arquivo>.csv — 13 arquivos (Alvara_de_Pesquisa, Cessoes_de_Direitos, Guia_de_Utilizacao_Autorizada, Licenciamento, PLG, Portaria_de_Lavra, …)",
         metadados_oficiais="https://dadosabertos.anm.gov.br/SCM/metadados-scm.ods (cópia em dados/ANM/cadastro_mineiro/)",
         padroes=["dados/ANM/cadastro_mineiro/*.csv"], granularidade=("processo × título — recorte de Goiás do arquivo nacional (recorte_goias.json; mesma regra de município do pipeline)"
                    if os.path.exists(arquivo("dados/ANM/cadastro_mineiro/recorte_goias.json")) else "processo × título — arquivo NACIONAL"),
         formato_declarado="CSV separado por ponto e vírgula; Windows-1252", frequencia_atualizacao="diária (metadados ANM)",
         periodo=lambda: "fotografia da situação cadastral na data dos arquivos", confiabilidade="alta (oficial)",
         limitacoes="Filtrar GO exige checar CADA município do campo multivalorado 'Municipio(s)' e rejeitar sufixo de UF ≠ GO sem casar pelo nome "
                    "(24 municípios homônimos em outros estados; 1.186 ocorrências). NÃO filtrar pela Superintendência (jurisdição ≠ fronteira). "
                    "O município textual guarda a divisão da época do registro (ex.: Jussara × Santa Fé de Goiás). Não cobre os processos da série 96xxxx que aparecem na CFEM. "
                    "Separador local (vírgula) difere do declarado."),
    dict(source_id="SRC_ANM_SIGMINE", nome_fonte="ANM — SIGMINE: polígonos dos processos minerários de Goiás", orgao="ANM", tipo_fonte="oficial",
         url_catalogo="https://dadosabertos.anm.gov.br/SIGMINE/", url_recurso="https://dadosabertos.anm.gov.br/SIGMINE/PROCESSOS_MINERARIOS/GO.zip",
         metadados_oficiais="https://dadosabertos.anm.gov.br/SIGMINE/metadados-sigmine.ods (NÃO baixado)",
         padroes=["dados/ANM/sigmine/GO.zip"], granularidade="polígono por processo (shapefile, SIRGAS 2000 / EPSG:4674)",
         formato_declarado="Shapefile zipado", frequencia_atualizacao="não verificada (metadados não baixados)",
         periodo=lambda: "fotografia na data do arquivo", confiabilidade="alta (oficial)",
         limitacoes="Sem campo de município (junção espacial; 99,84% de concordância com o Cadastro Mineiro). Campo UF não é recorte territorial. "
                    "27 polígonos com autointerseção e 176 processos fragmentados. ULT_EVENTO tem datas futuras (até 30/06/2028): não serve como data de extração. "
                    "Titular só por nome, sem CNPJ. A cópia local (10.296.115 bytes) difere da publicada em 11/09/2026 (10.292.361 bytes): reprodutibilidade pelo sha256."),
    dict(source_id="SRC_IBGE_MALHA_2025", nome_fonte="IBGE — Malha Municipal Digital 2025 (Goiás)", orgao="IBGE", tipo_fonte="oficial",
         url_catalogo="https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais.html",
         url_recurso="https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2025/UFs/GO/GO_Municipios_2025.zip",
         metadados_oficiais="Nota metodológica da Malha Municipal (leitura exigida pelo leia-me do arquivo)",
         padroes=["dados/IBGE/GO_Municipios_2025.zip"], granularidade="polígono por município (246), SIRGAS 2000",
         formato_declarado="Shapefile zipado", frequencia_atualizacao="anual",
         periodo=lambda: "limites vigentes em 2025 (arquivo publicado em 26/02/2026)", confiabilidade="alta (oficial)",
         limitacoes="O uso implica aceitar a nota metodológica do IBGE (condição do leia-me). O centro da caixa envolvente cai fora do município em 20 casos — usar representative_point."),
    dict(source_id="SRC_IBGE_POP", nome_fonte="IBGE — Estimativas de população (SIDRA, tabela 6579, variável 9324)", orgao="IBGE", tipo_fonte="oficial",
         url_catalogo="https://sidra.ibge.gov.br/tabela/6579",
         url_recurso="https://apisidra.ibge.gov.br/values/t/6579/n6/all/v/9324/p/2025 (consulta equivalente ao arquivo local)",
         metadados_oficiais="https://apisidra.ibge.gov.br/desctabapi.aspx?c=6579",
         padroes=["dados/IBGE/populacao_municipal_goias_ultimo_ano.json"], granularidade="município × ano",
         formato_declarado="JSON da API SIDRA (1ª linha = cabeçalho)", frequencia_atualizacao="anual",
         periodo=lambda: periodo_json("dados/IBGE/populacao_municipal_goias_ultimo_ano.json"), confiabilidade="alta (oficial; estimativa)",
         limitacoes="Apesar do nome, o arquivo traz todos os municípios do Brasil e ainda uma linha da UF de Goiás (código 52) — filtrar código de 7 dígitos começando com 52, "
                    "senão a soma de Goiás dobra. A tabela 6579 já publica 2026: o arquivo local está um ano defasado. "
                    "Estimativa, não contagem censitária."),
    dict(source_id="SRC_IBGE_PIB", nome_fonte="IBGE — PIB dos Municípios (SIDRA, tabela 5938, variável 37)", orgao="IBGE", tipo_fonte="oficial",
         url_catalogo="https://sidra.ibge.gov.br/tabela/5938",
         url_recurso="https://apisidra.ibge.gov.br/values/t/5938/n6/all/v/37/p/2023 (consulta equivalente ao arquivo local)",
         metadados_oficiais="https://apisidra.ibge.gov.br/desctabapi.aspx?c=5938",
         padroes=["dados/IBGE/pib_municipal_goias_ultimo_ano.json"], granularidade="município × ano",
         formato_declarado="JSON da API SIDRA (1ª linha = cabeçalho)", frequencia_atualizacao="anual (defasagem de ~2 anos)",
         periodo=lambda: periodo_json("dados/IBGE/pib_municipal_goias_ultimo_ano.json"), confiabilidade="alta (oficial)",
         limitacoes="Unidade = MIL REAIS (convertida para R$ na Base 2 desde a v5; antes estava rotulada como R$). 2023 é o último ano da tabela (2002–2023). "
                    "Arquivo com todos os municípios do Brasil e ainda uma linha da UF de Goiás (código 52) — filtrar código de 7 dígitos começando com 52."),
    dict(source_id="SRC_SGB_GEOSGB", nome_fonte="SGB — GeoSGB: pacotes de geoquímica (Oeste de Goiás, Noroeste de Goiás/Bonópolis, Folha Goiás PLGB)", orgao="SGB", tipo_fonte="oficial",
         url_catalogo="https://geosgb.sgb.gov.br/", url_recurso="não verificável automaticamente (o portal é uma aplicação JavaScript) — registrar o link de download à mão",
         metadados_oficiais="", padroes=["dados/SGB_GeoSGB/sig_vetorial/geoquimica_*.zip"],
         granularidade="ponto de amostragem + planilhas de resultados analíticos (chave NUM_LAB)",
         formato_declarado="Shapefile + XLSX zipados (EPSG:4674)", frequencia_atualizacao="estática (levantamentos concluídos)",
         periodo=lambda: periodo_sgb, confiabilidade="alta (oficial) — evidência geológica, não ocorrência",
         limitacoes="Os pacotes locais NÃO contêm ocorrências minerais (conferido camada a camada; o RECMIN veio do WFS do SGB: SRC_SGB_RECMIN). Au abaixo do limite de "
                    "detecção em 100% das amostras, com LD de 100 ppb numa campanha e 0,1 ppb na outra. "
                    "Separador decimal misto nas planilhas ('< 0,1' × '11.1'). 82 pontos fora de GO. PLGB: 403 amostras com mais de uma análise (mantido o maior teor)."),
    dict(source_id="SRC_SGB_RECMIN", nome_fonte="SGB — GeoSGB: Ocorrências de Recursos Minerais (RECMIN), recorte de Goiás pelo WFS oficial", orgao="SGB", tipo_fonte="oficial",
         url_catalogo="https://geosgb.sgb.gov.br/", url_recurso=_META_RECMIN.get("url_requisicao", "(metadados do download não encontrados)"),
         metadados_oficiais="DescribeFeatureType do WFS (geosgb:ocorrencias_recursos_minerais); ArcGIS REST: https://geoportal.sgb.gov.br/server/rest/services/geologia/ocorrencias/MapServer/0",
         padroes=["dados/SGB_GeoSGB/recmin/ocorrencias_recursos_minerais_GO.geojson"], granularidade="ponto por ocorrência (id_ocorrencia do GeoSGB)",
         formato_declarado="WFS 2.0 (GeoServer): GeoJSON, SHAPE-ZIP ou CSV; baixado em GeoJSON (WGS84)", frequencia_atualizacao="contínua (base corporativa do GeoSGB)",
         periodo=lambda: periodo_recmin, confiabilidade="alta (oficial) — evidência geológica, não projeto; posição por carta 1:250.000 na maioria dos pontos",
         limitacoes="Baixado em 12/09/2026 com autorização do Eliel, pela caixa de Goiás com folga (inclui pontos de MG, MT, DF, TO e MS, recortados pela malha do IBGE). "
                    "Evidência geológica (ocorrência, depósito, mina, garimpo), não lista de projetos (guia, seção 9). data_cadastro é a data de carga no banco, não a de "
                    "descoberta: 'Mina Ativo(a)' é a situação daquele cadastro, não a atual. Maioria dos pontos posicionada em carta 1:250.000. Status e importância "
                    "'Indeterminado' na maior parte. Campos sem informação: localizacao_mina ('Mina subterrânea (GPS sem sinal)' em quase tudo), situacao_garimpo "
                    "(cópia de situacao_mina), sureg e origem (valor único). Substâncias em ordem alfabética, sem a principal. Base viva: reprodutibilidade pelo sha256."),
    dict(source_id="SRC_ANM_AGUA_MINERAL", nome_fonte="ANM — AMB: produção de água mineral", orgao="ANM", tipo_fonte="oficial",
         url_catalogo="https://dadosabertos.anm.gov.br/AMB/", url_recurso="https://dadosabertos.anm.gov.br/AMB/Agua_Mineral_Producao.csv",
         metadados_oficiais="https://dadosabertos.anm.gov.br/AMB/metadados-amb.ods", padroes=["dados/ANM/agua_mineral/Agua_Mineral_Producao.csv"],
         granularidade="UF × ano", formato_declarado="CSV separado por ponto e vírgula; Windows-1252", frequencia_atualizacao="diária (metadados ANM)",
         periodo=lambda: periodo_ano("dados/ANM/agua_mineral/Agua_Mineral_Producao.csv"), confiabilidade="alta (oficial), declaratória",
         limitacoes="Água mineral aparece no Cadastro Mineiro e na CFEM, mas esta produção ainda não foi integrada à Base 1.", status_padrao="disponível em dados/, ainda não usada"),
    dict(source_id="SRC_ANM_INVEST_PESQUISA", nome_fonte="ANM — Investimento em pesquisa mineral por UF", orgao="ANM", tipo_fonte="oficial",
         url_catalogo="não verificada", url_recurso="não verificada", metadados_oficiais="", padroes=["dados/ANM/investimento_pesquisa/InvestimentoPesquisaMineralUf.csv"],
         granularidade="UF × substância × ano × rubrica", formato_declarado="não verificado", frequencia_atualizacao="não verificada",
         periodo=lambda: periodo_ano("dados/ANM/investimento_pesquisa/InvestimentoPesquisaMineralUf.csv"), confiabilidade="alta (oficial)",
         limitacoes="Origem exata e metadados não localizados em dados/.", status_padrao="disponível em dados/, ainda não usada"),
    dict(source_id="SRC_IMB_GOIAS_EM_DADOS", nome_fonte="IMB — Goiás em Dados (4 consultas: energia elétrica e produção mineral estadual)", orgao="IMB", tipo_fonte="oficial",
         url_catalogo="https://www.imb.go.gov.br/", url_recurso="exportação manual do Goiás em Dados (parâmetros da consulta não registrados)",
         metadados_oficiais="", padroes=["dados/IMB/consulta*.csv"], granularidade="estado × variável × ano",
         formato_declarado="não declarado (exportação do portal)", formato_local="CSV separado por ponto e vírgula, com aspas, milhar '.'; Windows-1252",
         frequencia_atualizacao="anual",
         periodo=periodo_imb, confiabilidade="média (secundária para produção)",
         limitacoes="A produção mineral (estado e municípios) só tem valor até 2016; a energia elétrica por setor vai até 2025. Usada só como checagem "
                    "cruzada do AMB (14b); reprodutibilidade limitada (parâmetros da consulta não registrados).",
         status_padrao="usada só como validação cruzada (14b: produção do estado × AMB)"),
    dict(source_id="SRC_ANM_PANORAMA_DERIVADO", nome_fonte="Panorama da Mineração em Goiás (análise derivada de dados ANM, extração de 04/08/2026)", orgao="interno (base ANM)", tipo_fonte="derivada",
         url_catalogo="—", url_recurso="—", metadados_oficiais="", padroes=["dados/ANM_derivados_analises/Panorama_Mineracao_Goias_ANM.xlsx"],
         granularidade=f"várias ({len(openpyxl.load_workbook(arquivo('dados/ANM_derivados_analises/Panorama_Mineracao_Goias_ANM.xlsx'), read_only=True).sheetnames)} abas)", formato_declarado="XLSX", frequencia_atualizacao="—", periodo=lambda: "2007–2026 conforme a aba",
         confiabilidade="média (derivada, sem script versionado)",
         limitacoes="Usada só para validação cruzada, nunca como fonte de valores: CFEM por empresa bateu ao centavo em 4 de 6 empresas; as divergências vêm dos processos 96xxxx.",
         status_padrao="usada só como validação cruzada"),
    # v13: arquivos de dados/ que estavam sem source_id (nenhum alimenta as abas de dados; status_uso diz o papel de cada um)
    dict(source_id="SRC_ANM_MINERADORAS_DERIVADO", nome_fonte="Mineradoras de Goiás: operação atual e potencial (análise derivada de SIGMINE, CFEM, TAH e REPEM da ANM)",
         orgao="interno (base ANM)", tipo_fonte="derivada", url_catalogo="—", url_recurso="—", metadados_oficiais="",
         padroes=["dados/ANM_derivados_analises/Mineradoras_Goias_operacao_e_potencial.xlsx"],
         granularidade="empresa × processo × polígono, em duas abas (Operacao_atual e Potencial_futuro)", formato_declarado="XLSX", frequencia_atualizacao="—",
         periodo=lambda: periodo_mineradoras("dados/ANM_derivados_analises/Mineradoras_Goias_operacao_e_potencial.xlsx"),
         confiabilidade="média (derivada, sem script versionado)",
         limitacoes="Produto derivado, não fonte primária: cruza GO.zip (SIGMINE), CFEM_Arrecadacao_2022_2026, TAH e REPEM com uma classificação própria "
                    "(Categoria, Confianca_classificacao, Criterio_classificacao) feita fora deste pipeline. No arquivo registrado: Operacao_atual = 406 empresas, "
                    "728 processos, 753 registros; Potencial_futuro = 2.092 empresas, 9.951 processos, 10.366 registros — só pessoas jurídicas (confirmadas ou inferidas). "
                    "Documento_CNPJ_CPF só traz CNPJ; as colunas de documento e nome vindas de TAH e REPEM não foram conferidas para LGPD — revisar antes de publicar. "
                    "Insumo do Radar de Projetos (Squad 1 / Estudante 2); a 04 não usa.",
         status_padrao="disponível em dados/, ainda não usada"),
    dict(source_id="SRC_IBGE_MALHA_2024", nome_fonte="IBGE — Malha Municipal Digital 2024 (Goiás)", orgao="IBGE", tipo_fonte="oficial",
         url_catalogo="https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais.html",
         url_recurso="https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2024/UFs/GO/GO_Municipios_2024.zip",
         metadados_oficiais="Nota metodológica da Malha Municipal", padroes=["dados/IBGE/ibge_malha_municipal_goias_2024.zip"],
         granularidade="polígono por município, SIRGAS 2000", formato_declarado="Shapefile zipado", frequencia_atualizacao="anual",
         periodo=lambda: "limites vigentes em 2024 — " + periodo_zip(["dados/IBGE/ibge_malha_municipal_goias_2024.zip"]), confiabilidade="alta (oficial)",
         limitacoes="Versão anterior à usada no pipeline (SRC_IBGE_MALHA_2025): serve só para comparar limites entre anos. Renomeada na cópia local — o zip contém "
                    "GO_Municipios_2024.shp, o mesmo nome do arquivo publicado (listagem do geoftp conferida em 12/09/2026: GO_Municipios_2024.zip, 16 MB, de "
                    "29/04/2025). O sha256 contra o publicado não foi conferido (exigiria baixar de novo).",
         status_padrao="disponível em dados/, não usada (o pipeline usa a malha 2025)"),
    dict(source_id="SRC_IBGE_POP_UF", nome_fonte="IBGE — Estimativa de população de Goiás (SIDRA, tabela 6579, variável 9324, nível UF)", orgao="IBGE", tipo_fonte="oficial",
         url_catalogo="https://sidra.ibge.gov.br/tabela/6579",
         url_recurso="https://apisidra.ibge.gov.br/values/t/6579/n3/52/v/9324/p/2025 (consulta conferida em 12/09/2026: mesmo valor do arquivo local)",
         metadados_oficiais="https://apisidra.ibge.gov.br/desctabapi.aspx?c=6579", padroes=["dados/IBGE/populacao_goias_ultimo_ano.json"],
         granularidade="UF × ano", formato_declarado="JSON da API SIDRA (1ª linha = cabeçalho)", frequencia_atualizacao="anual",
         periodo=lambda: periodo_json_uf("dados/IBGE/populacao_goias_ultimo_ano.json"), confiabilidade="alta (oficial; estimativa)",
         limitacoes="Um único número por ano. A Base 2 usa a população municipal (SRC_IBGE_POP); este total serve de checagem. " + checagem_pop_uf()
                    + " Estimativa, não contagem censitária.",
         status_padrao="disponível em dados/, ainda não usada"),
    dict(source_id="SRC_SGB_GEOQUIMICA_NAZARIO", nome_fonte="SGB — Geoquímica do Projeto Sudeste de Goiás, Folha Nazário (resultados analíticos em planilha)",
         orgao="SGB", tipo_fonte="oficial", url_catalogo="https://geosgb.sgb.gov.br/",
         url_recurso="não verificável automaticamente (o portal é uma aplicação JavaScript) — registrar o link de download à mão", metadados_oficiais="",
         padroes=["dados/SGB_GeoSGB/geoquimica_tabular/projeto_se_de_goias_fl_nazario_geoquimica.xlsx"],
         granularidade="amostra × método analítico, em 4 abas por classe de amostra (concentrado de bateia, mineralometria, rocha, sedimento de corrente)",
         formato_declarado="XLSX", frequencia_atualizacao="estática (levantamento concluído)",
         periodo=lambda: periodo_nazario("dados/SGB_GeoSGB/geoquimica_tabular/projeto_se_de_goias_fl_nazario_geoquimica.xlsx"),
         confiabilidade="alta (oficial) — evidência geológica, não ocorrência",
         limitacoes="A mesma amostra aparece em mais de uma linha quando tem mais de um método (356 casos no arquivo registrado, ex.: absorção atômica e "
                    "espectrografia com o mesmo número de laboratório) — escolher o método antes de comparar teores. Parte das análises é semiquantitativa "
                    "(espectrografia ótica de emissão). Coordenadas em graus decimais (LATITUDE/LONGITUDE), datum não conferido; pontos só na Folha Nazário "
                    "(lat. −17,0 a −16,5; long. −50,0 a −49,5). Não entra na camada de amostras geoquímicas da Base 4, que usa os pacotes de SRC_SGB_GEOSGB.",
         status_padrao="disponível em dados/, ainda não usada"),
    dict(source_id="SRC_SGB_SIG_GEOLOGIA", nome_fonte="SGB — SIG geológicos 1:250.000 (ARIM Centro-Norte da Faixa Brasília, Oeste de Goiás integrado, Folha Barro Alto)",
         orgao="SGB", tipo_fonte="oficial", url_catalogo="https://geosgb.sgb.gov.br/",
         url_recurso="não verificável automaticamente (o portal é uma aplicação JavaScript) — registrar o link de download à mão",
         metadados_oficiais="Leia-me.txt dentro de cada pacote (projeto, escala, datum, data de publicação e atributos da litologia)",
         padroes=["dados/SGB_GeoSGB/sig_vetorial/sig_geologico_integ_centro_norte_faixa_brasilia_vr.zip",
                  "dados/SGB_GeoSGB/sig_vetorial/sig_oeste_de_goias_integrado_vr.zip", "dados/SGB_GeoSGB/sig_vetorial/sig_barro_alto_vr.zip"],
         granularidade="camadas vetoriais por projeto — litologia, estruturas, afloramentos e base cartográfica (14, 31 e 10 shapefiles)",
         formato_declarado="Shapefile zipado, com estilos ArcGIS (.lyr/.lyrx) e QGIS (.qml/.sld)", frequencia_atualizacao="estática (mapas publicados)",
         periodo=lambda: periodo_zip(["dados/SGB_GeoSGB/sig_vetorial/sig_geologico_integ_centro_norte_faixa_brasilia_vr.zip",
                                      "dados/SGB_GeoSGB/sig_vetorial/sig_oeste_de_goias_integrado_vr.zip", "dados/SGB_GeoSGB/sig_vetorial/sig_barro_alto_vr.zip"]),
         confiabilidade="alta (oficial) — evidência geológica na escala 1:250.000",
         limitacoes="Não trazem ocorrências minerais (conferido camada a camada; o RECMIN veio do WFS do SGB: SRC_SGB_RECMIN). Datum diferente entre pacotes: "
                    "Faixa Brasília e Oeste de Goiás em SIRGAS 2000 (EPSG:4674), Barro Alto em WGS 84 (EPSG:4326) — reprojetar antes de sobrepor. Escala "
                    "1:250.000: não serve para comparar com limites de processo. O Leia-me da Faixa Brasília traz o ano de publicação com dois dígitos.",
         status_padrao="disponível em dados/, ainda não usada"),
    dict(source_id="SRC_SGB_MAPAS_REFERENCIA", nome_fonte="SGB — mapas de referência de Goiás em PDF (recursos minerais, favorabilidade, metalogenético, geológico-geofísico, agrominerais, geotécnico)",
         orgao="SGB", tipo_fonte="oficial", url_catalogo="https://geosgb.sgb.gov.br/", url_recurso="não registrado", metadados_oficiais="",
         padroes=["dados/SGB_GeoSGB/mapas_referencia_GO/*.pdf"], granularidade="mapa em PDF por projeto ou tema", formato_declarado="PDF", formato_local="PDF",
         frequencia_atualizacao="estática (mapas publicados)", periodo=lambda: "data de publicação impressa em cada mapa (não extraída)",
         confiabilidade="alta (oficial) — referência visual, não dado estruturado",
         limitacoes="PDF: nada daqui entra nas abas sem digitalização, e evidência geológica não vira projeto (guia, seção 9). Serve para conferir à mão "
                    "ocorrências da 06 e o contexto dos projetos da 04.",
         status_padrao="referência (PDF, não estruturado)"),
]
if ABAS_MAQUETE:  # o placeholder só existe enquanto houver aba em maquete (desde a v11 não há; saiu do catálogo na v12)
    FONTES.append(dict(source_id="SRC_EXEMPLO_ILUSTRATIVO", nome_fonte="Placeholder das abas ainda em maquete (não é fonte)", orgao="—", tipo_fonte="—",
                       url_catalogo="—", url_recurso="—", metadados_oficiais="", padroes=[], granularidade="—", formato_declarado="—", frequencia_atualizacao="—",
                       periodo=lambda: "—", confiabilidade="—", limitacoes="Marca as linhas de exemplo das abas em maquete. Nunca usar como dado.",
                       status_padrao="placeholder (abas maquete)"))

AUSENTE = "arquivo não incluído nesta cópia (fonte catalogada, não usada nas abas de dados)"
fontes_rows = []
for f in FONTES:
    inf = info_arquivos(f["padroes"])
    arq_local = "; ".join(f["padroes"])
    fmt_local = formato_csv_local(f["padroes"][0]) if inf["arquivos"] and f["padroes"] and f["padroes"][0].endswith(".csv") and "*" not in f["padroes"][0] else (
        "CSV separado por vírgula; lido como Windows-1252" if f["padroes"] and "cadastro" in f["padroes"][0] else
        "JSON" if f["padroes"] and f["padroes"][0].endswith(".json") else "ZIP (shapefile)" if f["padroes"] and f["padroes"][0].endswith(".zip") else
        "XLSX" if f["padroes"] and f["padroes"][0].endswith(".xlsx") else "")
    cit = citacoes.get(f["source_id"], Counter())
    fontes_rows.append(dict(
        source_id=f["source_id"], nome_fonte=f["nome_fonte"], orgao=f["orgao"], tipo_fonte=f["tipo_fonte"],
        status_uso="em uso" if cit else (f.get("status_padrao", "catalogada, não citada") if inf["arquivos"] or not f["padroes"] else AUSENTE),
        usado_em="; ".join(f"{a} ({n:,} linhas)".replace(",", ".") for a, n in sorted(cit.items())),
        url_catalogo=f["url_catalogo"], url_recurso=f["url_recurso"], metadados_oficiais=f["metadados_oficiais"],
        arquivo_local=arq_local, arquivos=inf["arquivos"], tamanho_mb=inf["tamanho_mb"], sha256=inf["sha256"],
        data_arquivo_local=inf["data_arquivo_local"], periodo_coberto=f["periodo"]() if inf["arquivos"] or not f["padroes"] else AUSENTE,
        granularidade=f["granularidade"],
        formato_declarado=f["formato_declarado"], formato_arquivo_local=f.get("formato_local") or fmt_local, frequencia_atualizacao=f["frequencia_atualizacao"],
        confiabilidade=f["confiabilidade"], limitacoes_conhecidas=f["limitacoes"]))
REG = {f["source_id"] for f in FONTES}
print(f"Catálogo de fontes: {len(fontes_rows)} fontes; citadas: {len(citacoes)}; citadas sem registro: {sorted(set(citacoes) - REG)}")

# ---------------------------------------------------------------------------
# 2b) v16: campos de governança por linha (Entrega Avaliativa §3) nas abas 01, 02, 03, 05, 09, 10, 11 e 13; método na 04
# ---------------------------------------------------------------------------
RESPONSAVEL = "Squad 1 / Estudante 1 — checagens automáticas do pipeline (ver 14b)"
_F07 = {r["source_id"]: r for r in fontes_rows}


def _ids(v):
    return [x.strip() for x in str(v or "").split(";") if x.strip()]


def _periodo_fonte(sid):
    p = str(_F07[sid]["periodo_coberto"] or "")
    return p.split(" (")[0].split(";")[0].strip() if p[:1].isdigit() else f"arquivo de {_F07[sid]['data_arquivo_local'] or '—'}"


_st = defaultdict(set)  # alertas das linhas da 08 que entram em cada linha consolidada
for r in DADOS["08_fato_producao_energia"][1]:
    st = r.get("status_validacao")
    if not st or st == "valido":
        continue
    m, y = r.get("mineral_id"), r.get("year")
    if r.get("source_id") == "SRC_ANM_CFEM":
        _st[("09", m, "GO", y)].add(st)
        _st[("10", str(r.get("municipality_id")), y)].add(st)
        _st[("11", r.get("company_id"), m, y)].add(st)
        if r.get("operation_id"):
            _st[("03", r.get("operation_id"))].add(st)
    else:
        _st[("09", m, r.get("uf"), y)].add(st)
        _st[("09", m, "BR", y)].add(st)


def _status(chave):
    return "; ".join(sorted(_st.get(chave, ()))) or "valido"


NATUREZA_GOV = {"01_dim_minerais": "calculado", "02_dim_empresas": "observado", "03_dim_operacoes": "observado", "05_dim_municipios": "observado",
                "09_cons_mineral_ano": "observado", "10_cons_municipio_ano": "observado", "11_cons_empresa_ano_mineral": "observado",
                "13_mapas_camadas": "calculado"}
METODO_GOV = {
    "01_dim_minerais": "Padronização: cada grafia das fontes vira uma categoria da ANM pelo crosswalk da 01b (rochas pelo tipo de uso, 01c); mineral_id por ordenação (classe, nome).",
    "13_mapas_camadas": "Camada gerada pelo pipeline a partir das abas de origem (ver chaves_de_juncao e simplificacao_web).",
}
CONSULTAS = ("09_cons_mineral_ano", "10_cons_municipio_ano", "11_cons_empresa_ano_mineral")
for _aba, _nat in NATUREZA_GOV.items():
    _valores = []
    for r in DADOS[_aba][1]:
        ids = [i for i in _ids(r.get("source_ids")) if i in _F07]
        if _aba in CONSULTAS:
            periodo = str(r["year"]) + (" (parcial)" if str(r["year"]) == "2026" else "")
            chave = {"09_cons_mineral_ano": ("09", r.get("mineral_id"), r.get("uf"), r.get("year")),
                     "10_cons_municipio_ano": ("10", str(r.get("municipality_id")), r.get("year")),
                     "11_cons_empresa_ano_mineral": ("11", r.get("company_id"), r.get("mineral_id"), r.get("year"))}[_aba]
            status = _status(chave)
        else:
            periodo = "; ".join(_periodo_fonte(i) for i in ids)
            status = (_status(("03", r.get("operation_id"))) if _aba == "03_dim_operacoes" else
                      "alerta_titular_nao_identificado" if _aba == "02_dim_empresas" and r.get("company_id") == "COM_NAO_IDENTIFICADO" else "valido")
        _valores.append(dict(
            source_url="; ".join(_F07[i]["url_recurso"] for i in ids), data_acesso="; ".join(str(_F07[i]["data_arquivo_local"]) for i in ids),
            periodo_referencia=periodo, tipo_fonte="; ".join(dict.fromkeys(_F07[i]["tipo_fonte"] for i in ids)),
            valor_observado_estimado=_nat, metodo_estimacao=METODO_GOV.get(_aba), status_validacao=status, responsavel_validacao=RESPONSAVEL))
    acrescentar_colunas(_aba, _valores)
    DADOS[_aba] = ler(_aba)
acrescentar_colunas("04_dim_projetos", [dict(metodo_estimacao=(
    "Projeto = processos contíguos (até 100 m) do mesmo titular e mineral; classificação por evidência na ANM (critério em criterio_classificacao; "
    "tipos de evento na 04b)."))] * len(DADOS["04_dim_projetos"][1]))
DADOS["04_dim_projetos"] = ler("04_dim_projetos")
print("v16: campos de governança da §3 em " + ", ".join(a[:2] for a in NATUREZA_GOV) + " e metodo_estimacao na 04")

DA_GOV = {}
for _aba in NATUREZA_GOV:
    DA_GOV.update({
        (_aba, "source_url"): "URL de cada fonte da linha, na mesma ordem de source_ids (igual a url_recurso da 07).",
        (_aba, "data_acesso"): "Data do arquivo local de cada fonte, na mesma ordem de source_ids (igual a data_arquivo_local da 07).",
        (_aba, "tipo_fonte"): "Tipo das fontes da linha (oficial, companhia, setorial, imprensa ou derivada), como na 07.",
        (_aba, "responsavel_validacao"): "Quem validou: as checagens automáticas do pipeline, registradas na 14b.",
        (_aba, "periodo_referencia"): ("Ano da linha; 2026 é parcial (CFEM com registros até o início de agosto)." if _aba in CONSULTAS else
                                       "Período coberto por cada fonte da linha (da 07), na mesma ordem de source_ids."),
        (_aba, "valor_observado_estimado"): ("observado: somas de valores observados das fontes (linhas da 08), sem estimativa." if _aba in CONSULTAS else
                                             "observado: registro como consta nas fontes; atributos derivados estão descritos neste dicionário." if NATUREZA_GOV[_aba] == "observado" else
                                             "calculado: gerado pelo pipeline; o método está em metodo_estimacao."),
        (_aba, "metodo_estimacao"): "Método quando o valor não é observado; vazio nas linhas observadas.",
        (_aba, "status_validacao"): ("valido, ou os alertas das linhas da 08 que entram na soma (alerta_processo_09c, quantidade_excluida_da_soma_09b, "
                                     "alerta_producao_repetida), separados por ';'." if _aba in CONSULTAS else
                                     "valido, ou os alertas das linhas de CFEM do processo na 08." if _aba == "03_dim_operacoes" else
                                     "valido; alerta_titular_nao_identificado no grupo COM_NAO_IDENTIFICADO (processos sem titular no Cadastro Mineiro)." if _aba == "02_dim_empresas" else
                                     "valido: passou nas checagens automáticas da 14b."),
    })
DA_GOV[("01_dim_minerais", "source_ids")] = ("Fontes em que o mineral aparece: AMB (produção), CFEM, Cadastro Mineiro e SIGMINE (aba 09) e RECMIN (aba 06). "
                                              "Categoria oficial sem dado em nenhuma fonte cita o AMB, de onde vem a lista de categorias.")
DA_GOV[("02_dim_empresas", "source_ids")] = "Fontes em que o titular aparece: Cadastro Mineiro (processos e CNPJ), SIGMINE (aba 03) e CFEM (aba 11)."
DA_GOV[("04_dim_projetos", "metodo_estimacao")] = "Como o projeto e a classificação foram calculados (os projetos são valor calculado)."

# ---------------------------------------------------------------------------
# 3) dicionário de dados (14) — a partir das colunas reais
# ---------------------------------------------------------------------------
# unidades misturadas na quantidade comercializada da CFEM, por mineral canônico (checagem automática)
nota_cfem_qtd = ""
try:
    _src = open(f"{BASE}/base_consolidada_work/scripts/build_base1_mineral_ano.py", encoding="utf-8").read()
    _ns = {}
    with contextlib.redirect_stdout(io.StringIO()):
        exec(_src.split("# 2) Carregar as fontes")[0].replace("sys.stdout.reconfigure", "(lambda **k: None)"), _ns)
    if _cf is not None:
        _cf["_k"] = _cf["Substância"].map(lambda s: _ns["RAW2KEY"].get(_ns["norm"](s)))
        _u = _cf.dropna(subset=["_k"]).groupby("_k")["UnidadeDeMedida"].agg(lambda s: sorted({x.strip() for x in s if x.strip()}))
        _mix = {_ns["MIN_DEF"][k][0]: v for k, v in _u.items() if len(v) > 1}
        nota_cfem_qtd = ("UNIDADES MISTURADAS no mesmo mineral — a soma não é fisicamente comparável: "
                         + "; ".join(f"{k} ({', '.join(v)})" for k, v in sorted(_mix.items()))) if _mix else "Cada mineral tem uma única unidade na CFEM."
except Exception as e:
    nota_cfem_qtd = f"(checagem de unidades não executada: {e})"
print("CFEM qtd comercializada:", nota_cfem_qtd[:160])

D = {  # campo -> (descrição, unidade/domínio, fonte ou derivação)
    "mineral_id": ("Identificador estável do mineral. Atribuído por ordenação (classe, nome) sobre as 57 categorias oficiais da ANM + subitens justificados; nunca por hash do nome. Para rochas, a categoria depende do tipo de uso declarado (ver 01c).", "MIN_### (3 dígitos)", "Derivado — 01_dim_minerais / crosswalk 01b"),
    "company_id": ("Identificador estável do titular. PJ: raiz do CNPJ (agrupa matriz e filiais). PF: CPF íntegro ou sha1 do nome normalizado (CPF mascarado por LGPD). COM_NAO_IDENTIFICADO = CFEM de processo ausente do Cadastro Mineiro e do SIGMINE.", "COM_CNPJ_########, COM_CPF_###########, COM_NOME_<8 hex>, COM_NAO_IDENTIFICADO", "Derivado — Cadastro Mineiro (Titular, CPF/CNPJ)"),
    "operation_id": ("Identificador estável do processo minerário, derivado do número canônico do processo ANM.", "OPE_<número>_<ano>", "Derivado — SIGMINE.PROCESSO"),
    "municipality_id": ("Código IBGE do município (7 dígitos). Padrão externo estável.", "52##### (7 dígitos)", "IBGE — malha 2025 (CD_MUN)"),
    "source_ids": ("Fontes de onde vieram os valores da linha. Cada fonte entra se, e somente se, alguma coluna da linha veio dela.", "SRC_* separados por ';' (IDs da aba 07)", "Governança"),
    "mineral_name": ("Nome padronizado do mineral (campo fixado no Contrato de Dados).", "texto", "01_dim_minerais"),
    "municipality_name": ("Nome oficial do município (campo fixado no Contrato de Dados).", "texto", "IBGE — malha 2025 (NM_MUN)"),
    "razao_social": ("Razão social mais frequente do titular nas fontes de título. CPF que venha dentro do nome (empresário individual) sai mascarado por LGPD: ***456789**.", "texto", "Cadastro Mineiro (Titular)"),
    "classe_substancia": ("Classe da substância segundo a ANM.", "", "ANM AMB / definição da dimensão"),
    "mineral_grupo_pai": ("mineral_id do mineral-pai quando o item é subtipo (ex.: Calcário Calcítico → Calcário).", "MIN_### ou vazio", "Derivado"),
    "categoria_agregada_anm": ("VERDADEIRO quando o nome é uma categoria composta da própria ANM (ex.: 'Dolomito e Magnesita'), que não pode ser desagregada.", "booleano", "ANM AMB"),
    "status_producao_go": ("Evidência de produção em Goiás, CALCULADA: confirmada = há produção ANM ou CFEM em GO; exploracao = só título minerário; sem_titulo_ou_producao_go = categoria nacional sem ocorrência em GO.", "", "Derivado — AMB + CFEM + Cadastro Mineiro + SIGMINE"),
    "observacao": ("Nota metodológica ou de rastreabilidade da linha.", "texto livre", "—"),
    "cnpj_raiz": ("8 primeiros dígitos do CNPJ: identificam a empresa (o restante é o estabelecimento).", "8 dígitos; vazio para PF", "Cadastro Mineiro (CPF/CNPJ do titular)"),
    "cnpj_completo_exemplo": ("Um CNPJ completo observado para o titular (pode haver outros, de filiais).", "##.###.###/####-##", "Cadastro Mineiro"),
    "tipo_pessoa": ("Natureza do titular.", "", "Cadastro Mineiro"),
    "identificacao_empresa": ("Como o company_id foi atribuído.", "", "Governança — resolução de entidade"),
    "nomes_alternativos": ("Outras grafias do titular vistas nas fontes (até 3).", "texto separado por ';'", "Cadastro Mineiro"),
    "qtd_processos": ("Processos minerários distintos do titular em Goiás.", "contagem", "Cadastro Mineiro"),
    "qtd_municipios": ("Municípios de Goiás onde o titular tem títulos (o titular inteiro: todos os minerais e fases).", "contagem", "Cadastro Mineiro"),
    "qtd_municipios_mineral_ano": ("Quantos municípios há por trás de municipios_atuacao, antes do corte em 6 nomes (mesma regra: CFEM do mineral no ano; sem CFEM, os dos títulos).", "contagem", "CFEM / Cadastro Mineiro"),
    "principais_minerais": ("Minerais mais citados nos títulos.", "texto separado por ';'", "Cadastro Mineiro → crosswalk 01b"),
    "fase_predominante": ("Fase processual mais frequente nos títulos do titular.", "texto (fases ANM)", "Cadastro Mineiro (Fase Atual)"),
    "processo_anm": ("Número do processo na ANM, formato canônico <número sem zeros à esquerda>/<ano>.", "texto", "SIGMINE.PROCESSO / CFEM (Processo + AnoDoProcesso)"),
    "mineral_ids": ("Todos os minerais declarados no título, normalizados.", "MIN_### separados por ';'", "SIGMINE.SUBS → crosswalk 01b"),
    "mineral_principal": ("Primeiro mineral declarado no título, normalizado.", "texto", "SIGMINE.SUBS → crosswalk 01b"),
    "municipios_intersectados": ("Todos os municípios de GO tocados pelo polígono, da maior para a menor área.", "texto separado por ';'", "Junção espacial SIGMINE × malha IBGE"),
    "fase_atual": ("Fase do processo no SIGMINE.", "", "SIGMINE.FASE"),
    "status_operacional": ("Rótulo legível da categoria_mapa.", "", "Derivado"),
    "categoria_mapa": ("Classe para simbologia do mapa. 1 = título de lavra + CFEM em 2024–2026; 2 = lavra sem CFEM recente; 3 = CFEM sem título de lavra; 4 = pré-lavra; 5 = pesquisa; 6 = requerimento de licenciamento/garimpeira; 7 = disponibilidade; 8 = outros.", "", "Derivado — SIGMINE.FASE + CFEM"),
    "cfem_2024_2026_brl": ("CFEM recolhida pelo processo em 2024–2026 (2026 parcial, até 08/2026).", "R$ nominais", "ANM CFEM (ValorRecolhido)"),
    "cfem_2022_2026_brl": ("CFEM recolhida pelo processo em 2022–2026 (2026 parcial).", "R$ nominais", "ANM CFEM (ValorRecolhido)"),
    "area_ha_calculada": ("Área do polígono dissolvido, calculada em Albers equivalente sobre SIRGAS 2000.", "ha", "Derivado — geometria SIGMINE"),
    "area_ha_declarada": ("Soma do AREA_HA declarado no SIGMINE para as feições do processo.", "ha", "SIGMINE.AREA_HA"),
    "fracao_area_em_go": ("Fração da área do processo dentro do território de Goiás.", "0 a 1", "Junção espacial"),
    "latitude": ("Latitude do ponto representativo (representative_point, sempre dentro do polígono).", "graus decimais, SIRGAS 2000", "Derivado — geometria"),
    "longitude": ("Longitude do ponto representativo (representative_point, sempre dentro do polígono).", "graus decimais, SIRGAS 2000", "Derivado — geometria"),
    "ultimo_evento": ("Último evento processual registrado. Contém eventos com data futura (até 2028): não serve como data de extração.", "texto '<código> - <descrição>'", "SIGMINE.ULT_EVENTO"),
    "uso_declarado": ("Uso declarado da substância.", "", "SIGMINE.USO"),
    "uf_declarada_sigmine": ("UF declarada no SIGMINE. NÃO é recorte territorial (há processos com UF=MG ou PA parcial/totalmente em GO) — use fracao_area_em_go.", "", "SIGMINE.UF"),
    "qtd_feicoes_originais": ("Feições do SIGMINE dissolvidas no processo (fragmentos sem sobreposição).", "contagem", "SIGMINE"),
    "geometria_reparada": ("VERDADEIRO se o polígono tinha autointerseção e foi reparado (make_valid, área inalterada).", "booleano", "Derivado"),
    "uf": ("Unidade da federação.", "", "—"),
    "area_km2": ("Área oficial do município.", "km²", "IBGE — malha 2025 (AREA_KM2)"),
    "regiao_geografica_imediata": ("Região geográfica imediata oficial do IBGE.", "texto", "IBGE — malha 2025 (NM_RGI)"),
    "regiao_geografica_intermediaria": ("Região geográfica intermediária oficial do IBGE.", "texto", "IBGE — malha 2025 (NM_RGINT)"),
    "populacao": ("População residente estimada; preenchida só na linha do ano de referência (populacao_ano).", "pessoas", "IBGE SIDRA 6579, variável 9324"),
    "populacao_ano": ("Ano de referência da população.", "AAAA", "IBGE SIDRA 6579"),
    "pib_total_brl": ("PIB a preços correntes, convertido de mil reais (SIDRA) para R$; só na linha do ano de referência.", "R$ correntes", "IBGE SIDRA 5938, variável 37"),
    "pib_ano": ("Ano de referência do PIB.", "AAAA", "IBGE SIDRA 5938"),
    "cfem_qtd_titulares_distintos": ("Titulares distintos que recolheram CFEM no município no ano. " + AVISO_CNPJ, "contagem", "ANM CFEM (CPF_CNPJ)"),
    "cfem_qtd_minerais_distintos": ("Minerais canônicos distintos com CFEM no município no ano.", "contagem", "ANM CFEM → crosswalk 01b"),
    "qtd_processos_cadastro_mineiro": ("Processos distintos com título — fotografia atual, repetida em todas as linhas.", "contagem", "Cadastro Mineiro"),
    "qtd_titulares_cadastro_mineiro": ("Titulares distintos com título — fotografia atual, repetida em todas as linhas.", "contagem", "Cadastro Mineiro"),
    "qtd_processos_sigmine": ("Processos com polígono no SIGMINE — fotografia atual.", "contagem", "SIGMINE"),
    "year": ("Ano de referência (campo fixado no Contrato de Dados).", "AAAA", "—"),
    "cfem_recolhido_brl": ("CFEM recolhida.", "R$ nominais", "ANM CFEM (ValorRecolhido)"),
    "production_t_rom": ("Produção bruta (minério ROM): massa de minério, NÃO metal contido. No contrato, equivale a production_t com production_basis = ROM.", "t", "ANM AMB — produção bruta"),
    "production_beneficiada": ("Produção beneficiada, na unidade de production_beneficiada_unit. Só equivale a production_t (basis = beneficiada) quando a unidade é t; não somar entre minerais.", "ver production_beneficiada_unit", "ANM AMB — produção beneficiada"),
    "production_beneficiada_unit": ("Unidade da produção beneficiada.", "", "ANM AMB — produção beneficiada"),
    "valor_venda_beneficiada_brl": ("Valor de venda da produção beneficiada.", "R$ nominais", "ANM AMB — produção beneficiada"),
    "cfem_qtd_comercializada_t": ("Quantidade comercializada declarada na CFEM, só unidades de massa convertidas para t (kg, g, quilate), sem as linhas corrompidas ou implausíveis (ver 09b). NÃO é produção. "
                                  "NÃO USAR COMO PROXY DE PRODUÇÃO sem validação mineral a mineral: a CFEM não informa a base (minério bruto, concentrado ou metal), que varia entre substâncias "
                                  "e declarantes, e dezenas de mineral-anos ficam fora da faixa de 0,05–2× da produção do AMB (lista e causas conhecidas na 14b).", "t", "ANM CFEM (QuantidadeComercializada, UnidadeDeMedida)"),
    "cfem_qtd_outras_unidades": ("Quantidade comercializada em unidades sem conversão para t (m³, l, m²), somada por unidade.", "texto '<unidade>: <quantidade>' separado por ';'", "ANM CFEM (QuantidadeComercializada, UnidadeDeMedida)"),
    "cfem_qtd_linhas_excluidas": ("Linhas da CFEM do mineral no ano cuja quantidade saiu da soma (o R$ foi mantido). Detalhe linha a linha na aba 09b.", "contagem", "Derivado — regra da 09b"),
    "month": ("Mês de competência da CFEM.", "1 a 12", "ANM CFEM (Mês)"),
    "substancia_original": ("Substância exatamente como aparece na CFEM.", "texto", "ANM CFEM (Substância)"),
    "quantidade_bruta": ("Quantidade comercializada exatamente como veio na fonte (texto).", "texto", "ANM CFEM (QuantidadeComercializada)"),
    "quantidade_convertida": ("Quantidade após conversão para a unidade padronizada (vazia se ilegível).", "ver unidade_convertida", "Derivado"),
    "unidade_convertida": ("Unidade padronizada usada na comparação (t para massa; m³, l ou m² sem conversão).", "", "Derivado"),
    "valor_recolhido_brl": ("Valor da CFEM recolhido na linha (mantido nas somas em R$).", "R$ nominais", "ANM CFEM (ValorRecolhido)"),
    "r_por_unidade": ("R$ recolhido por unidade de quantidade na linha.", "R$ por unidade", "Derivado"),
    "mediana_r_por_unidade_mineral": ("Mediana do R$ por unidade entre as linhas válidas do mesmo mineral e unidade (referência da regra de plausibilidade).", "R$ por unidade", "Derivado"),
    "motivo": ("Por que a quantidade da linha saiu da soma.", "", "Derivado — regra da 09b"),
    "substancia": ("Rocha, com o nome normalizado (maiúsculas, sem acento).", "texto", "Cadastro Mineiro / SIGMINE / CFEM"),
    "tipo_de_uso": ("Tipo de uso que decidiu a categoria (normalizado).", "", "Cadastro Mineiro (Tipo(s) de Uso) / SIGMINE (USO)"),
    "origem_do_uso": ("De onde veio o uso: declarado no título, campo USO do SIGMINE, número do processo (para a CFEM) ou uso majoritário da rocha em GO.", "", "Derivado — regra da 01c"),
    "regra": ("Qual regra atribuiu a categoria (uso declarado, uso majoritário da rocha em GO, rocha de categoria fixa ou sem uso informativo).", "", "Derivado — regra da 01c"),
    "cfem_t": ("Toneladas comercializadas na CFEM para essa rocha, uso e regra (só massa, sem as linhas excluídas na 09b).", "t", "ANM CFEM"),
    "substancias": ("Substâncias declaradas pelo processo na CFEM.", "texto separado por ';'", "ANM CFEM (Substância)"),
    "usos": ("Tipos de uso atribuídos às rochas do processo (vazio para não-rochas).", "texto separado por ';'", "Derivado — regra da 01c"),
    "cfem_t_processo": ("Toneladas comercializadas declaradas por esse processo no ano, na categoria.", "t", "ANM CFEM"),
    "amb_total_uf_t": ("Limite do AMB para Goiás na categoria e ano: maior entre produção bruta e beneficiada em t; nos metais que o AMB mede em kg (ouro, prata), a produção beneficiada convertida para t. Vazio = sem AMB no ano.", "t", "ANM AMB"),
    "amb_base": ("Qual medida do AMB serviu de limite: maior entre bruta e beneficiada em t, ou beneficiada em kg no caso de metal (a bruta desses minerais é tonelagem de minério).", "texto", "Derivado — regra da 09c"),
    "criterio": ("O que disparou o alerta: tonelagem acima do total estadual e/ou, em metais, R$/t mais de 10× abaixo da mediana do mineral.", "texto", "Derivado — regra da 09c"),
    "razao": ("cfem_t_processo ÷ amb_total_uf_t. Acima de 1 = um único processo declara mais que o estado inteiro. Vazio = sem AMB no ano.", "razão", "Derivado"),
    "r_por_t": ("R$ recolhido por tonelada declarada pelo processo.", "R$/t", "Derivado"),
    "severidade": ("alta = mais de 2× o total estadual OU R$/t mais de 10× abaixo da mediana do mineral (nos metais medidos em kg, esse R$/t sozinho já gera alerta); moderada = entre 1 e 2× com R$/t compatível.", "", "Derivado — regra da 09c"),
    "mediana_r_por_t_mineral": ("Mediana do R$ por tonelada nas linhas da CFEM do mesmo mineral (todos os processos e anos), para comparar com r_por_t. Nos metais medidos em kg (ouro, prata) é ponderada pelo R$ recolhido, para não ser puxada pelas próprias declarações erradas.", "R$/t", "Derivado — ANM CFEM"),
    "qtd_titulares_cfem": ("Titulares distintos que recolheram CFEM para o mineral (2022–2026). " + AVISO_CNPJ, "contagem", "ANM CFEM (CPF_CNPJ)"),
    "qtd_titulos_com_esse_mineral": ("Menções do mineral nos títulos do titular no Cadastro Mineiro (ocorrências, não processos distintos).", "contagem", "Cadastro Mineiro"),
    "qtd_processos_total_empresa": ("Processos distintos do titular em Goiás.", "contagem", "Cadastro Mineiro"),
    "municipios_atuacao": ("Municípios onde o titular recolheu CFEM para o mineral no ano; sem CFEM, os municípios dos títulos. Até 6 nomes, em ordem alfabética; o total está em qtd_municipios_mineral_ano.", "texto separado por ';'", "CFEM / Cadastro Mineiro"),
    "production_t": ("VAZIO de propósito: a ANM não publica produção por empresa (gap QC07). Nome fixado no contrato.", "t", "—"),
    "energy_mwh": ("VAZIO de propósito: depende do pareamento com a CCEE (Squad 2). Nome fixado no contrato.", "MWh", "—"),
    "energy_intensity_mwh_t": ("VAZIO de propósito: energy_mwh / production_t na mesma production_basis. Nome fixado no contrato.", "MWh/t", "—"),
    "fonte": ("Base e recorte de onde veio o valor bruto.", "", "—"),
    "valor_original": ("Valor exatamente como aparece na fonte.", "texto", "fonte da linha"),
    "valor_normalizado": ("Valor após normalização (maiúsculas, sem acento, sufixo de UF tratado).", "texto", "Derivado"),
    "chave_normalizada": ("Chave usada na resolução de entidade (raiz de CNPJ ou razão social normalizada).", "texto", "Derivado"),
    "contagem": ("Ocorrências do valor bruto na fonte.", "contagem", "fonte da linha"),
    "atribuido_a": ("ID (e nome) canônico ao qual o valor foi atribuído, ou o motivo da exclusão.", "texto", "Derivado"),
    "tipo_correspondencia": ("Como a correspondência foi feita, ou o achado do pente fino.", "", "Derivado"),
    "camada": ("Camada de mapa verificada.", "", "—"), "verificacao": ("Checagem realizada.", "texto", "—"),
    "n": ("Quantidade de itens envolvidos na checagem.", "contagem", "—"), "resultado": ("Resultado observado.", "texto", "—"),
    "decisao": ("Decisão tomada a partir do resultado.", "texto", "—"),
    "camada_id": ("Identificador da camada de mapa.", "CAM_##[_WEB_#|_TILES]", "—"), "nome_camada": ("Nome da camada (= nome do arquivo/camada GPKG).", "texto", "—"),
    "descricao": ("Descrição da camada.", "texto", "—"), "tipo_geometria": ("Tipo de geometria.", "", "—"),
    "n_feicoes": ("Número de feições.", "contagem", "—"), "arquivo": ("Caminho do arquivo web (GeoJSON ou PMTiles).", "caminho relativo ao repositório", "—"),
    "tamanho_mb": ("Tamanho do arquivo.", "MB", "—"), "camada_gpkg": ("Camada correspondente no GeoPackage (resolução total).", "texto", "—"),
    "crs": ("Sistema de referência de coordenadas.", "texto", "—"), "simplificacao_web": ("Generalização aplicada à versão web.", "texto", "—"),
    "chave_primaria": ("Campo identificador da camada.", "texto", "—"), "chaves_de_juncao": ("Como a camada se liga às abas da planilha.", "texto", "—"),
    "simbologia": ("Simbologia recomendada.", "texto", "—"),
}
DA = {  # (aba, campo) -> descrição específica da aba
    ("01_dim_minerais", "observacao"): "Decisões do pente fino para o mineral (fusões, ambiguidades, categorias oficiais).",
    ("09_cons_mineral_ano", "uf"): "GO = Goiás; BR = soma nacional de todas as UFs, para comparação.",
    ("05_dim_municipios", "uf"): "Sempre GO.", ("10_cons_municipio_ano", "uf"): "Sempre GO.",
    ("09_cons_mineral_ano", "year"): "Ano de referência (contrato). Vazio = linha-fotografia de mineral só com título (sem produção nem CFEM).",
    ("10_cons_municipio_ano", "year"): "Ano de referência (contrato): CFEM 2022–2026; população 2025; PIB 2023.",
    ("11_cons_empresa_ano_mineral", "year"): "Ano da CFEM (contrato). Vazio = mineral citado nos títulos do titular, sem CFEM.",
    ("09_cons_mineral_ano", "cfem_recolhido_brl"): "CFEM recolhida em GO para o mineral no ano (vazia nas linhas BR: só temos CFEM de GO).",
    ("10_cons_municipio_ano", "cfem_recolhido_brl"): "CFEM recolhida no município no ano (CodigoMunicipio da CFEM).",
    ("11_cons_empresa_ano_mineral", "cfem_recolhido_brl"): "CFEM do titular para o mineral no ano, ligada pela ponte do número do processo. A soma da coluna bate com o arquivo bruto (R$ 867.578.398,91).",
    ("09_cons_mineral_ano", "qtd_processos_cadastro_mineiro"): "Processos distintos em GO com título citando o mineral — fotografia atual, repetida em todas as linhas do mineral.",
    ("10_cons_municipio_ano", "qtd_processos_cadastro_mineiro"): "Processos distintos com título no município — fotografia atual, repetida em todas as linhas do município.",
    ("11_cons_empresa_ano_mineral", "qtd_processos_sigmine"): "Processos do titular no SIGMINE casados pelo NOME (a Base 4 mostra que a ponte do processo cobre mais: 92% × 66%).",
    ("11_cons_empresa_ano_mineral", "qtd_municipios"): "Municípios de Goiás onde o titular tem títulos — do titular inteiro (todos os minerais e fases), não só da linha; por isso pode diferir de qtd_municipios_mineral_ano. 0 em COM_NAO_IDENTIFICADO (processos fora do Cadastro Mineiro).",
    ("03_dim_operacoes", "qtd_municipios"): "Municípios de Goiás que o polígono do processo intersecta.",
    ("03_dim_operacoes", "razao_social"): "Razão social do titular (Cadastro Mineiro pela ponte do processo; se ausente, nome do SIGMINE). CPF dentro do nome sai mascarado (LGPD).",
    ("03_dim_operacoes", "company_id"): "Titular do processo: ponte do número do processo com o Cadastro Mineiro; reserva, nome do SIGMINE casado com raiz de CNPJ. Vazio em 858 processos sem correspondência.",
    ("02_dim_empresas", "principais_minerais"): "Até 4 minerais mais citados nos títulos do titular.",
    ("10_cons_municipio_ano", "principais_minerais"): "Até 5 minerais mais citados nos títulos do município — fotografia atual.",
    ("05_dim_municipios", "latitude"): "Latitude do representative_point do polígono municipal (dentro do município; não é a sede).",
    ("05_dim_municipios", "longitude"): "Longitude do representative_point do polígono municipal (dentro do município; não é a sede).",
    ("10_cons_municipio_ano", "latitude"): "Latitude do representative_point do polígono municipal (dentro do município; não é a sede).",
    ("10_cons_municipio_ano", "longitude"): "Longitude do representative_point do polígono municipal (dentro do município; não é a sede).",
    ("13_mapas_camadas", "source_ids"): "Fontes dos atributos da camada (IDs do catálogo 07).",
    ("13_mapas_camadas", "observacao"): "Observação sobre a camada.",
    ("08_fato_producao_energia", "uf"): "UF da linha na fonte. AMB: todas as UFs (a linha BR da 09 é a soma delas); CFEM: sempre GO.",
    ("08_fato_producao_energia", "year"): "Ano da medida (contrato): ano base no AMB, ano de competência na CFEM.",
    ("08_fato_producao_energia", "mineral_id"): "Mineral da medida. AMB: categoria oficial (01b); CFEM: crosswalk da substância, com rochas pelo tipo de uso (01c). Mesma atribuição da 09.",
    ("08_fato_producao_energia", "mineral_name"): "Nome padronizado do mineral de mineral_id (contrato).",
    ("08_fato_producao_energia", "company_id"): "Só na CFEM, pela ponte do número do processo (igual à 11). Vazio no AMB, que não identifica empresa.",
    ("08_fato_producao_energia", "operation_id"): "Só na CFEM, quando o processo tem poligonal no SIGMINE de GO (03_dim_operacoes). Vazio no AMB (grão UF).",
    ("08_fato_producao_energia", "municipality_id"): "Só na CFEM (CodigoMunicipio, igual à 10). Vazio no AMB (grão UF).",
    ("08_fato_producao_energia", "project_id"): "Vazio: nenhuma fonte do Squad 1 / Estudante 1 identifica projeto (vem do Radar de Projetos).",
    ("08_fato_producao_energia", "valor_original"): "Texto exatamente como na célula da fonte (vírgula decimal; a notação científica corrompida da CFEM é preservada). Nunca sobrescrito.",
    ("08_fato_producao_energia", "processo_anm"): "Só na CFEM: Processo + AnoDoProcesso em formato canônico — identifica também os processos sem poligonal (sem operation_id).",
    ("08_fato_producao_energia", "metodo_estimacao"): "Vazio: a 08 só tem valores observados na fonte.",
    ("12_interface_squad1_squad2", "mineral_id"): "Categoria do AMB. No nível operação, a CFEM dos subitens de Calcário (calcítico, dolomítico, industrial) entra em Calcário.",
    ("12_interface_squad1_squad2", "company_id"): "Nível operação: titular do processo pela ponte do número do processo (igual à 08 e à 11). Vazio no nível estado.",
    ("12_interface_squad1_squad2", "operation_id"): "Nível operação, quando o processo tem poligonal no SIGMINE de GO (03_dim_operacoes). Vazio no nível estado.",
    ("12_interface_squad1_squad2", "project_id"): "Vazio: depende do Radar de Projetos (Squad 1 / Estudante 2).",
    ("12_interface_squad1_squad2", "municipality_id"): "Nível operação: município principal do polígono (03); sem poligonal, o município com mais CFEM do processo no ano. Vazio no nível estado.",
    ("12_interface_squad1_squad2", "year"): "Ano (contrato): produção do AMB 2010–2025; abertura por operação só em 2022–2025 (anos com CFEM na base).",
    ("12_interface_squad1_squad2", "production_t"): "Produção em t (contrato): OBSERVADA no nível estado (AMB, massa convertida para t) e ESTIMADA no nível operação (rateio pela CFEM).",
    ("12_interface_squad1_squad2", "production_basis"): "ROM (produção bruta) ou beneficiada — a mesma base do total rateado. O conteúdo mineral (contido) fica na 08, porque depende da indicação (Au, Nb2O5…).",
    ("12_interface_squad1_squad2", "latitude"): "Latitude do representative_point do polígono do processo (03). Vazia no nível estado e em processos sem poligonal no SIGMINE.",
    ("12_interface_squad1_squad2", "longitude"): "Longitude do representative_point do polígono do processo (03). Vazia no nível estado e em processos sem poligonal no SIGMINE.",
    ("12_interface_squad1_squad2", "source_id"): "Fontes de todos os valores da linha, separadas por ';' (a estimativa combina AMB, CFEM, Cadastro Mineiro, SIGMINE e malha do IBGE).",
    ("12_interface_squad1_squad2", "source_url"): "URL de cada fonte, na mesma ordem de source_id (igual a url_recurso da 07).",
    ("12_interface_squad1_squad2", "data_acesso"): "Data do arquivo local de cada fonte, na mesma ordem de source_id (igual a data_arquivo_local da 07).",
    ("12_interface_squad1_squad2", "processo_anm"): "Processo cuja CFEM define a participação no rateio (formato canônico) — identifica também processos sem poligonal (sem operation_id).",
    ("12_interface_squad1_squad2", "metodo_estimacao"): "Preenchido nas linhas estimadas (nível operação): regra do rateio e suas premissas.",
    ("12_interface_squad1_squad2", "erro_estimativa_intervalo"): "Nível operação: faixa entre o rateio por R$ (production_t) e o rateio pela quantidade em t da CFEM (production_t_rateio_por_t).",
    ("12_interface_squad1_squad2", "status_validacao"): "Estado: valido ou alerta_producao_repetida (vem da 08). Operação: estimativa_conferida_no_total, ou estimativa_com_alerta_09c quando o processo está na 09c.",
    ("12_interface_squad1_squad2", "periodo_referencia"): "Ano de referência (AAAA).",
    ("12_interface_squad1_squad2", "observacao"): "Nota da linha: por que não há abertura, subitens somados, processo sem poligonal ou titular não identificado.",
    ("04_dim_projetos", "nome_projeto"): "Nome descritivo gerado (mineral — titular — município): a ANM não publica nome de projeto; o nome anunciado vem de RI, CVM ou SEMAD. CPF dentro do nome do titular sai mascarado (LGPD).",
    ("04_dim_projetos", "company_id"): "Titular do processo-âncora pela ponte do número do processo com o Cadastro Mineiro; vazio quando só há o nome no SIGMINE.",
    ("04_dim_projetos", "municipality_id"): "Município principal do processo-âncora (03); os demais municípios do projeto vão na observação.",
    ("04_dim_projetos", "latitude"): "Latitude do representative_point da união dos polígonos do projeto (sempre dentro da área).",
    ("04_dim_projetos", "longitude"): "Longitude do representative_point da união dos polígonos do projeto (sempre dentro da área).",
    ("04_dim_projetos", "classificacao_maturidade"): "Escala do guia (operação, expansão, construção, definido, provável, possível, sinal). A camada ANM só atribui provável, possível ou "
                                                     "sinal; as demais exigem RI, CVM ou SEMAD (Squad 1 / Estudante 2).",
    ("04_dim_projetos", "ano_previsto_entrada"): "VAZIO de propósito: a ANM não publica cronograma; vem de RI, CVM ou SEMAD (Estudante 2).",
    ("04_dim_projetos", "ultimo_evento"): "Texto do evento mais recente entre os processos do projeto (código, descrição e data).",
    ("04_dim_projetos", "valor_observado_estimado"): "calculado: projeto e classe derivados por regra documentada a partir de registros observados da ANM.",
    ("04_dim_projetos", "status_validacao"): "pendente_evidencia_corporativa: o estágio vem da ANM; nome, capacidade, CAPEX, cronograma e classes acima de 'provável' dependem de "
                                             "RI, CVM ou SEMAD.",
    ("04_dim_projetos", "periodo_referencia"): "Data do arquivo do SIGMINE usado (fotografia da situação dos processos).",
    ("04_dim_projetos", "source_id"): "Fontes da linha separadas por ';': SIGMINE (fase, evento, geometria), Cadastro Mineiro (titular, relatório aprovado), CFEM (sem produção) e malha do IBGE.",
    ("04_dim_projetos", "source_url"): "URL de cada fonte, na mesma ordem de source_id (igual a url_recurso da 07).",
    ("04_dim_projetos", "data_acesso"): "Data do arquivo local de cada fonte, na mesma ordem de source_id (igual a data_arquivo_local da 07).",
    ("04_dim_projetos", "observacao"): "Nota da linha: vários municípios, titular sem CNPJ, processo sem substância ou candidato a expansão.",
    ("06_dim_ocorrencias_geologicas", "mineral_ids"): "Todas as substâncias da ocorrência com categoria ANM, pelo crosswalk da 06b (o RECMIN não indica a principal).",
    ("06_dim_ocorrencias_geologicas", "municipality_id"): "Município da malha do IBGE 2025 onde o ponto cai (vale sobre o município digitado no RECMIN).",
    ("06_dim_ocorrencias_geologicas", "municipality_name"): "Nome oficial do município da malha do IBGE 2025 onde o ponto cai.",
    ("06_dim_ocorrencias_geologicas", "latitude"): "Latitude do RECMIN (WGS84); precisão dada por metodo_geoposicionamento (carta 1:250.000 na maioria).",
    ("06_dim_ocorrencias_geologicas", "longitude"): "Longitude do RECMIN (WGS84); precisão dada por metodo_geoposicionamento (carta 1:250.000 na maioria).",
    ("06_dim_ocorrencias_geologicas", "descricao"): "Descrição do afloramento no RECMIN (preenchida em poucas ocorrências).",
    ("06_dim_ocorrencias_geologicas", "status_validacao"): "valido, ou alerta_localizacao quando a UF ou o município digitados no RECMIN divergem da malha do IBGE (detalhe em observacao).",
    ("06_dim_ocorrencias_geologicas", "periodo_referencia"): "Data de cadastro da ocorrência no GeoSGB.",
    ("06_dim_ocorrencias_geologicas", "source_id"): "Fontes da linha separadas por ';': RECMIN (a ocorrência), malha do IBGE (município) e SIGMINE (processos sobrepostos).",
    ("06_dim_ocorrencias_geologicas", "source_url"): "URL de cada fonte, na mesma ordem de source_id (igual a url_recurso da 07; a do RECMIN é a requisição WFS usada).",
    ("06_dim_ocorrencias_geologicas", "data_acesso"): "Data do arquivo local de cada fonte, na mesma ordem de source_id (igual a data_arquivo_local da 07).",
    ("06_dim_ocorrencias_geologicas", "observacao"): "Nota da linha: município ou UF divergente, coordenada repetida, motivo do garimpo diferente, substância sem categoria ANM.",
    ("06_dim_ocorrencias_geologicas", "metodo_estimacao"): "Vazio: a 06 só tem valores observados na fonte.",
    ("06b_crosswalk_recmin", "mineral_id"): "Mineral canônico da 01 atribuído à substância; vazio quando não há categoria ANM.",
    ("06b_crosswalk_recmin", "tipo_correspondencia"): "crosswalk_base1 (mesmo mapeamento das bases ANM), sinonimo_recmin (decidido um a um) ou sem_categoria_anm.",
}


def tipo_de(v):
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return "booleano"
    if isinstance(v, int):
        return "inteiro"
    if isinstance(v, float):
        return "inteiro" if v.is_integer() else "decimal"
    return "texto"


def perfil(cab, linhas):
    out = {}
    for c in cab:
        vals = [r.get(c) for r in linhas]
        cheios = [v for v in vals if v not in (None, "")]
        tipos = Counter(filter(None, map(tipo_de, cheios)))
        tp = "vazio" if not tipos else ("decimal" if set(tipos) <= {"inteiro", "decimal"} and "decimal" in tipos else max(tipos, key=tipos.get))
        dist = list(dict.fromkeys(str(v) for v in cheios))
        out[c] = dict(tipo=tp, pct_vazio=round(100 * (1 - len(cheios) / max(1, len(vals))), 1), n_distintos=len(dist),
                      exemplo=(dist[0][:60] if dist else ""), dominio=("; ".join(dist) if tp == "texto" and 0 < len(dist) <= 12 else ""),
                      tipos_brutos=dict(tipos))
    return out


cab07 = list(fontes_rows[0].keys())
DADOS["07_dim_fontes"] = (cab07, fontes_rows)
D.update({
    "nome_fonte": ("Nome da fonte e do recurso.", "texto", "—"), "orgao": ("Órgão produtor.", "", "—"), "tipo_fonte": ("Natureza da fonte (Entrega Avaliativa 1).", "", "—"),
    "status_uso": ("Se a fonte alimenta alguma aba real (calculado pelas citações em source_ids).", "", "Governança"),
    "usado_em": ("Abas que citam a fonte e em quantas linhas.", "texto", "Governança"),
    "url_catalogo": ("Página oficial do conjunto de dados.", "URL", "metadados oficiais / verificação web"),
    "url_recurso": ("URL do arquivo ou da consulta equivalente.", "URL", "metadados oficiais / verificação web"),
    "metadados_oficiais": ("Onde estão os metadados oficiais.", "texto", "—"), "arquivo_local": ("Arquivo(s) em dados/.", "caminho", "—"),
    "arquivos": ("Quantidade de arquivos locais.", "contagem", "—"), "sha256": ("Hash SHA-256 do arquivo (ou do conjunto de arquivos) usado.", "hex", "calculado"),
    "data_arquivo_local": ("Data de modificação do arquivo local (proxy da data de acesso).", "AAAA-MM-DD", "calculado"),
    "periodo_coberto": ("Período efetivamente presente no arquivo (calculado dos dados).", "texto", "calculado"),
    "granularidade": ("Grão da fonte.", "texto", "—"), "formato_declarado": ("Formato segundo os metadados oficiais.", "texto", "metadados oficiais"),
    "formato_arquivo_local": ("Formato observado no arquivo local.", "texto", "calculado"),
    "frequencia_atualizacao": ("Frequência de atualização declarada.", "texto", "metadados oficiais"),
    "confiabilidade": ("Avaliação de confiabilidade para o uso no projeto.", "texto", "—"),
    "limitacoes_conhecidas": ("Limitações e armadilhas encontradas no pente fino.", "texto", "Pente fino (auditorias 01b, 02b, 05b, 13b)"),
    # campos das abas ainda em maquete cuja descrição a v0 deixou vazia (e o ID da aba 07)
    "source_id": ("Identificador estável e legível da fonte (referenciado pelas colunas source_ids).", "SRC_*", "Governança"),
    "project_id": ("Identificador estável do projeto mineral (campo fixado no Contrato de Dados). Na camada ANM (04): PRJ_ + processo-âncora, estável enquanto o "
                   "processo-âncora existir.", "PRJ_<número>_<ano>", "Derivado — SIGMINE (camada ANM do Radar de Projetos)"),
    "nome_projeto": ("Nome do projeto como divulgado pela empresa ou pelo órgão licenciador.", "texto", "RI / CVM / SEMAD"),
    "ano_previsto_entrada": ("Ano previsto de início de operação, quando anunciado.", "AAAA", "RI / CVM / SEMAD"),
    "classificacao_maturidade": ("Estágio de maturidade (operação, expansão, construção, definido, provável, possível, sinal).", "texto", "Critério do Radar de Projetos"),
    "nome_local": ("Nome do depósito, ocorrência ou distrito mineral.", "texto", "RECMIN / GeoSGB"),
    "unidade_original": ("Unidade exatamente como veio da fonte, antes da conversão para a unidade padrão.", "texto", "fonte da linha"),
    "erro_estimativa_intervalo": ("Erro ou intervalo de referência da estimativa (obrigatório quando o dado não é observado).", "texto/número", "Método de estimação"),
    "status_validacao": ("Situação da validação do valor. Na 08: valido = entra nas somas; quantidade_excluida_da_soma_09b = quantidade corrompida ou "
                         "implausível, fora da soma (o R$ fica); alerta_processo_09c = processo sinalizado, mantido na soma; alerta_producao_repetida = "
                         "a mesma tonelagem aparece em outra linha da mesma UF e ano (co-produto, teor ou categoria), mantida na soma — não somar entre essas linhas.", "", "Governança"),
    "responsavel_validacao": ("Quem validou o valor.", "texto", "Governança"),
    "notas": ("Notas de rastreabilidade da linha.", "texto livre", "—"),
    # aba 08 (fato longo, real na v8)
    "fato_id": ("Identificador da medida, sequencial na ordem (fonte, linha da fonte, coluna). Estável enquanto o arquivo da fonte for o mesmo (sha256 na 07).",
                "FATO_###### (6 dígitos)", "Derivado"),
    "metrica": ("O que a linha mede, uma por coluna numérica da fonte.",
                "AMB bruta: producao_rom; contido_rom; venda_rom; valor_venda_rom; consumo_mina_rom; valor_consumo_mina_rom; transferencia_rom; valor_transferencia_rom | "
                "AMB beneficiada: producao_beneficiada; contido_beneficiada; venda_beneficiada; valor_venda_beneficiada; consumo_usina_beneficiada; "
                "valor_consumo_usina_beneficiada; transferencia_beneficiada; valor_transferencia_beneficiada | CFEM: quantidade_comercializada_cfem; cfem_recolhido",
                "coluna_original da fonte"),
    "periodo_referencia": ("Período da medida (Entrega Avaliativa §3): ano base no AMB, competência mensal na CFEM.", "AAAA ou AAAA-MM", "fonte da linha"),
    "tratamento": ("O que foi feito entre valor_original e valor_tratado. Vazio = só a leitura do número (vírgula decimal).", "texto", "Derivado — regras da Base 1 (09b)"),
    "valor_tratado": ("Valor final na unidade padrão: massa convertida para t (contrato), R$ como BRL, m3/l/m2 sem conversão (sem densidade). Vazio quando a quantidade "
                      "saiu da soma (09b). É a coluna que as abas 09–11 somam.", "número", "Derivado"),
    "unidade_padrao": ("Unidade de valor_tratado.", "", "Contrato de Dados (produção em t)"),
    "production_basis": ("Base física da quantidade (campo do contrato): ROM (produção bruta), beneficiada ou conteudo_mineral (contido). Vazio para valores em R$ e para a "
                         "CFEM, que não informa a base.", "", "Contrato de Dados / AMB"),
    "valor_observado_estimado": ("observado, calculado, estimado ou benchmark (Contrato de Dados §1; Entrega Avaliativa §3).", "", "Governança"),
    "metodo_estimacao": ("Obrigatório quando valor_observado_estimado ≠ observado.", "texto", "Governança"),
    "source_url": ("URL do recurso na fonte oficial (igual a url_recurso da 07).", "URL", "07_dim_fontes"),
    "data_acesso": ("Data do arquivo local usado (igual a data_arquivo_local da 07; proxy da data de acesso).", "AAAA-MM-DD", "07_dim_fontes"),
    "source_file": ("Arquivo exato em dados/ de onde a medida veio.", "caminho relativo ao repositório", "—"),
    "source_linha": ("Linha do arquivo (cabeçalho = linha 1). Com source_file e coluna_original, aponta a célula exata.", "número da linha", "—"),
    "coluna_original": ("Nome da coluna da fonte de onde veio o valor.", "texto", "—"),
    "mineral_nome_original": ("Substância exatamente como escrita na fonte, antes do crosswalk para mineral_id (01b/01c).", "texto", "fonte da linha"),
    # aba 12 (interface Squad 1 → Squad 2, real na v9)
    "nivel_agregacao": ("estado = total observado de Goiás (AMB); operacao = abertura estimada desse total por processo. Não somar os dois níveis.", "", "Derivado"),
    "participacao_cfem_brl": ("Participação do processo na CFEM recolhida (R$) do mineral no ano em Goiás — a chave do rateio.", "0 a 1", "Derivado — 08 (cfem_recolhido)"),
    "cfem_brl_operacao": ("CFEM recolhida pelo processo no mineral e ano (numerador da participação).", "R$ nominais", "ANM CFEM (via 08)"),
    "cfem_brl_mineral_ano": ("CFEM recolhida em Goiás no mineral e ano (denominador da participação).", "R$ nominais", "ANM CFEM (via 08)"),
    "production_t_rateio_por_t": ("Sensibilidade: o mesmo total rateado pela quantidade comercializada em t da CFEM. Distorcida pelos erros de quantidade da CFEM (09b/09c); "
                                  "vazia quando a CFEM do mineral no ano não tem quantidade em t.", "t", "Derivado — 08 (quantidade_comercializada_cfem)"),
    "fato_ids": ("Linhas da 08 somadas no total do AMB (no nível operação, o total que foi rateado).", "FATO_###### separados por ';'", "08_fato_producao_energia"),
    # abas 04 e 04b (camada ANM do Radar de Projetos, real na v10)
    "tipo_projeto": ("brownfield_adjacente_a_operacao = a até 500 m de operação ativa (03) do mesmo titular e mineral — candidato a expansão, a confirmar; "
                     "sem_operacao_adjacente = nenhuma operação ativa do mesmo titular e mineral por perto.", "", "Derivado — SIGMINE (geometria) + 03"),
    "estagio": ("Estágio jurídico-minerário do processo-âncora: lavra_autorizada_sem_producao (título de lavra sem CFEM em 2024–2026), requerimento_de_lavra, "
                "direito_de_requerer_lavra (pesquisa aprovada) ou requerimento_de_licenciamento_ou_lavra_garimpeira.", "", "SIGMINE (FASE) + CFEM"),
    "criterio_classificacao": ("Regra que levou à classe: estágio, recência do último evento (3 anos antes do arquivo do SIGMINE), disputa e licenciamento ambiental.",
                               "texto", "Derivado — build_projetos_04"),
    "capacidade_t_ano": ("Capacidade anunciada. VAZIA de propósito: nenhuma fonte do Squad 1 publica capacidade (vem de RI, CVM ou SEMAD — Estudante 2).", "t/ano", "RI / CVM / SEMAD"),
    "capex_brl": ("CAPEX anunciado. VAZIO de propósito: vem de RI ou CVM (Estudante 2).", "R$", "RI / CVM"),
    "processo_ancora": ("Processo de estágio mais avançado do projeto (desempate: evento mais recente); dá o project_id.", "<número>/<ano>", "SIGMINE"),
    "qtd_processos": ("Processos contíguos (até 100 m) do mesmo titular e mineral agrupados no projeto.", "contagem", "Derivado — SIGMINE (geometria)"),
    "processos_anm": ("Processos que formam o projeto.", "<número>/<ano> separados por ';'", "SIGMINE"),
    "operation_ids": ("operation_id dos processos do projeto (03_dim_operacoes).", "OPE_… separados por ';'", "03_dim_operacoes"),
    "area_ha": ("Soma das áreas calculadas dos processos do projeto (projeção Albers equivalente).", "ha", "SIGMINE (geometria)"),
    "relatorio_final_aprovado": ("sim = algum processo do projeto consta em Relatorio_de_Pesquisa_Aprovado do Cadastro Mineiro (pesquisa com relatório final aprovado).",
                                 "sim | não", "Cadastro Mineiro"),
    "evento_licenciamento_ambiental": ("sim = o último evento de algum processo do projeto cita licença ambiental ou órgão ambiental.", "sim | não", "SIGMINE (ULT_EVENTO)"),
    "operacao_adjacente": ("Operações ativas (03) do mesmo titular e mineral a até 500 m do projeto.", "OPE_… separados por ';'", "Derivado — SIGMINE (geometria) + 03"),
    "data_evidencia": ("Data do último evento na ANM entre os processos do projeto — a evidência mais recente.", "AAAA-MM-DD", "SIGMINE (ULT_EVENTO)"),
    "tipo_evento": ("Descrição do último evento do processo na ANM, sem o código numérico e sem a data.", "texto", "SIGMINE (ULT_EVENTO)"),
    "classe_evento": ("encerramento (o processo não vira projeto), disputa, licenciamento_ambiental ou andamento — a primeira regra que casa vence.", "",
                      "Derivado — regras do build_projetos_04"),
    "palavra_chave": ("Trecho do tipo de evento que decidiu a classe.", "texto", "Derivado"),
    "processos": ("Processos candidatos cujo último evento é desse tipo.", "contagem", "SIGMINE"),
    "fases": ("Fases atuais mais comuns desses processos.", "texto", "SIGMINE (FASE)"),
    "exemplo_processo": ("Um processo com esse evento, para conferência.", "<número>/<ano>", "SIGMINE"),
    "vira_projeto": ("não para encerramento; sim para as demais classes.", "sim | não", "Derivado"),
    # abas 06 e 06b (ocorrências do RECMIN, reais na v11)
    "occurrence_id": ("Identificador da ocorrência: OCC_ + id_ocorrencia do GeoSGB (ID externo estável do SGB).", "OCC_<número>", "SGB RECMIN (id_ocorrencia)"),
    "nome_local": ("Toponímia da ocorrência no RECMIN.", "texto", "SGB RECMIN (toponimia)"),
    "mineral_names": ("Nomes padronizados dos minerais de mineral_ids, na mesma ordem.", "texto separado por ';'", "01_dim_minerais"),
    "substancias_original": ("Substâncias exatamente como no RECMIN (ordem alfabética; a fonte não indica a principal).", "texto", "SGB RECMIN (substancias)"),
    "substancias_sem_categoria_anm": ("Substâncias sem categoria ANM (sem mineral_id), guardadas pelo nome — ver 06b.", "texto separado por ';'", "Derivado — 06b"),
    "classe_utilitaria": ("Classe utilitária do SGB (metais nobres, material de construção civil, gemas…).", "", "SGB RECMIN (classes_utilitarias)"),
    "importancia": ("Importância segundo o SGB: Depósito, Ocorrência, Indício ou Indeterminado.", "", "SGB RECMIN (importancia)"),
    "status_economico": ("Status econômico segundo o SGB: Mina, Garimpo, Não explotado ou Indeterminado — na data do cadastro, não hoje.", "", "SGB RECMIN (status_economico)"),
    "situacao_explotacao": ("Ativo(a) ou Inativo(a) na data do cadastro (situacao_mina; situacao_garimpo é cópia idêntica na fonte).", "", "SGB RECMIN (situacao_mina)"),
    "motivo_inatividade": ("Motivo da inatividade na data do cadastro (exaurido, paralisado, intermitente).", "", "SGB RECMIN (motivo_inatividade_mina)"),
    "municipio_informado": ("Município como digitado no RECMIN (antes da malha do IBGE).", "texto", "SGB RECMIN (municipio)"),
    "uf_informada": ("UF como digitada no RECMIN.", "", "SGB RECMIN (uf)"),
    "metodo_geoposicionamento": ("Como o ponto foi posicionado (GPS ou escala da carta) — indica a precisão da coordenada.", "", "SGB RECMIN"),
    "provincia_mineral": ("Província geológica (Tocantins, São Francisco, Paraná).", "", "SGB RECMIN (provincia)"),
    "rochas_hospedeiras": ("Rochas que hospedam a mineralização.", "texto", "SGB RECMIN"),
    "rochas_encaixantes": ("Rochas encaixantes da mineralização.", "texto", "SGB RECMIN"),
    "rochas_afloramento": ("Rochas descritas no afloramento.", "texto", "SGB RECMIN (rochas)"),
    "morfologia": ("Morfologia do corpo mineralizado (filoneana, estratificada, lenticular…).", "", "SGB RECMIN"),
    "texturas": ("Textura da mineralização.", "", "SGB RECMIN"),
    "tipos_alteracao": ("Alterações hidrotermais/intempéricas associadas.", "", "SGB RECMIN"),
    "tipo_afloramento": ("Tipo de afloramento (pedreira, mina, corte de estrada…); vazio na maioria.", "", "SGB RECMIN"),
    "projeto_sgb": ("Projeto de mapeamento do SGB que cadastrou a ocorrência; vazio na maioria.", "texto", "SGB RECMIN (projeto)"),
    "folha_sgb": ("Folha cartográfica do SGB.", "texto", "SGB RECMIN (folha)"),
    "numero_campo": ("Número de campo do ponto no projeto do SGB.", "texto", "SGB RECMIN"),
    "afloramento_id_sgb": ("id_afloramento do GeoSGB (1:1 com a ocorrência em Goiás).", "número", "SGB RECMIN"),
    "data_cadastro": ("Data de cadastro no banco do GeoSGB — data de carga (82% em 2003), não de descoberta.", "AAAA-MM-DD", "SGB RECMIN"),
    "categoria_anm_sobreposta": ("Categoria mais avançada (Base 4) dos processos da ANM cujo polígono contém o ponto; fora_de_processo se nenhum.", "",
                                 "Derivado — SIGMINE (junção espacial)"),
    "processos_anm_sobrepostos": ("Processos da ANM cujo polígono contém o ponto.", "<número>/<ano> separados por ';'", "Derivado — SIGMINE"),
    "operation_ids_sobrepostos": ("operation_id desses processos (03).", "OPE_… separados por ';'", "Derivado — SIGMINE + 03"),
    "project_ids_sobrepostos": ("Projetos da 04 que contêm esses processos.", "PRJ_… separados por ';'", "Derivado — 04"),
    "substancia_original": ("Nome da substância exatamente como no RECMIN.", "texto", "SGB RECMIN"),
    "substancia_normalizada": ("Nome normalizado (maiúsculas, sem acento) usado no crosswalk.", "texto", "Derivado"),
    "ocorrencias": ("Ocorrências de Goiás que citam a substância.", "contagem", "SGB RECMIN"),
    "justificativa": ("Por que a substância foi ligada a esse mineral (ou ficou sem categoria).", "texto", "Pente fino da 06"),
})

status_aba = {**{a: "real" for a in ABAS_REAIS + ["07_dim_fontes"]}, **{a: "auditoria" for a in ABAS_AUDITORIA},
              **{a: "maquete (ilustrativa v0)" for a in ABAS_MAQUETE}}
ordem_abas = sorted(DADOS, key=lambda a: a)
dic_rows, sem_desc = [], []
tipos_por_campo = defaultdict(dict)
for aba in ordem_abas:
    cab, linhas = DADOS[aba]
    pf = perfil(cab, linhas)
    for c in cab:
        p = pf[c]
        if aba in ABAS_MAQUETE:
            dsc, dom = desc_v0.get((aba, nome_original.get((aba, c), c)), ("", ""))
            if not dsc and c in D:  # a v0 deixou vazia: usa a descrição geral do campo
                dsc, dom = D[c][0], dom or D[c][1]
            fonte = "maquete v0"
        else:
            base = D.get(c)
            dsc = DA_GOV.get((aba, c)) or DA.get((aba, c)) or (base[0] if base else "")
            dom = (base[1] if base else "") or p["dominio"]
            fonte = base[2] if base else ""
        if not dsc:
            sem_desc.append((aba, c))
        obs = []
        if p["pct_vazio"] == 100.0 and aba not in ABAS_MAQUETE:
            obs.append("coluna 100% vazia")
        if c in ("cfem_qtd_comercializada_t", "cfem_qtd_outras_unidades"):
            obs.append("Na fonte: " + nota_cfem_qtd)
        if (aba, c) in nome_original:
            obs.append(f"renomeada de '{nome_original[(aba, c)]}' na v6")
        if aba not in ABAS_MAQUETE and p["tipo"] != "vazio":
            tipos_por_campo[c][aba] = p["tipo"]
        dic_rows.append(dict(aba=aba, status_aba=status_aba[aba], campo=c, contrato_de_dados="sim" if c in CONTRATO else "",
                             descricao=dsc or "SEM DESCRIÇÃO", unidade_ou_dominio=dom, fonte_ou_derivacao=fonte, tipo=p["tipo"],
                             pct_vazio=p["pct_vazio"], n_distintos=p["n_distintos"], exemplo=p["exemplo"], observacao=" | ".join(obs)))

# ---------------------------------------------------------------------------
# 4) validações
# ---------------------------------------------------------------------------
val = []


def V(verificacao, n, resultado, ok):
    val.append(dict(verificacao=verificacao, n=n, resultado=resultado, status="OK" if ok else "ALERTA"))


V("Cabeçalhos renomeados para o padrão (contrato + unificação entre abas)", len(renomeados),
  "; ".join(sorted({f"{o} → {n}" for _, o, n in renomeados})), True)
fora_snake = [(a, c) for a in ABAS_REAIS + ABAS_AUDITORIA + ["07_dim_fontes"] for c in DADOS[a][0] if not SNAKE.match(str(c))]
V("Nomes de coluna fora do padrão snake_case ASCII (abas reais, auditorias e 07)", len(fora_snake), "; ".join(f"{a}.{c}" for a, c in fora_snake) or "nenhum", not fora_snake)
dups = [(a, c) for a in DADOS for c, k in Counter(DADOS[a][0]).items() if k > 1]
V("Nomes de coluna duplicados dentro da mesma aba", len(dups), "; ".join(f"{a}.{c}" for a, c in dups) or "nenhum", not dups)
presentes = sorted({c for a in ABAS_REAIS for c in DADOS[a][0] if c in CONTRATO})
V("Campos do Contrato de Dados presentes com o nome fixado", len(presentes), ", ".join(presentes), True)
# presente = coluna com pelo menos um valor preenchido (uma coluna 100% vazia não entrega o campo)
preenchidos = {c for a in ABAS_REAIS for c in DADOS[a][0] if c in CONTRATO and any(r.get(c) not in (None, "") for r in DADOS[a][1])}
ausentes_contrato = sorted({"project_id", "production_basis"} - preenchidos)
V("Campos do fluxo Squad 1 → Squad 2 sem nenhum valor preenchido nas abas reais", len(ausentes_contrato),
  (", ".join(ausentes_contrato) + " — project_id depende do Radar de Projetos (Squad 1 / Estudante 2)") if ausentes_contrato else "nenhum",
  not ausentes_contrato)
incons = {c: t for c, t in tipos_por_campo.items() if len(set(t.values())) > 1}
V("Mesma coluna com tipo diferente entre abas", len(incons), "; ".join(f"{c}: {t}" for c, t in incons.items()) or "nenhuma", not incons)
V("Colunas sem descrição no dicionário", len(sem_desc), "; ".join(f"{a}.{c}" for a, c in sem_desc) or "nenhuma", not sem_desc)
V("Valores em source_ids que não são ID de fonte (texto livre)", sum(citacao_invalida.values()),
  "; ".join(f"{a}: '{s}'" for (a, s) in citacao_invalida) or "nenhum", not citacao_invalida)
sem_reg = sorted(set(citacoes) - REG)
V("Fontes citadas em source_ids sem registro no catálogo 07", len(sem_reg), ", ".join(sem_reg) or "nenhuma", not sem_reg)
nao_cit = [r for r in fontes_rows if r["status_uso"] != "em uso"]
V("Fontes catalogadas que nenhuma aba real cita", len(nao_cit), "; ".join(f"{r['source_id']} ({r['status_uso']})" for r in nao_cit), True)
# v13: todo arquivo de dados/ precisa de source_id na 07; só a documentação das fontes fica de fora
DOC_DADOS = ["dados/LEIA-ME.md", "dados/*/LEIA-ME.md", "dados/*/*/metadados*.ods", "dados/ANM/cadastro_mineiro/mer-microdados-scm.pdf",
             "dados/ANM/cadastro_mineiro/recorte_goias.json", "dados/SGB_GeoSGB/recmin/*.metadados.json", "dados/datas_de_acesso.json"]
import fnmatch as _fnm
_brutos = arquivos_brutos()  # caminhos lógicos, na cópia de trabalho (dados/) ou no GitHub (Dados brutos/)
_cobertos = {a for a in _brutos if any(_fnm.fnmatch(a, p) for f in FONTES for p in f["padroes"])}
_doc_dados = {a for a in _brutos if any(_fnm.fnmatch(a, p) for p in DOC_DADOS)}
_sem_src = sorted(a for a in _brutos if a not in _cobertos | _doc_dados)
V("Arquivos de dados/ sem source_id no catálogo 07 (fora a documentação: LEIA-ME, metadados .ods, dicionário do SCM, metadados do download do RECMIN)",
  len(_sem_src), "; ".join(_sem_src) or f"nenhum ({len(_cobertos)} arquivos catalogados, {len(_doc_dados)} de documentação)", not _sem_src)
PAD = {"mineral_id": r"^MIN_\d{3}$", "municipality_id": r"^52\d{5}$", "operation_id": r"^OPE_\d+_\d{4}$", "fato_id": r"^FATO_\d{6}$", "project_id": r"^PRJ_\d+_\d{4}$", "occurrence_id": r"^OCC_\d+$",
       "company_id": r"^COM_(CNPJ_\d{8}|CPF_\d{11}|NOME_[0-9A-F]{8}|NAO_IDENTIFICADO)$"}
fora_pad = Counter()
for a in ABAS_REAIS:
    cab, linhas = DADOS[a]
    for c, pat in PAD.items():
        if c in cab:
            fora_pad[(a, c)] += sum(1 for r in linhas if r[c] not in (None, "") and not re.match(pat, str(r[c])))
V("IDs fora do padrão", sum(fora_pad.values()), "; ".join(f"{a}.{c}: {n}" for (a, c), n in fora_pad.items() if n) or "nenhum", not sum(fora_pad.values()))

# LGPD (v12): nenhum CPF completo em texto. Candidato = 11 dígitos (com ou sem pontuação) com dígito verificador válido. Ignora célula que
# é só número (o valor_original da 08 tem decimais longos que às vezes passam no DV por acaso) e hash hexadecimal.
_CPF_V = re.compile(r"(?<![\d/])(\d{3}\.?\d{3}\.?\d{3}-?\d{2})(?![\d/])")
_SO_NUMERO = re.compile(r"[\d\s.,+\-eE]+|(conjunto:)?[0-9a-f]{64}")


def _cpf_valido(s):
    d = re.sub(r"\D", "", s)
    if len(set(d)) == 1:
        return False
    v1 = sum(int(d[i]) * (10 - i) for i in range(9)) * 10 % 11 % 10
    v2 = sum(int(d[i]) * (11 - i) for i in range(10)) * 10 % 11 % 10
    return (v1, v2) == (int(d[9]), int(d[10]))


_cpf_achados = Counter()
for _a, (_cab, _linhas) in DADOS.items():
    for _r in _linhas:
        for _c in _cab:
            _v = _r.get(_c)
            if isinstance(_v, str) and not _SO_NUMERO.fullmatch(_v):
                _cpf_achados[(_a, _c)] += sum(1 for _m in _CPF_V.finditer(_v) if _cpf_valido(_m.group(1)))
_cpf_achados = {k: n for k, n in _cpf_achados.items() if n}
_cpf_mascarados = sum(1 for _r in DADOS["02_dim_empresas"][1] if re.search(r"\*\*\*[\d.]{6,8}-?\*\*", str(_r.get("razao_social") or "")))
V("LGPD: CPF completo em campo de texto (11 dígitos com dígito verificador válido)", sum(_cpf_achados.values()),
  ("; ".join(f"{a}.{c}: {n}" for (a, c), n in sorted(_cpf_achados.items())) if _cpf_achados else "nenhum")
  + f". Titulares da 02 com CPF dentro do nome, mascarado na exibição (***456789**): {_cpf_mascarados}; o company_id não muda.",
  not _cpf_achados)
dom = {"mineral_id": {r["mineral_id"] for r in DADOS["01_dim_minerais"][1]}, "company_id": {r["company_id"] for r in DADOS["02_dim_empresas"][1]},
       "municipality_id": {r["municipality_id"] for r in DADOS["05_dim_municipios"][1]},
       "operation_id": {r["operation_id"] for r in DADOS["03_dim_operacoes"][1]},
       "project_id": {r["project_id"] for r in DADOS["04_dim_projetos"][1]}}
orf = Counter()
for a, c, multi, d in [("03_dim_operacoes", "company_id", False, "company_id"), ("03_dim_operacoes", "mineral_ids", True, "mineral_id"),
                       ("03_dim_operacoes", "municipality_id", False, "municipality_id"), ("09_cons_mineral_ano", "mineral_id", False, "mineral_id"),
                       ("10_cons_municipio_ano", "municipality_id", False, "municipality_id"), ("11_cons_empresa_ano_mineral", "mineral_id", False, "mineral_id"),
                       ("11_cons_empresa_ano_mineral", "company_id", False, "company_id"),
                       ("08_fato_producao_energia", "mineral_id", False, "mineral_id"), ("08_fato_producao_energia", "company_id", False, "company_id"),
                       ("08_fato_producao_energia", "municipality_id", False, "municipality_id"),
                       ("08_fato_producao_energia", "operation_id", False, "operation_id"),
                       ("12_interface_squad1_squad2", "mineral_id", False, "mineral_id"), ("12_interface_squad1_squad2", "company_id", False, "company_id"),
                       ("12_interface_squad1_squad2", "municipality_id", False, "municipality_id"),
                       ("12_interface_squad1_squad2", "operation_id", False, "operation_id"),
                       ("04_dim_projetos", "company_id", False, "company_id"), ("04_dim_projetos", "mineral_id", False, "mineral_id"),
                       ("04_dim_projetos", "municipality_id", False, "municipality_id"), ("04_dim_projetos", "operation_ids", True, "operation_id"),
                       ("04_dim_projetos", "operacao_adjacente", True, "operation_id"),
                       ("06_dim_ocorrencias_geologicas", "mineral_ids", True, "mineral_id"), ("06_dim_ocorrencias_geologicas", "municipality_id", False, "municipality_id"),
                       ("06_dim_ocorrencias_geologicas", "operation_ids_sobrepostos", True, "operation_id"),
                       ("06_dim_ocorrencias_geologicas", "project_ids_sobrepostos", True, "project_id"),
                       ("06b_crosswalk_recmin", "mineral_id", False, "mineral_id")]:
    for r in DADOS[a][1]:
        v = r.get(c)
        if v in (None, ""):
            continue
        for x in ([s.strip() for s in str(v).split(";")] if multi else [str(v)]):
            if x not in dom[d]:
                orf[f"{a}.{c}"] += 1
V("Integridade referencial (chaves das abas consolidadas → dimensões)", sum(orf.values()), "; ".join(f"{k}: {n}" for k, n in orf.items()) or "0 órfãos", not orf)
vazias = [(r["aba"], r["campo"]) for r in dic_rows if "coluna 100% vazia" in r["observacao"]]
V("Colunas 100% vazias em abas reais (placeholders declarados)", len(vazias), "; ".join(f"{a}.{c}" for a, c in vazias), True)
_cab09 = DADOS["09_cons_mineral_ano"][0]
_n_exc = len(DADOS["09b_auditoria_cfem_quantidade"][1])
V("Quantidade comercializada da CFEM: unidades misturadas e valores corrompidos tratados", _n_exc,
  f"Na fonte: {nota_cfem_qtd}. Tratamento na Base 1: massa convertida para t; m³/l/m² fora da soma em t; "
  f"{_n_exc} linhas com quantidade corrompida ou implausível excluídas da soma de quantidade (R$ mantido) — ver 09b.",
  "cfem_qtd_comercializada_t" in _cab09 and "cfem_qtd_comercializada" not in _cab09)

# plausibilidade permanente: quantidade da CFEM (t) x producao bruta do AMB (t), mesmo mineral e ano em GO
import math
_PARA_T = {"t": 1.0, "kg": 1e-3, "g": 1e-6}
_pl = []
for _r in DADOS["09_cons_mineral_ano"][1]:
    _c = _r.get("cfem_qtd_comercializada_t")
    if _r.get("uf") != "GO" or not _c:
        continue
    _benef = _r.get("production_beneficiada")
    _fb = _PARA_T.get(str(_r.get("production_beneficiada_unit") or "").strip().lower())
    _bases = [("bruta", _r.get("production_t_rom")), ("beneficiada", _benef * _fb if (_benef and _fb) else None)]
    _cands = [(b, _c / v) for b, v in _bases if v]
    if not _cands:
        continue
    _b, _z = min(_cands, key=lambda x: abs(math.log10(x[1])))  # compara com a base mais próxima
    if _z > 2 or _z < 0.05:
        _pl.append((_r["mineral_name"], _r["year"], _z, _b))
_pl.sort(key=lambda x: -abs(math.log10(x[2])))
V("Plausibilidade: CFEM comercializada (t) ÷ produção do AMB na base mais próxima (bruta ou beneficiada), por mineral e ano em GO, fora de 0,05–2×", len(_pl),
  "; ".join(f"{m} {a}: {z:,.2f}× ({b})" for m, a, z, b in _pl[:30]) + (" …" if len(_pl) > 30 else "")
  + f". CONCLUSÃO: com {len(_pl)} mineral-anos fora da faixa, a quantidade comercializada da CFEM NÃO serve como proxy de produção sem validação mineral a mineral. "
    "Causas investigadas: (1) rochas — resolvido na v7 com o mapeamento por tipo de uso (01c); o que sobra são processos isolados listados na 09c "
    "(ex.: basalto declarado como revestimento com volume de brita; granito para brita acima do total estadual); (2) Níquel 2025 — um único processo "
    "(960146/2003) passa a declarar ~10× mais toneladas a partir de julho, com o mesmo R$; (3) Ouro e Prata — CFEM em g/kg, na escala de metal, acima do AMB "
    "beneficiado: desde a v14 a 09c compara esses metais com a produção beneficiada (não com o minério) e lista os processos responsáveis (minério declarado "
    "como metal e declarações acima do estado inteiro). Os demais NÃO foram investigados — valores perto de zero (Amianto, Gemas, Diamante) sugerem unidade "
    "ou base incomparável; nos valores muito acima, Titânio, Nióbio e Manganês têm processos isolados que sozinhos superam o total estadual "
    "(ver 09c; causa não investigada). "
    "Afeta só a QUANTIDADE; os valores em R$ não são afetados.",
  not _pl)
_al9c = DADOS["09c_alertas_cfem_processo"][1]
_alta9c = [r for r in _al9c if r["severidade"] == "alta"]
V("Processos com quantidade na CFEM implausível frente ao AMB do estado (acima do total ou, em metais, R$/t incompatível; mantidos na soma, sinalizados na 09c)", len(_al9c),
  f"severidade alta: {len(_alta9c)}; moderada: {len(_al9c) - len(_alta9c)}. Alta: "
  + ("; ".join(f"{r['mineral_name']} {r['year']} proc. {r['processo_anm']}: " + (f"{r['razao']:,.1f}×" if r["razao"] else "R$/t incompatível, sem AMB no ano")
               for r in _alta9c) or "nenhum"), not _alta9c)
_ru_cfem = [r for r in DADOS["01c_rochas_por_tipo_de_uso"][1] if r["fonte"] == "CFEM (GO)"]
_rs_regra = Counter()
for _r in _ru_cfem:
    _rs_regra[_r["regra"]] += _r["valor_recolhido_brl"] or 0.0
_tot_ru = sum(_rs_regra.values()) or 1.0
V("Rochas na CFEM: de onde veio a categoria (% do R$ de CFEM de rochas)", len(_ru_cfem),
  "; ".join(f"{k}: {100 * v / _tot_ru:.1f}%" for k, v in _rs_regra.most_common()), True)

# v17: IMB (Goiás em Dados) como checagem cruzada da produção do estado no AMB, nos anos em que as duas fontes têm valor
import unicodedata as _ud


def _chave_mineral(t):
    return _ud.normalize("NFD", str(t)).encode("ascii", "ignore").decode().upper().strip()


_imb = {}
for _p in sorted(glob.glob(arquivo("dados/IMB/consulta*.csv"))):
    _di = pd.read_csv(_p, sep=";", encoding="cp1252", encoding_errors="replace", dtype=str, keep_default_na=False)
    _anos_imb = [c for c in _di.columns if re.fullmatch(r"\d{4}", str(c).strip())]
    for _, _r in _di[_di["Localidade"].str.upper().str.contains("ESTADO DE GOI")].iterrows():
        _m = re.match(r"Produção de (.+?) \((.*)\)\s*$", str(_r["Variável"]))
        if not _m:
            continue
        for _a in _anos_imb:
            _txt = str(_r[_a]).strip()
            if re.fullmatch(r"-?[\d.]+(,\d+)?", _txt) and float(_txt.replace(".", "").replace(",", ".")) > 0:
                _imb[(_chave_mineral(_m.group(1)), int(_a))] = (float(_txt.replace(".", "").replace(",", ".")), _m.group(2))
_amb_go = {(_chave_mineral(r["mineral_name"]), int(r["year"])): r for r in DADOS["09_cons_mineral_ano"][1] if r.get("uf") == "GO" and r.get("year")}
_razoes = defaultdict(list)
for (_nome, _ano), (_v, _un) in sorted(_imb.items()):
    _r = _amb_go.get((_nome, _ano))
    if _r and _r.get("production_beneficiada"):
        _razoes[(_r["mineral_name"], _un, _r.get("production_beneficiada_unit") or "")].append((_ano, _v / _r["production_beneficiada"]))
_iguais = sorted(k[0] for k, l in _razoes.items() if all(0.99 <= x <= 1.01 for _, x in l))
_difer = [k for k in sorted(_razoes) if not all(0.99 <= x <= 1.01 for _, x in _razoes[k])]
if _razoes:
    _anos_cmp = sorted({a for l in _razoes.values() for a, _ in l})
    _res_imb = (f"{len(_razoes)} minerais comparados em {_anos_cmp[0]}–{_anos_cmp[-1]}; o IMB não traz produção mineral depois de "
                f"{max(a for _, a in _imb)}. Iguais à produção beneficiada do AMB em todos os anos (razão 0,99–1,01): {', '.join(_iguais) or 'nenhum'}. "
                "Diferentes em algum ano (razão IMB ÷ AMB): "
                + "; ".join(f"{m} (IMB em {u or 'unidade não informada'}, AMB em {ua}): " + ", ".join(f"{a} {x:.2f}×" for a, x in _razoes[(m, u, ua)])
                            for m, u, ua in _difer)
                + ". O IMB republica parte do AMB; onde difere, pode informar outra base (por exemplo, metal contido). A divergência fica registrada e a "
                  "base segue o AMB.")
else:
    _res_imb = "sem anos em comum entre o IMB e o AMB nos arquivos desta cópia"
V("IMB (Goiás em Dados) × AMB: produção do estado por mineral nos anos em que as duas fontes têm valor (checagem cruzada, informativa)",
  sum(len(l) for l in _razoes.values()), _res_imb, True)
# --- aba 08 (fato longo): cobertura das fontes, conciliação com 09–11 e governança por linha ---
_F = DADOS["08_fato_producao_energia"][1]
_PT = {"t": 1.0, "kg": 1e-3, "g": 1e-6, "ct": 2e-7}


def _num_br(s):
    s = str(s).strip()
    if not s or s == "-":
        return None
    s = s.replace(".", "").replace(",", ".") if "," in s else s
    try:
        return float(s)
    except ValueError:
        return None


# (a) cobertura: cada célula numérica das 3 fontes vira exatamente uma linha (menos o contido 'não se aplica', unidade '-')
_esperado, _pulado = Counter(), Counter()
for _sid, _arq in (("SRC_ANM_PROD_BRUTA", "dados/ANM/producao_amb_ral/Producao_Bruta.csv"),
                   ("SRC_ANM_PROD_BENEF", "dados/ANM/producao_amb_ral/Producao_Beneficiada.csv"),
                   ("SRC_ANM_CFEM", "dados/ANM/cfem/CFEM_Arrecadacao_2022_2026_GO.csv")):
    _df, _ = csv_local(_arq)
    for _c in [c for c in _df.columns if re.match(r"^(Quantidade|Valor)", c.strip())]:
        _cheio = _df[_c].str.strip().ne("")
        if _c.strip() == "Quantidade Contido":
            _na = _df["Unidade de Medida - Contido"].str.strip().eq("-") & _df[_c].map(lambda s: _num_br(s) == 0)
            _pulado[_sid] += int((_cheio & _na).sum())
            _cheio = _cheio & ~_na
        _esperado[_sid] += int(_cheio.sum())
_carregado = Counter(r["source_id"] for r in _F)
_dif_cob = {s: (_esperado[s], _carregado[s]) for s in set(_esperado) | set(_carregado) if _esperado[s] != _carregado[s]}
V("08: cada célula numérica das fontes (AMB bruta, AMB beneficiada, CFEM) vira exatamente uma linha — contado de novo nos arquivos", len(_F),
  "; ".join(f"{s}: {_carregado[s]:,} linhas × {_esperado[s]:,} células" for s in sorted(_esperado))
  + f". Fora: {sum(_pulado.values()):,} células de contido com unidade '-' (não se aplica). Divergências: {_dif_cob or 'nenhuma'}", not _dif_cob)

# (b) conciliação: 09, 10 e 11 são somas de valor_tratado da 08
_M09 = {"producao_rom": "production_t_rom", "producao_beneficiada": "production_beneficiada_t", "valor_venda_beneficiada": "valor_venda_beneficiada_brl",
        "cfem_recolhido": "cfem_recolhido_brl", "quantidade_comercializada_cfem": "cfem_qtd_comercializada_t"}
_i09, _i10, _i11 = defaultdict(float), defaultdict(float), defaultdict(float)
for r in _F:
    vt, m = r["valor_tratado"], r["metrica"]
    if vt is None or r["year"] in (None, ""):
        continue
    ano = int(r["year"])
    if m == "cfem_recolhido":
        if r["municipality_id"] not in (None, ""):
            _i10[(str(r["municipality_id"]), ano)] += vt
        if r["mineral_id"] not in (None, ""):
            _i11[(r["company_id"], r["mineral_id"], ano)] += vt
    campo = _M09.get(m)
    if not campo or r["mineral_id"] in (None, "") or (campo == "cfem_qtd_comercializada_t" and r["unidade_padrao"] != "t"):
        continue
    # a 09 só tem GO e BR (= soma de todas as UFs); as outras UFs ficam na 08 sem linha própria na 09
    for uf in ({r["uf"]} if r["source_id"] == "SRC_ANM_CFEM" else {r["uf"], "BR"}) & {"GO", "BR"}:
        _i09[(uf, r["mineral_id"], ano, campo)] += vt


def _confere(esperado_08, linhas, chave, campos):
    difs, vistos, n = [], set(), 0
    for r in linhas:
        if r.get("year") in (None, ""):
            continue
        for campo, v_aba in campos(r).items():
            k = chave(r) + (campo,) if campo else chave(r)
            vistos.add(k)
            v08 = esperado_08.get(k, 0.0)
            n += 1
            if abs((v_aba or 0.0) - v08) > 1e-6 * max(1.0, abs(v_aba or 0.0)):
                difs.append((k, v_aba, v08))
    difs += [(k, None, v) for k, v in esperado_08.items() if k not in vistos and abs(v) > 1e-9]
    return difs, n


def _campos09(r):
    fb = _PT.get(str(r.get("production_beneficiada_unit") or "").strip().lower())
    pb = r.get("production_beneficiada")
    return {"production_t_rom": r.get("production_t_rom"), "production_beneficiada_t": (pb * fb) if (pb is not None and fb) else pb,
            "valor_venda_beneficiada_brl": r.get("valor_venda_beneficiada_brl"), "cfem_recolhido_brl": r.get("cfem_recolhido_brl"),
            "cfem_qtd_comercializada_t": r.get("cfem_qtd_comercializada_t")}


_d09, _n09 = _confere(_i09, DADOS["09_cons_mineral_ano"][1], lambda r: (r["uf"], r["mineral_id"], int(r["year"])), _campos09)
_d10, _n10 = _confere(_i10, DADOS["10_cons_municipio_ano"][1], lambda r: (str(r["municipality_id"]), int(r["year"])),
                      lambda r: {None: r.get("cfem_recolhido_brl")})
_d11, _n11 = _confere(_i11, DADOS["11_cons_empresa_ano_mineral"][1], lambda r: (r["company_id"], r["mineral_id"], int(r["year"])),
                      lambda r: {None: r.get("cfem_recolhido_brl")})
_dd = _d09 + _d10 + _d11
V("08 → 09/10/11: as abas consolidadas são somas de valor_tratado da 08 (produção bruta/beneficiada, venda e CFEM por mineral×UF×ano; CFEM por município e por empresa)",
  len(_dd), f"09: {len(_d09)} divergências em {_n09:,} comparações; 10: {len(_d10)} em {_n10:,}; 11: {len(_d11)} em {_n11:,}"
  + (". Exemplos: " + "; ".join(str(d) for d in _dd[:8]) if _dd else ""), not _dd)

# (c) campos de governança por linha (Entrega Avaliativa §3)
_reg07 = {f["source_id"]: f for f in fontes_rows}
_inc = Counter(r["source_id"] for r in _F if r["source_id"] not in _reg07 or r["source_url"] != _reg07[r["source_id"]]["url_recurso"]
               or r["data_acesso"] != _reg07[r["source_id"]]["data_arquivo_local"] or r["tipo_fonte"] != _reg07[r["source_id"]]["tipo_fonte"])
_sem_metodo = sum(1 for r in _F if r["valor_observado_estimado"] != "observado" and not r["metodo_estimacao"])
_dup = sum(k - 1 for k in Counter((r["source_id"], r["source_linha"], r["coluna_original"]) for r in _F).values() if k > 1)
V("08: campos de governança por linha — source_url, data_acesso e tipo_fonte iguais à 07; não observado sem método; mesma célula da fonte em duas linhas",
  sum(_inc.values()) + _sem_metodo + _dup,
  f"divergentes da 07: {dict(_inc) or 0}; não observado sem metodo_estimacao: {_sem_metodo}; células repetidas: {_dup}. "
  f"valor_observado_estimado: {dict(Counter(r['valor_observado_estimado'] for r in _F))}; status_validacao: {dict(Counter(r['status_validacao'] for r in _F))}",
  not (_inc or _sem_metodo or _dup))

# (c2) v16: campos de governança da Entrega Avaliativa §3 em todas as abas de dados
_GOV3 = ["source_url", "data_acesso", "periodo_referencia", "tipo_fonte", "valor_observado_estimado", "metodo_estimacao", "status_validacao", "responsavel_validacao"]
_res3, _prob3 = [], 0
for _a in ["01_dim_minerais", "02_dim_empresas", "03_dim_operacoes", "04_dim_projetos", "05_dim_municipios", "06_dim_ocorrencias_geologicas",
           "08_fato_producao_energia", "09_cons_mineral_ano", "10_cons_municipio_ano", "11_cons_empresa_ano_mineral", "12_interface_squad1_squad2",
           "13_mapas_camadas"]:
    _cab, _ls = DADOS[_a]
    _sc = "source_ids" if "source_ids" in _cab else "source_id"
    _falta = [c for c in [_sc] + _GOV3 if c not in _cab]
    _cheios = [c for c in [_sc] + _GOV3 if c in _cab and c != "metodo_estimacao"]
    _vaz = sum(1 for r in _ls for c in _cheios if r.get(c) in (None, ""))
    _div = sum(1 for r in _ls if "source_url" in _cab and "data_acesso" in _cab and (
        r.get("source_url") != "; ".join(_reg07[i]["url_recurso"] for i in _ids(r.get(_sc)) if i in _reg07)
        or r.get("data_acesso") != "; ".join(str(_reg07[i]["data_arquivo_local"]) for i in _ids(r.get(_sc)) if i in _reg07)))
    _sm = sum(1 for r in _ls if r.get("valor_observado_estimado") not in (None, "", "observado") and r.get("metodo_estimacao") in (None, ""))
    _prob3 += len(_falta) + _vaz + _div + _sm
    _res3.append(f"{_a[:2]}: " + ("ok" if not (_falta or _vaz or _div or _sm) else f"faltam {_falta}; vazios {_vaz}; URL/data ≠ 07 {_div}; sem método {_sm}"))
V("§3 da Entrega: fonte, source_url, data_acesso, periodo_referencia, tipo_fonte, valor_observado_estimado, metodo_estimacao, status_validacao e "
  "responsavel_validacao em todas as abas de dados — preenchidos (método só quando não observado) e com URL e data iguais à 07",
  _prob3, "; ".join(_res3), not _prob3)

# (d) produção repetida no AMB (co-produto ou teor): recontada aqui, sinalizada na 08, mantida nas somas
_grp = defaultdict(list)
for r in _F:
    if r["metrica"] in ("producao_rom", "producao_beneficiada") and (r["valor_tratado"] or 0) > 0:
        _grp[(r["source_id"], r["uf"], r["year"], r["metrica"], str(r["valor_original"]), r["unidade_original"])].append(r)  # unidade na chave: 43 kg ≠ 43 t
_rep = [g for g in _grp.values() if len(g) > 1]
_n_rep = sum(len(g) for g in _rep)
_n_status = sum(1 for r in _F if r["status_validacao"] == "alerta_producao_repetida")
_dentro = sum(g[0]["valor_tratado"] * (len(g) - 1) for g in _rep if len({x["mineral_id"] for x in g}) == 1)
_entre = sum(g[0]["valor_tratado"] * (len(g) - 1) for g in _rep if len({x["mineral_id"] for x in g}) > 1)
_rep_go = "; ".join(f"{g[0]['metrica']} {g[0]['year']}: {g[0]['valor_original']} {g[0]['unidade_original']} em " + " + ".join(x["mineral_name"] for x in g)
                    for g in _rep if g[0]["uf"] == "GO") or "nenhum"
V("08: mesma tonelagem de produção em linhas diferentes da mesma UF e ano no AMB (co-produto, mineral separado por teor ou mesma declaração em duas categorias) — sinalizada, mantida nas somas", _n_rep,
  f"{len(_rep)} grupos, {_n_rep} linhas (com status alerta_producao_repetida: {_n_status}). Numa soma contam a mais {_dentro:,.0f} t dentro do mesmo mineral "
  f"(infla a linha BR da 09) e {_entre:,.0f} t entre minerais. Goiás: {_rep_go}. A fonte não tem linha 100% duplicada — as linhas diferem na substância, na categoria ou no contido/teor; "
  "divergência registrada, não corrigida (guia: 'divergências devem ser registradas, não corrigidas silenciosamente').", _n_rep == 0)

# --- aba 12 (interface Squad 1 → Squad 2): estado = 08, operações somam o estado, cobertura e governança por linha ---
_I = DADOS["12_interface_squad1_squad2"][1]
_est = [r for r in _I if r["nivel_agregacao"] == "estado"]
_ops12 = [r for r in _I if r["nivel_agregacao"] == "operacao"]
_p08 = defaultdict(float)
for r in _F:
    if r["uf"] == "GO" and r["metrica"] in ("producao_rom", "producao_beneficiada") and r["valor_tratado"] is not None:
        _p08[(r["mineral_id"], int(r["year"]), "ROM" if r["metrica"] == "producao_rom" else "beneficiada")] += r["valor_tratado"]
_e12 = {(r["mineral_id"], int(r["year"]), r["production_basis"]): (r["production_t"] or 0.0) for r in _est}
_d12a = [(k, _e12.get(k), v) for k, v in _p08.items() if k not in _e12 or abs(_e12[k] - v) > 1e-6 * max(1.0, abs(v))]
_d12a += [(k, v, None) for k, v in _e12.items() if k not in _p08]
_s12, _sh12 = defaultdict(float), defaultdict(float)
for r in _ops12:
    k = (r["mineral_id"], int(r["year"]), r["production_basis"])
    _s12[k] += r["production_t"] or 0.0
    _sh12[k] += r["participacao_cfem_brl"] or 0.0
_d12b = [(k, v, _e12.get(k)) for k, v in _s12.items() if k not in _e12 or abs(v - _e12[k]) > 1e-6 * max(1.0, abs(_e12[k]))]
_d12b += [(k, "soma das participações", round(v, 9)) for k, v in _sh12.items() if abs(v - 1) > 1e-9]
V("12: nível estado = produção de GO na 08 (AMB); nível operação soma exatamente o total do estado (rateio conservativo)", len(_d12a) + len(_d12b),
  f"estado: {len(_est):,} linhas, {len(_d12a)} divergências com a 08; operação: {len(_ops12):,} linhas em {len(_s12):,} totais rateados, "
  f"{len(_d12b)} divergências de soma ou participação" + (". Exemplos: " + "; ".join(str(d) for d in (_d12a + _d12b)[:6]) if (_d12a or _d12b) else ""),
  not (_d12a or _d12b))

_tot12, _ab12 = defaultdict(float), defaultdict(float)
for k, v in _e12.items():
    if 2022 <= k[1] <= 2025:
        _tot12[k[1]] += v
        if k in _s12:
            _ab12[k[1]] += v
_t_op = sum(r["production_t"] or 0.0 for r in _ops12) or 1e-9
_sem_ab = sorted({f"{r['mineral_name']} {r['year']}" for r in _est if 2022 <= r["year"] <= 2025 and (r["production_t"] or 0) > 0
                  and (r["mineral_id"], r["year"], r["production_basis"]) not in _s12})
V("12: cobertura da abertura por operação (2022–2025) — produção do estado com CFEM para ratear; parte estimada com operation_id e com coordenadas", len(_ops12),
  "; ".join(f"{a}: {100 * _ab12[a] / _tot12[a]:.1f}% das t abertas" for a in sorted(_tot12) if _tot12[a])
  + f". Da produção estimada: {100 * sum(r['production_t'] or 0.0 for r in _ops12 if r['operation_id']) / _t_op:.1f}% com operation_id, "
  f"{100 * sum(r['production_t'] or 0.0 for r in _ops12 if r['latitude'] is not None) / _t_op:.1f}% com coordenadas; {len({r['processo_anm'] for r in _ops12}):,} processos. "
  f"Sem abertura (sem CFEM do mineral no ano): {'; '.join(_sem_ab) or 'nenhum'}", True)

_reg12 = {f["source_id"]: f for f in fontes_rows}
_viol12 = Counter()
for r in _I:
    _estim = r["valor_observado_estimado"] == "estimado"
    if _estim and not (r["metodo_estimacao"] and r["erro_estimativa_intervalo"]):
        _viol12["estimado sem método ou intervalo"] += 1
    if not _estim and (r["metodo_estimacao"] or r["erro_estimativa_intervalo"]):
        _viol12["observado com método de estimativa"] += 1
    if (r["nivel_agregacao"] == "operacao") != _estim:
        _viol12["nível e natureza incoerentes"] += 1
    _ids = [s.strip() for s in str(r["source_id"] or "").split(";")]
    _urls = [s.strip() for s in str(r["source_url"] or "").split("; ")]
    _dts = [s.strip() for s in str(r["data_acesso"] or "").split(";")]
    if len(_ids) != len(_urls) or len(_ids) != len(_dts) or any(
            i not in _reg12 or u != _reg12[i]["url_recurso"] or d != _reg12[i]["data_arquivo_local"] for i, u, d in zip(_ids, _urls, _dts)):
        _viol12["source_url/data_acesso diferentes da 07"] += 1
V("12: governança por linha (Entrega Avaliativa §3) — estimado com método e intervalo, observado sem; fontes, URLs e datas iguais à 07", sum(_viol12.values()),
  f"{dict(_viol12) or 'nenhuma violação'}. valor_observado_estimado: {dict(Counter(r['valor_observado_estimado'] for r in _I))}; "
  f"status_validacao: {dict(Counter(r['status_validacao'] for r in _I))}", not _viol12)

# --- aba 04 (projetos, camada ANM do radar): cobertura do universo, regra de classificação e governança por linha ---
_P04 = DADOS["04_dim_projetos"][1]
_EV04 = {r["tipo_evento"]: r["classe_evento"] for r in DADOS["04b_eventos_anm_classificados"][1]}
_CAND04 = {"2_lavra_sem_cfem_recente", "4_pre_lavra", "6_requerimento_licenc_garimpeira"}


def _tipo_evento04(txt):  # mesma regra do build_projetos_04.py
    t = re.sub(r"^\d+\s*-\s*", "", str(txt))
    return re.sub(r"\s+(EM|PUBL?|PROTOC|HOM|EFETUADO)\b.*$", "", t).strip()


_ev03 = {r["processo_anm"]: r["ultimo_evento"] for r in DADOS["03_dim_operacoes"][1]}
_univ04 = [r for r in DADOS["03_dim_operacoes"][1] if r["categoria_mapa"] in _CAND04]
_sem_tipo04 = sum(1 for r in _univ04 if _tipo_evento04(r["ultimo_evento"]) not in _EV04)
_vivos04 = {r["processo_anm"] for r in _univ04 if _EV04.get(_tipo_evento04(r["ultimo_evento"])) != "encerramento"}
_mortos04 = {r["processo_anm"] for r in _univ04} - _vivos04
_em_proj04 = Counter(p.strip() for r in _P04 for p in str(r["processos_anm"]).split(";"))
_fora04 = _vivos04 - set(_em_proj04)
_dup04 = [p for p, n in _em_proj04.items() if n > 1]
_morto_em04 = _mortos04 & set(_em_proj04)
_extra04 = set(_em_proj04) - _vivos04 - _mortos04
V("04: cada processo vivo do universo (título de lavra sem CFEM, pré-lavra, requerimento de licenciamento/garimpeira) está em exatamente um projeto; "
  "os de último evento terminal (04b) em nenhum", len(_fora04) + len(_dup04) + len(_morto_em04) + len(_extra04) + _sem_tipo04,
  f"universo na 03: {len(_univ04):,} processos; vivos {len(_vivos04):,} → {len(_P04):,} projetos; terminais {len(_mortos04):,}. Vivos fora de projeto: {len(_fora04)}; "
  f"em dois projetos: {len(_dup04)}; terminais em projeto: {len(_morto_em04)}; fora do universo: {len(_extra04)}; tipos de evento sem classe na 04b: {_sem_tipo04}",
  not (_fora04 or _dup04 or _morto_em04 or _extra04 or _sem_tipo04))

_ref04 = pd.Timestamp(next(f["data_arquivo_local"] for f in fontes_rows if f["source_id"] == "SRC_ANM_SIGMINE"))


def _classe04(r):  # tabela de decisão documentada no build_projetos_04.py (teto 'provável' sem evidência corporativa)
    if _EV04.get(_tipo_evento04(_ev03.get(r["processo_ancora"]))) == "disputa":
        return "sinal"
    if not r["data_evidencia"] or pd.Timestamp(r["data_evidencia"]) < _ref04 - pd.DateOffset(years=3):
        return "sinal"
    if r["estagio"] == "lavra_autorizada_sem_producao":
        return "provável"
    if r["estagio"] in ("requerimento_de_lavra", "direito_de_requerer_lavra"):
        return "possível"
    return "possível" if r["evento_licenciamento_ambiental"] == "sim" else "sinal"


_div04 = [(r["project_id"], r["classificacao_maturidade"], _classe04(r)) for r in _P04 if _classe04(r) != r["classificacao_maturidade"]]
V("04: classificação refeita a partir do estágio, da data do último evento, de disputa e de licenciamento ambiental (teto 'provável' sem evidência corporativa)",
  len(_div04), f"{len(_P04):,} projetos: {dict(Counter(r['classificacao_maturidade'] for r in _P04))}; divergências com a regra: {len(_div04)}"
  + (f" {_div04[:5]}" if _div04 else ""), not _div04)

_reg04 = {f["source_id"]: f for f in fontes_rows}
_viol04 = Counter()
for r in _P04:
    _ids = [s.strip() for s in str(r["source_id"] or "").split(";")]
    _urls = [s.strip() for s in str(r["source_url"] or "").split("; ")]
    _dts = [s.strip() for s in str(r["data_acesso"] or "").split(";")]
    if len(_ids) != len(_urls) or len(_ids) != len(_dts) or any(
            i not in _reg04 or u != _reg04[i]["url_recurso"] or d != _reg04[i]["data_arquivo_local"] for i, u, d in zip(_ids, _urls, _dts)):
        _viol04["source_url/data_acesso diferentes da 07"] += 1
    if any(r[c] not in (None, "") for c in ("capacidade_t_ano", "capex_brl", "ano_previsto_entrada")):
        _viol04["capacidade, CAPEX ou ano previsto preenchidos sem fonte corporativa"] += 1
    if not (r["status_validacao"] and r["responsavel_validacao"] and r["criterio_classificacao"]):
        _viol04["sem status, responsável ou critério"] += 1
V("04: governança por linha — fontes, URLs e datas iguais à 07; capacidade, CAPEX e ano previsto vazios (não inventados); status, responsável e critério preenchidos",
  sum(_viol04.values()), f"{dict(_viol04) or 'nenhuma violação'}. tipo_projeto: {dict(Counter(r['tipo_projeto'] for r in _P04))}; "
  f"estágio: {dict(Counter(r['estagio'] for r in _P04))}", not _viol04)

# --- aba 06 (ocorrências do RECMIN): recorte refeito do arquivo baixado, crosswalk, campos descartados e governança por linha ---
_O6 = DADOS["06_dim_ocorrencias_geologicas"][1]
try:
    import geopandas as gpd

    _rg = gpd.read_file(arquivo("dados/SGB_GeoSGB/recmin/ocorrencias_recursos_minerais_GO.geojson"))
    _mg = gpd.read_file(f"{BASE}/outputs/mapas/minera_goias_mapas_v1.gpkg", layer="municipios_go", engine="pyogrio")
    _dg = gpd.sjoin(_rg.to_crs(_mg.crs), _mg[["municipality_id", "geometry"]], predicate="within", how="inner")
    _esp06 = {f"OCC_{int(i)}": m for i, m in zip(_dg["id_ocorrencia"], _dg["municipality_id"])}
    _tab06 = {r["occurrence_id"]: r["municipality_id"] for r in _O6}
    _falta06, _sobra06 = set(_esp06) - set(_tab06), set(_tab06) - set(_esp06)
    _mun06 = [k for k in set(_esp06) & set(_tab06) if str(_esp06[k]) != str(_tab06[k])]
    V("06: recorte refeito do arquivo baixado — cada ponto do RECMIN dentro da malha de Goiás está na 06 uma vez, com o mesmo município; os de fora não",
      len(_falta06) + len(_sobra06) + len(_mun06),
      f"arquivo: {len(_rg):,} pontos, {len(_esp06):,} dentro de GO; 06: {len(_tab06):,} linhas (repetidas: {len(_O6) - len(_tab06)}). Faltando: {len(_falta06)}; "
      f"a mais: {len(_sobra06)}; município diferente: {len(_mun06)}", not (_falta06 or _sobra06 or _mun06 or len(_O6) != len(_tab06)))
    _dd = _dg
    _loc = Counter(_dd["localizacao_mina"].fillna("(vazio)")).most_common(1)[0]
    V("06: campos do RECMIN fora da aba por não terem informação (evidência recalculada no arquivo)", 6,
      f"localizacao_mina = '{_loc[0]}' em {100 * _loc[1] / len(_dd):.0f}% dos pontos de GO (inclusive garimpo e não explotado); situacao_garimpo = situacao_mina em "
      f"{100 * (_dd['situacao_mina'].fillna('~') == _dd['situacao_garimpo'].fillna('~')).mean():.0f}%; sureg: {dict(Counter(_dd['sureg']))}; origem: "
      f"{dict(Counter(_dd['origem']))}; datum: {dict(Counter(_dd['datum']))}; geologo não usado. O arquivo original fica intacto em dados/.", True)
except Exception as _e:
    V("06: recorte refeito do arquivo baixado", 1, f"não executado: {_e}", False)

# --- aba 13 (camadas de mapa): toda camada do catálogo tem arquivo; processos, ocorrências e projetos têm uma feição por linha ---
import os as _os
_C13 = DADOS["13_mapas_camadas"][1]
_ORIGEM13 = {"CAM_02": "03_dim_operacoes", "CAM_05": "06_dim_ocorrencias_geologicas", "CAM_06": "04_dim_projetos"}
_prob13 = []
for _c in _C13:
    _arq = str(_c.get("arquivo") or "")
    if not _arq or not _os.path.exists(f"{BASE}/{_arq}"):
        _prob13.append(f"{_c['camada_id']}: arquivo '{_arq or 'vazio'}' não existe")
    _ab = _ORIGEM13.get(_c["camada_id"])
    if _ab and _c.get("n_feicoes") != len(DADOS[_ab][1]):
        _prob13.append(f"{_c['camada_id']}: {_c.get('n_feicoes')} feições × {len(DADOS[_ab][1])} linhas na aba {_ab[:2]}")
V("13: toda camada do catálogo tem arquivo em outputs/mapas/; processos (CAM_02), ocorrências (CAM_05) e projetos (CAM_06) têm uma feição por linha da aba de origem",
  len(_prob13), "; ".join(_prob13) or f"{len(_C13)} camadas com arquivo; CAM_02 = aba 03, CAM_05 = aba 06, CAM_06 = aba 04", not _prob13)


def _partes06(s):  # mesma regra do build_ocorrencias_06.py
    return list(dict.fromkeys(p.strip() for p in re.split(r";|,(?![^()]*\))", str(s or "")) if p.strip()))


_cw06 = {r["substancia_original"]: r["mineral_id"] for r in DADOS["06b_crosswalk_recmin"][1]}
_div06, _semcw06 = [], set()
for r in _O6:
    _ps = _partes06(r["substancias_original"])
    _semcw06 |= {p for p in _ps if p not in _cw06}
    _esperado = list(dict.fromkeys(_cw06[p] for p in _ps if _cw06.get(p)))
    _atual = [x.strip() for x in str(r["mineral_ids"] or "").split(";") if x.strip()]
    if _esperado != _atual:
        _div06.append((r["occurrence_id"], _atual, _esperado))
_tipos06 = Counter(r["tipo_correspondencia"] for r in DADOS["06b_crosswalk_recmin"][1])
V("06: substâncias → mineral_ids refeito pela 06b (toda substância tem decisão; nenhum mineral novo, IDs MIN_### da 01)", len(_div06) + len(_semcw06),
  f"{len(_cw06)} nomes na 06b: {dict(_tipos06)}; sem categoria ANM: "
  f"{', '.join(r['substancia_original'] for r in DADOS['06b_crosswalk_recmin'][1] if not r['mineral_id']) or 'nenhum'}. "
  f"Substâncias da 06 sem linha na 06b: {len(_semcw06)}; ocorrências com mineral_ids diferente do crosswalk: {len(_div06)}" + (f" {_div06[:3]}" if _div06 else ""),
  not (_div06 or _semcw06))

_reg06 = {f["source_id"]: f for f in fontes_rows}
_viol06 = Counter()
for r in _O6:
    _ids = [s.strip() for s in str(r["source_id"] or "").split(";")]
    _urls = [s.strip() for s in str(r["source_url"] or "").split("; ")]
    _dts6 = [s.strip() for s in str(r["data_acesso"] or "").split(";")]
    if len(_ids) != len(_urls) or len(_ids) != len(_dts6) or any(
            i not in _reg06 or u != _reg06[i]["url_recurso"] or d != _reg06[i]["data_arquivo_local"] for i, u, d in zip(_ids, _urls, _dts6)):
        _viol06["source_url/data_acesso diferentes da 07"] += 1
    if r["valor_observado_estimado"] != "observado" or r["metodo_estimacao"]:
        _viol06["não observado ou com método de estimativa"] += 1
_minas06 = [r for r in _O6 if r["status_economico"] == "Mina"]
V("06: governança por linha — fontes, URLs e datas iguais à 07; tudo observado na fonte. Cruzamento com a ANM (informativo)", sum(_viol06.values()),
  f"{dict(_viol06) or 'nenhuma violação'}. status_validacao: {dict(Counter(r['status_validacao'] for r in _O6))}; categoria ANM do ponto: "
  f"{dict(Counter(r['categoria_anm_sobreposta'] for r in _O6))}; dentro de projeto da 04: {sum(1 for r in _O6 if r['project_ids_sobrepostos'])}; 'minas' do RECMIN "
  f"em operação ativa hoje: {sum(1 for r in _minas06 if r['categoria_anm_sobreposta'] == '1_operacao_ativa')} de {len(_minas06)}", not _viol06)

for v in val:
    print(f"  [{v['status']:6s}] {v['verificacao']}: {v['n']}")

# ---------------------------------------------------------------------------
# 5) grava as abas 07, 14 e 14b
# ---------------------------------------------------------------------------
for nome in ("07_dim_fontes", "14_dicionario_dados", "14b_validacoes_governanca"):
    if nome in wb.sheetnames:
        del wb[nome]

ws = wb.create_sheet("07_dim_fontes")
ws.sheet_view.showGridLines = False
w07 = dict(source_id=24, nome_fonte=46, orgao=10, tipo_fonte=11, status_uso=22, usado_em=44, url_catalogo=38, url_recurso=52,
           metadados_oficiais=40, arquivo_local=40, arquivos=9, tamanho_mb=10, sha256=30, data_arquivo_local=13, periodo_coberto=40,
           granularidade=30, formato_declarado=30, formato_arquivo_local=30, frequencia_atualizacao=18, confiabilidade=24, limitacoes_conhecidas=90)
cols07 = [dict(key=k, width=w07.get(k, 16), fmt=("0.00" if k == "tamanho_mb" else None)) for k in cab07]
style_header(ws, "Dimensão — Catálogo mestre de fontes",
             f"{len(fontes_rows)} fontes. URLs dos metadados oficiais (.ods da ANM) e verificadas nas páginas do SIDRA e do geoftp do IBGE em 11/09/2026 "
             "(as fontes que entraram na v13, em 12/09/2026). "
             "sha256, tamanho, período e formato local são CALCULADOS dos arquivos em dados/; 'usado_em' é calculado das colunas source_ids das abas reais. "
             "'limitacoes_conhecidas' consolida as armadilhas encontradas no pente fino de cada base.", len(cols07), 60)
write_table(ws, cols07, fontes_rows, "DimFontesV6", wrap=("nome_fonte", "usado_em", "url_recurso", "periodo_coberto", "limitacoes_conhecidas"))

ws = wb.create_sheet("14_dicionario_dados")
ws.sheet_view.showGridLines = False
cols14 = [dict(key="aba", width=28), dict(key="status_aba", width=14), dict(key="campo", width=30), dict(key="contrato_de_dados", width=10),
          dict(key="descricao", width=70), dict(key="unidade_ou_dominio", width=36), dict(key="fonte_ou_derivacao", width=32),
          dict(key="tipo", width=10), dict(key="pct_vazio", width=9, fmt="0.0"), dict(key="n_distintos", width=10, fmt="#,##0"),
          dict(key="exemplo", width=28), dict(key="observacao", width=50)]
style_header(ws, "Dicionário de dados (gerado das colunas reais)",
             f"{len(dic_rows)} campos em {len(ordem_abas)} abas. Tipo, % vazio, nº de valores distintos, exemplo e (para texto com até 12 valores) o domínio são CALCULADOS "
             "dos dados da própria planilha — o dicionário não pode mais ficar desatualizado em relação às abas. contrato_de_dados = 'sim' para os nomes fixados no "
             "Contrato de Dados V1." + (" Abas ainda em maquete mantêm a descrição da v0." if ABAS_MAQUETE else ""), len(cols14), 60)
write_table(ws, cols14, dic_rows, "DicionarioV6", wrap=("descricao", "unidade_ou_dominio", "observacao"))

ws = wb.create_sheet("14b_validacoes_governanca")
ws.sheet_view.showGridLines = False
cols14b = [dict(key="verificacao", width=62), dict(key="n", width=8, fmt="#,##0"), dict(key="resultado", width=110), dict(key="status", width=10)]
style_header(ws, "Validações de governança",
             "Checagens automáticas feitas ao gerar o dicionário e o catálogo: padrão de nomes, campos do contrato, tipos entre abas, descrições, fontes citadas × "
             "catalogadas, padrão de IDs e integridade referencial. ALERTA = algo a tratar; OK = sem pendência.", len(cols14b), 44)
write_table(ws, cols14b, val, "ValidacoesV6", wrap=("resultado",))

leia = wb["00_LEIA-ME"]
r = leia.max_row + 2
for col in (1, 2):
    leia.cell(row=r, column=col).fill = PatternFill("solid", fgColor=TEAL)
leia.cell(row=r, column=2, value="ATUALIZAÇÃO v6 — governança: catálogo de fontes, dicionário e nomes do contrato").font = Font(bold=True, size=12, color=WHITE)
c = leia.cell(row=r + 1, column=2, value=(
    "07_dim_fontes e 14_dicionario_dados passam a ser reais e calculados a partir dos arquivos e das colunas efetivas; 14b_validacoes_governanca "
    "registra as checagens. Nomes de coluna alinhados ao Contrato de Dados V1 (ano→year, mineral_nome→mineral_name, municipio_nome→municipality_name, "
    "producao_t→production_t, consumo_energia_mwh→energy_mwh, intensidade_mwh_t→energy_intensity_mwh_t) e nomes diferentes para a mesma informação "
    "unificados. Correções na origem: status_producao_go da 01 agora é o calculado (divergia em 7 minerais); source_ids passam a citar TODAS as fontes "
    "usadas na linha (a 09 não citava Cadastro Mineiro/SIGMINE; a 10 não citava população/PIB)."))
c.font = Font(size=10.5)
c.alignment = Alignment(wrap_text=True, vertical="top")
leia.row_dimensions[r + 1].height = 100
r7 = r + 3
for col in (1, 2):
    leia.cell(row=r7, column=col).fill = PatternFill("solid", fgColor=TEAL)
leia.cell(row=r7, column=2, value="ATUALIZAÇÃO v7 — rochas mapeadas pelo tipo de uso").font = Font(bold=True, size=12, color=WHITE)
c7 = leia.cell(row=r7 + 1, column=2, value=(
    "Para rochas, a categoria da ANM passa a ser decidida por (substância, tipo de uso) em TODAS as bases: brita/construção civil → Rochas (Britadas) e Cascalho; "
    "revestimento → Rochas Ornamentais; usos industriais → Minerais Industriais (Outros), etc. (regras e contagens na 01c). Na CFEM, que não tem campo de uso, o uso vem "
    "do número do processo (Cadastro Mineiro/SIGMINE). Resultado (CFEM t ÷ AMB, GO): Rochas Ornamentais 35–191× → 0,5–1,3×; Rochas (Britadas) e Cascalho 0,26× → "
    "0,6–1,1× em 2022–24 (2025 = 2,35× por um único processo, 860555/2014); Rochas Ornamentais - Outras 90–3.861× → 14–363×, ainda alto por dois processos de basalto "
    "declarados como revestimento (860633/2014 e 860529/2006). O R$ total da CFEM não muda (R$ 867,6 mi nas Bases 1, 2 e 3). A nova aba 09c sinaliza os processos "
    "cuja tonelagem na CFEM supera o total do AMB para o estado inteiro (severidade alta ou moderada) — mantidos na soma, marcados para revisão."))
c7.font = Font(size=10.5)
c7.alignment = Alignment(wrap_text=True, vertical="top")
leia.row_dimensions[r7 + 1].height = 115
r8 = r7 + 3
for col in (1, 2):
    leia.cell(row=r8, column=col).fill = PatternFill("solid", fgColor=TEAL)
leia.cell(row=r8, column=2, value="ATUALIZAÇÃO v8 — 08_fato_producao_energia real (fato longo, rastreável até a célula)").font = Font(bold=True, size=12, color=WHITE)
c8 = leia.cell(row=r8 + 1, column=2, value=(
    f"Uma linha por célula numérica das fontes: AMB produção bruta e beneficiada (todas as UFs) e CFEM de Goiás — {len(_F):,} linhas, 18 métricas. ".replace(",", ".")
    + "Cada linha aponta a célula exata (source_file + source_linha + coluna_original), guarda o valor como veio (valor_original, texto) e o valor final na unidade "
    "padrão (valor_tratado: massa em t, R$ em BRL) com o tratamento aplicado, e traz os campos de governança da Entrega Avaliativa §3 (source_url, data_acesso, "
    "periodo_referencia, tipo_fonte, valor_observado_estimado, metodo_estimacao, status_validacao, responsavel_validacao). As abas 09, 10 e 11 passam a ser somas da 08, "
    "com conciliação na 14b. Pente fino: o AMB repete a mesma tonelagem em linhas de co-produtos (em Goiás, Bário + Nióbio 2023), do mesmo mineral separado "
    "por teor e da mesma declaração em duas categorias (Rochas Ornamentais e Rochas Ornamentais - Outras, GO 2011) — essas linhas ficam sinalizadas "
    "(alerta_producao_repetida), sem correção. Energia: nenhuma fonte do Squad 1 mede consumo; as linhas de energia "
    "entram com o Squad 2, marcadas como estimado/benchmark e com o método."))
c8.font = Font(size=10.5)
c8.alignment = Alignment(wrap_text=True, vertical="top")
leia.row_dimensions[r8 + 1].height = 120
r9 = r8 + 3
for col in (1, 2):
    leia.cell(row=r9, column=col).fill = PatternFill("solid", fgColor=TEAL)
leia.cell(row=r9, column=2, value="ATUALIZAÇÃO v9 — 12_interface_squad1_squad2 real (entrega Squad 1 → Squad 2)").font = Font(bold=True, size=12, color=WHITE)
c9 = leia.cell(row=r9 + 1, column=2, value=(
    f"Campos do Contrato de Dados + production_basis + governança, em dois níveis que NÃO se somam: {len(_est)} linhas de nível estado (produção OBSERVADA de Goiás "
    f"no AMB, 2010–2025, ROM e beneficiada, igual à 08) e {len(_ops12)} linhas de nível operação (abertura ESTIMADA em 2022–2025, rateada pela participação de cada "
    "processo na CFEM em R$ do mineral no ano; soma igual ao total do estado). A ANM não publica produção por operação: o rateio supõe a mesma relação R$/t entre as "
    "operações do mesmo mineral, traz a faixa contra o rateio pela quantidade em t da CFEM e não deve ser usado como produção observada nem como denominador observado "
    "de intensidade operação-específica. Sem abertura: minerais sem CFEM no ano (ex.: areias industriais, feldspato, talco). A 08 ganhou processo_anm, que "
    "identifica também a CFEM de processos sem poligonal. project_id segue vazio (Radar de Projetos)."))
c9.font = Font(size=10.5)
c9.alignment = Alignment(wrap_text=True, vertical="top")
leia.row_dimensions[r9 + 1].height = 110
r10 = r9 + 3
for col in (1, 2):
    leia.cell(row=r10, column=col).fill = PatternFill("solid", fgColor=TEAL)
leia.cell(row=r10, column=2, value="ATUALIZAÇÃO v10 — 04_dim_projetos real (camada ANM do Radar de Projetos) + 04b").font = Font(bold=True, size=12, color=WHITE)
_c04 = Counter(r["classificacao_maturidade"] for r in _P04)
c10 = leia.cell(row=r10 + 1, column=2, value=(
    f"{len(_P04)} projetos que ainda não produzem, a partir de {len(_vivos04)} processos de Goiás em estágio de desenvolvimento (título de lavra sem CFEM em 2024–2026, "
    f"pré-lavra, requerimento de licenciamento/lavra garimpeira); {len(_mortos04)} processos ficaram de fora por último evento terminal (indeferimento, desistência, "
    "baixa, caducidade, renúncia — cada tipo de evento classificado na 04b) e os processos de pesquisa não entram (processo de pesquisa não é projeto). Processos "
    f"contíguos do mesmo titular e mineral formam um projeto. Classificação só com evidência da ANM, com teto em 'provável': provável {_c04.get('provável', 0)}, "
    f"possível {_c04.get('possível', 0)}, sinal {_c04.get('sinal', 0)}. Capacidade, CAPEX e ano previsto ficam vazios de propósito: o Radar de Projetos completo "
    "(RI, CVM, SEMAD, classes definido/construção/expansão) é entrega do Squad 1 / Estudante 2, que parte destes IDs. Próximo dado útil: microdados do SCM "
    "(ProcessoEvento.txt), com o histórico completo de eventos de cada processo."))
c10.font = Font(size=10.5)
c10.alignment = Alignment(wrap_text=True, vertical="top")
leia.row_dimensions[r10 + 1].height = 115
r11 = r10 + 3
for col in (1, 2):
    leia.cell(row=r11, column=col).fill = PatternFill("solid", fgColor=TEAL)
leia.cell(row=r11, column=2, value="ATUALIZAÇÃO v11 — 06_dim_ocorrencias_geologicas real (RECMIN do SGB) + 06b; nenhuma aba em maquete").font = Font(bold=True, size=12, color=WHITE)
_imp06 = Counter(r["importancia"] for r in _O6)
c11 = leia.cell(row=r11 + 1, column=2, value=(
    f"{len(_O6)} ocorrências minerais de Goiás do RECMIN, baixadas do WFS oficial do SGB em 12/09/2026 com autorização do Eliel (os pacotes GeoSGB locais não tinham "
    f"ocorrências) e recortadas pela malha do IBGE. Importância: depósito {_imp06.get('Depósito', 0)}, ocorrência {_imp06.get('Ocorrência', 0)}, indício "
    f"{_imp06.get('Indício', 0)}, indeterminado {_imp06.get('Indeterminado', 0)}. É evidência geológica, não projeto: o status 'mina ativa' é do cadastro (a maioria de "
    "2003), não de hoje. Cada ocorrência traz mineral_ids (crosswalk das substâncias na 06b, sem criar minerais novos), o município da malha e os processos da ANM "
    "e projetos da 04 que contêm o ponto. Campos sem informação na fonte ficaram de fora com a evidência na 14b. Com a v11, todas as abas da planilha são reais."))
c11.font = Font(size=10.5)
c11.alignment = Alignment(wrap_text=True, vertical="top")
leia.row_dimensions[r11 + 1].height = 100

# ---------------------------------------------------------------------------
# v12 — títulos sem rótulo de versão: cada writer carimbava a versão em que a aba nasceu ("(v4, real)", "— v1, dados reais"),
# e a mesma planilha mostrava v1…v11 misturados. A versão da planilha fica no 00_LEIA-ME e no nome do arquivo.
# ---------------------------------------------------------------------------
_ROTULO = [(r"\(v\d+, real — ", "("), (r"\s*\(v\d+(, real)?\)", ""), (r"\(v\d+, ", "("), (r"\s*—\s*v\d+, dados reais", "")]
for ws in wb.worksheets:
    if ws.title != "00_LEIA-ME" and isinstance(ws["A1"].value, str):
        _t = ws["A1"].value
        for _pat, _rep in _ROTULO:
            _t = re.sub(_pat, _rep, _t)
        ws["A1"].value = _t.strip()
_com_rotulo = [(ws.title, ws["A1"].value) for ws in wb.worksheets if ws.title != "00_LEIA-ME" and re.search(r"\bv\d+\b", str(ws["A1"].value))]
assert not _com_rotulo, f"título ainda com rótulo de versão: {_com_rotulo}"

# ---------------------------------------------------------------------------
# v12 — 00_LEIA-ME reescrito. O topo ainda era o texto do protótipo v0 ("rascunho de formato", placeholders, IDs sequenciais
# COM_###/OPE_#####). Agora descreve a planilha como ela é; as notas de cada versão ficam embaixo, como histórico, sem reescrita.
# ---------------------------------------------------------------------------
DATA_VERSAO = "2026-09-13"
# Quando o robô de atualização (robo/robo_bases.py) refaz a planilha com arquivos novos da ANM, ele passa a data em
# MINERA_DATA_DADOS: a estrutura continua a da v17, os dados são os baixados naquele dia.
DATA_DADOS = os.environ.get("MINERA_DATA_DADOS")
_lin = list(wb["00_LEIA-ME"].iter_rows(max_col=2, values_only=True))
HIST = [(b, _lin[i + 1][1] if i + 1 < len(_lin) else "") for i, (_, b) in enumerate(_lin) if isinstance(b, str) and b.startswith("ATUALIZAÇÃO")]
assert [h[0].split()[1] for h in HIST] == [f"v{i}" for i in range(1, 12)], [h[0][:24] for h in HIST]
_mask_aba = {}
for _a in ABAS_REAIS:
    _cab, _linhas = DADOS[_a]
    _k = sum(1 for _r in _linhas for _c in ("razao_social", "nome_projeto", "nomes_alternativos")
             if _c in _cab and re.search(r"\*\*\*[\d.]{6,8}-?\*\*", str(_r.get(_c) or "")))
    if _k:
        _mask_aba[_a] = _k
HIST.append(("ATUALIZAÇÃO v12 — verificação geral: LGPD, reprodutibilidade e documentação", (
    f"LGPD: o CPF completo que vinha dentro do nome de {_cpf_mascarados} titulares (empresário individual) passa a sair mascarado, no padrão que a ANM usa "
    f"(***456789**), nas abas ({'; '.join(f'{a}: {n} células' for a, n in _mask_aba.items())}) e nas camadas de mapa. Os IDs não mudam: o company_id continua "
    "calculado do nome e do documento originais. A 14b ganhou a checagem 'nenhum CPF completo em texto'. Reprodutibilidade: municipios_atuacao (aba 11) listava "
    "6 municípios tirados de um conjunto sem ordem fixa, e cerca de 660 linhas mudavam a cada execução; agora são os 6 primeiros em ordem alfabética, e a nova "
    "coluna qtd_municipios_mineral_ano dá o total antes do corte (qtd_municipios é do titular inteiro). Documentação: este LEIA-ME foi reescrito (o topo ainda "
    "descrevia o protótipo v0), os títulos das abas perderam o rótulo de versão, a 13 aponta CAM_05 e CAM_06 para as abas 06 e 04, o placeholder "
    "SRC_EXEMPLO_ILUSTRATIVO saiu da 07 e dados/LEIA-ME.md teve períodos e contagens conferidos com os arquivos. Fora essas mudanças, os valores das abas de dados "
    "são os mesmos da v11.")))
HIST.append(("ATUALIZAÇÃO v13 — catálogo de fontes completo e pipeline que roda em outra máquina", (
    f"A 07 passa de 14 para {len(fontes_rows)} fontes: entraram a planilha derivada Mineradoras_Goias_operacao_e_potencial, a malha municipal do IBGE de 2024, "
    "a população estimada de Goiás (SIDRA), a geoquímica da Folha Nazário, os três SIG geológicos do SGB (Centro-Norte da Faixa Brasília, Oeste de Goiás e Barro "
    "Alto) e os oito mapas de referência em PDF. Todo arquivo de dados/ tem agora um source_id, exceto documentação (LEIA-ME, metadados .ods, dicionário do SCM e "
    "metadados do download do RECMIN), e a 14b confere isso a cada geração. Nenhuma das fontes novas alimenta as abas de dados (status_uso diz o papel de cada "
    "uma). Reprodutibilidade: os scripts não têm mais caminho fixo da máquina do Eliel — base_consolidada_work/scripts/caminhos.py calcula a pasta do projeto "
    "pela posição do arquivo e manda os intermediários para a pasta temporária do sistema (ou MINERA_TMP); rodar_pipeline.py roda as 17 etapas em ordem, com "
    "log por etapa e retomada com --de; requirements.txt fixa as versões usadas. Os valores das abas de dados são os mesmos da v12.")))
_al14 = DADOS["09c_alertas_cfem_processo"][1]
_metal14 = [r for r in _al14 if str(r.get("amb_base") or "").startswith("beneficiada")]
_preco14 = [r for r in _metal14 if "R$/t" in str(r.get("criterio") or "")]
HIST.append(("ATUALIZAÇÃO v14 — regra da 09c corrigida para metais medidos em kg (ouro e prata)", (
    "A 09c comparava a tonelagem declarada na CFEM com o maior entre a produção bruta e a beneficiada do AMB, e só aceitava a beneficiada em t. No ouro "
    "isso deixava como limite a produção bruta de minério (22 a 31 Mt por ano em Goiás), enquanto a CFEM declara metal em kg ou g: nenhum processo de ouro "
    "era sinalizado. Na prata, sem produção bruta, não havia limite nenhum. Agora, nos minerais cuja produção beneficiada o AMB mede em kg ou g, o limite é "
    "essa produção beneficiada convertida para t; e, como o preço do metal é bem definido, o alerta também dispara quando o R$/t do processo fica mais de "
    f"10× abaixo da mediana do mineral ponderada pelo valor recolhido, o que pega minério declarado como metal. Resultado: {len(_al14)} processo-anos na 09c, {len(_metal14)} deles de "
    f"{' e '.join(sorted({r['mineral_name'] for r in _metal14})) or 'metais'} ({len(_preco14)} só ou também pelo critério de preço). A 09c ganhou as colunas "
    "amb_base e criterio. Nada foi excluído de soma: mudam só os status das linhas de CFEM desses processos na 08 (alerta_processo_09c) e das operações "
    "na 12 (estimativa_com_alerta_09c).")))

_cam15 = {c["camada_id"]: c for c in DADOS["13_mapas_camadas"][1]}
_n06, _n05 = (f"{_cam15[k]['n_feicoes']:,}".replace(",", ".") for k in ("CAM_06", "CAM_05"))
HIST.append(("ATUALIZAÇÃO v15 — camadas de mapa dos projetos (04) e das ocorrências (06)", (
    f"A 13 não tem mais camada reservada: CAM_06 projetos_futuros ({_n06} pontos) e CAM_05 ocorrencias_minerais_recmin "
    f"({_n05} pontos) passam a ser gravadas por um passo novo do pipeline, build_mapas_04_06.py, que roda depois das abas 04 e 06 "
    "(a Base 4 roda antes delas). Cada camada sai no GeoPackage (SIRGAS 2000, com todas as colunas da aba) e em GeoJSON para a web (WGS 84, colunas "
    "principais), com as mesmas chaves da aba de origem; as coordenadas não são recalculadas. A 13b registra se cada ponto cai dentro de Goiás e no mesmo "
    "município da aba, e a 14b passa a conferir que toda camada do catálogo tem arquivo e que processos, ocorrências e projetos têm uma feição por linha. "
    "O pipeline passa a ter 18 etapas. Os valores das abas de dados são os mesmos da v14.")))

HIST.append(("ATUALIZAÇÃO v16 — campos de governança em todas as abas de dados e dados brutos no GitHub", (
    "Os campos da seção 3 da Entrega Avaliativa (fonte, source_url, data_acesso, periodo_referencia, tipo_fonte, valor_observado_estimado, "
    "metodo_estimacao, status_validacao e responsavel_validacao) estavam completos só nas abas 04, 06, 08 e 12. Agora estão também nas abas 01, 02, 03, "
    "05, 09, 10, 11 e 13: a 01 e a 02 ganharam source_ids (fontes em que o mineral ou o titular aparece); URL, data e tipo vêm do catálogo 07, na ordem "
    "das fontes da linha; nas consultas 09, 10 e 11 o período é o ano e o status herda os alertas das linhas da 08 que entram na soma; a 04 ganhou "
    "metodo_estimacao. A 14b confere esses campos em todas as abas de dados. Os dados brutos usados passaram a ser publicados no GitHub em "
    "Squad 1/Dados brutos/, uma pasta por fonte (Cadastro Mineiro recortado para Goiás com a mesma regra de município do pipeline), e o pipeline acha "
    "os arquivos tanto nesse arranjo quanto na cópia de trabalho (caminhos.py), sem mudar o caminho citado nas abas. Os valores das abas de dados são "
    "os mesmos da v15.")))

HIST.append(("ATUALIZAÇÃO v17 — IMB (Goiás em Dados) como checagem cruzada do AMB", (
    "A 14b ganhou a comparação da produção do estado publicada pelo IMB com a produção beneficiada do AMB (aba 09), mineral a mineral, nos anos em "
    "que as duas fontes têm valor. O IMB só traz produção mineral até 2016; em parte dos minerais repete o AMB e, em outros, informa outra base. "
    "A divergência fica registrada e a base continua usando o AMB. Na 07, a fonte passa a constar como usada só em validação cruzada, e as quatro "
    "consultas foram publicadas em Squad 1/Dados brutos/IMB - Goiás em Dados/. Os valores das abas de dados são os mesmos da v16.")))

ABA_DESC = {
    "01_dim_minerais": "dimensão de minerais: as categorias oficiais da ANM mais subitens justificados na 01b",
    "01b_crosswalk_pente_fino": "auditoria: cada grafia de substância nas fontes → mineral_id",
    "01c_rochas_por_tipo_de_uso": "auditoria: rochas classificadas na categoria da ANM pelo tipo de uso",
    "02_dim_empresas": "dimensão de titulares (empresas e pessoas físicas) com título minerário em Goiás",
    "02b_crosswalk_empresas": "auditoria: grafias e raízes de CNPJ fundidas ou mantidas separadas",
    "03_dim_operacoes": "dimensão de processos minerários do SIGMINE que tocam Goiás, com categoria operacional, município e CFEM (atributos da camada CAM_02)",
    "04_dim_projetos": "projetos que ainda não produzem — camada ANM do Radar de Projetos (o radar completo é do Squad 1 / Estudante 2)",
    "04b_eventos_anm_classificados": "auditoria: classe atribuída a cada tipo de último evento da ANM",
    "05_dim_municipios": "dimensão dos municípios de Goiás (malha IBGE 2025)",
    "05b_crosswalk_municipios": "auditoria: nomes de município das fontes → código IBGE",
    "06_dim_ocorrencias_geologicas": "ocorrências e depósitos minerais do RECMIN (SGB) dentro de Goiás — evidência geológica, não projeto",
    "06b_crosswalk_recmin": "auditoria: substâncias do RECMIN → mineral_id",
    "07_dim_fontes": "catálogo de fontes: URL oficial, arquivo local, sha256, período e abas que usam cada fonte",
    "08_fato_producao_energia": "fato longo: uma linha por célula numérica do AMB (produção bruta e beneficiada) e da CFEM, rastreável até a célula da fonte",
    "09_cons_mineral_ano": "consulta: mineral × ano, Goiás e Brasil (produção AMB, CFEM, processos e titulares)",
    "09b_auditoria_cfem_quantidade": "auditoria: quantidades da CFEM excluídas da soma de toneladas (o R$ continua somado)",
    "09c_alertas_cfem_processo": "alertas: processo com quantidade declarada na CFEM implausível frente ao AMB (acima do total estadual ou, em metais como ouro e prata, R$/t incompatível)",
    "10_cons_municipio_ano": "consulta: município × ano (CFEM, processos, população e PIB)",
    "11_cons_empresa_ano_mineral": "consulta: empresa × mineral × ano (CFEM e títulos)",
    "12_interface_squad1_squad2": "entrega ao Squad 2: produção por mineral e ano, observada no nível estado e estimada por operação — os dois níveis não se somam",
    "13_mapas_camadas": "catálogo das camadas de mapa em outputs/mapas/ (GeoJSON, GeoPackage e PMTiles), inclusive projetos (04) e ocorrências (06)",
    "13b_auditoria_mapas": "auditoria das chaves espaciais: coordenadas, polígonos e junção com municípios",
    "14_dicionario_dados": "dicionário: cada campo de cada aba, com tipo, % vazio e exemplo calculados dos dados",
    "14b_validacoes_governanca": "validações automáticas: nomes, IDs, integridade, conciliações e LGPD",
}
_faltam = sorted(set(wb.sheetnames) - {"00_LEIA-ME"} - set(ABA_DESC))
assert not _faltam, f"aba sem descrição no 00_LEIA-ME: {_faltam}"


def _n_linhas(a):
    return f"{max(wb[a].max_row - HDR, 0):,}".replace(",", ".")


SECOES = [
    ("O que é esta planilha", [
        "A base do Squad 1 para o MINERA Goiás: minerais, empresas, processos e projetos da ANM, municípios, ocorrências geológicas do SGB e a produção mineral e "
        "a CFEM de Goiás — com ID estável, fonte e unidade em cada número, como pede o Contrato de Dados. A entrega ao Squad 2 é a aba 12.",
        "Três camadas. Registro: dimensões 01–07 e o fato longo 08, que guarda cada célula numérica das fontes com o valor original e o tratado. Consulta: 09, 10 e "
        "11, bases largas por mineral × ano, município × ano e empresa × mineral × ano, somadas da 08 e conciliadas com ela na 14b. Entrega e apoio: 12 (Squad 1 → "
        "Squad 2), 13 (camadas de mapa) e 14/14b (dicionário e validações). Abas com letra (01b, 02b, 04b…) são auditorias: registram cada decisão de normalização "
        "e cruzamento, uma a uma."]),
    ("Abas", [f"{a}  —  {ABA_DESC[a]} ({_n_linhas(a)} linhas)" for a in sorted(wb.sheetnames) if a != "00_LEIA-ME"]),
    ("IDs (estáveis — não recalcular por correção de nome)", [
        "mineral_id = MIN_### (ordem de classe e nome da 01; criar mineral renumeraria os IDs, por isso só com decisão do grupo) · municipality_id = código IBGE "
        "de 7 dígitos · source_id = SRC_<órgão>_<base> · fato_id = FATO_###### · camada_id = CAM_##.",
        "company_id = COM_CNPJ_<8 primeiros dígitos do CNPJ> (a raiz agrupa matriz e filiais); pessoa física ou titular sem documento = COM_NOME_<sha1 do nome "
        "normalizado>; CFEM de processo que não está em nenhuma base de título = COM_NAO_IDENTIFICADO.",
        "operation_id = OPE_<número>_<ano> do processo na ANM · project_id = PRJ_<número>_<ano> do processo-âncora do projeto · occurrence_id = OCC_<id da "
        "ocorrência no RECMIN>."]),
    ("Cuidados de uso", [
        "Quantidade comercializada da CFEM não é produção: há unidades misturadas e erros de exportação (ver 09b e 09c). A produção oficial é o AMB/RAL da ANM, "
        "que só existe por UF × mineral × ano.",
        "Na 12, o nível estado é produção observada; o nível operação é ESTIMADO (rateio pela participação de cada processo na CFEM em R$) e não deve ser somado ao "
        "estado, usado como produção observada nem como denominador observado de intensidade energética.",
        "Alertas ficam sinalizados, não corrigidos: produção repetida no AMB (08, alerta_producao_repetida), processo com quantidade implausível na CFEM (09c) e "
        "mineral-anos com CFEM × AMB fora da faixa plausível (14b).",
        "A 04 usa só evidência da ANM (classe no máximo 'provável'); capacidade, CAPEX e ano previsto ficam vazios até o Radar de Projetos completo (Squad 1 / "
        "Estudante 2). A 06 é potencial geológico: o status 'mina ativa' é do cadastro do SGB (a maioria de 2003), não de hoje.",
        "Energia (energy_mwh e energy_intensity_mwh_t) fica vazia: nenhuma fonte do Squad 1 mede consumo; entra com o Squad 2, marcada como estimado ou benchmark.",
        "LGPD: o CPF que aparece dentro do nome de um titular (empresário individual) sai mascarado (***456789**) na planilha e nos mapas; os arquivos brutos em "
        "dados/ ficam como vieram."]),
    ("Como regenerar", [
        "Tudo de uma vez, a partir de qualquer pasta: python base_consolidada_work/scripts/rodar_pipeline.py (cerca de 12 minutos; --de <etapa> retoma do meio, "
        "--lista mostra as etapas). Requer Python 3.11 e os pacotes de base_consolidada_work/requirements.txt; passo a passo em "
        "base_consolidada_work/scripts/LEIA-ME.md.",
        "Scripts em base_consolidada_work/scripts/, nesta ordem. Dados intermediários: build_base1_mineral_ano → build_base2_municipio_ano → "
        "build_base3_empresa_mineral_ano → build_base4_mapas (camadas de mapa; a etapa mais lenta) → build_fato_08 → build_interface_12 → build_projetos_04 → "
        "build_ocorrencias_06.",
        "Montagem da planilha: write_base1 → write_base2 → write_base3 → write_base4 → write_ocorrencias_06 → write_projetos_04 → write_interface_12 → "
        f"write_fato_08 → write_governanca (gera as abas 07, 14 e 14b, este LEIA-ME e o arquivo {os.path.basename(OUT)}).",
        "Os caminhos saem de base_consolidada_work/scripts/caminhos.py: a pasta do projeto é calculada pela posição do arquivo e os intermediários vão para a pasta "
        "temporária do sistema (ou para MINERA_TMP). A ANM republica os arquivos com frequência: para reproduzir um número, use os arquivos cujo sha256 está "
        "registrado na 07."]),
]

_pos = wb.sheetnames.index("00_LEIA-ME")
del wb["00_LEIA-ME"]
leia = wb.create_sheet("00_LEIA-ME", _pos)
leia.sheet_view.showGridLines = False
leia.column_dimensions["A"].width = 4
leia.column_dimensions["B"].width = 118


def _faixa(row, texto, fundo, tamanho, cor=WHITE):
    for col in (1, 2):
        leia.cell(row=row, column=col).fill = PatternFill("solid", fgColor=fundo)
    leia.cell(row=row, column=2, value=texto).font = Font(bold=True, size=tamanho, color=cor)


def _paragrafo(row, texto, tamanho=10.5, cor="000000"):
    c = leia.cell(row=row, column=2, value=texto)
    c.font = Font(size=tamanho, color=cor)
    c.alignment = Alignment(wrap_text=True, vertical="top")
    leia.row_dimensions[row].height = 15 * max(1, -(-len(texto) // 120)) + 2


_faixa(1, f"MINERA Goiás — Bases consolidadas do Squad 1 / Estudante 1 ({VERSAO})", NAVY, 16)
leia.row_dimensions[1].height = 30
_paragrafo(2, "Base Mineral de Goiás — versão 1 · Eliel (Squad 1 / Estudante 1), com apoio do Claude Code. Todas as abas são dados reais, gerados por script a "
              "partir dos arquivos em dados/ — nenhum número foi digitado à mão.", 11, "404040")
_r = 4
for _titulo, _paras in SECOES:
    _faixa(_r, _titulo, TEAL, 12)
    _r += 1
    for _p in _paras:
        _paragrafo(_r, _p)
        _r += 1
    _r += 1
_faixa(_r, "Histórico de versões", TEAL, 12)
_paragrafo(_r + 1, "Cada nota descreve a planilha naquela versão — frases como 'ainda é maquete' valiam para a época e ficaram como registro.", 10.5, "404040")
_r += 3
for _titulo, _texto in HIST:
    _faixa(_r, _titulo, LBLUE, 11, NAVY)
    _paragrafo(_r + 1, str(_texto or ""))
    _r += 3
_paragrafo(_r, f"Última atualização: {DATA_VERSAO} · {VERSAO} · autor: Eliel (Squad 1 / Estudante 1) com apoio do Claude Code."
              + (f" Dados das fontes atualizados pelo robô de atualização em {DATA_DADOS} (robo/robo_bases.py)." if DATA_DADOS else ""), 9, "808080")

wb._sheets.sort(key=lambda s: s.title)
wb.active = 0
wb.save(OUT)
print("SALVO:", OUT)

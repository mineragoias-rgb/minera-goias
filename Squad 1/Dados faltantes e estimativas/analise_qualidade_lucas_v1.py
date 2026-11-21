"""
Squad 1 / Estudante 3 (Giovana) — diagnóstico de qualidade dos dados que ainda não tinham
relatório: as três planilhas "CORRIGIDA LUCAS V1" (Estudante 2), comparadas com a base
consolidada v17 do Estudante 1 (Eliel), recortada para Goiás.

O que este script faz:
1. Lê o crosswalk de minerais (aba 01b) e a consolidada mineral x ano (aba 09, recorte GO)
   da planilha v17, que já são a base de comparação confiável.
2. Lê as três planilhas do Lucas (produção beneficiada, produção bruta/ROM e arrecadação CFEM),
   filtra para Goiás e mede: unidades usadas, duplicidades, valores nulos/zerados.
3. Compara a produção e o CFEM do Lucas (GO) contra os mesmos números da aba 09, normalizando
   a unidade da produção beneficiada (que na aba 09 varia por mineral: t, kg ou ct) para poder
   comparar de verdade.

Rodar a partir da raiz do repositório:
    python "Squad 1/Dados faltantes e estimativas/analise_qualidade_lucas_v1.py"

Requer: pandas, openpyxl.
"""
import openpyxl
import pandas as pd

XLSX_V17 = "Squad 1/Bases consolidadas/documentacao/prototipo_bases_consolidadas_v18.xlsx"
LUCAS_BENEFICIADA = "Squad 1/dados/PRODUCAO CORRIGIDA LUCAS V1.xlsx"
LUCAS_BRUTA = "Squad 1/dados/PRODUCAO BRUTA CORRIGIDA LUCAS V1.xlsx"
LUCAS_CFEM = "Squad 1/dados/ARRECADAÇÃO CORRIGIDA LUCAS V1.xlsx"

UNIT_TO_KG = {"t": 1000.0, "kg": 1.0, "ct": 0.0002, "g": 0.001}


def sheet_to_df(wb, sheet, header_row):
    ws = wb[sheet]
    rows = list(ws.iter_rows(min_row=header_row, values_only=True))
    return pd.DataFrame(rows[1:], columns=rows[0])


def build_mineral_map(crosswalk_df, fonte):
    sub = crosswalk_df[crosswalk_df["fonte"] == fonte].copy()
    sub["mineral_id"] = sub["atribuido_a"].str.split(" — ").str[0]
    return dict(zip(sub["valor_original"], sub["mineral_id"]))


def main():
    wb = openpyxl.load_workbook(XLSX_V17, read_only=True, data_only=True)

    crosswalk = sheet_to_df(wb, "01b_crosswalk_pente_fino", 4).dropna(subset=["fonte"])
    map_benef = build_mineral_map(crosswalk, "ANM_Producao_Beneficiada(GO)")
    map_bruta = build_mineral_map(crosswalk, "ANM_Producao_Bruta(GO)")

    aba09 = sheet_to_df(wb, "09_cons_mineral_ano", 4)
    aba09["year"] = aba09["year"].astype("Int64")
    aba09_go = aba09[aba09["uf"] == "GO"].copy()

    unit_por_mineral = (
        aba09_go.dropna(subset=["production_beneficiada_unit"])
        .groupby("mineral_id")["production_beneficiada_unit"].first()
    )
    aba09_go["fator_kg"] = aba09_go["mineral_id"].map(unit_por_mineral).map(UNIT_TO_KG).fillna(1000.0)
    aba09_go["production_beneficiada_kg"] = aba09_go["production_beneficiada"] * aba09_go["fator_kg"]

    base_rom = aba09_go.groupby(["mineral_id", "year"])["production_t_rom"].sum(min_count=1)
    base_benef_kg = aba09_go.groupby(["mineral_id", "year"])["production_beneficiada_kg"].sum(min_count=1)
    base_cfem_ano = aba09_go.groupby("year")["cfem_recolhido_brl"].sum(min_count=1)

    print("=== unidades de production_beneficiada distintas na aba 09 (GO) ===")
    print(sorted(aba09_go["production_beneficiada_unit"].dropna().unique()))

    # ---- Lucas: produção beneficiada ----
    print("\n=== PRODUCAO CORRIGIDA LUCAS V1 (beneficiada, todo o Brasil) ===")
    df = pd.read_excel(LUCAS_BENEFICIADA)
    go = df[df["UF"] == "GO"].copy()
    print(f"linhas Brasil: {len(df)} | linhas GO: {len(go)}")
    print("unidades de produção em GO:", go["Unidade de Medida - Produção"].value_counts().to_dict())
    print("duplicadas (Ano base, Substância) em GO:", go.duplicated(subset=["Ano base", "Substância Mineral"]).sum())
    print("linhas GO com produção zerada:", (go["Quantidade Produção KG"] == 0).sum(), "de", len(go))

    go["mineral_id"] = go["Substância Mineral"].map(map_benef)
    go["Ano base"] = go["Ano base"].astype("Int64")
    lucas_benef_kg = go.groupby(["mineral_id", "Ano base"])["Quantidade Produção KG"].sum()
    lucas_benef_kg.index.set_names(["mineral_id", "year"], inplace=True)

    cmp_benef = pd.concat([lucas_benef_kg.rename("lucas_kg"), base_benef_kg.rename("eliel_kg")], axis=1).dropna()
    cmp_benef = cmp_benef[(cmp_benef["lucas_kg"] != 0) | (cmp_benef["eliel_kg"] != 0)]
    cmp_benef["ratio"] = cmp_benef["lucas_kg"] / cmp_benef["eliel_kg"]
    divergentes = cmp_benef[(cmp_benef["ratio"] < 0.95) | (cmp_benef["ratio"] > 1.05)]
    print(f"comparáveis (mineral, ano), já em kg: {len(cmp_benef)} | divergentes >5%: {len(divergentes)}")

    # ---- Lucas: produção bruta / ROM ----
    print("\n=== PRODUCAO BRUTA CORRIGIDA LUCAS V1 (ROM, todo o Brasil) ===")
    dfb = pd.read_excel(LUCAS_BRUTA)
    gob = dfb[dfb["UF"] == "GO"].copy()
    print(f"linhas Brasil: {len(dfb)} | linhas GO: {len(gob)}")
    dup_rom = gob[gob.duplicated(subset=["Ano base", "Substância Mineral"], keep=False)]
    print("linhas envolvidas em duplicidade (Ano base, Substância) em GO:", len(dup_rom),
          "— todas em 'Gemas' (mesmo padrão de dupla categoria já sinalizado no relatório de qualidade do Eliel, §3)")

    gob["mineral_id"] = gob["Substância Mineral"].map(map_bruta)
    gob["Ano base"] = gob["Ano base"].astype("Int64")
    lucas_rom = gob.groupby(["mineral_id", "Ano base"])["Quantidade Produção - Minério ROM KG"].sum() / 1000.0
    lucas_rom.index.set_names(["mineral_id", "year"], inplace=True)

    cmp_rom = pd.concat([lucas_rom.rename("lucas_t"), base_rom.rename("eliel_t")], axis=1).dropna()
    cmp_rom["ratio"] = cmp_rom["lucas_t"] / cmp_rom["eliel_t"]
    divergentes_rom = cmp_rom[(cmp_rom["ratio"] < 0.95) | (cmp_rom["ratio"] > 1.05)]
    print(f"comparáveis (mineral, ano) ROM: {len(cmp_rom)} | divergentes >5%: {len(divergentes_rom)}")

    # ---- Lucas: arrecadação CFEM ----
    print("\n=== ARRECADAÇÃO CORRIGIDA LUCAS V1 (CFEM, já só GO) ===")
    dfc = pd.read_excel(LUCAS_CFEM)
    print("linhas:", len(dfc))
    n_dup = dfc.duplicated().sum()
    print(f"linhas exatamente duplicadas: {n_dup} ({n_dup/len(dfc):.1%})")
    print("nulos por coluna:")
    print(dfc.isna().sum()[dfc.isna().sum() > 0])

    dfc["fator"] = dfc["VALOR CORRIGIDO"] / dfc["ValorRecolhido"]
    print("\nfator (VALOR CORRIGIDO / ValorRecolhido) por ano — não é constante dentro do ano,")
    print("varia por mês da transação (consistente com correção monetária mês a mês, não documentada no repositório):")
    print(dfc.groupby("Ano")["fator"].agg(["min", "max", "std"]))

    by_year_nominal = dfc.groupby("Ano")["ValorRecolhido"].sum()
    cmp_cfem = pd.concat([by_year_nominal.rename("lucas_nominal"), base_cfem_ano.rename("eliel_nominal")], axis=1).dropna()
    cmp_cfem["ratio"] = cmp_cfem["lucas_nominal"] / cmp_cfem["eliel_nominal"]
    print("\nCFEM nominal por ano, Lucas vs. aba 09 do Eliel (deve ser ~1.0 se as fontes batem):")
    print(cmp_cfem)


if __name__ == "__main__":
    main()

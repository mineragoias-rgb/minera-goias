# -*- coding: utf-8 -*-
"""Regras de série decididas pelo grupo — um só lugar para a Base 1 (aba 09), a interface (aba 12) e a governança.

SÉRIE DO BENEFICIADO PELO CONTIDO (decisão do Eliel em 19/11/2026; ERR_005 do repositório de erros):
o AMB mudou o conceito da produção beneficiada do nióbio em 2024 — de ~31 mil t de concentrado (≈ 50% Nb2O5) em 2023 para
3,56 Mt em 2024 e 3,28 Mt em 2025 (≈ 1,4% Nb2O5: passou a declarar o que entra na usina). A quantidade beneficiada não é
comparável antes e depois de 2024; o contido (t de Nb2O5) é. Para esses minerais:
  - aba 09: serie_beneficiada = 'contido' e a coluna contido_beneficiada_t é a série a usar (a quantidade fica como registro);
  - aba 12: a base física da linha 'beneficiada' passa a ser production_basis = 'conteudo_mineral' (t de contido).
A 08 não muda: guarda as duas medidas da fonte, célula a célula.
"""

SERIE_BENEF_POR_CONTIDO = {
    # chave do mineral (MIN_DEF da Base 1) -> nome da categoria ANM, indicação do contido e motivo
    "niobio": dict(nome="Nióbio", indicacao="Nb2O5",
                   motivo="a produção beneficiada do AMB mudou de conceito em 2024 (31 mil t de concentrado em 2023 → 3,56 Mt em 2024, teor "
                          "≈ 50% → 1,4% Nb2O5); a série comparável é o contido em Nb2O5 (decisão de 19/11/2026, ERR_005)"),
}
NOMES_SERIE_CONTIDO = {v["nome"] for v in SERIE_BENEF_POR_CONTIDO.values()}

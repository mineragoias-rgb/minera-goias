# Entregas — Squad 1

Painéis e produtos finais dos estudantes do Squad 1.

## `minerais-criticos-goias-inteligencia-mercado.html`

Central de inteligência de mercado sobre minerais críticos em Goiás (painel HTML
estático, abre direto no navegador, sem dependências além das fontes do Google Fonts).

- **Autor:** Gabriel Gonçalves — Estudante 3 do Squad 1
- **Tema:** inteligência de mercado de minerais críticos
- **Data dos dados:** setembro de 2026

### Conteúdo

| Seção | O que traz |
| --- | --- |
| Panorama GO | Terras raras (Serra Verde/Minaçu), níquel (Niquelândia e Barro Alto), nióbio e fosfato (Catalão/Ouvidor), alvos não explorados e a lacuna de processamento |
| Notícias | Seis movimentos do setor nos últimos 12 meses, cada um com link para a fonte |
| Benchmarks | Lynas, MP Materials, CBMM e CMOC — escala, margem e estrutura de capital |
| Financeiro | Receita, crescimento de lucro e valor das transações recentes de ativos em Goiás |
| Regulação | Lei estadual nº 23.597/25 — AMIC-GO, ZEMC e FEDMC |
| Riscos | Oportunidades e riscos para quem for constituir operação no estado |

As fontes consultadas estão listadas no rodapé do próprio painel.

O conteúdo deste painel também alimenta a aba **Mercado** da plataforma
(`public/mercado.js` e `public/data/mercado/mercado_v1.json`), lá em português e inglês
e com a estética do site.

## `projetos_minerais_goias.xlsx`

Base consolidada dos projetos minerais de Goiás, em três abas, para inteligência de mercado e acompanhamento do pipeline do estado.

- **Origem:** pesquisa em fontes públicas — RI, documentos regulatórios, órgãos públicos, associações setoriais e imprensa
- **Data da pesquisa:** 2026-11-06
- **Volume:** 37 projetos e 57 evidências
- **Gerado por:** `python scripts/build_projetos_base.py`, a partir da curadoria em `projetos/base_curada.json`

| Aba | O que traz |
| --- | --- |
| PROJETOS | Uma linha por empreendimento, com as 31 colunas: empresa, controladora, mineral, município, fase, maturidade, capacidade, CAPEX, cronograma, confiança, evidência e observações |
| NOTÍCIAS | Uma linha por fonte e projeto, ligada pelo ID do projeto, com título, veículo, tipo de fonte, trecho extraído, relevância e link |
| METODOLOGIA | Objetivo, abrangência, fontes, critérios de inclusão e exclusão, as sete maturidades, deduplicação, regras de CAPEX e capacidade, confiança, significado de NA e limitações |

Cada aba abre com um cabeçalho de **nome da base, origem e última atualização**. Campo sem informação aparece como **NA** — nunca estimativa.

Regras, ressalvas e o caminho para fechar as lacunas estão em `projetos/README.md`. A aba **Base de dados** do painel lista esta e as demais
bases do sistema, cada uma com origem e data.

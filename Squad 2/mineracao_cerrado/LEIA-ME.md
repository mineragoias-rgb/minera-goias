# Mineração e Cerrado em Goiás (Squad 2)

Material do Squad 2 (novembro de 2026) sobre o impacto territorial da mineração: quanto de vegetação nativa a mineração tirou de
Goiás entre 1985 e 2025, quanto CO₂ isso representa e o risco ambiental dos 1.046 projetos do Radar até 2040.

| Arquivo | Conteúdo |
|---|---|
| `relatorio_mineracao_cerrado_GO.html` | Relatório autocontido (dados e gráficos embutidos): série 1985–2025 da área minerada, emissões diretas (biomassa e solo), estudo de evento do entorno das minas, títulos e defasagem até a lavra, cenários 2026–2040, risco por projeto, método e limitações |
| `GO_radar_risco_ambiental.geojson` | 1.046 projetos (polígono do título ANM) com área, vegetação nativa, carbono do solo, desmatamento e emissão potenciais (p05/p50/p95, até 2035), impacto, probabilidade e risco |

**Separado da previsão de demanda de energia.** Mede impacto territorial, não consumo. No site, fica na aba própria
**Território e emissões**.

**Acesso.** Os arquivos trazem nome de projeto e de empresa titular; por isso não vão para `public/` (servido sem login). O site os
entrega por `/api/territorio/relatorio` e `/api/territorio/risco.geojson`, atrás da sessão (`Squad 3/backend/territorio.py`).
Pessoas físicas aparecem só como "Titulares pessoa física (nomes não publicados)"; `tests/test_territorio.py` confere que não há CPF
na camada.

**Atualização.** Para publicar uma versão nova, substitua os dois arquivos com os mesmos nomes. Fontes declaradas no relatório:
MapBiomas Coleção 11 e MapBiomas Solo Coleção 2, SEEG 12 e títulos da ANM (aba 04 da base consolidada do Squad 1, pesquisa, CFEM).

## Verificação e reprodução dos artefatos publicados

Na raiz do repositório, execute:

```bash
python "Squad 2/mineracao_cerrado/validate_territorio.py" --summary
```

O comando verifica que o relatório HTML, o objeto de dados embutido que a aba lê e a camada GeoJSON estão presentes e coerentes; também verifica que a camada contém 1.046 projetos e não expõe sequências em formato de CPF.

O modelo elétrico do Squad 2 é reproduzível integralmente pelos comandos em `Squad 2/modello_reale/README.md`. Esta análise territorial é complementar: o repositório preserva os artefatos finais, as fontes, o método e a verificação dos outputs, mas não inclui o pipeline geoespacial original que processou os rasters do MapBiomas e os cálculos intermediários. Portanto, este comando reproduz a **verificação e a publicação dos resultados**, não o processamento espacial original pixel a pixel.

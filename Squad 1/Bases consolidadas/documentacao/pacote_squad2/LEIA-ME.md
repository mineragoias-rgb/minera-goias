# Pacote da aba 12 para o Squad 2 — produção por mineral, ano e operação (v17)

Squad 1 / Estudante 1 → Squad 2. Gerado por `gerar_pacote_squad2.py` a partir de `prototipo_bases_consolidadas_v17.xlsx`, aba
`12_interface_squad1_squad2`. Todos os números abaixo saem da planilha; rodar o script de novo depois de uma versão nova atualiza o pacote.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `interface_squad1_squad2.csv` | a aba 12 inteira: 5.576 linhas, as 29 colunas da aba e `versao_base` |
| `dicionario_interface_squad1_squad2.csv` | um campo por linha (descrição, unidade, fonte, % vazio, exemplo) e o campo correspondente no contrato do motor |
| `rascunho_mensagem_squad2.md` | rascunho da mensagem pedindo a confirmação do formato — **não enviado** |

Os CSV seguem a convenção dos exemplos do Squad 2 em `Squad 2/data/demo/`: vírgula como separador, UTF-8 com BOM e ponto decimal. Campos
vazios ficam vazios (nada foi preenchido com zero).

## Dois níveis que não se somam

| `nivel_agregacao` | Linhas | Anos | `valor_observado_estimado` | O que é |
|---|---:|---|---|---|
| `estado` | 745 | 2010–2025 | observado: 745 | produção de Goiás no AMB por mineral, ano e base (ROM ou beneficiada), em t |
| `operacao` | 4.831 | 2022–2025 | estimado: 4.831 | o total do estado rateado entre 931 processos pela participação de cada um na CFEM recolhida (R$) do mineral no ano |

- Em 153 das 181 combinações de mineral, ano e base de 2022–2025 com produção no estado, a soma das operações é igual ao total do estado (diferença até 0,1%); em 28 não há abertura por operação (1,4% da produção do estado nesses anos — Areias Industriais: 8; Feldspato, Leucita e Nefelina-Sienito: 7; Talco e outras Cargas Minerais: 6; Diamante: 3; Monazita e Terras-Raras: 2; Bário: 1; Fluorita e Criolita: 1; o motivo fica em `observacao` na linha do estado).
- **Sem `operation_id`:** 457 linhas do nível operação (112 processos, 18,3% da
  produção estimada) são de processos que recolhem CFEM mas não têm poligonal no SIGMINE de Goiás. O `processo_anm` identifica essas
  linhas; a lista está em `../operacoes_sem_coordenadas.csv` e a explicação em `../nota_squad2_operacoes_sem_coordenadas.md`.
- **Titular não identificado:** 439 linhas do nível operação têm `company_id = COM_NAO_IDENTIFICADO`
  (17,8% da produção estimada).
- **Base de produção:** 2.875 linhas em `ROM` e 2.701 em `beneficiada`; 29 dos 33 minerais têm as duas bases no nível estado, e cada série deve usar uma só (só uma base: Caulim (ROM), Fluorita e Criolita (beneficiada), Quartzo (Cristal) e outros Piezelétricos (ROM) e Turfa (ROM)).
- **Estimativa:** a ANM não publica produção por operação. As linhas de operação trazem `metodo_estimacao` e a faixa
  `erro_estimativa_intervalo` (rateio por R$ × rateio pela quantidade comercializada da CFEM, que também está em `production_t_rateio_por_t`).
- **Status de validação:** `alerta_producao_repetida` (estado): 4; `valido` (estado): 741; `estimativa_com_alerta_09c` (operacao): 62; `estimativa_conferida_no_total` (operacao): 4.769.
- `project_id` fica vazio até o Radar de Projetos (Estudante 2). Consumo de energia não vem do Squad 1.

## Correspondência com o contrato do motor

Contrato em `Squad 2/README (1).md`, seção "Produção histórica (`production_history`)":

| Campo do motor | Obrigatório | Campo da aba 12 | Situação |
|---|---|---|---|
| `mineral_id` | Sim | `mineral_id` | pronto (33 minerais, catálogo na aba 01) |
| `company_id` | Sim | `company_id` | pronto no nível operação; vazio no nível estado |
| `operation_id` | Sim | `operation_id` | vazio em 457 linhas do nível operação; `processo_anm` pode servir de identificador |
| `year` | Sim | `year` | pronto |
| `production_t` | Sim | `production_t` | pronto |
| `production_basis` | Sim | `production_basis` | a aba usa `ROM` e `beneficiada`; o motor escreve `rom`, `beneficiada` e `conteudo_mineral` |
| `data_nature` | Sim | `valor_observado_estimado` | `observado` no nível estado, `estimado` no nível operação |
| `source_id` | Sim | `source_id` | uma fonte no nível estado; várias, separadas por `;`, no nível operação |

Os catálogos `minerals` e `sources` do motor correspondem às abas 01 e 07 da planilha. `projects` depende do Radar de Projetos (a aba 04 é a
camada ANM). `energy_intensity` não vem do Squad 1.

## Pontos a confirmar com o Squad 2

1. **Nível:** o motor usa a produção estimada por operação (2022–2025) ou o total observado do estado (2010–2025)?
2. **`operation_id` vazio:** usar `processo_anm` como identificador dessas 457 linhas, agrupar ou deixar de fora?
3. **Base:** qual base (`rom` ou `beneficiada`) por mineral, compatível com a intensidade energética; e se o valor vai em minúsculas, como no contrato.
4. **Incerteza:** receber `erro_estimativa_intervalo` e `production_t_rateio_por_t` junto, já que o contrato não tem campo de erro?
5. **Entrega:** CSV no GitHub, como este pacote, ou leitura direta do banco do site?

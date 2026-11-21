# Como atualizar a base consolidada com dados novos sem repetir os erros

Passo a passo para quem vai trocar um arquivo de `Squad 1/Dados brutos/` (CFEM nova, Anuário Mineral novo, Cadastro Mineiro
do mês…) e refazer a planilha `documentacao/prototipo_bases_consolidadas_v19.xlsx`. Foi escrito para um colega do grupo seguir
sem ajuda. Os comandos são rodados da raiz do repositório e precisam do Python 3.11 com os pacotes de
`base_consolidada_work/requirements.txt` (os mesmos do pipeline).

O processo tem duas travas automáticas. Elas fazem o pipeline terminar com código **3** e uma mensagem dizendo o que fazer:

1. **Antes de rodar:** um arquivo bruto mudou de bytes sem uma nova data de acesso (`manifesto_brutos.py`, erro ERR_040).
2. **No fim:** uma verificação da aba 14b de nível "bloqueia" deu ALERTA acima do que o grupo já aceitou (`travas.py`).

Quando trava, a planilha fica gravada para inspeção, mas **não pode ser publicada**. O robô do GitHub (`robo-bases.yml`) usa as
mesmas duas travas.

## 1. Baixar a base nova

O jeito recomendado é o robô, que baixa, confere a forma do arquivo, recorta Goiás, registra a data e o sha256:

```
python robo/robo_bases.py --so CFEM            # só a CFEM; outras fontes: ids em robo/fontes.json
python robo/robo_bases.py --checar             # sem rede: os arquivos estão no formato esperado?
```

Se baixar à mão:

1. Salve o arquivo em `Squad 1/Dados brutos/<pasta da fonte>/` **com o mesmo nome** do arquivo que ele substitui.
2. Registre a data do download (AAAA-MM-DD) em `Squad 1/Dados brutos/datas_de_acesso.json`, na linha do arquivo. Use o
   caminho lógico, por exemplo `dados/ANM/cfem/CFEM_Arrecadacao_2022_2026.csv`.
3. Atualize o tamanho e o sha256 na lista de arquivos do `Squad 1/Dados brutos/LEIA-ME.md`. Para calcular o sha256:
   `python -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" <arquivo>`.
4. Rode `python robo/robo_bases.py --checar` e confira que não aparece nenhum problema.

## 2. Ver o que mudou nos brutos (manifesto)

```
python "Squad 1/Bases consolidadas/base_consolidada_work/scripts/manifesto_brutos.py"
```

O comando compara os brutos de hoje com `documentacao/manifesto_brutos.json`. Esse manifesto registra a fonte, o arquivo, a data
de acesso, o tamanho e o sha256 de cada arquivo que gerou a planilha atual. A saída lista os arquivos novos, removidos e alterados.

**Trava (ERR_040):** um arquivo mudou de bytes e a data de acesso continua a mesma. Ou faltou registrar a data do download novo
(passo 1), ou o arquivo foi alterado sem querer. Isso acontece com o git trocando a quebra de linha, com uma edição à mão ou com
uma cópia errada. No segundo caso, volte o arquivo com `git checkout -- "<arquivo>"`.

## 3. Rodar o pipeline

```
python "Squad 1/Bases consolidadas/base_consolidada_work/scripts/rodar_pipeline.py"
```

O pipeline leva uns 15 minutos e faz, em ordem:

1. confere o manifesto (trava 1);
2. guarda uma cópia da planilha atual (a "anterior");
3. roda as 19 etapas;
4. gera `documentacao/relatorio_diferencas.md` comparando a planilha anterior com a nova;
5. aplica as travas da 14b (trava 2);
6. se nada travou, grava o manifesto novo.

| Código de saída | Significado |
|---|---|
| 0 | Pode seguir. Leia os avisos. |
| 3 | **Travou.** Veja o passo 5. |
| outro | Uma etapa falhou. O log diz qual; corrija e retome com `--de <etapa>`. |

## 4. Ler o relatório de diferenças

O relatório fica em `documentacao/relatorio_diferencas.md`. Para comparar duas planilhas quaisquer, rode
`relatorio_diferencas.py ANTES.xlsx DEPOIS.xlsx --saida arquivo.md --limiar 5`.

O relatório tem cinco seções:

1. **Dados brutos:** o que mudou desde o manifesto, com a data de acesso e o tamanho antes e depois.
2. **Linhas por aba:** abas que ganharam ou perderam linhas, abas novas e abas que sumiram. Uma aba de dados que perde muitas
   linhas é suspeita: veja se o arquivo novo veio cortado.
3. **IDs que entraram e saíram** das dimensões 01 a 06 (minerais, empresas, operações, projetos, municípios, ocorrências).
   Um mineral ou município que sumiu quase sempre é erro.
4. **Totais por substância e ano** na aba 09 (mineral × UF × ano) e na aba 12 (mineral × nível × base × ano, a entrega ao
   Squad 2): combinações que entraram ou saíram, valores que mudaram mais que o limiar (padrão 5%) e os totais de Goiás por
   ano (ROM e CFEM). Uma mudança que só redistribui a produção entre operações não altera esses totais; ela aparece como
   linhas a mais ou a menos na aba 12 (seção 2). Ano novo entrando é esperado. Ano antigo mudando é a ANM republicando dados
   preliminares (ERR_010): registre no commit.
5. **Aba 14b e travas:** verificações que mudaram de status e a decisão de cada uma (trava, aviso ou aceito).

## 5. Se travou

Para cada linha `TRAVA:` da saída:

- **Verificação estrutural ou de governança** (integridade referencial, nomes de coluna, LGPD, conciliação 08 → 09/10/11,
  §3 da Entrega…): é erro do dado ou do pipeline. Abra a aba 14b, leia o resultado, corrija e rode de novo.
- **"Repositório de erros (ERR_…)" com ocorrência nova:** a base nova trouxe um caso novo de um erro conhecido, como um contido
  incoerente ou uma quebra de série. O resultado da 14b lista as ocorrências novas, e as abas 15d a 15f mostram o detalhe.
  1. Confira cada ocorrência na fonte (linha do CSV citada na 15d).
  2. Se for erro do dado, corrija a regra no pipeline e registre o erro no catálogo (`gerar_repositorio_erros.py`).
  3. Se for legítima (o dado está certo), registre-a como conhecida e retome a partir do repositório de erros:
     ```
     python "Squad 1/Bases consolidadas/base_consolidada_work/scripts/gerar_repositorio_erros.py" --atualizar-conhecidos
     python "Squad 1/Bases consolidadas/base_consolidada_work/scripts/rodar_pipeline.py" --de write_repositorio_erros_into_workbook
     ```
  4. Explique no commit por que a ocorrência é legítima. O precedente é o nióbio de 2024: a quebra de série era uma mudança de
     conceito da ANM e virou regra (série pelo contido).
- **Alerta aceito que cresceu** ("acima do aceito"): o número de casos passou do que o grupo aceitou. Os aceitos ficam em
  `base_consolidada_work/scripts/erros_conhecidos.json` → `alertas_aceitos`, com o n aceito e o motivo. Se o aumento estiver
  conferido, suba o `n_aceito` e complete o motivo. Isso é **decisão do grupo**, como o bário × nióbio no ROM de 2023, que
  continua como alerta, sem correção por inferência.
- **Verificação nova sem nível:** quem criou a verificação precisa classificá-la em `travas.py` (lista `CHECAGENS`) como
  `bloqueia` ou `avisa`, com o motivo.

Os avisos (`aviso:`) não travam, mas devem ser lidos antes de publicar.

## 6. Depois que passou

1. Refaça o repositório de erros avulso:
   `python "Squad 1/Bases consolidadas/base_consolidada_work/scripts/gerar_repositorio_erros.py"`, que gera
   `Squad 1/Auditoria e qualidade/repositorio_erros.xlsx` e `REPOSITORIO_ERROS.md`.
2. Faça o commit dos brutos, da planilha, do manifesto e do relatório de diferenças, e depois refaça os derivados (pacote do
   Squad 2, panorama, simulador, previsão…), com os testes de cada um:
   `python scripts/atualizar_derivados.py`. Esse comando exige a árvore sem saídas pendentes, por isso o commit vem antes.
3. Refaça o atlas e o Radar, que dependem do GeoPackage do pipeline:
   - `python scripts/build_atlas_base.py --base "Squad 1/Bases consolidadas"`;
   - `python scripts/build_projetos_minerais_goias.py`.
4. Rode `python -m unittest discover tests`.

## 7. Publicar (só com o OK do Eliel)

O `main` vai direto para o site (labfgv.com.br), que importa todo xlsx e csv do repositório. Por isso:

1. Peça o OK do Eliel antes do push.
2. Faça um backup local do `main` antes do push. O repositório não deixa criar branch, então use um bundle:
   `git bundle create main-AAAAMMDD-antes-<assunto>.bundle <último backup>..origin/main`.
3. Dê o push, confira o CI (aba Actions do GitHub) e confira o site em `https://labfgv.com.br/api/public/summary`.

Para uma **versão nova** da planilha (v19 → v20), o nome do arquivo muda e as referências a ele precisam mudar junto: workflows,
scripts do site, do Squad 2, LEIA-MEs, `public/i18n.js` e `public/metodologia.js`. Procure com
`git grep "consolidadas_v19"`. O robô não cria versão: refaz a versão atual no lugar.

## Nível de cada erro do repositório

Nesta tabela, "trava" quer dizer que o pipeline e o robô param; "só avisa" quer dizer que o erro aparece no relatório sem
travar. Ela é gerada por `python travas.py --tabela`: se mudar `travas.py`, gere a tabela de novo e cole aqui.

| Erro | Nível | Onde é checado | Por quê |
|---|---|---|---|
| ERR_001 | só avisa | 14b: 08: mesma tonelagem de produção… | co-produto ou mesma declaração em duas categorias: mantido e sinalizado (inclui bário × nióbio no ROM de 2023, sem correção) |
| ERR_002 | só avisa | 14b: 08: mesma tonelagem de produção… | co-produto ou mesma declaração em duas categorias: mantido e sinalizado (inclui bário × nióbio no ROM de 2023, sem correção) |
| ERR_003 | trava | 14b: Repositório de erros (ERR_003/004)… | contido incoerente novo no AMB de GO: conferir antes de publicar |
| ERR_004 | trava | 14b: Repositório de erros (ERR_003/004)… | contido incoerente novo no AMB de GO: conferir antes de publicar |
| ERR_005 | trava | 14b: 08 → 09/10/11…; 14b: Repositório de erros (ERR_005)…; 14b: 12: nível estado = produção de GO… | as abas consolidadas têm de ser a soma da 08; quebra de série nova (o caso do nióbio em 2024): conferir o conceito antes de publicar; entrega ao Squad 2 tem de fechar com a 08 |
| ERR_006 | só avisa | 14b: Processos com quantidade na CFEM implausível… | mantidos na soma e sinalizados na 09c, de propósito |
| ERR_007 | só avisa | 14b: Repositório de erros (ERR_007)… | lacuna é fato da fonte (a ANM não publicou o mineral no ano) |
| ERR_008 | sem checagem automática | — | contido sem indicação é o padrão da fonte (C3 é só informativo na 15d); não há valor certo para comparar |
| ERR_009 | só avisa | 14b: Repositório de erros (ERR_043–045)… | comparação econômica: todo ano novo traz pares sem correspondência; conferir, mas não trava |
| ERR_010 | sem checagem automática | — | a ANM republica dados preliminares: não é erro do dado novo; o relatório de diferenças mostra o que mudou |
| ERR_011 | trava | 14b: Quantidade comercializada da CFEM… | unidade misturada ou valor corrompido sem tratamento distorce as somas |
| ERR_012 | trava | 14b: Quantidade comercializada da CFEM… | unidade misturada ou valor corrompido sem tratamento distorce as somas |
| ERR_013 | trava | 14b: Repositório de erros (ERR_013)… | CNPJ em notação científica não identifica a empresa (abas 02 e 11) |
| ERR_014 | trava | 14b: 08 → 09/10/11… | as abas consolidadas têm de ser a soma da 08 |
| ERR_015 | só avisa | 14b: Plausibilidade: CFEM…; 14b: Processos com quantidade na CFEM implausível… | sinalizado de propósito: a quantidade da CFEM é declaração do contribuinte; mantidos na soma e sinalizados na 09c, de propósito |
| ERR_016 | só avisa | 14b: Processos com quantidade na CFEM implausível… | mantidos na soma e sinalizados na 09c, de propósito |
| ERR_017 | trava | 14b: 08: cada célula numérica das fontes… | célula da fonte perdida ou contada duas vezes |
| ERR_018 | só avisa | 14b: Rochas na CFEM… | informativa: de onde veio a categoria das rochas |
| ERR_019 | sem checagem automática | — | o último ano da CFEM é parcial por natureza; o pipeline marca periodo_referencia, não há o que travar |
| ERR_020 | trava | 14b: Integridade referencial… | chave sem dimensão = número que não soma em lugar nenhum |
| ERR_021 | trava | 14b: Integridade referencial… | chave sem dimensão = número que não soma em lugar nenhum |
| ERR_022 | sem checagem automática | — | característica da fonte (dados abertos só com processos ativos) |
| ERR_023 | sem checagem automática | — | característica da fonte (jurisdição regional da ANM); tratada pelo recorte por município |
| ERR_024 | trava | 14b: Repositório de erros (ERR_024)… | linha de Goiás descartada em silêncio pelo leitor do Cadastro Mineiro |
| ERR_025 | trava | 14b: LGPD… | CPF completo não pode ser publicado |
| ERR_026 | sem checagem automática | — | detectado comparando dois arranjos de dados (v16), à mão; não há assinatura num arquivo só |
| ERR_027 | sem checagem automática | — | geometria (UF do SIGMINE) — auditada na 13b, sem assinatura simples para travar |
| ERR_028 | sem checagem automática | — | geometria (autointerseção) — corrigida no pipeline e auditada na 13b |
| ERR_029 | sem checagem automática | — | geometria × cadastro (desmembramentos) — auditada na 13b |
| ERR_030 | trava | 14b: 04: cada processo vivo… | processo vivo fora de projeto ou em dois |
| ERR_031 | sem checagem automática | — | geometria (simplificação) — auditada na 13b |
| ERR_032 | só avisa | 14b: 06: campos do RECMIN fora da aba… | informativa: campos sem informação na fonte |
| ERR_033 | trava | 14b: 06: substâncias → mineral_ids… | substância sem decisão ou mineral novo fora da 01 |
| ERR_034 | sem checagem automática | — | regra de leitura do SIDRA (linha da UF), conferida na montagem da 05/07 |
| ERR_035 | trava | 14b: Colunas sem descrição no dicionário… | todo campo novo precisa estar no dicionário 14 |
| ERR_036 | sem checagem automática | — | geometria (centroide) — auditada na 13b |
| ERR_037 | só avisa | 14b: IMB (Goiás em Dados) × AMB… | checagem cruzada informativa |
| ERR_038 | sem checagem automática | — | CCEE não entra na planilha consolidada |
| ERR_039 | sem checagem automática | — | reprodutibilidade: se vê rodando duas vezes e comparando (relatório de diferenças vazio) |
| ERR_040 | trava | manifesto dos brutos (manifesto_brutos.py) | arquivo bruto mudou de bytes sem nova data de acesso (download não registrado ou quebra de linha trocada) |
| ERR_041 | trava | 14b: 08: campos de governança por linha… | fonte, URL e data de cada linha (Entrega §3) |
| ERR_042 | trava | 14b: Cabeçalhos renomeados…; 14b: Nomes de coluna fora do padrão…; 14b: Nomes de coluna duplicados… | cabeçalho fora do contrato quebra quem lê a planilha (Squad 2, site); estrutura da planilha |
| ERR_043 | só avisa | 14b: Repositório de erros (ERR_043–045)… | comparação econômica: todo ano novo traz pares sem correspondência; conferir, mas não trava |
| ERR_044 | só avisa | 14b: Repositório de erros (ERR_043–045)… | comparação econômica: todo ano novo traz pares sem correspondência; conferir, mas não trava |
| ERR_045 | só avisa | 14b: Repositório de erros (ERR_043–045)… | comparação econômica: todo ano novo traz pares sem correspondência; conferir, mas não trava |

Resumo: 18 erros travam, 13 só avisam e 14 não têm checagem automática (o motivo de cada um está na tabela).

### Alertas aceitos na base atual (v19)

Estes são os quatro ALERTA que a v19 já tem. Eles estão registrados em `erros_conhecidos.json` → `alertas_aceitos` e não travam
enquanto o n não passar do aceito.

| Verificação da 14b | n aceito | Nível se passar | Motivo |
|---|---:|---|---|
| Arquivos de dados/ sem source_id no catálogo 07 | 12 | trava | Só no GitHub: fontes de energia (ANEEL, EPE, ONS), planilha do Lucas Maia e `.gitattributes` ainda fora do catálogo 07. |
| Plausibilidade: CFEM ÷ AMB fora de 0,05–2× | 30 | avisa | A quantidade da CFEM é declaração do contribuinte: fica sinalizada, sem correção (ERR_015). |
| Processos com quantidade na CFEM implausível (09c) | 37 | avisa | Os processos ficam na soma e são sinalizados na 09c (ERR_015, ERR_016). |
| 08: mesma tonelagem em linhas diferentes | 170 | avisa | Co-produto ou mesma declaração em duas categorias (ERR_001, ERR_002). **Inclui bário × nióbio no ROM de 2023**: alerta mantido sem correção por inferência, por decisão do grupo. |

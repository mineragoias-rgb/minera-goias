# Continuidade do Minera Goiás

## Produto e ambiente

O site https://labfgv.com.br tem identidade própria em azul e branco, landing page pública, login individual e painel protegido. Não utiliza logotipos da FGV. O painel mostra **contagens de registros** das parcelas de carga CCEE em Goiás por mês, município e atividade. Não apresenta essas contagens como consumo, produção mineral ou empresas únicas. A base CCEE inclui atividades não minerais; o filtro permite recortar o ramo. Os dados ainda estão em validação técnica.

- GitHub: mineragoias-rgb/minera-goias, branch de produção `main`.
- VPS: 187.77.3.27, Ubuntu, Nginx, systemd, Python 3.10 e MySQL.
- API: `Squad 3/backend/main.py`, FastAPI, porta interna 18141.
- Interface: HTML/CSS/JS sem build em `public/`; `index.html`, `login.html`, `painel.html`.
- Banco de fontes: MySQL `db_minera_goias`, tabelas `ingest_*`; conta da API somente leitura.
- Contas e sessões: SQLite privado `/srv/minera-goias/shared/auth.sqlite`, persistente entre versões e acessível somente ao serviço. Não é o banco dos dados de pesquisa.

## Publicação automática

A VPS consulta `main` a cada **2 minutos**. Instala dependências, testa a API na porta 18142 e troca `current` somente após sucesso. O importador consulta a versão publicada a cada **5 minutos**. Acrescente o tempo de processamento a esses intervalos. GitHub Actions executa os testes, mas **o deploy atual não espera pelo Actions**; revise e rode os testes antes de enviar para `main`.

```sh
python -m pip install -r deploy/requirements-vps.txt httpx==0.28.1
python -m unittest discover -s tests -p test_web.py -v
python -m unittest discover -s tests -p test_ingestion.py -v
node --check public/painel.js
node --check public/login.js
```

`public/` é a única pasta exposta pelo Nginx. Arquivos de fonte, senhas, sessões, planilhas e configurações não devem ser copiados para ela. Mudanças nos scripts administrativos em `deploy/` e no importador instalado exigem reinstalação administrativa; não são aplicadas pelo deploy da API.

## Autenticação e perfis

`auth.py` mantém hashes scrypt com salt individual. Sessões de oito horas usam tokens aleatórios, armazenados como hash no servidor e cookie Secure, HttpOnly e SameSite=Strict no navegador. Requisições autenticadas que alteram estado exigem token CSRF. Há limite de tentativas por IP (10 em 15 minutos). Não há cadastro público. A troca de senha encerra todas as sessões. A desativação de uma conta também revoga sessões.

- Usuário: consultar painel, catálogo, exportar resumo agregado e mudar sua senha.
- Administrador: as mesmas funções, criar contas e ativar/desativar outras contas.
- Toda conta nova deve alterar a senha inicial antes de consultar dados.
- Contas iniciais: `admin` e `usuario`. Senhas aleatórias são entregues fora do GitHub.
- Recuperação de senha: administrador do servidor usa a ferramenta abaixo. Não há recuperação por e-mail implementada.

```sh
# Execute na VPS. A saída contém senha: entregue em canal privado, nunca em commit/log público.
sudo -u minera-goias /srv/minera-goias/current/.venv/bin/python \
  /srv/minera-goias/current/deploy/manage-users.py --reset usuario
```

`AUTH_DB_PATH` permite armazenamento alternativo. `COOKIE_SECURE=0` serve apenas para testes locais HTTP. Em produção, o padrão é cookie seguro. A API antiga `/api/projetos`, `/api/projecoes`, `/api/fontes` continua pública para compatibilidade; o painel e administração novos exigem sessão. Não publique dados pessoais nesses endpoints antigos.

## Dados e limites

`dashboard.py` consulta a versão atual do MySQL, sem expor CPF/CNPJ ou nomes empresariais no painel. O resumo público contém apenas contagens do acervo. O catálogo autenticado mostra nomes de arquivos, abas e alertas. Séries CCEE limitadas às fontes 2024–2026 presentes no repositório. Adicionar novos anos exige atualizar a validação da API e o seletor. A API lê as linhas de um ano para agregá-las em memória; com crescimento da base, migrar agregações para SQL/materialização e cache invalidado pelo commit.

Fontes corrigidas e originais podem se sobrepor. O acervo não é uma tabela analítica única. O mapeamento validado para `tb_projetos` e `tb_projecoes` ainda está pendente. Não rodar `seed.sql` de demonstração em produção.

## Operação e próximos passos

```sh
systemctl status minera-goias minera-goias-deploy.timer minera-goias-ingestion.timer
journalctl -u minera-goias-deploy.service -n 50 --no-pager
journalctl -u minera-goias-ingestion.service -n 50 --no-pager
readlink /srv/minera-goias/current
```

A instalação tem backup pontual pré-ingestão, não uma política recorrente completa. Configurar backups recorrentes do MySQL e do SQLite de autenticação usando backup consistente, armazenamento fora da VPS e teste de restauração. Outros próximos passos: validar unidades e chaves das bases, integrar os modelos científicos e mapas reais, tornar CI requisito do deploy, adicionar testes de navegador ao CI, auditoria administrativa e MFA se o uso exigir. A interface usa Google Fonts com fallback local; não depende de bibliotecas de gráficos externas.

Consulte `METODOLOGIA.md` para o que cada indicador mede e em que unidade, e `deploy/README.md` e `ingestion/README.md` para publicação e importação. Não altere outros projetos hospedados na VPS. Configurações e senhas permanecem fora do repositório.

## Integração da atualização ANM da equipe

Em 10/09/2026 foram integrados os commits `db532a0` e `48dabce` da equipe. O novo `schema.sql` foi preservado. A API detecta a coluna `processo_anm` para consultar o modelo novo ou o legado instalado na VPS. O deploy não aplica o novo SQL automaticamente. Antes de migrar, revisar diferenças, fazer backup e transformar os dados explicitamente. O endpoint público de projetos não retorna `documento_cnpj_cpf`; ele é usado somente nas junções internas do modelo novo.

## Atlas Leaflet e artefatos Eliel / Rodrigo

Integração de 10/09/2026: seção `Atlas mineral` em `public/atlas.js`, `atlas.css` e `painel.html`, com seis camadas, radar pesquisável, exportação CSV e séries históricas. Leaflet 1.9.4 local, renderização Canvas e criação de polígonos em lotes para não bloquear a interface. A landing mantém o layout e usa linguagem gerencial.

Endpoints autenticados em `Squad 3/backend/atlas.py`; pacote de dados e limitações em `data/atlas/README.md`. Desde 13/09/2026 o atlas é um retrato da base consolidada do Squad 1 (v17), gerado por `scripts/build_atlas_base.py` (municípios, CFEM, quantidade comercializada, séries, processos, projetos da aba 04, ocorrências do RECMIN da aba 06 e os gráficos de `charts`); energia e barragens seguem do retrato `eliel.html`. Novos retratos exigem executar o script, revisar o diff dos dados, rodar `tests/test_atlas.py` e enviar para main. Eles não são reconstruídos pelo importador MySQL. O protótipo Rodrigo forneceu referências de navegação/filtros, sem seus dados fictícios. Os dados do atlas têm origem e períodos explícitos e não são comparados automaticamente com o banco CCEE.

## Panorama (aba do painel)

Aba `Panorama` entre o Atlas e o Radar (`public/panorama.js`, `panorama-charts.js`, `panorama-cards1..4.js`, `panorama.css`), servida por `Squad 3/backend/panorama.py` em `/api/panorama`. Refaz os gráficos e tabelas do *Panorama da Mineração de Goiás* com a base consolidada do Squad 1 e os brutos do repositório; o navegador filtra por ano, mês, município, mineral, titular, fase, gasto em pesquisa e ramo da CCEE. O pacote `data/panorama/panorama.json` é gerado por `python scripts/build_panorama_base.py` (limitações e fontes em `data/panorama/README.md`) e conferido por `tests/test_panorama.py`. Energia por município e barragens vêm de `/api/atlas`.

## Preços e custo de energia (aba do Panorama)

Aba **Preços e custo de energia** dentro do Panorama (`public/panorama-cards4.js`), servida por `Squad 3/backend/precos.py` em
`/api/precos`. Junta o consumo observado das cargas da CCEE com título minerário na base do Squad 1 com a projeção de preço
(R$/MWh) e de custo (R$) de 2027 a 2040, e publica o custo como matriz cenário de preço × cenário de demanda.

**Nenhum preço de energia existe no repositório**: PLD, tarifa homologada, preço de leilão e preço de contrato ainda não foram
coletados. Todo preço da aba é premissa do Squad 2, marcada `premissa_ilustrativa` linha por linha e avisada em cada quadro,
a substituir pelas fontes listadas em `Squad 2/precos/premissas/fontes_preco_energia.csv`. Antes de qualquer entrega externa,
trocar as premissas pelas séries oficiais.

O pacote `data/precos/precos.json` é gerado por `python scripts/build_precos_energia.py` (premissas em
`Squad 2/precos/premissas/`, saídas em CSV em `Squad 2/precos/saidas/`, método e contrato em `Squad 2/precos/README.md`,
limitações em `data/precos/README.md`) e conferido por `tests/test_precos.py`. Regenerar depois de editar qualquer premissa.

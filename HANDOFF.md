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

Consulte `deploy/README.md` e `ingestion/README.md`. Não altere outros projetos hospedados na VPS. Configurações e senhas permanecem fora do repositório.

# Publicação na VPS

O ambiente de `labfgv.com.br` acompanha `main` deste repositório. A VPS consulta o GitHub a cada dois minutos; não é necessário configurar chaves administrativas ou secrets no GitHub.

## Fluxo

1. Atualize a API em `Squad 3/backend/` ou a interface estática em `public/` e envie para `main`.
2. A VPS baixa o commit para uma pasta de versão independente, instala `deploy/requirements-vps.txt` e testa as três rotas contra o banco.
3. Se os testes passarem, troca a versão e reinicia somente a API do Minera Goiás.
4. Se a versão falhar antes da troca, o site atual permanece. Se falhar após a troca, a versão anterior é restaurada.

A landing page está em `public/index.html`, com login em `public/login.html` e painel em `public/painel.html`. Consulte `HANDOFF.md` para autenticação, testes e continuidade. O diretório público é o único servido pelo Nginx: planilhas, código e configurações não ficam expostos como arquivos web.

## Banco e dados

- Banco exclusivo: `db_minera_goias`.
- A API utiliza um usuário MySQL exclusivo, limitado a leitura desse banco.
- A estrutura é criada uma vez a partir de `Squad 3/database/schema.sql`.
- O `seed.sql` contém dados fictícios e **não é aplicado** neste ambiente.
- Atualizações de código não executam SQL nem sobrescrevem as tabelas de negócio. A rotina separada descrita em `ingestion/README.md` importa arquivos novos/alterados para as tabelas de origem `ingest_*`, mantendo histórico. Migrações e transformações para as tabelas de negócio precisam de mapeamento revisado e backup.
- Segredos permanecem na VPS, em `/etc/minera-goias.env`, fora do Git.

## Administração na VPS

```sh
systemctl status minera-goias minera-goias-deploy.timer
journalctl -u minera-goias-deploy.service -n 80
systemctl start minera-goias-deploy.service
systemctl stop minera-goias-deploy.timer # pausar atualizações
readlink /srv/minera-goias/current
```

As versões ficam em `/srv/minera-goias/releases/`; arquivos persistentes ficam em `/srv/minera-goias/shared/`. A API escuta apenas em `127.0.0.1:18141`; a porta `18142` serve exclusivamente para testar versões candidatas localmente.

Os scripts e units deste diretório são instalados como arquivos de administração pertencentes a root. Mudá-los no GitHub **não** altera automaticamente a infraestrutura. Apenas código da aplicação, interface e dependências de execução acompanham a publicação.

## DNS e HTTPS

Configure no Registro.br:

| Tipo | Nome | Valor |
|---|---|---|
| A | labfgv.com.br | 187.77.3.27 |
| CNAME | www.labfgv.com.br | labfgv.com.br |

O serviço `minera-goias-https.timer` verifica o DNS a cada 15 minutos. Quando ambos os nomes apontarem exclusivamente para a VPS, ele emite o certificado com a conta Let's Encrypt já existente, ativa o redirecionamento para HTTPS e desativa essa verificação inicial. A renovação posterior fica a cargo do `certbot.timer` existente. O cadastro do domínio já foi confirmado; a configuração DNS depende do acesso à conta.

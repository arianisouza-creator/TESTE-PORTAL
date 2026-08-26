# Portal MSE - Passagens (projeto novo, unificado)

Projeto novo que junta em um só lugar:

- Formulário público de solicitação de passagem (substitui o "outro local" de hoje), com o toggle **"Cotar minha passagem"**.
- Robô de cotação (LATAM/Azul via Playwright, reaproveitado do TESTE-PORTAL) - sempre roda na máquina da Ariani.
- Painel administrativo (login com senha única) para revisar cotações, aprovar uma opção, registrar a compra e acompanhar Aéreo, Rodoviário, Hospedagem, Carros, Cadastro manual, Créditos e KPI - tudo no visual corporativo MSE "Capex Seguro".

Banco local: SQLite (arquivo `portal_mse.db`, criado sozinho). Em produção, basta apontar `DATABASE_URL` para o MySQL real - o código é o mesmo.

## Como rodar local (dois terminais)

```powershell
# 1) instalar dependencias (uma vez só)
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-api.txt
.\.venv\Scripts\python.exe -m playwright install chromium

# 2) copiar o arquivo de ambiente e conferir o e-mail de admin
copy .env.example .env
# edite o .env e confira ADMIN_EMAIL (e troque FLASK_SECRET_KEY)
```

Terminal 1 - robô de cotação (Playwright, navegador visível):

```powershell
$env:COTACOES_LATAM_MODE='browser'
$env:COTACOES_AZUL_MODE='browser'
$env:COTACOES_LATAM_HEADLESS='false'
$env:COTACOES_AZUL_HEADLESS='false'
$env:COTACOES_LATAM_PROFILE_DIR='.playwright-latam-profile'
$env:COTACOES_AZUL_PROFILE_DIR='.playwright-azul-profile'
.\.venv\Scripts\python.exe -m uvicorn cotacoes_api:app --host 127.0.0.1 --port 8001
```

Terminal 2 - app principal (Flask):

```powershell
.\.venv\Scripts\python.exe app.py
```

Depois é só abrir:

- `http://127.0.0.1:8000/` - formulário público de solicitação.
- `http://127.0.0.1:8000/login` - login do admin (senha do `.env`).
- `http://127.0.0.1:8000/portal` - painel administrativo (exige login).

Antes de cotar de verdade, configure o login/senha da LATAM e da Azul do jeito que já era feito no TESTE-PORTAL (ver `PACOTE_TI_COTACOES.md` que veio junto, se você copiou ele também) - são endpoints da API de cotação (`/api/cotacoes/config`), não deste app novo.

## Onde ficam as coisas

```text
app.py                        Casca do app (Flask): cria o app, login admin, REST generico,
                               sincronizacao automatica, e registra os modulos abaixo. NAO
                               tem regra de negocio de nenhuma aba especifica.
modules/
  solicitacao/routes.py       Modulo Solicitacao (formulario publico + fila admin + compra).
  fechamento_cartao/routes.py Modulo Fechamento de cartao (conferencia da fatura).
  pedidos_status/routes.py    API de Pedidos (infra compartilhada por varias abas).
  passagens_externas/routes.py Sincronizacao com o sistema atual de passagens (infra).
db.py                         Acesso ao banco (sqlite3 builtin local, pymysql em producao).
auth.py                       Login simples de admin (por e-mail, sem senha).
cotacoes_client.py             Chama a API de cotacoes pra disparar uma cotacao.
cotacoes_api.py / cotacoes/    Modulo "Login LATAM/Azul": robo de cotacao (FastAPI + Playwright).
templates/_style.html          Sistema de design MSE "Capex Seguro" - fonte unica de estilo.
templates/_icons.html          Catalogo de icones (SVG inline).
templates/base_admin.html      Casca do painel (header, sidebar, apiFetch, navegacao entre abas).
templates/login.html           Login do admin.
templates/portal.html          Casca fina que so inclui os modulos abaixo (ver secao "Modulos").
templates/modules/*.html       Um arquivo de HTML+JS por modulo de negocio (ver "Modulos").
```

Veja o **mapa completo de módulos** (o que é de cada aba e o que é compartilhado) na seção "Módulos" logo abaixo.

## Módulos - onde mexer pra cada coisa

O objetivo desta estrutura é simples: **pra mudar só o Fechamento de cartão, por exemplo, você mexe em 2 arquivos (um de backend, um de front) e não precisa entender o resto do sistema.**

| Módulo (o que a Ariani pediu) | Backend | Frontend |
|---|---|---|
| Solicitação | `modules/solicitacao/routes.py` | `templates/modules/solicitacao_panels.html`, `solicitacao_modais.html`, `solicitacao.js.html` |
| Fechamento de cartão | `modules/fechamento_cartao/routes.py` | `templates/modules/fechamento_cartao_panel.html`, `fechamento_cartao.js.html` |
| Login LATAM/Azul | `cotacoes_api.py`, `cotacoes_client.py`, `cotacoes/` (já era separado) | `templates/modules/login_latam_azul_panel.html`, `login_latam_azul.js.html` |
| Aéreo / Rodoviário | *(nenhum - ver nota abaixo)* | `templates/modules/aereo_rodoviario_panels.html`, `aereo_rodoviario.js.html` |
| Hospedagem / Carros | *(nenhum - ver nota abaixo)* | `templates/modules/hospedagem_carros_panels.html`, `hospedagem_carros_modal.html`, `hospedagem_carros.js.html` |
| Cadastro manual | *(nenhum)* | `templates/modules/cadastro_manual_panel.html`, `cadastro_manual.js.html` |
| Créditos | *(nenhum)* | `templates/modules/creditos_panel.html`, `creditos.js.html` |
| KPI | *(nenhum)* | `templates/modules/kpi_panel.html`, `kpi.js.html` |

**Por que Aéreo/Rodoviário e Hospedagem/Carros não têm backend próprio:** essas abas nunca tiveram rota dedicada - elas sempre leram/gravaram direto no REST genérico (`/rest/v1/<tabela>`, dentro de `app.py`). Se um dia precisar mudar uma regra de negócio dessas abas no backend, o lugar é `app.py` (função `rest()`) ou `db.py`.

**Por que Aéreo+Rodoviário são 1 arquivo só (e não 2), e o mesmo pra Hospedagem+Carros:** no código de hoje elas usam a mesma função (só muda um parâmetro: "Aereo" ou "Rodoviario"). Separar de verdade em 2 arquivos duplicaria a lógica toda - e aí um conserto (como os que fizemos essa semana no fechamento de cartão) precisaria ser feito 2 vezes, o que é oq costuma causar bug. Então: pra mudar um texto/comportamento só do Aéreo (não do Rodoviário), o arquivo é o mesmo, mas normalmente dá pra achar pelo `if(modalidade==='Aereo')`; pra mudar algo que vale pros dois, mexe uma vez só e já vale pros dois.

**`templates/modules/_core.js.html`**: funções realmente compartilhadas por 3+ módulos (formatação de moeda/data, navegação entre abas, cache de status de pedido, finalizar/reabrir passagem). Se o Codex disser "não achei essa função no arquivo do módulo", ela provavelmente está aqui.

## Subir no GitHub

Eu não tenho como rodar comandos `git` direto na sua máquina - só consigo ler e gravar arquivos nessa pasta. Então: eu já deixei tudo pronto e organizado aqui dentro de `Subir no Github\Passagens`; falta só você rodar isso (Terminal/PowerShell, dentro desta pasta):

```powershell
git init
git add .
git commit -m "Portal MSE - Passagens (estrutura modular)"
```

Se já existe um repositório vazio criado no GitHub pra isso, conecta e sobe:

```powershell
git remote add origin <URL do seu repositorio no GitHub>
git branch -M main
git push -u origin main
```

Se ainda não criou o repositório: entra no GitHub, "New repository" (pode deixar vazio, sem README/gitignore - já tem aqui), copia a URL que ele mostra (`https://github.com/seu-usuario/nome-do-repo.git`) e usa nos comandos acima.

O `.gitignore` já impede que o banco (`portal_mse.db`), os uploads e o `.env` (senhas/tokens) subam junto - só vai código.

## Segurança

- `.env` nunca deve ir para o Git (já está no `.gitignore`).
- `ADMIN_EMAIL` protege `/portal`, `/rest/v1/*` e as rotas de cotação/compra: só quem digitar esse e-mail exato no login entra. Sem essa variável configurada, o login fica bloqueado por padrão (mais seguro que liberar tudo). **Importante**: não há senha nem confirmação por e-mail - é uma checagem de conveniência para uso local, não uma autenticação forte. Se este portal um dia for exposto para outras pessoas além da Ariani, vale trocar por um login de verdade.
- O formulário de solicitação (`/` e `POST /api/solicitacoes`) continua público de propósito - é para qualquer colaborador usar.

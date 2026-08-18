# Deploy do TESTE-PORTAL no GitHub + Streamlit

Este projeto fica inteiro no repositorio `TESTE-PORTAL`.

## 1. Portal no Streamlit Cloud

No Streamlit Cloud, crie um app apontando para:

- Repository: `arianisouza-creator/TESTE-PORTAL`
- Branch: `main`
- Main file path: `app.py`

O Streamlit vai usar `requirements.txt`.

## 2. Secrets do Streamlit

No painel do Streamlit Cloud, abra **App settings > Secrets** e cole os campos de `streamlit-secrets.example.toml`.

Para as solicitacoes de viagem aparecerem para todos os usuarios, configure tambem:

```toml
supabase_url = "https://SEU-PROJETO.supabase.co"
supabase_anon_key = "SUA_CHAVE_ANON"
```

Antes de liberar para uso, rode o SQL de `supabase-schema.sql` no Supabase. Ele cria inclusive a tabela `passagens_solicitacoes`, usada pelas abas **Solicitacao de viagem** e **Cotacao realizada**.

O campo mais importante para as cotacoes e:

```toml
cotacoes_api_base_url = "https://URL-PUBLICA-DA-SUA-API"
```

Quando estiver vazio, o portal abre, mas a cotacao real nao roda pela internet.

Fluxo esperado em producao:

1. O colaborador acessa o Streamlit Cloud.
2. Ele registra a solicitacao em **Passagens > Solicitacao de viagem**.
3. A solicitacao fica salva no Supabase.
4. A API publica de cotacoes consulta LATAM/Azul e devolve as opcoes.
5. Depois que o colaborador escolhe o voo, voce ve tudo em **Cotacao realizada**.

## 3. API/robo de cotacoes

O robo que abre LATAM/Azul nao deve rodar dentro do Streamlit Cloud. Ele deve ficar em um servico separado, como Render, Railway, Fly.io ou VPS.

Arquivos preparados:

- `cotacoes_api.py`: API FastAPI.
- `cotacoes/`: conectores LATAM/Azul.
- `requirements-api.txt`: dependencias da API.
- `Dockerfile.api`: imagem Docker com Playwright para hospedar o robo.
- `render.yaml`: blueprint para criar a API no Render pelo GitHub.

Com Docker, o comando de subida usa:

```bash
uvicorn cotacoes_api:app --host 0.0.0.0 --port $PORT
```

### Deploy pelo Render

1. Entre em [Render](https://render.com/).
2. Escolha **Blueprints > New Blueprint Instance**.
3. Conecte o repositorio `arianisouza-creator/TESTE-PORTAL`.
4. O Render vai ler `render.yaml` e criar o servico `teste-portal-cotacoes-api`.
5. Preencha as variaveis marcadas como secretas:

```bash
COTACOES_LATAM_USUARIO=...
COTACOES_LATAM_SENHA=...
COTACOES_AZUL_USUARIO=...
COTACOES_AZUL_SENHA=...
```

6. Depois do deploy, abra `https://NOME-DA-API.onrender.com/health`.
7. Se aparecer `{"status":"ok","service":"cotacoes-api"}`, copie a URL base da API.
8. No Streamlit Cloud, cole essa URL em `cotacoes_api_base_url`.

## 4. Variaveis da API de cotacoes

Configure no provedor da API:

```bash
COTACOES_LATAM_MODE=browser
COTACOES_AZUL_MODE=browser
COTACOES_LATAM_HEADLESS=true
COTACOES_AZUL_HEADLESS=true
COTACOES_CORS_ORIGINS=https://SEU-APP.streamlit.app
COTACOES_DATA_FILE=/data/cotacoes_data.json
COTACOES_LATAM_SITE_URL=https://www.corporate.latamairlines.com/br/pt
COTACOES_AZUL_SITE_URL=https://apps.voeazul.com.br/PortalEmpresas/?ReturnUrl=%2fPortalEmpresas%2fReserva%2fComprar%2f
COTACOES_LATAM_USUARIO=seu-login-latam
COTACOES_LATAM_SENHA=sua-senha-latam
COTACOES_AZUL_USUARIO=seu-login-azul
COTACOES_AZUL_SENHA=sua-senha-azul
```

As credenciais das companhias devem ser salvas pela tela **Administrativo > API** ou configuradas como armazenamento persistente no provedor.

Em producao, prefira as variaveis de ambiente acima. Assim a API ja sobe com LATAM/Azul configuradas e o robo consegue cotar de forma invisivel quando uma solicitacao for criada no portal.

## 5. O que nao subir para o GitHub

Nao suba:

- `.streamlit/secrets.toml`
- `cotacoes_data*.json`
- `.playwright-*`
- `.venv`
- arquivos com senha ou sessao local

O `.gitignore` ja esta configurado para bloquear esses arquivos.

# TESTE-PORTAL | Portal MSE

Portal administrativo em Streamlit com interface HTML/CSS customizada para os modulos:

- `Controle de Telefonia e Internet`
- `Controle da Diarista`
- `Controle de Passagens`
- `API de Cotacoes`

## Como rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

Para rodar a API local de cotacoes/robo:

```bash
pip install -r requirements-api.txt
playwright install chromium
uvicorn cotacoes_api:app --host 127.0.0.1 --port 8001
```

Depois configure no ambiente local:

```bash
COTACOES_API_BASE_URL=http://127.0.0.1:8001
```

## Como publicar no GitHub + Streamlit Cloud

Este projeto ja esta preparado para ficar inteiro no repositorio `TESTE-PORTAL`.

No Streamlit Cloud:

1. Conecte o GitHub.
2. Escolha o repositorio `arianisouza-creator/TESTE-PORTAL`.
3. Configure o arquivo principal como `app.py`.
4. Copie os campos de `streamlit-secrets.example.toml` para **Secrets**.
5. Preencha `cotacoes_api_base_url` com a URL publica da API de cotacoes.

Guia completo: [DEPLOY-STREAMLIT.md](DEPLOY-STREAMLIT.md)

Importante: o portal roda no Streamlit Cloud, mas o robo que abre LATAM/Azul deve rodar em um backend separado. O projeto inclui `Dockerfile.api` e `requirements-api.txt` para isso.

## Como configurar o Supabase

1. Crie um projeto no Supabase.
2. Rode o SQL de [supabase-schema.sql](supabase-schema.sql).
3. Configure as credenciais publicas no Streamlit:

```toml
# .streamlit/secrets.toml
supabase_url = "https://SEU-PROJETO.supabase.co"
supabase_anon_key = "SUA_CHAVE_ANON"
```

Voce tambem pode usar variaveis de ambiente:

```bash
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
```

## Comportamento atual

- O layout continua 100% no arquivo HTML.
- Quando o Supabase estiver configurado, o portal passa a ler e gravar direto nele.
- O modulo de `Passagens` tambem sincroniza:
  - linhas importadas da API
  - complementos manuais
  - creditos cadastrados
  - solicitacoes de viagem e cotacoes realizadas
- Se o Supabase nao estiver configurado ou ficar indisponivel, o portal usa cache local do navegador para nao quebrar a interface.
- As abas protegidas continuam usando:
  - Usuario: `ADM`
  - Senha: `mse2026`

Para outras pessoas conseguirem fazer solicitacoes pelo site publicado, o Supabase precisa estar configurado e o SQL de `supabase-schema.sql` precisa ter sido executado. Sem isso, cada navegador salva apenas no proprio cache local.

## Estrutura principal

- [app.py](app.py): wrapper Streamlit que injeta a configuracao no HTML.
- [controle-internet.html](controle-internet.html): layout, interacoes e sincronizacao com Supabase.
- [cotacoes_api.py](cotacoes_api.py): API FastAPI usada pelo robo de cotacoes.
- [cotacoes/](cotacoes): conectores LATAM/Azul.
- [supabase-schema.sql](supabase-schema.sql): schema das tabelas usadas pelo portal.
- [streamlit-secrets.example.toml](streamlit-secrets.example.toml): exemplo de secrets para Streamlit Cloud.

## Observacao importante

O acesso protegido por `ADM / mse2026` protege a navegacao do portal, mas nao substitui uma modelagem de seguranca mais forte no banco. Para uma fase futura, o ideal e mover a escrita sensivel para um backend autenticado com regras mais fechadas.

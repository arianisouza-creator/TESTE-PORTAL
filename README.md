# Portal-MSE

Portal administrativo em Streamlit com interface HTML/CSS customizada para os modulos:

- `Controle de Telefonia e Internet`
- `Controle da Diarista`
- `Controle de Passagens`

## Como rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Como configurar o Supabase

1. Crie um projeto no Supabase.
2. Rode o SQL de [supabase-schema.sql](/C:/Users/notebook/Documents/Conferencia%20Cartão/supabase-schema.sql).
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
- Se o Supabase nao estiver configurado ou ficar indisponivel, o portal usa cache local do navegador para nao quebrar a interface.
- As abas protegidas continuam usando:
  - Usuario: `ADM`
  - Senha: `mse2026`

## Estrutura principal

- [app.py](/C:/Users/notebook/Documents/Conferencia%20Cartão/app.py): wrapper Streamlit que injeta a configuracao no HTML.
- [controle-internet.html](/C:/Users/notebook/Documents/Conferencia%20Cartão/controle-internet.html): layout, interacoes e sincronizacao com Supabase.
- [supabase-schema.sql](/C:/Users/notebook/Documents/Conferencia%20Cartão/supabase-schema.sql): schema das tabelas usadas pelo portal.

## Observacao importante

O acesso protegido por `ADM / mse2026` protege a navegacao do portal, mas nao substitui uma modelagem de seguranca mais forte no banco. Para uma fase futura, o ideal e mover a escrita sensivel para um backend autenticado com regras mais fechadas.

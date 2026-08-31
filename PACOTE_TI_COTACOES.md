# Pacote TI - Robo de Cotacoes Aereas

Projeto: TESTE-PORTAL

Este pacote contem a parte de cotacoes com automacao local via Playwright. A ideia atual e:

- O portal Streamlit abre a tela administrativa e de solicitacao.
- A tela chama uma API local em FastAPI.
- A API local abre um navegador controlado pelo Playwright.
- O robo acessa os portais das companhias, preenche origem, destino, datas e passageiro.
- O retorno da API volta para o portal com as opcoes encontradas.

## Como esta rodando hoje

Portal local:

```text
http://127.0.0.1:8506
```

API local do robo:

```text
http://127.0.0.1:8001
```

Health check da API:

```text
http://127.0.0.1:8001/health
```

Debug sem mostrar senhas:

```text
http://127.0.0.1:8001/api/cotacoes/debug
```

O robo local deve rodar com navegador visivel:

```text
COTACOES_LATAM_MODE=browser
COTACOES_AZUL_MODE=browser
COTACOES_LATAM_HEADLESS=false
COTACOES_AZUL_HEADLESS=false
```

## Onde ficam os arquivos principais

```text
cotacoes_api.py
```

API FastAPI. Expoe endpoints de configuracao, historico e teste de cotacao.

```text
cotacoes/models.py
```

Modelos de dados usados pela API e pelos conectores.

```text
cotacoes/service.py
```

Camada que escolhe qual conector usar e salva historico.

```text
cotacoes/storage.py
```

Leitura e escrita do arquivo local de dados.

```text
cotacoes/connectors/base.py
```

Base dos conectores. Foi adicionada a classe `CotacaoStageError`, usada para informar exatamente em qual etapa o robo travou.

```text
cotacoes/connectors/latam.py
```

Robo Playwright da LATAM Corporate.

```text
cotacoes/connectors/azul.py
```

Robo Playwright da Azul Empresas.

```text
controle-internet.html
```

Tela do portal onde a solicitacao dispara as cotacoes e mostra as opcoes.

## Onde ficam login, senha e sites

As configuracoes locais ficam no arquivo:

```text
cotacoes_data.json
```

Esse arquivo pode conter:

- URL do site da companhia.
- Usuario/login.
- Senha.
- Status do conector.
- Historico das cotacoes.

Importante: esse arquivo NAO deve ser enviado para GitHub nem para terceiros. Ele esta no `.gitignore` como:

```text
cotacoes_data*.json
```

As configuracoes do Streamlit local ficam em:

```text
.streamlit/secrets.toml
```

Hoje ele aponta o portal para a API local:

```text
cotacoes_api_base_url = "http://127.0.0.1:8001"
```

Esse arquivo tambem nao deve ser enviado para o GitHub.

## Sessao do navegador

Os cookies/sessoes dos navegadores usados pelo Playwright ficam em pastas locais como:

```text
.playwright-latam-profile
.playwright-azul-profile
.playwright-azul-empresas-profile
```

Essas pastas ajudam o robo a manter sessao quando possivel, mas nao devem ser enviadas para GitHub ou compartilhadas.

## Como iniciar localmente

No PowerShell, dentro da pasta `TESTE-PORTAL`:

```powershell
$env:COTACOES_LATAM_MODE='browser'
$env:COTACOES_AZUL_MODE='browser'
$env:COTACOES_LATAM_HEADLESS='false'
$env:COTACOES_AZUL_HEADLESS='false'
$env:COTACOES_LATAM_PROFILE_DIR='.playwright-latam-profile'
$env:COTACOES_AZUL_PROFILE_DIR='.playwright-azul-profile'
.\.venv\Scripts\python.exe -m uvicorn cotacoes_api:app --host 127.0.0.1 --port 8001
```

Em outro terminal:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8506 --server.headless true
```

## Endpoints principais

```text
GET /health
```

Confirma se a API esta no ar.

```text
GET /api/cotacoes/debug
```

Mostra se LATAM/AZUL estao configuradas, sem revelar senha.

```text
GET /api/cotacoes/config
```

Retorna configuracoes dos conectores.

```text
POST /api/cotacoes/config
```

Salva configuracao de uma companhia.

```text
POST /api/cotacoes/teste
```

Executa uma cotacao.

Payload exemplo:

```json
{
  "companhia": "LATAM",
  "origem": "LDB",
  "destino": "GRU",
  "dataIda": "2026-11-24",
  "dataVolta": "2026-11-26",
  "adultos": 1,
  "cabine": "Economica",
  "comando": ""
}
```

```text
GET /api/cotacoes/historico
```

Retorna historico local salvo.

## Mudancas recentes feitas no robo

### Erro por etapa

Foi adicionada a classe `CotacaoStageError` em `cotacoes/connectors/base.py`.

Agora a API consegue devolver mensagens como:

```text
LATAM: etapa busca: Parou ao preencher origem/destino/datas...
LATAM: etapa resultados_ida: Parou ao ler os voos de ida...
LATAM: etapa resultados_volta: Parou ao ler os voos de volta...
```

Isso facilita descobrir se o problema foi no login, no captcha, no calendario, na ida ou na volta.

### LATAM

Foram feitas melhorias em:

- Login.
- Preenchimento de origem e destino.
- Avanco de meses no calendario.
- Clique na data.
- Confirmacao de que a data entrou no campo.
- Espera da tela de ida.
- Espera da tela de volta depois de escolher a tarifa Light.
- Filtro para nao confundir `BRL` com codigo de aeroporto.

Ponto de atencao: a LATAM pode pedir reCAPTCHA/validacao manual. O robo nao deve burlar isso; quando aparecer, precisa de intervencao humana.

### Azul

Foram feitas melhorias em:

- Login da Azul Empresas.
- Clique em botao `Fazer Login`, `Entrar`, `Login` ou `Acessar`.
- Envio do formulario se o botao nao responder.
- Preenchimento de origem/destino com selecao de aeroporto.
- Preenchimento de data digitada.
- Selecionar primeiro passageiro.
- Ler resultados de ida e volta na mesma tela.
- Separar rota de volta quando a tabela inverte origem/destino.

## Pontos importantes para o TI

1. Este robo esta rodando localmente porque os sites das companhias podem bloquear acesso em servidor cloud.
2. No Render/Streamlit Cloud, o navegador headless pode ser bloqueado ou pedir validacao.
3. O portal online pode chamar a API local apenas se houver tunel/rede configurada. No momento, o uso mais estavel e rodar API e portal na maquina local.
4. Senhas e cookies nao devem ir para GitHub.
5. O ideal futuro e usar API oficial das companhias, GDS ou fornecedor de viagens, se disponivel.
6. ~~Se continuar com Playwright, recomenda-se criar logs por etapa e screenshots de erro para diagnostico.~~ Feito em 2026-08-20 — ver secao "Melhorias 2026-08-20" abaixo.

## Melhorias 2026-08-20

Depois de revisar o codigo, foram feitas as seguintes mudancas em `cotacoes/connectors/base.py`, `latam.py`, `azul.py`, `cotacoes/storage.py` e `cotacoes_api.py`:

1. **Log por etapa + screenshot automatico no erro.** Toda etapa do robo (abrir site, login, busca, ler resultados) agora passa pela funcao `run_stage` em `cotacoes/connectors/base.py`. Ela loga inicio/fim de cada etapa e, quando uma etapa falha definitivamente, tira um print de tela automatico salvo em `debug-output/<companhia>_<etapa>_<data>.png` (mesma pasta que os scripts de debug ja usavam manualmente). Os 40 prints mais recentes por companhia sao mantidos; os antigos sao apagados sozinhos. As mensagens de erro que a API ja devolvia (`LATAM: etapa busca: ...`) continuam identicas — so ganharam log e screenshot por tras.
2. **Azul passou a ter erro por etapa tambem.** Antes so a LATAM usava `CotacaoStageError`; a Azul lançava erro generico e caia na mensagem menos detalhada da API. Agora as duas usam as mesmas etapas (`abertura_site`, `login`, `busca`/`formulario_compra`, `resultados`).
3. **Retry automatico so onde e seguro.** Abrir o site e ler a tela de resultados agora tentam de novo uma vez antes de desistir (falha de rede passageira). Etapas que clicam/preenchem formulario (login, busca) continuam sem retry de proposito, pra nao clicar em botao ou preencher campo duas vezes.
4. **Senha criptografada em repouso (opcional).** Se a variavel `COTACOES_SECRET_KEY` for configurada, a senha salva em `cotacoes_data.json` passa a ser gravada criptografada (prefixo `enc::...`). Sem essa variavel, continua exatamente como antes (texto puro) — nada quebra em quem ja estava rodando. Gerar uma chave:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
   Depois configure `COTACOES_SECRET_KEY=<chave gerada>` no ambiente onde a API roda. **Guarde essa chave** — se ela mudar ou sumir, as senhas ja criptografadas nao conseguem mais ser lidas (vai ser preciso reconfigurar login/senha das companhias na aba API).
5. **Trava de arquivo no `cotacoes_data.json`.** Duas cotacoes salvando ao mesmo tempo nao corrompem mais o arquivo (antes podia acontecer). Testado com 8 gravacoes simultaneas.
6. **CORS mais restrito por padrao.** Sem `COTACOES_CORS_ORIGINS` configurada, a API antes liberava `*` (qualquer site). Agora, sem essa variavel, so aceita `localhost`/`127.0.0.1` (qualquer porta) e `*.streamlit.app`, que e o que o projeto realmente usa. Quem ja configurava `COTACOES_CORS_ORIGINS` (ex.: no Render) nao é afetado.

**Nova dependencia:** `cryptography` foi adicionada a `requirements-api.txt`. Depois de atualizar o codigo, rode de novo:
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-api.txt
```

## Arquivos que nao devem ser compartilhados

Nao incluir:

```text
cotacoes_data.json
cotacoes_data.debug.json
.streamlit/secrets.toml
.env
.venv/
.playwright-*/
.playwright-*-profile/
debug-output/
```

## Conteudo deste pacote

O zip entregue ao TI contem apenas codigo e documentacao:

```text
cotacoes/
cotacoes_api.py
controle-internet.html
Dockerfile.api
render.yaml
requirements-api.txt
requirements.txt
README-COTACOES.md
PACOTE_TI_COTACOES.md
streamlit-secrets.example.toml
```

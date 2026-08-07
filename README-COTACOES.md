# API de Cotacoes

## Rodar em sandbox

```bash
uvicorn cotacoes_api:app --host 127.0.0.1 --port 8001
```

## Preparar automacao LATAM

```bash
pip install -r requirements.txt
playwright install chromium
set COTACOES_LATAM_MODE=browser
uvicorn cotacoes_api:app --host 127.0.0.1 --port 8001
```

O conector para LATAM abre o portal corporativo, tenta login autorizado e procura precos visiveis. Se o site pedir CAPTCHA, token ou outra validacao manual, a automacao para e retorna erro para intervencao humana.

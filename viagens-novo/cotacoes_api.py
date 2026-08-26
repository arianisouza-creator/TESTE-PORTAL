import os
import logging
import traceback
from typing import Any

try:
    from dotenv import load_dotenv

    # Le o .env desta mesma pasta - assim COTACOES_LATAM_USUARIO/SENHA e
    # COTACOES_AZUL_USUARIO/SENHA (se preenchidos ali) ficam disponiveis pro
    # env_config() de cotacoes/storage.py, sem precisar editar o
    # .vscode/launch.json nem redigitar o login toda vez. So preenche essas
    # linhas no .env LOCAL (nunca no .env.example, nunca em nada versionado).
    load_dotenv()
except Exception:  # dotenv e opcional
    pass

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from cotacoes.connectors.base import CotacaoStageError
from cotacoes.models import ConnectorConfig, QuoteRequest
from cotacoes.service import get_company_config, get_config, history, quote, save_config


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("cotacoes_api")

app = FastAPI(title="MSE Cotacoes API", version="0.1.0")
# Antes, sem COTACOES_CORS_ORIGINS configurada a API liberava "*" (qualquer
# origem). O CORS_REGEX abaixo ja cobre localhost/127.0.0.1 em qualquer porta
# e qualquer *.streamlit.app, que e o que o projeto realmente precisa; entao
# agora, sem a variavel definida, nao caimos mais no wildcard.
CORS_ORIGINS = [origin.strip() for origin in os.getenv("COTACOES_CORS_ORIGINS", "").split(",") if origin.strip()]
CORS_REGEX = os.getenv("COTACOES_CORS_REGEX", r"https://.*\.streamlit\.app|http://(localhost|127\.0\.0\.1):[0-9]+")
if not CORS_ORIGINS:
    logger.info(
        "COTACOES_CORS_ORIGINS nao configurada; usando apenas o padrao (localhost/127.0.0.1 e *.streamlit.app)."
    )
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=CORS_REGEX or None,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "cotacoes-api"}


@app.get("/api/cotacoes/config")
def read_config() -> dict[str, Any]:
    return {"status": "ok", "config": get_config()}


@app.get("/api/cotacoes/debug")
def read_debug() -> dict[str, Any]:
    config = get_config()
    return {
        "status": "ok",
        "companies": {
            company: {
                "siteUrl": bool(payload.get("siteUrl")),
                "usuario": bool(payload.get("usuario")),
                "senhaMask": bool(payload.get("senhaMask")),
                "ambiente": payload.get("ambiente", ""),
                "status": payload.get("status", ""),
            }
            for company, payload in config.items()
        },
        "modes": {
            "latam": os.getenv("COTACOES_LATAM_MODE", ""),
            "azul": os.getenv("COTACOES_AZUL_MODE", ""),
            "latam_headless": os.getenv("COTACOES_LATAM_HEADLESS", ""),
            "azul_headless": os.getenv("COTACOES_AZUL_HEADLESS", ""),
        },
    }


@app.post("/api/cotacoes/config")
def write_config(config: ConnectorConfig) -> dict[str, Any]:
    return {"status": "ok", "config": save_config(config)}


@app.post("/api/cotacoes/teste")
def quote_test(request: QuoteRequest) -> dict[str, Any]:
    config = get_company_config(request.companhia or "LATAM")
    company = (request.companhia or "LATAM").strip().upper()
    if not config.get("siteUrl"):
        raise HTTPException(status_code=400, detail=f"Configure {request.companhia or 'LATAM'} antes de cotar.")
    if company == "AZUL" and not config.get("usuario"):
        raise HTTPException(status_code=400, detail="Configure o login da Azul antes de cotar.")
    try:
        return {"status": "ok", "quote": quote(request)}
    except CotacaoStageError as exc:
        logger.error(
            "Erro na cotacao %s etapa=%s %s-%s %s/%s screenshot=%s: %s\n%s",
            company,
            exc.etapa,
            request.origem,
            request.destino,
            request.dataIda,
            request.dataVolta or "sem-volta",
            getattr(exc, "screenshot_path", None) or "indisponivel",
            exc.mensagem,
            traceback.format_exc(),
        )
        raise HTTPException(status_code=502, detail=f"{company}: etapa {exc.etapa}: {exc.mensagem}") from exc
    except Exception as exc:
        logger.error(
            "Erro na cotacao %s %s-%s %s/%s: %s\n%s",
            company,
            request.origem,
            request.destino,
            request.dataIda,
            request.dataVolta or "sem-volta",
            exc,
            traceback.format_exc(),
        )
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/cotacoes/historico")
def quote_history() -> dict[str, Any]:
    return {"status": "ok", "quotes": history()}

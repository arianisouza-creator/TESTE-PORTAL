import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from cotacoes.models import ConnectorConfig, QuoteRequest
from cotacoes.service import get_company_config, get_config, history, quote, save_config


app = FastAPI(title="MSE Cotacoes API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("COTACOES_CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "cotacoes-api"}


@app.get("/api/cotacoes/config")
def read_config() -> dict[str, Any]:
    return {"status": "ok", "config": get_config()}


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
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/cotacoes/historico")
def quote_history() -> dict[str, Any]:
    return {"status": "ok", "quotes": history()}

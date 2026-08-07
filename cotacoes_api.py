import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from cotacoes.models import ConnectorConfig, QuoteRequest
from cotacoes.service import get_config, history, quote, save_config


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
    config = get_config()
    if not config.get("siteUrl") or not config.get("usuario"):
        raise HTTPException(status_code=400, detail="Configure companhia, site e login antes de cotar.")
    return {"status": "ok", "quote": quote(request)}


@app.get("/api/cotacoes/historico")
def quote_history() -> dict[str, Any]:
    return {"status": "ok", "quotes": history()}

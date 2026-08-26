"""Sincronização com o sistema atual de passagens (hub_mse/api_passagens) -
traz pra cá as viagens já registradas lá. Infraestrutura compartilhada
(principalmente usada pela aba Aéreo), não é um dos módulos de negócio.

Extraído de app.py sem mudar nada na lógica - só virou Blueprint.
"""
from __future__ import annotations

import requests
from flask import Blueprint, jsonify, request

import passagens_sync
from auth import login_required_api

bp = Blueprint("passagens_externas", __name__)


def _clean(value: str | None) -> str:
    return (value or "").strip()


@bp.get("/api/passagens-externas/status")
@login_required_api
def status_passagens_externas():
    return jsonify({"configurado": passagens_sync.configurado(), "base_url": passagens_sync.BASE_URL})


@bp.post("/api/passagens-externas/sincronizar")
@login_required_api
def sincronizar_passagens_externas():
    payload = request.get_json(silent=True) or {}
    try:
        resultado = passagens_sync.sincronizar(
            fonte=_clean(payload.get("fonte")) or "compradas",
            tabela=_clean(payload.get("tabela")) or None,
        )
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 400
    except requests.RequestException as exc:
        return jsonify({"error": f"Nao consegui falar com o sistema atual de passagens ({passagens_sync.BASE_URL}). Detalhe: {exc}"}), 502
    return jsonify(resultado)


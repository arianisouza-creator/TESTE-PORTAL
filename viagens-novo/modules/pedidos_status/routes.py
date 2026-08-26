"""API de Pedidos (portalmse.com.br) - consulta o status (Em Aberto,
Finalizado etc) de um número de pedido. Usado pelas abas Aéreo,
Rodoviário, Hospedagem, Carros e pelo Fechamento de cartão - por isso não
é um módulo de negócio isolado, é infraestrutura compartilhada (igual o
db.py), com pacote próprio só pra não poluir o app.py.

Extraído de app.py sem mudar nada na lógica - só virou Blueprint.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from flask import Blueprint, abort, jsonify, request

import db
import pedidos_api
from auth import login_required_api

bp = Blueprint("pedidos_status", __name__)


def _clean(value: str | None) -> str:
    return (value or "").strip()


@bp.get("/api/pedidos/config-status")
@login_required_api
def config_status_pedidos():
    return jsonify({"configurado": pedidos_api.configurado()})


@bp.get("/api/pedidos/status")
@login_required_api
def status_pedido():
    numero = _clean(request.args.get("numero_pedido"))
    if not numero:
        abort(400, "numero_pedido obrigatorio")
    return jsonify(pedidos_api.consultar_pedido(numero))


def _numeros_pedido_em_uso() -> list[str]:
    """Junta os numeros de pedido ja digitados nas passagens (aereo/rodoviario),
    hospedagens e carros - sem duplicar - pra sincronizar o status de todos de
    uma vez (botao do Dashboard)."""
    numeros: set[str] = set()
    for row in db.fetch_all("passagens_rows"):
        numero = _clean((row.get("item") or {}).get("pedido"))
        if numero:
            numeros.add(numero)
    for tabela in ("passagens_hospedagens", "passagens_carros"):
        for row in db.fetch_all(tabela):
            numero = _clean((row.get("data") or {}).get("pedido"))
            if numero:
                numeros.add(numero)
    return sorted(numeros)


def _sincronizar_status_pedidos() -> dict[str, Any]:
    """Consulta na API de Pedidos o status de cada numero de pedido em uso e
    atualiza o cache local (passagens_pedidos_status). Usado tanto pelo botao
    manual quanto pela sincronizacao automatica de 30 em 30 minutos."""
    numeros = _numeros_pedido_em_uso()
    encontrados = 0
    nao_encontrados: list[str] = []
    for numero in numeros:
        resultado = pedidos_api.consultar_pedido(numero)
        if not resultado.get("encontrado"):
            nao_encontrados.append(numero)
            continue
        encontrados += 1
        db.upsert_row("passagens_pedidos_status", {
            "numero_pedido": numero,
            "status_pedido": resultado.get("status_pedido", ""),
            "fornecedor": resultado.get("fornecedor", ""),
            "obra": resultado.get("obra", ""),
            "valor": resultado.get("valor"),
            "data_pedido": resultado.get("data_pedido", ""),
            "data_entrega": resultado.get("data_entrega", ""),
            "tipo_descricao": resultado.get("tipo_descricao", ""),
            "atualizado_em": datetime.utcnow().isoformat(timespec="seconds"),
        })
    return {
        "total": len(numeros),
        "encontrados": encontrados,
        "nao_encontrados": nao_encontrados,
    }


@bp.post("/api/pedidos/sincronizar")
@login_required_api
def sincronizar_pedidos():
    if not pedidos_api.configurado():
        return jsonify({"error": "PEDIDOS_API_TOKEN nao configurado no .env."}), 400
    return jsonify(_sincronizar_status_pedidos())



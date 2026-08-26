"""Cliente somente-leitura da API de Pedidos do Portal MSE
(portalmse.com.br/microservices/pedidos_usuarios_api).

Documentada no guia "API de Pedidos - Guia do Usuario" que a TI entrega -
GET /v1/pedidos com filtro numero_pedido devolve status_pedido (Em Aberto,
Finalizado etc). Usado na aba Aereo pra mostrar se o pedido de uma passagem
ja foi aprovado/finalizado, e no fechamento de fatura de cartao.

A chave (Bearer token, 64 caracteres) e pessoal e so-leitura - nunca fica no
codigo. Igual ao usuario/senha da LATAM/Azul, ela vem do .env:

  PEDIDOS_API_TOKEN=<a chave que a TI te passou>

Sem essa variavel configurada, consultar_pedido() devolve um erro claro em
vez de travar - a funcionalidade so fica indisponivel, sem quebrar o resto
do portal.
"""

from __future__ import annotations

import os
from typing import Any

import requests

PEDIDOS_API_BASE_URL = os.getenv(
    "PEDIDOS_API_BASE_URL", "https://portalmse.com.br/microservices/pedidos_usuarios_api"
).rstrip("/")
PEDIDOS_API_TOKEN = os.getenv("PEDIDOS_API_TOKEN", "").strip()
PEDIDOS_API_TIMEOUT = float(os.getenv("PEDIDOS_API_TIMEOUT_SECONDS", "20"))


def configurado() -> bool:
    return bool(PEDIDOS_API_TOKEN)


def _pedido_resumido(pedido: dict[str, Any]) -> dict[str, Any]:
    return {
        "encontrado": True,
        "numero_pedido": pedido.get("numero_pedido", ""),
        "status_pedido": pedido.get("status_pedido", ""),
        "banco_s1": pedido.get("banco_s1", ""),
        "obra": pedido.get("obra", ""),
        "fornecedor": pedido.get("fornecedor", ""),
        "valor": pedido.get("valor"),
        "data_pedido": pedido.get("data_pedido", ""),
        "data_entrega": pedido.get("data_entrega", ""),
        "tipo_descricao": pedido.get("tipo_descricao", ""),
    }


def consultar_pedido(numero_pedido: str) -> dict[str, Any]:
    """Busca um pedido pelo numero (a API aceita o numero completo ou parte
    dele). Se vier mais de um resultado, prefere o que bate exatamente com o
    numero pedido; senao usa o primeiro da lista."""
    numero = (numero_pedido or "").strip()
    if not numero:
        return {"encontrado": False, "erro": "Numero do pedido vazio."}
    if not configurado():
        return {
            "encontrado": False,
            "erro": "PEDIDOS_API_TOKEN nao configurado no .env - peca a chave pra TI e adicione essa variavel.",
        }
    try:
        resp = requests.get(
            f"{PEDIDOS_API_BASE_URL}/v1/pedidos",
            params={"numero_pedido": numero, "per_page": 5},
            headers={"Authorization": f"Bearer {PEDIDOS_API_TOKEN}"},
            timeout=PEDIDOS_API_TIMEOUT,
        )
    except requests.RequestException as exc:
        return {"encontrado": False, "erro": f"Nao consegui falar com a API de pedidos: {exc}"}

    if resp.status_code == 401:
        return {"encontrado": False, "erro": "A API de pedidos nao recebeu a chave (401)."}
    if resp.status_code == 403:
        return {
            "encontrado": False,
            "erro": "A chave da API de pedidos foi recusada (403) - confira se nao ficou espaco extra ao salvar no .env.",
        }
    if resp.status_code == 404:
        return {"encontrado": False, "erro": "Pedido nao encontrado (404)."}
    if resp.status_code != 200:
        return {"encontrado": False, "erro": f"A API de pedidos respondeu HTTP {resp.status_code}."}

    try:
        body = resp.json()
    except ValueError:
        return {"encontrado": False, "erro": "A API de pedidos devolveu uma resposta que nao entendi."}

    dados = body.get("data") or []
    exato = next((p for p in dados if str(p.get("numero_pedido", "")).strip() == numero), None)
    pedido = exato or (dados[0] if dados else None)
    if not pedido:
        return {"encontrado": False, "erro": "Nenhum pedido encontrado com esse numero."}
    return _pedido_resumido(pedido)


def listar_pedidos(per_page: int = 200, pagina: int = 1) -> dict[str, Any]:
    """Lista pedidos recentes, sem filtrar por numero - usado no fechamento de
    fatura pra tentar achar (por valor) o pedido de um lancamento que ainda
    nao tem correspondencia local no portal. O guia da TI documenta principalmente
    a consulta por numero_pedido; aqui a gente so pede uma pagina grande e casa
    por valor do lado de ca. Se a API precisar de outro parametro pra listar sem
    numero, isso volta so com "erro" preenchido (tratado sem quebrar a tela)."""
    if not configurado():
        return {"encontrados": [], "erro": "PEDIDOS_API_TOKEN nao configurado no .env."}
    try:
        resp = requests.get(
            f"{PEDIDOS_API_BASE_URL}/v1/pedidos",
            params={"per_page": per_page, "page": pagina},
            headers={"Authorization": f"Bearer {PEDIDOS_API_TOKEN}"},
            timeout=PEDIDOS_API_TIMEOUT,
        )
    except requests.RequestException as exc:
        return {"encontrados": [], "erro": f"Nao consegui falar com a API de pedidos: {exc}"}
    if resp.status_code != 200:
        return {"encontrados": [], "erro": f"A API de pedidos respondeu HTTP {resp.status_code}."}
    try:
        body = resp.json()
    except ValueError:
        return {"encontrados": [], "erro": "A API de pedidos devolveu uma resposta que nao entendi."}
    dados = body.get("data") or []
    return {"encontrados": [_pedido_resumido(p) for p in dados], "erro": None}

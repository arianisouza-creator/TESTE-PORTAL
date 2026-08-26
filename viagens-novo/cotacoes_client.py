"""Cliente HTTP que fala com a API local de cotacoes (cotacoes_api.py,
FastAPI + Playwright, rodando sempre na maquina da Ariani - nunca na do
visitante). Mesma API que o portal Streamlit do TESTE-PORTAL ja usa hoje
(POST /api/cotacoes/teste); aqui so orquestramos: uma solicitacao publica
com "cotar minha passagem" marcado dispara LATAM e Azul em paralelo, guarda
o resultado de cada uma e atualiza o status da solicitacao.
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
import unicodedata
import uuid
from typing import Any

import requests

import db

logger = logging.getLogger("cotacoes_client")

COTACOES_API_BASE_URL = os.getenv("COTACOES_API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
COTACOES_TIMEOUT = float(os.getenv("COTACOES_TIMEOUT_SECONDS", "180"))
COMPANHIAS = ["LATAM", "AZUL"]

# Cidades de origem que tambem cotamos automaticamente quando a pessoa pede
# uma passagem saindo de X (ex.: saindo de Londrina, tambem vale a pena ver
# o preco saindo de Maringa e de Sao Paulo). So entra aqui por pedido
# explicito da Ariani - pode crescer conforme ela for pedindo mais grupos.
ORIGENS_PROXIMAS: dict[str, list[str]] = {
    "LONDRINA": ["Maringa", "Sao Paulo"],
}


def _normalizar_cidade(valor: str) -> str:
    texto = unicodedata.normalize("NFD", (valor or "").strip())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto.upper()


def _origens_para_cotar(dados: dict[str, Any]) -> list[str]:
    """Monta a lista de cidades/aeroportos de origem a cotar: a que a pessoa
    digitou, mais as origens proximas automaticas (exceto se coincidirem com
    o destino - nao faz sentido cotar Sao Paulo -> Sao Paulo), mais qualquer
    origem extra que a propria pessoa tenha digitado no campo opcional do
    formulario ("outras_origens", separadas por virgula)."""
    origem_principal = (dados.get("cidade_ida") or dados.get("origem") or "").strip()
    destino = (dados.get("cidade_destino") or dados.get("destino") or "").strip()
    destino_norm = _normalizar_cidade(destino)

    candidatas = [origem_principal] if origem_principal else []
    candidatas += ORIGENS_PROXIMAS.get(_normalizar_cidade(origem_principal), [])

    extra = (dados.get("outras_origens") or "").strip()
    if extra:
        candidatas += [parte.strip() for parte in re.split(r"[,;/]", extra) if parte.strip()]

    vistas: set[str] = set()
    origens: list[str] = []
    for cidade in candidatas:
        chave = _normalizar_cidade(cidade)
        if not chave or chave == destino_norm or chave in vistas:
            continue
        vistas.add(chave)
        origens.append(cidade)
    return origens or ([origem_principal] if origem_principal else [""])


def _quote_payload(dados: dict[str, Any], companhia: str, origem: str) -> dict[str, Any]:
    ida_volta = (dados.get("ida_volta") or "").strip().lower()
    return {
        "companhia": companhia,
        "origem": origem,
        "destino": dados.get("cidade_destino", "") or dados.get("destino", ""),
        "dataIda": dados.get("data_ida", ""),
        "dataVolta": dados.get("data_volta", "") if ida_volta.startswith("ida e volta") else "",
        "adultos": 1,
        "cabine": "Economica",
        "comando": "",
    }


def _quote_one(solicitacao_id: str, dados: dict[str, Any], companhia: str, origem: str) -> None:
    payload = _quote_payload(dados, companhia, origem)
    row: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "solicitacao_id": solicitacao_id,
        "companhia": companhia,
        "aprovada": False,
    }
    try:
        resp = requests.post(
            f"{COTACOES_API_BASE_URL}/api/cotacoes/teste",
            json=payload,
            timeout=COTACOES_TIMEOUT,
        )
        if resp.status_code == 200:
            row["status"] = "ok"
            row["mensagem_erro"] = ""
            row["quote"] = resp.json().get("quote") or {}
        else:
            detail = ""
            try:
                detail = resp.json().get("detail", "")
            except ValueError:
                detail = resp.text
            row["status"] = "erro"
            row["mensagem_erro"] = detail or f"HTTP {resp.status_code}"
            row["quote"] = {}
    except requests.RequestException as exc:
        row["status"] = "erro"
        row["mensagem_erro"] = (
            f"Nao consegui falar com o robo de cotacoes em {COTACOES_API_BASE_URL}. "
            f"Confirma que ele esta rodando na sua maquina. Detalhe: {exc}"
        )
        row["quote"] = {}
    except Exception as exc:  # noqa: BLE001
        # Qualquer outro erro inesperado (ex.: resposta 200 mas com um corpo
        # que nao e JSON valido) - nao pode derrubar a cotacao das OUTRAS
        # cidades/companhias so por causa de uma que deu problema. Registra
        # como erro dessa origem especifica e segue a vida.
        logger.exception(
            "Erro inesperado cotando %s (solicitacao=%s, companhia=%s)",
            origem, solicitacao_id, companhia,
        )
        row["status"] = "erro"
        row["mensagem_erro"] = f"Erro inesperado ao cotar {origem}: {exc}"
        row["quote"] = {}
    # Marca de qual cidade essa cotacao especifica saiu - importante quando a
    # solicitacao pede varias origens (a original + as proximas automaticas
    # ou as que a pessoa digitou), pra tela mostrar "saindo de Maringa" etc.
    if isinstance(row.get("quote"), dict):
        row["quote"]["origemBusca"] = origem
    try:
        db.add_cotacao_resultado(row)
    except Exception:
        # LATAM e Azul gravam quase ao mesmo tempo, cada uma na sua thread -
        # se por algum motivo a gravacao falhar aqui, nao deixa sumir sem
        # rastro: loga o erro completo (aparece no terminal do Flask) em vez
        # de a companhia simplesmente nao aparecer na tela.
        logger.exception(
            "Falha ao gravar resultado da cotacao (solicitacao=%s, companhia=%s, origem=%s)",
            solicitacao_id, companhia, origem,
        )


def _quote_companhia_todas_origens(
    solicitacao_id: str, dados: dict[str, Any], companhia: str, origens: list[str]
) -> None:
    # Uma companhia so roda uma cotacao de cada vez (o robo usa um perfil de
    # navegador persistente por companhia - rodar duas origens da MESMA
    # companhia ao mesmo tempo tentaria abrir dois navegadores no mesmo
    # perfil e ia dar conflito). LATAM e Azul continuam em paralelo entre si.
    #
    # Cada origem roda isolada: se uma cidade nao achar nada ou der erro, as
    # outras continuam sendo cotadas normalmente - a pessoa tem que ver pelo
    # menos o que deu certo, em vez de uma cidade com problema apagar o
    # resultado das demais.
    for origem in origens:
        try:
            _quote_one(solicitacao_id, dados, companhia, origem)
        except Exception:
            logger.exception(
                "Falha nao tratada cotando %s (solicitacao=%s, companhia=%s) - seguindo pras proximas origens",
                origem, solicitacao_id, companhia,
            )


def _run_quotes(solicitacao_id: str, dados: dict[str, Any]) -> None:
    origens = _origens_para_cotar(dados)
    threads = [
        threading.Thread(
            target=_quote_companhia_todas_origens,
            args=(solicitacao_id, dados, companhia, origens),
            daemon=True,
        )
        for companhia in COMPANHIAS
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    resultados = db.list_cotacoes_resultado(solicitacao_id)
    novo_status = "cotado" if any(r["status"] == "ok" for r in resultados) else "erro"
    db.update_solicitacao(solicitacao_id, {"status": novo_status})
    logger.info(
        "Solicitacao %s cotada (origens=%s), status=%s", solicitacao_id, origens, novo_status
    )


def disparar_cotacao(solicitacao_id: str, dados: dict[str, Any]) -> None:
    """Dispara a cotacao em segundo plano (nao trava a resposta HTTP)."""
    db.update_solicitacao(solicitacao_id, {"status": "cotando"})
    thread = threading.Thread(target=_run_quotes, args=(solicitacao_id, dados), daemon=True)
    thread.start()

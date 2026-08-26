"""Portal MSE - Passagens (projeto novo, unificado).

Duas partes rodam juntas, sempre local na maquina da Ariani:
  - este app.py (Flask): casca do app (login admin, pagina publica, REST
    generico, sincronizacao automatica) + registra os modulos de negocio
    (cada um em modules/<nome>/routes.py, como Blueprint).
  - cotacoes_api.py (FastAPI + Playwright), rodando a parte, na porta 8001:
    robo que cota LATAM/Azul de verdade (modulo "Login LATAM/Azul"). Este
    app.py so chama ele por HTTP (ver cotacoes_client.py).

Onde fica o codigo de cada modulo (pra mexer em um sem precisar entender
os outros):
  - Solicitacao          -> modules/solicitacao/routes.py
  - Fechamento de cartao  -> modules/fechamento_cartao/routes.py
  - Login LATAM/Azul      -> cotacoes_api.py / cotacoes_client.py / cotacoes/
  - API de Pedidos (infra compartilhada por varias abas)
                          -> modules/pedidos_status/routes.py
  - Sistema atual de passagens (infra, usada pelo Aereo)
                          -> modules/passagens_externas/routes.py
  - Aereo, Rodoviario, Hospedagem, Carros, Cadastro manual, Creditos, KPI
                          -> NAO tem rota propria no backend: essas abas
    conversam direto com o REST generico logo abaixo (/rest/v1/<table>).
    O que diferencia uma aba da outra e so a tabela que ela le/grava e o
    JavaScript de cada uma (ver templates/modules/*.js.html). Se precisar
    mudar uma regra de negocio dessas abas especificamente no backend, o
    lugar mais provavel e este proprio arquivo (funcao rest()) ou db.py -
    mas normalmente a mudanca e so no front.

Rotas principais (as que sobraram aqui, o resto esta nos Blueprints acima):
  GET  /                          -> pagina unica (publico ve so Solicitar)
  GET  /login, POST /api/login    -> login do admin (por e-mail, sem senha)
  GET  /portal                    -> redireciona pra "/" (link antigo)
  GET/POST/DELETE /rest/v1/<table> -> REST generico (exige login)
  GET  /api/auto-sync/status      -> status da sincronizacao automatica
"""

from __future__ import annotations

import os
import threading
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

import requests
from flask import Flask, Response, abort, jsonify, redirect, render_template, request, session, url_for

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # dotenv é opcional
    pass

import db
import passagens_sync
import pedidos_api
from auth import check_email, is_logged_in, login_required_api

from modules.solicitacao.routes import bp as solicitacao_bp
from modules.fechamento_cartao.routes import bp as fechamento_cartao_bp
from modules.pedidos_status.routes import bp as pedidos_status_bp
from modules.pedidos_status.routes import _sincronizar_status_pedidos
from modules.passagens_externas.routes import bp as passagens_externas_bp

BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "").strip() or "dev-only-troque-no-env"
application = app

db.init_db()

app.register_blueprint(solicitacao_bp)
app.register_blueprint(fechamento_cartao_bp)
app.register_blueprint(pedidos_status_bp)
app.register_blueprint(passagens_externas_bp)


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _json_default(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise TypeError(f"Nao sei serializar {type(value)}")


@app.get("/")
def index():
    return render_template("portal.html", logged_in=is_logged_in())


@app.get("/portal")
def portal_page():
    # Compatibilidade com o link antigo - agora e tudo a mesma pagina.
    return redirect(url_for("index"))


@app.get("/health")
def health():
    try:
        db.fetch_all("passagens_rows")
        return jsonify({"status": "ok"})
    except Exception as exc:  # pragma: no cover - diagnostico
        return jsonify({"status": "error", "detail": str(exc)}), 500


# --------------------------------------------------------------------------- #
# Login
# --------------------------------------------------------------------------- #
@app.get("/login")
def login_page():
    if is_logged_in():
        return redirect(url_for("portal_page"))
    return render_template("login.html", erro=request.args.get("erro", ""))


@app.post("/api/login")
def api_login():
    payload = request.get_json(silent=True) or request.form.to_dict()
    email = _clean(payload.get("email"))
    if check_email(email):
        session["admin"] = True
        session.permanent = True
        return jsonify({"status": "ok"})
    return jsonify({"status": "error", "detail": "Esse e-mail nao tem acesso a gestao."}), 401


@app.post("/api/logout")
def api_logout():
    session.pop("admin", None)
    return jsonify({"status": "ok"})


def _parse_rest_filters() -> dict[str, str]:
    """Formato PostgREST simples usado pelo front: coluna=eq.valor."""
    filters: dict[str, str] = {}
    for column, raw in request.args.items():
        if column in ("select", "order"):
            continue
        operator, _, value = raw.partition(".")
        if operator != "eq":
            abort(400, f"Operador nao suportado em {column}: {operator}")
        filters[column] = value
    return filters


@app.route("/rest/v1/<table>", methods=["GET", "POST", "DELETE", "OPTIONS"])
def rest(table: str):
    if request.method == "OPTIONS":
        return ("", 204)
    if table not in db.TABLE_REGISTRY:
        abort(404, f"Tabela desconhecida: {table}")
    if not is_logged_in():
        return jsonify({"error": "login necessario"}), 401

    if request.method == "GET":
        filters = _parse_rest_filters()
        order = request.args.get("order") or None
        return jsonify(db.fetch_all(table, filters or None, order))

    if request.method == "DELETE":
        filters = _parse_rest_filters()
        if not filters:
            abort(400, "DELETE sem filtro nao e permitido.")
        db.delete_rows(table, filters)
        return ("", 204)

    payload = request.get_json(silent=True)
    if payload is None:
        abort(400, "Corpo JSON invalido.")
    rows = payload if isinstance(payload, list) else [payload]
    for row in rows:
        db.upsert_row(table, row)
    return (jsonify(rows), 201) if "return=representation" in request.headers.get("Prefer", "") else ("", 201)


@app.after_request
def add_headers(response: Response) -> Response:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    return response


AUTO_SYNC_INTERVALO_SEGUNDOS = int(os.getenv("AUTO_SYNC_INTERVALO_SEGUNDOS", str(30 * 60)))

_auto_sync_status: dict[str, Any] = {
    "ativo": False,
    "ultima_execucao": None,
    "passagens": None,
    "pedidos": None,
}


def _auto_sync_ciclo() -> None:
    agora = datetime.utcnow().isoformat(timespec="seconds")
    _auto_sync_status["ultima_execucao"] = agora
    if passagens_sync.configurado():
        try:
            resultado = passagens_sync.sincronizar(fonte="compradas")
            _auto_sync_status["passagens"] = {"ok": True, "resumo": resultado}
        except Exception as exc:  # nao pode derrubar a thread por um erro de rede
            _auto_sync_status["passagens"] = {"ok": False, "erro": str(exc)}
    else:
        _auto_sync_status["passagens"] = {"ok": False, "erro": "nao configurado"}

    if pedidos_api.configurado():
        try:
            resultado = _sincronizar_status_pedidos()
            _auto_sync_status["pedidos"] = {"ok": True, "resumo": resultado}
        except Exception as exc:
            _auto_sync_status["pedidos"] = {"ok": False, "erro": str(exc)}
    else:
        _auto_sync_status["pedidos"] = {"ok": False, "erro": "nao configurado"}


def _auto_sync_loop() -> None:
    _auto_sync_status["ativo"] = True
    while True:
        try:
            _auto_sync_ciclo()
        except Exception:  # protecao extra - a thread nunca pode morrer
            pass
        time.sleep(AUTO_SYNC_INTERVALO_SEGUNDOS)


def _iniciar_auto_sync() -> None:
    # Com o reloader do Flask (FLASK_DEBUG=1) o processo sobe duas vezes; so
    # inicia a thread na copia "de verdade" (WERKZEUG_RUN_MAIN), senao ela
    # rodaria em dobro. Sem debug, so ha um processo mesmo.
    if os.getenv("FLASK_DEBUG") == "1" and os.getenv("WERKZEUG_RUN_MAIN") != "true":
        return
    threading.Thread(target=_auto_sync_loop, daemon=True).start()


@app.get("/api/auto-sync/status")
@login_required_api
def auto_sync_status():
    return jsonify({**_auto_sync_status, "intervalo_segundos": AUTO_SYNC_INTERVALO_SEGUNDOS})


_iniciar_auto_sync()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="127.0.0.1", port=port, debug=debug, threaded=True)


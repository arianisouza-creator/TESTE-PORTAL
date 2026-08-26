"""Login simples de admin: identifica quem esta entrando pelo e-mail, sem
senha - so um e-mail e liberado a acessar a parte de gestao. Protege as
telas/rotas de cotacao, compra e as abas administrativas; o formulario
publico de solicitacao (/ e /api/solicitacoes) continua sem login.

IMPORTANTE (limitacao de seguranca, pra deixar claro): como nao existe mais
senha, esse controle so evita acesso por engano - qualquer pessoa que
descubra qual e-mail esta liberado (ADMIN_EMAIL) consegue digitar esse
mesmo e-mail e entrar, sem precisar provar que e dona dele de verdade (nao
ha confirmacao por link/codigo). Enquanto o uso for local, na maquina da
Ariani, o risco pratico e baixo; se um dia isso for rodar num servidor
acessivel por outras pessoas, o ideal e trocar por um login de verdade
(ex.: Google/Microsoft) em vez de so conferir o texto do e-mail.
"""

from __future__ import annotations

import os
from functools import wraps

from flask import jsonify, redirect, request, session, url_for

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "ariani.souza@mse.com.br").strip().lower()


def is_logged_in() -> bool:
    return bool(session.get("admin"))


def check_email(email: str) -> bool:
    if not ADMIN_EMAIL:
        # Sem e-mail configurado, nao ha como logar - evita liberar tudo por engano.
        return False
    return (email or "").strip().lower() == ADMIN_EMAIL


def login_required_page(view):
    """Para rotas que servem HTML: sem sessao, manda pro /login."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_logged_in():
            return redirect(url_for("login_page", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def login_required_api(view):
    """Para rotas de API: sem sessao, devolve 401 JSON em vez de redirecionar."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_logged_in():
            return jsonify({"error": "login necessario"}), 401
        return view(*args, **kwargs)
    return wrapped

"""Camada de banco de dados do Portal MSE - Passagens.

Sem ORM, sem dependencia nova para instalar: usa `sqlite3` (builtin do
Python) para rodar local sem precisar instalar nenhum servidor, e o mesmo
`pymysql` que o Portal-Passagens atual ja usa quando DATABASE_URL apontar
para o MySQL de producao. As colunas JSON viram TEXT no SQLite
(json.dumps/json.loads na leitura/escrita) e continuam JSON de verdade no
MySQL - o resto do app (app.py, cotacoes_client.py) nao sabe nem precisa
saber qual dos dois esta rodando por baixo.

Upsert e feito "na mao" (SELECT + UPDATE ou INSERT) em vez de usar
ON DUPLICATE KEY UPDATE (MySQL) ou ON CONFLICT (SQLite), porque a sintaxe
de cada banco e diferente e assim o mesmo codigo funciona nos dois.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SQLITE_PATH = BASE_DIR / "portal_mse.db"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
IS_MYSQL = DATABASE_URL.startswith("mysql")

_local = threading.local()


def _clean(value: str) -> str:
    return (value or "").strip()


# --------------------------------------------------------------------------- #
# Whitelist de tabelas/colunas (mesmo espirito do app.py original): evita SQL
# injection nos nomes de tabela/coluna montados dinamicamente pelo /rest/v1.
# --------------------------------------------------------------------------- #
TABLE_REGISTRY: dict[str, dict[str, Any]] = {
    "internet_contracts": {
        "pk": ["id"],
        "columns": ["id", "empresa", "obra", "vencimento", "numero_contrato", "status_contrato",
                    "inicio_contrato", "fim_contrato", "contato", "obs_contrato", "created_at"],
        "json": [],
    },
    "internet_month_entries": {
        "pk": ["month_key", "contract_id"],
        "columns": ["month_key", "contract_id", "status", "valor", "pedido", "aprovado", "s1",
                    "login_acesso", "senha_acesso", "obs", "created_at"],
        "json": [],
    },
    "internet_lines": {
        "pk": ["id"],
        "columns": ["id", "month_key", "numero", "responsavel", "status", "centro_custo", "percentual", "created_at"],
        "json": [],
    },
    "diarista_cadastros": {
        "pk": ["id"],
        "columns": ["id", "obra_diarista", "nome_diarista", "status_diarista", "inicio_diarista", "fim_diarista", "created_at"],
        "json": [],
    },
    "diarista_month_entries": {
        "pk": ["month_key", "diarista_id"],
        "columns": ["month_key", "diarista_id", "pedido", "valor", "protocolado", "link", "created_at"],
        "json": [],
    },
    "hitachi_collaborators": {
        "pk": ["id"],
        "columns": ["id", "month_key", "empresa", "colaborador", "situacao", "holerite",
                    "comprovante_pagamento", "comprovante_adiantamento", "kit_rescisao", "created_at"],
        "json": [],
    },
    "hitachi_company_docs": {
        "pk": ["id"],
        "columns": ["id", "month_key", "empresa", "documento", "status", "created_at"],
        "json": [],
    },
    "passagens_rows": {
        "pk": ["key"],
        "columns": ["key", "tabela", "item", "updated_at"],
        "json": ["item"],
    },
    "passagens_complements": {
        "pk": ["key"],
        "columns": ["key", "data", "updated_at"],
        "json": ["data"],
    },
    "passagens_creditos": {
        "pk": ["id"],
        "columns": ["id", "data", "updated_at"],
        "json": ["data"],
    },
    "passagens_hospedagens": {
        "pk": ["id"],
        "columns": ["id", "data", "updated_at"],
        "json": ["data"],
    },
    "passagens_carros": {
        "pk": ["id"],
        "columns": ["id", "data", "updated_at"],
        "json": ["data"],
    },
    "passagens_pedidos_status": {
        "pk": ["numero_pedido"],
        "columns": ["numero_pedido", "status_pedido", "fornecedor", "obra", "valor",
                    "data_pedido", "data_entrega", "tipo_descricao", "atualizado_em"],
        "json": [],
    },
    "passagens_fechamentos_fatura": {
        "pk": ["id"],
        "columns": ["id", "data", "criado_em"],
        "json": ["data"],
    },
    "passagens_fatura_rascunhos": {
        "pk": ["id"],
        "columns": ["id", "data", "atualizado_em"],
        "json": ["data"],
    },
}

# Tabelas novas (nao passam pelo /rest/v1 generico - tem rotas dedicadas em
# app.py - mas moram no mesmo banco).
SOLICITACOES_COLUMNS = ["id", "status", "cotar_passagem", "nome_colaborador", "obra",
                         "tipo_passagem", "created_at", "updated_at", "dados"]
SOLICITACOES_JSON = ["dados"]
COTACOES_RESULTADO_COLUMNS = ["id", "solicitacao_id", "companhia", "status", "mensagem_erro",
                               "quote", "aprovada", "criado_em"]
COTACOES_RESULTADO_JSON = ["quote"]


SQLITE_DDL = """
CREATE TABLE IF NOT EXISTS internet_contracts (
  id TEXT PRIMARY KEY, empresa TEXT DEFAULT '', obra TEXT DEFAULT '', vencimento TEXT DEFAULT '',
  numero_contrato TEXT DEFAULT '', status_contrato TEXT DEFAULT 'Ativo', inicio_contrato TEXT DEFAULT '',
  fim_contrato TEXT DEFAULT '', contato TEXT DEFAULT '', obs_contrato TEXT DEFAULT '',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS internet_month_entries (
  month_key TEXT, contract_id TEXT, status TEXT DEFAULT 'Ativo', valor REAL, pedido TEXT DEFAULT '',
  aprovado INTEGER, s1 INTEGER, login_acesso TEXT DEFAULT '', senha_acesso TEXT DEFAULT '',
  obs TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (month_key, contract_id)
);
CREATE TABLE IF NOT EXISTS internet_lines (
  id TEXT PRIMARY KEY, month_key TEXT, numero TEXT DEFAULT '', responsavel TEXT DEFAULT '',
  status TEXT DEFAULT 'Ativo', centro_custo TEXT DEFAULT '', percentual TEXT DEFAULT '',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS diarista_cadastros (
  id TEXT PRIMARY KEY, obra_diarista TEXT DEFAULT '', nome_diarista TEXT DEFAULT '',
  status_diarista TEXT DEFAULT 'Ativo', inicio_diarista TEXT DEFAULT '', fim_diarista TEXT DEFAULT '',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS diarista_month_entries (
  month_key TEXT, diarista_id TEXT, pedido TEXT DEFAULT '', valor REAL, protocolado TEXT DEFAULT '',
  link TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (month_key, diarista_id)
);
CREATE TABLE IF NOT EXISTS hitachi_collaborators (
  id TEXT PRIMARY KEY, month_key TEXT, empresa TEXT DEFAULT 'MSE ENGENHARIA', colaborador TEXT DEFAULT '',
  situacao TEXT DEFAULT 'Ativo', holerite TEXT DEFAULT 'OK', comprovante_pagamento TEXT DEFAULT 'OK',
  comprovante_adiantamento TEXT DEFAULT 'OK', kit_rescisao TEXT DEFAULT 'N/A',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS hitachi_company_docs (
  id TEXT PRIMARY KEY, month_key TEXT, empresa TEXT DEFAULT 'MSE ENGENHARIA', documento TEXT DEFAULT '',
  status TEXT DEFAULT 'OK', created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS passagens_rows (
  key TEXT PRIMARY KEY, tabela TEXT DEFAULT 'passagens', item TEXT NOT NULL,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS passagens_complements (
  key TEXT PRIMARY KEY, data TEXT NOT NULL, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS passagens_creditos (
  id TEXT PRIMARY KEY, data TEXT NOT NULL, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS passagens_hospedagens (
  id TEXT PRIMARY KEY, data TEXT NOT NULL, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS passagens_carros (
  id TEXT PRIMARY KEY, data TEXT NOT NULL, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS passagens_pedidos_status (
  numero_pedido TEXT PRIMARY KEY, status_pedido TEXT DEFAULT '', fornecedor TEXT DEFAULT '',
  obra TEXT DEFAULT '', valor REAL, data_pedido TEXT DEFAULT '', data_entrega TEXT DEFAULT '',
  tipo_descricao TEXT DEFAULT '', atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS passagens_fechamentos_fatura (
  id TEXT PRIMARY KEY, data TEXT NOT NULL, criado_em TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS passagens_fatura_rascunhos (
  id TEXT PRIMARY KEY, data TEXT NOT NULL, atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS passagens_solicitacoes (
  id TEXT PRIMARY KEY, status TEXT DEFAULT 'pendente', cotar_passagem INTEGER DEFAULT 0,
  nome_colaborador TEXT DEFAULT '', obra TEXT DEFAULT '', tipo_passagem TEXT DEFAULT '',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, dados TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS passagens_cotacoes_resultado (
  id TEXT PRIMARY KEY, solicitacao_id TEXT, companhia TEXT DEFAULT '', status TEXT DEFAULT '',
  mensagem_erro TEXT DEFAULT '', quote TEXT, aprovada INTEGER DEFAULT 0,
  criado_em TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def _sqlite_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn"):
        # timeout maior (30s) porque a cotacao roda LATAM e Azul em threads
        # paralelas, cada uma gravando o resultado no mesmo arquivo SQLite
        # quase ao mesmo tempo - sem isso, uma das duas podia esbarrar num
        # "database is locked" e perder o resultado (ficava faltando na tela).
        conn = sqlite3.connect(str(DEFAULT_SQLITE_PATH), check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 30000")
        _local.conn = conn
    return _local.conn


def _mysql_conn():
    import pymysql
    from pymysql.cursors import DictCursor

    parsed = urlparse(DATABASE_URL)
    return pymysql.connect(
        host=parsed.hostname or "localhost",
        port=parsed.port or 3306,
        user=parsed.username or "",
        password=parsed.password or "",
        database=(parsed.path or "/").lstrip("/"),
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
        connect_timeout=10,
    )


def _placeholder() -> str:
    return "%s" if IS_MYSQL else "?"


def _execute(sql: str, params: list | None = None):
    params = params or []
    if IS_MYSQL:
        conn = _mysql_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall() if cur.description else []
                return rows, cur.rowcount
        finally:
            conn.close()
    else:
        conn = _sqlite_conn()
        cur = conn.execute(sql, params)
        conn.commit()
        rows = [dict(row) for row in cur.fetchall()] if cur.description else []
        return rows, cur.rowcount


def init_db() -> None:
    if IS_MYSQL:
        return  # schema aplicado manualmente em producao (mysql-schema.sql)
    conn = _sqlite_conn()
    conn.executescript(SQLITE_DDL)
    conn.commit()
    _maybe_seed()


def _decode_row(meta: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    for col in meta.get("json", []):
        if col in out and isinstance(out[col], (str, bytes)) and out[col] not in (None, ""):
            try:
                out[col] = json.loads(out[col])
            except (TypeError, ValueError):
                pass
    for key, value in list(out.items()):
        if key in ("cotar_passagem", "aprovada", "aprovado", "s1") and not IS_MYSQL:
            out[key] = bool(value)
    return out


def _encode_value(meta: dict[str, Any], column: str, value: Any) -> Any:
    if column in meta.get("json", []):
        return json.dumps(value if value is not None else {}, ensure_ascii=False)
    if isinstance(value, bool) and not IS_MYSQL:
        return 1 if value else 0
    return value


# --------------------------------------------------------------------------- #
# Helpers genericos - usados pelo /rest/v1/<table> e pelas rotas novas.
# --------------------------------------------------------------------------- #
def fetch_all(table_name: str, filters: dict[str, Any] | None = None, order_by: str | None = None) -> list[dict]:
    meta = TABLE_REGISTRY[table_name]
    ph = _placeholder()
    sql = f"SELECT * FROM {table_name}"
    params: list[Any] = []
    if filters:
        clauses = []
        for column, value in filters.items():
            if column not in meta["columns"]:
                continue
            clauses.append(f"{column} = {ph}")
            params.append(value)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
    if order_by:
        column, _, direction = order_by.partition(".")
        if column in meta["columns"]:
            sql += f" ORDER BY {column} {'DESC' if direction.lower() == 'desc' else 'ASC'}"
    rows, _ = _execute(sql, params)
    return [_decode_row(meta, row) for row in rows]


def upsert_row(table_name: str, row: dict[str, Any]) -> None:
    meta = TABLE_REGISTRY[table_name]
    ph = _placeholder()
    values = {c: row[c] for c in row if c in meta["columns"]}
    pk_cols = meta["pk"]
    if not all(c in values for c in pk_cols):
        raise ValueError(f"upsert em {table_name} exige a(s) coluna(s) {pk_cols}")

    where = " AND ".join(f"{c} = {ph}" for c in pk_cols)
    exists_rows, _ = _execute(f"SELECT 1 FROM {table_name} WHERE {where}", [values[c] for c in pk_cols])

    cols = list(values.keys())
    if exists_rows:
        set_cols = [c for c in cols if c not in pk_cols]
        if set_cols:
            set_sql = ", ".join(f"{c} = {ph}" for c in set_cols)
            params = [_encode_value(meta, c, values[c]) for c in set_cols] + [values[c] for c in pk_cols]
            _execute(f"UPDATE {table_name} SET {set_sql} WHERE {where}", params)
    else:
        col_sql = ", ".join(cols)
        ph_sql = ", ".join([ph] * len(cols))
        params = [_encode_value(meta, c, values[c]) for c in cols]
        _execute(f"INSERT INTO {table_name} ({col_sql}) VALUES ({ph_sql})", params)


def delete_rows(table_name: str, filters: dict[str, Any]) -> int:
    meta = TABLE_REGISTRY[table_name]
    ph = _placeholder()
    clauses = [f"{c} = {ph}" for c in filters if c in meta["columns"]]
    params = [v for c, v in filters.items() if c in meta["columns"]]
    if not clauses:
        return 0
    _, rowcount = _execute(f"DELETE FROM {table_name} WHERE " + " AND ".join(clauses), params)
    return rowcount


# --------------------------------------------------------------------------- #
# Solicitacoes
# --------------------------------------------------------------------------- #
_SOL_META = {"pk": ["id"], "columns": SOLICITACOES_COLUMNS, "json": SOLICITACOES_JSON}
_COT_META = {"pk": ["id"], "columns": COTACOES_RESULTADO_COLUMNS, "json": COTACOES_RESULTADO_JSON}


def create_solicitacao(row: dict[str, Any]) -> None:
    ph = _placeholder()
    cols = [c for c in SOLICITACOES_COLUMNS if c in row]
    values = [_encode_value(_SOL_META, c, row[c]) for c in cols]
    col_sql = ", ".join(cols)
    ph_sql = ", ".join([ph] * len(cols))
    _execute(f"INSERT INTO passagens_solicitacoes ({col_sql}) VALUES ({ph_sql})", values)


def update_solicitacao(solicitacao_id: str, values: dict[str, Any]) -> None:
    ph = _placeholder()
    cols = [c for c in values if c in SOLICITACOES_COLUMNS]
    if not cols:
        return
    set_sql = ", ".join(f"{c} = {ph}" for c in cols)
    params = [_encode_value(_SOL_META, c, values[c]) for c in cols] + [solicitacao_id]
    _execute(f"UPDATE passagens_solicitacoes SET {set_sql} WHERE id = {ph}", params)


def get_solicitacao(solicitacao_id: str) -> dict[str, Any] | None:
    ph = _placeholder()
    rows, _ = _execute(f"SELECT * FROM passagens_solicitacoes WHERE id = {ph}", [solicitacao_id])
    return _decode_row(_SOL_META, rows[0]) if rows else None


def list_solicitacoes(status: str | None = None) -> list[dict[str, Any]]:
    ph = _placeholder()
    sql = "SELECT * FROM passagens_solicitacoes"
    params: list[Any] = []
    if status:
        sql += f" WHERE status = {ph}"
        params.append(status)
    sql += " ORDER BY created_at DESC"
    rows, _ = _execute(sql, params)
    return [_decode_row(_SOL_META, row) for row in rows]


def add_cotacao_resultado(row: dict[str, Any]) -> None:
    ph = _placeholder()
    cols = [c for c in COTACOES_RESULTADO_COLUMNS if c in row]
    values = [_encode_value(_COT_META, c, row[c]) for c in cols]
    col_sql = ", ".join(cols)
    ph_sql = ", ".join([ph] * len(cols))
    _execute(f"INSERT INTO passagens_cotacoes_resultado ({col_sql}) VALUES ({ph_sql})", values)


def list_cotacoes_resultado(solicitacao_id: str) -> list[dict[str, Any]]:
    ph = _placeholder()
    rows, _ = _execute(
        f"SELECT * FROM passagens_cotacoes_resultado WHERE solicitacao_id = {ph} ORDER BY criado_em ASC",
        [solicitacao_id],
    )
    return [_decode_row(_COT_META, row) for row in rows]


def set_cotacao_opcao_escolhida(cotacao_id: str, solicitacao_id: str, tipo: str, opcao_index: int) -> None:
    """Marca qual opcao especifica de ida OU de volta (indice dentro de
    quote.detalhes filtrado por tipo) foi escolhida - ida e volta agora sao
    escolhidas de forma independente, tanto pela Ariani no painel quanto
    pelo proprio solicitante na tela publica de cotacao."""
    ph = _placeholder()
    rows, _ = _execute(f"SELECT * FROM passagens_cotacoes_resultado WHERE id = {ph}", [cotacao_id])
    if not rows:
        return
    cot = _decode_row(_COT_META, rows[0])
    quote = cot.get("quote") or {}
    if tipo == "volta":
        quote["voltaEscolhidaIndex"] = opcao_index
    else:
        quote["idaEscolhidaIndex"] = opcao_index
    set_cotacao_aprovada(cotacao_id, solicitacao_id)
    _execute(
        f"UPDATE passagens_cotacoes_resultado SET quote = {ph} WHERE id = {ph}",
        [_encode_value(_COT_META, "quote", quote), cotacao_id],
    )


def set_cotacao_aprovada(cotacao_id: str, solicitacao_id: str) -> None:
    ph = _placeholder()
    _execute(
        f"UPDATE passagens_cotacoes_resultado SET aprovada = {ph} WHERE solicitacao_id = {ph}",
        [0, solicitacao_id],
    )
    _execute(
        f"UPDATE passagens_cotacoes_resultado SET aprovada = {ph} WHERE id = {ph}",
        [1, cotacao_id],
    )


# --------------------------------------------------------------------------- #
# Seed inicial (dados de exemplo pra ter algo pra ver/testar local).
# --------------------------------------------------------------------------- #
def _maybe_seed() -> None:
    seed_path = BASE_DIR / "passagens-import-seed.json"
    if not seed_path.exists():
        return
    existing = fetch_all("passagens_rows")
    if existing:
        return
    try:
        payload = json.loads(seed_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    for item in payload.get("passagensRows", []):
        upsert_row("passagens_rows", {"key": item["id"], "tabela": item.get("tabela", "manual"), "item": item})
    for item in payload.get("passagensComplements", []):
        upsert_row("passagens_complements", {"key": item["key"], "data": item})
    for idx, item in enumerate(payload.get("passagensCreditos", [])):
        item_id = item.get("id") or f"seed-credito-{idx}-{int(time.time())}"
        upsert_row("passagens_creditos", {"id": item_id, "data": item})

"""Módulo Solicitação - formulário público de pedido de viagem + fila
admin (revisar cotação, escolher opção, fechar a compra).

Extraído de app.py sem mudar nada na lógica - só virou Blueprint pra poder
mexer nesse módulo sem precisar entender o resto do app.py. Se um dia
precisar mudar só a Solicitação, é só neste arquivo (e no
templates/modules/solicitacao*.html / solicitacao.js.html do lado do
front) que você mexe.

Depende de: db.py (leitura/gravação genérica), cotacoes_client.py (dispara
o robô de cotação - módulo "Login LATAM/Azul"), auth.py (login_required_api).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Blueprint, abort, jsonify, request
from werkzeug.utils import secure_filename

import db
import cotacoes_client
from auth import login_required_api

BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

bp = Blueprint("solicitacao", __name__)


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _save_upload(field_name: str, solicitacao_id: str) -> str:
    file = request.files.get(field_name)
    if not file or not file.filename:
        return ""
    dest_dir = UPLOADS_DIR / solicitacao_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = secure_filename(file.filename)
    dest = dest_dir / filename
    file.save(dest)
    return f"uploads/{solicitacao_id}/{filename}"


def _find_linked(table: str, solicitacao_id: str) -> dict | None:
    """Acha (se existir) o registro de passagens_hospedagens/passagens_carros
    ja vinculado a uma solicitacao (via data.solicitacaoId)."""
    for row in db.fetch_all(table):
        if (row.get("data") or {}).get("solicitacaoId") == solicitacao_id:
            return row
    return None


def _ensure_hospedagem_e_carro(solicitacao_id: str, dados: dict, nome_colaborador: str, obra: str) -> None:
    """Assim que a solicitacao chega (antes mesmo de cotar/comprar), ja cria o
    registro em Hospedagem/Carros se a pessoa marcou que precisa - assim a
    Ariani ve na hora que precisa providenciar, sem esperar a compra."""
    if _clean(dados.get("necessario_hospedagem")).lower() == "sim":
        hosp_id = _new_id("hosp")
        db.upsert_row("passagens_hospedagens", {
            "id": hosp_id,
            "data": {
                "id": hosp_id,
                "solicitacaoId": solicitacao_id,
                "passagemKey": "",
                "nome": nome_colaborador,
                "obra": obra,
                "tipoAcomodacao": dados.get("hosp_tipo_acomodacao", ""),
                "estadoAcomodacao": dados.get("hosp_estado_acomodacao", ""),
                "cidadeAcomodacao": dados.get("hosp_cidade_acomodacao", ""),
                "dataEntrada": dados.get("hosp_data_entrada", ""),
                "horarioEntrada": dados.get("hosp_horario_entrada", ""),
                "dataSaida": dados.get("hosp_data_saida", ""),
                "horarioSaida": dados.get("hosp_horario_saida", ""),
                "particularidade": dados.get("hosp_particularidade", ""),
                "pago": False,
            },
        })

    if _clean(dados.get("necessario_veiculo")).lower() == "sim":
        carro_id = _new_id("carro")
        db.upsert_row("passagens_carros", {
            "id": carro_id,
            "data": {
                "id": carro_id,
                "solicitacaoId": solicitacao_id,
                "passagemKey": "",
                "nome": nome_colaborador,
                "obra": obra,
                "dataRetirada": dados.get("veic_data_retirada", ""),
                "localRetirada": dados.get("veic_local_retirada", ""),
                "horarioRetirada": dados.get("veic_horario_retirada", ""),
                "dataDevolucao": dados.get("veic_data_devolucao", ""),
                "horarioDevolucao": dados.get("veic_horario_devolucao", ""),
                "observacoes": dados.get("veic_observacoes", ""),
                "pago": False,
            },
        })


@bp.post("/api/solicitacoes")
def criar_solicitacao():
    form = request.form.to_dict()
    solicitacao_id = _new_id("sol")

    documento_path = _save_upload("documento_viajante", solicitacao_id)
    cnh_path = _save_upload("cnh_condutor", solicitacao_id)

    dados = {k: v for k, v in form.items()}
    if documento_path:
        dados["documento_viajante_arquivo"] = documento_path
    if cnh_path:
        dados["cnh_condutor_arquivo"] = cnh_path

    cotar_passagem = _clean(form.get("cotar_passagem")).lower() in ("1", "true", "on", "sim")
    nome_colaborador = _clean(form.get("nome_colaborador"))
    obra = _clean(form.get("obra"))

    row = {
        "id": solicitacao_id,
        "status": "pendente",
        "cotar_passagem": cotar_passagem,
        "nome_colaborador": nome_colaborador,
        "obra": obra,
        "tipo_passagem": _clean(form.get("tipo_passagem")),
        "dados": dados,
    }
    db.create_solicitacao(row)
    _ensure_hospedagem_e_carro(solicitacao_id, dados, nome_colaborador, obra)

    if cotar_passagem:
        cotacoes_client.disparar_cotacao(solicitacao_id, dados)

    return jsonify({"status": "ok", "id": solicitacao_id, "cotando": cotar_passagem}), 201


# --------------------------------------------------------------------------- #
# Publico: acompanhar a propria cotacao e escolher uma opcao de voo.
# O protocolo (id da solicitacao) funciona como a "senha" de quem enviou o
# pedido - so quem tem o protocolo consegue ver/escolher; nao expoe nada de
# outras solicitacoes nem dado administrativo (preco pago, localizador etc).
# --------------------------------------------------------------------------- #
def _solicitacao_publica_view(sol: dict) -> dict:
    d = sol.get("dados") or {}
    cotacoes = db.list_cotacoes_resultado(sol["id"])
    return {
        "id": sol["id"],
        "status": sol["status"],
        "nome_colaborador": sol.get("nome_colaborador", ""),
        "origem": d.get("cidade_ida", ""),
        "destino": d.get("cidade_destino", ""),
        "data_ida": d.get("data_ida", ""),
        "data_volta": d.get("data_volta", ""),
        "completo": d.get("_completo") == "1",
        "cotacoes": [
            {
                "id": c["id"],
                "companhia": c["companhia"],
                "status": c["status"],
                "mensagem_erro": c.get("mensagem_erro", ""),
                "quote": c.get("quote"),
                "aprovada": c.get("aprovada", False),
            }
            for c in cotacoes
        ],
    }


@bp.get("/api/solicitacoes/<solicitacao_id>/publico")
def status_publico_solicitacao(solicitacao_id: str):
    sol = db.get_solicitacao(solicitacao_id)
    if not sol:
        abort(404)
    return jsonify(_solicitacao_publica_view(sol))


@bp.post("/api/solicitacoes/<solicitacao_id>/escolher-opcao")
def escolher_opcao_publica(solicitacao_id: str):
    """A propria pessoa que pediu a passagem escolhe a opcao de voo (ida
    [+volta]) que prefere, direto na tela de acompanhamento - sem precisar
    de login. Isso so marca a preferencia; a Ariani ainda revisa e fecha a
    compra (localizador, valor pago etc) no painel administrativo."""
    sol = db.get_solicitacao(solicitacao_id)
    if not sol:
        abort(404)
    payload = request.get_json(silent=True) or {}
    cotacao_id = payload.get("cotacao_id")
    opcao_index = payload.get("opcao_index")
    tipo = payload.get("tipo") or "ida"
    if not cotacao_id or opcao_index is None:
        abort(400, "cotacao_id e opcao_index sao obrigatorios")
    db.set_cotacao_opcao_escolhida(cotacao_id, solicitacao_id, tipo, int(opcao_index))
    if sol["status"] != "comprado":
        db.update_solicitacao(solicitacao_id, {"status": "aguardando_compra"})
    return jsonify({"status": "ok"})


@bp.post("/api/solicitacoes/<solicitacao_id>/completar")
def completar_solicitacao_publica(solicitacao_id: str):
    """Depois que a pessoa ja cotou e escolheu a opcao de voo na tela rapida
    de 'Cotar Passagem' (que so pede nome/setor/cidades/datas), ela completa
    o resto do pedido aqui (funcao, obra, cpf, hospedagem, veiculo,
    observacoes etc) - so atualiza a mesma solicitacao, sem disparar uma
    nova cotacao. Publica, protegida pelo protocolo (id), igual escolher-opcao."""
    sol = db.get_solicitacao(solicitacao_id)
    if not sol:
        abort(404)
    form = request.form.to_dict()

    documento_path = _save_upload("documento_viajante", solicitacao_id)
    cnh_path = _save_upload("cnh_condutor", solicitacao_id)

    dados = dict(sol.get("dados") or {})
    dados.update({k: v for k, v in form.items()})
    if documento_path:
        dados["documento_viajante_arquivo"] = documento_path
    if cnh_path:
        dados["cnh_condutor_arquivo"] = cnh_path
    dados["_completo"] = "1"

    nome_colaborador = _clean(form.get("nome_colaborador")) or sol.get("nome_colaborador") or ""
    obra = _clean(form.get("obra")) or sol.get("obra") or ""
    tipo_passagem = _clean(form.get("tipo_passagem")) or sol.get("tipo_passagem") or ""

    db.update_solicitacao(solicitacao_id, {
        "dados": dados,
        "nome_colaborador": nome_colaborador,
        "obra": obra,
        "tipo_passagem": tipo_passagem,
    })
    _ensure_hospedagem_e_carro(solicitacao_id, dados, nome_colaborador, obra)
    if sol["status"] != "comprado":
        db.update_solicitacao(solicitacao_id, {"status": "aguardando_compra"})
    return jsonify({"status": "ok"})


# --------------------------------------------------------------------------- #
# Admin: fila de solicitacoes / cotacao / compra
# --------------------------------------------------------------------------- #
@bp.get("/api/solicitacoes")
@login_required_api
def listar_solicitacoes():
    status = request.args.get("status") or None
    return jsonify(db.list_solicitacoes(status))


@bp.get("/api/solicitacoes/<solicitacao_id>")
@login_required_api
def detalhe_solicitacao(solicitacao_id: str):
    sol = db.get_solicitacao(solicitacao_id)
    if not sol:
        abort(404)
    sol["cotacoes"] = db.list_cotacoes_resultado(solicitacao_id)
    return jsonify(sol)


@bp.post("/api/solicitacoes/<solicitacao_id>/cotar")
@login_required_api
def recotar_solicitacao(solicitacao_id: str):
    sol = db.get_solicitacao(solicitacao_id)
    if not sol:
        abort(404)
    cotacoes_client.disparar_cotacao(solicitacao_id, sol["dados"])
    return jsonify({"status": "ok"})


@bp.post("/api/solicitacoes/<solicitacao_id>/aprovar-cotacao")
@login_required_api
def aprovar_cotacao(solicitacao_id: str):
    payload = request.get_json(silent=True) or {}
    cotacao_id = payload.get("cotacao_id")
    opcao_index = payload.get("opcao_index")
    tipo = payload.get("tipo") or "ida"
    if not cotacao_id:
        abort(400, "cotacao_id obrigatorio")
    if opcao_index is not None:
        db.set_cotacao_opcao_escolhida(cotacao_id, solicitacao_id, tipo, int(opcao_index))
    else:
        db.set_cotacao_aprovada(cotacao_id, solicitacao_id)
    return jsonify({"status": "ok"})


@bp.post("/api/solicitacoes/<solicitacao_id>/comprar")
@login_required_api
def comprar_solicitacao(solicitacao_id: str):
    """Fecha a compra: grava em passagens_rows/passagens_complements (mesma
    forma que a aba 'Cadastro manual' ja usa hoje) e, se a solicitacao
    pedia hospedagem/veiculo, cria automaticamente os registros vinculados
    em passagens_hospedagens/passagens_carros - igual ao comportamento que
    ja existe hoje (auto-preenchimento nas outras abas)."""
    sol = db.get_solicitacao(solicitacao_id)
    if not sol:
        abort(404)
    payload = request.get_json(silent=True) or {}
    dados = sol["dados"]

    row_key = _new_id("pg")
    modalidade = "Aereo" if (dados.get("tipo_viagem_modal") or "").strip().lower() == "aviao" else "Rodoviario"

    row_item = {
        "id": row_key,
        "tabela": "manual",
        "tipo": sol.get("tipo_passagem") or dados.get("motivo_viagem", ""),
        "nome_colab": sol.get("nome_colaborador", ""),
        "nome_obra": sol.get("obra", ""),
        "nome_funcao": dados.get("funcao", ""),
        "data_compra": payload.get("dataCompra", datetime.utcnow().date().isoformat()),
        "data_prevista": dados.get("data_ida", ""),
        "data_ida": payload.get("ida", {}).get("dataViagem", dados.get("data_ida", "")),
        "data_ida_volta": payload.get("volta", {}).get("dataViagem", dados.get("data_volta", "")),
        "valor_aereo": payload.get("valorPago", "") if modalidade == "Aereo" else "",
        "valor_rodoviario": payload.get("valorPago", "") if modalidade == "Rodoviario" else "",
        "valor_pago": payload.get("valorPago", ""),
        "data_chegada": payload.get("ida", {}).get("dataChegada", ""),
        "observacao": payload.get("observacaoInterna", ""),
    }
    db.upsert_row("passagens_rows", {"key": row_key, "tabela": "manual", "item": row_item})

    complement_data = {
        "key": row_key,
        "modalidade": modalidade,
        "reembolso": bool(payload.get("reembolso")),
        "ida": payload.get("ida", {}),
        "volta": payload.get("volta", {}),
        "valorAprovado": payload.get("valorAprovado", ""),
        "valorPago": payload.get("valorPago", ""),
        "pagoConfirmado": bool(payload.get("pagoConfirmado")),
        "observacaoInterna": payload.get("observacaoInterna", ""),
    }
    db.upsert_row("passagens_complements", {"key": row_key, "data": complement_data})

    if _clean(dados.get("necessario_hospedagem")).lower() == "sim":
        existente = _find_linked("passagens_hospedagens", solicitacao_id)
        hosp_id = existente["id"] if existente else _new_id("hosp")
        hosp_data = (existente or {}).get("data") or {}
        hosp_data.update({
            "id": hosp_id,
            "solicitacaoId": solicitacao_id,
            "passagemKey": row_key,
            "nome": sol.get("nome_colaborador", ""),
            "obra": sol.get("obra", ""),
            "tipoAcomodacao": hosp_data.get("tipoAcomodacao") or dados.get("hosp_tipo_acomodacao", ""),
            "estadoAcomodacao": hosp_data.get("estadoAcomodacao") or dados.get("hosp_estado_acomodacao", ""),
            "cidadeAcomodacao": hosp_data.get("cidadeAcomodacao") or dados.get("hosp_cidade_acomodacao", ""),
            "dataEntrada": hosp_data.get("dataEntrada") or dados.get("hosp_data_entrada", ""),
            "horarioEntrada": hosp_data.get("horarioEntrada") or dados.get("hosp_horario_entrada", ""),
            "dataSaida": hosp_data.get("dataSaida") or dados.get("hosp_data_saida", ""),
            "horarioSaida": hosp_data.get("horarioSaida") or dados.get("hosp_horario_saida", ""),
            "particularidade": hosp_data.get("particularidade") or dados.get("hosp_particularidade", ""),
            "pago": hosp_data.get("pago", False),
        })
        db.upsert_row("passagens_hospedagens", {"id": hosp_id, "data": hosp_data})

    if _clean(dados.get("necessario_veiculo")).lower() == "sim":
        existente = _find_linked("passagens_carros", solicitacao_id)
        carro_id = existente["id"] if existente else _new_id("carro")
        carro_data = (existente or {}).get("data") or {}
        carro_data.update({
            "id": carro_id,
            "solicitacaoId": solicitacao_id,
            "passagemKey": row_key,
            "nome": sol.get("nome_colaborador", ""),
            "obra": sol.get("obra", ""),
            "dataRetirada": carro_data.get("dataRetirada") or dados.get("veic_data_retirada", ""),
            "localRetirada": carro_data.get("localRetirada") or dados.get("veic_local_retirada", ""),
            "horarioRetirada": carro_data.get("horarioRetirada") or dados.get("veic_horario_retirada", ""),
            "dataDevolucao": carro_data.get("dataDevolucao") or dados.get("veic_data_devolucao", ""),
            "horarioDevolucao": carro_data.get("horarioDevolucao") or dados.get("veic_horario_devolucao", ""),
            "observacoes": carro_data.get("observacoes") or dados.get("veic_observacoes", ""),
            "pago": carro_data.get("pago", False),
        })
        db.upsert_row("passagens_carros", {"id": carro_id, "data": carro_data})

    db.update_solicitacao(solicitacao_id, {"status": "comprado"})
    return jsonify({"status": "ok", "passagemKey": row_key})


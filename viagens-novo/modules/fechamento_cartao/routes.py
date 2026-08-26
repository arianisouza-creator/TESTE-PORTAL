"""Módulo Fechamento de cartão - conferência da fatura do cartão
corporativo contra o que já foi comprado no portal (passagem pelo
localizador, hospedagem por colaborador/valor, e por último a API de
Pedidos).

Extraído de app.py sem mudar nada na lógica - só virou Blueprint. Esse é
o módulo mais isolado do projeto: toda a regra de "como casar um
lançamento da fatura com uma passagem/hospedagem/pedido" está inteira
neste arquivo. Pra mudar só a conferência de fatura, mexe só aqui (e em
templates/modules/fechamento_cartao*.html / fechamento_cartao.js.html).

Depende de: db.py, fatura_parser.py (lê o PDF), pedidos_api.py (consulta a
API de Pedidos), auth.py (login_required_api).
"""
from __future__ import annotations

import unicodedata
import re
import uuid
from pathlib import Path
from typing import Any

from flask import Blueprint, abort, jsonify, request

import db
import fatura_parser
import pedidos_api
from auth import login_required_api

BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

bp = Blueprint("fechamento_cartao", __name__)


def _clean(value: str | None) -> str:
    return (value or "").strip()


# --------------------------------------------------------------------------- #
# Admin: fechamento de fatura do cartao corporativo - a Ariani sobe o PDF da
# fatura (Bradesco/Elo), a gente separa os lancamentos por pessoa e casa os
# de passagem aerea (LATAM/AZUL/GOL, pelo localizador) com o que ja foi
# comprado no portal, pra ela conferir valor e status do pedido de uma vez.
# Nao persiste nada - a fatura e so analisada e o arquivo e apagado na hora.
# --------------------------------------------------------------------------- #
def _to_float_valor(valor: Any) -> float | None:
    if valor is None or valor == "":
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip()
    if "," in texto and texto.count(",") == 1 and texto.rfind(",") > texto.rfind("."):
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def _indexar_passagens_por_localizador() -> dict[str, dict[str, Any]]:
    """So oferece pra casar com a fatura as passagens que AINDA NAO foram
    finalizadas (pagoConfirmado) numa Conferencia OK anterior - uma vez
    confirmada, ela nao pode ser "achada" de novo se a Ariani analisar a
    mesma fatura (ou outra) outra vez (pedido dela: "se eles ja foram
    finalizados nao pode aparecer na conferencia da fatura")."""
    rows = db.fetch_all("passagens_rows")
    complements = db.fetch_all("passagens_complements")
    pago_confirmado: set[str] = {
        c.get("key") for c in complements if (c.get("data") or {}).get("pagoConfirmado")
    }
    indice: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = row.get("key")
        if key in pago_confirmado:
            continue
        item = row.get("item") or {}
        localizador = str(item.get("localizador") or "").strip().upper()
        if not localizador:
            continue
        indice[localizador[:6]] = {
            "key": key,
            "nome_colab": item.get("nome_colab", ""),
            "pedido": item.get("pedido", ""),
            "valor_pago": item.get("valor_pago", ""),
            "companhia": item.get("companhia", ""),
            "origem": item.get("origem", ""),
            "destino": item.get("destino", ""),
        }
    return indice


def _indexar_hospedagens_por_pessoa() -> list[dict[str, Any]]:
    """O jeito de casar um lancamento da fatura com uma hospedagem e por nome
    do colaborador + a data caindo dentro do periodo da estadia, e agora
    (desde que o cadastro de Hospedagem ganhou o campo Valor) tambem pelo
    valor lancado, quando tiver mais de uma hospedagem pro mesmo nome (ver
    _sugerir_hospedagem). So entram aqui hospedagens AINDA NAO finalizadas -
    uma ja confirmada numa Conferencia OK anterior nao pode ser sugerida de
    novo (mesmo motivo da passagem, ver _indexar_passagens_por_localizador)."""
    rows = db.fetch_all("passagens_hospedagens")
    out: list[dict[str, Any]] = []
    for row in rows:
        d = row.get("data") or {}
        if d.get("finalizado"):
            continue
        out.append({
            "id": row.get("id"),
            "nome_colab": d.get("nome", ""),
            "obra": d.get("obra", ""),
            "pedido": d.get("pedido", ""),
            "valor": d.get("valor", ""),
            "status_pedido": d.get("statusPedido", ""),
            "hotel": d.get("cidadeAcomodacao", ""),
            "data_entrada": d.get("dataEntrada", ""),
            "data_saida": d.get("dataSaida", ""),
        })
    return out


def _sugerir_hospedagem(lanc: dict[str, Any], nome_pessoa: str, candidatos: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Pra um lancamento sem correspondencia de passagem, tenta achar uma
    hospedagem do mesmo colaborador da fatura. Aceita: mesmo nome
    (normalizado) e, se a pessoa tiver mais de uma hospedagem, desempata
    primeiro pelo valor (se o cadastro tiver "Valor" preenchido e bater com
    o lancamento da fatura) e, se ainda faltar desempate, pelo mes do
    lancamento caindo dentro do periodo entrada->saida (a data da fatura vem
    sem ano, "DD/MM" - comparar so o mes e uma aproximacao razoavel pra uma
    fatura que cobre so ~1 mes)."""
    alvo = _normalizar_texto(nome_pessoa)
    if not alvo:
        return None
    mesmos = [c for c in candidatos if c["nome_colab"] and _normalizar_texto(c["nome_colab"]) == alvo]
    if not mesmos:
        return None
    if len(mesmos) == 1:
        return mesmos[0]
    valor_lanc = lanc.get("valor")
    if valor_lanc is not None:
        por_valor = [
            c for c in mesmos
            if _to_float_valor(c.get("valor")) is not None
            and abs(_to_float_valor(c.get("valor")) - float(valor_lanc)) < 0.01
        ]
        if len(por_valor) == 1:
            return por_valor[0]
    data_lanc = (lanc.get("data") or "").strip()
    if "/" in data_lanc:
        _, _, mes = data_lanc.partition("/")
        for c in mesmos:
            entrada, saida = c.get("data_entrada") or "", c.get("data_saida") or ""
            if len(entrada) >= 7 and len(saida) >= 7 and entrada[5:7] <= mes <= saida[5:7]:
                return c
    return None  # mais de uma hospedagem e nao deu pra desempatar - nao arrisca


def _sugerir_hospedagem_por_valor(lanc: dict[str, Any], candidatos: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Fallback quando nao acha hospedagem pelo nome do colaborador (o nome
    de quem fez a compra na fatura pode nao bater exatamente com o nome
    cadastrado - cadastro de teste, apelido, etc.). Tenta achar uma
    hospedagem qualquer (de qualquer pessoa) cujo Valor cadastrado bata
    exatamente com o lancamento da fatura. So aceita se a batida for unica,
    pra nao arriscar um match errado - a Ariani sempre confere antes de
    finalizar (o resultado ainda sai com o rotulo "confira")."""
    valor_lanc = lanc.get("valor")
    if valor_lanc is None:
        return None
    bateram = [
        c for c in candidatos
        if _to_float_valor(c.get("valor")) is not None
        and abs(_to_float_valor(c.get("valor")) - float(valor_lanc)) < 0.01
    ]
    if len(bateram) == 1:
        return bateram[0]
    return None


def _normalizar_texto(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", texto).strip().upper()


def _pedidos_ja_usados_em_fechamentos() -> set[str]:
    """Numeros de pedido que ja apareceram em algum fechamento de fatura
    anterior (depois que a Ariani clicou "Conferencia OK"). Um pedido que ja
    entrou num fechamento nao deve ser sugerido de novo pra outro lancamento
    (nem dessa fatura, nem de uma fatura futura) - evita "gastar" o mesmo
    pedido em duas conferencias diferentes por engano."""
    usados: set[str] = set()
    for row in db.fetch_all("passagens_fechamentos_fatura"):
        itens = (row.get("data") or {}).get("itens") or []
        for item in itens:
            numero = _clean(item.get("pedido"))
            if numero:
                usados.add(numero)
    return usados


def _sugerir_pedido(lanc: dict[str, Any], candidatos: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Pra um lancamento da fatura sem correspondencia local, tenta achar um
    pedido com o mesmo valor na lista trazida da API. Se mais de um pedido
    bater no valor, so aceita se der pra desempatar pelo texto (fornecedor/
    tipo) batendo com o historico - senao fica sem sugestao mesmo, pra nao
    arriscar um match errado."""
    valor = lanc.get("valor")
    if valor is None or not candidatos:
        return None
    perto = []
    for c in candidatos:
        valor_c = _to_float_valor(c.get("valor"))
        if valor_c is not None and abs(valor_c - float(valor)) < 0.01:
            perto.append(c)
    if not perto:
        return None
    if len(perto) == 1:
        return perto[0]
    alvo = _normalizar_texto(lanc.get("historico") or lanc.get("companhia") or "")
    if not alvo:
        return None
    for c in perto:
        candidato_txt = _normalizar_texto(f"{c.get('fornecedor', '')} {c.get('tipo_descricao', '')}")
        if candidato_txt and (candidato_txt in alvo or alvo in candidato_txt):
            return c
    return None


@bp.post("/api/fatura/analisar")
@login_required_api
def analisar_fatura():
    file = request.files.get("fatura")
    if not file or not file.filename:
        abort(400, "Envie o arquivo da fatura (PDF).")
    if not file.filename.lower().endswith(".pdf"):
        abort(400, "A fatura precisa ser um arquivo PDF.")

    tmp_dir = UPLOADS_DIR / "tmp"
    tmp_dir.mkdir(exist_ok=True)
    tmp_path = tmp_dir / f"fatura-{uuid.uuid4().hex[:12]}.pdf"
    file.save(tmp_path)
    try:
        resultado = fatura_parser.parse_fatura_pdf(str(tmp_path))
    except Exception as exc:
        return jsonify({"error": f"Nao consegui ler esse PDF: {exc}"}), 400
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass

    indice = _indexar_passagens_por_localizador()
    hospedagens = _indexar_hospedagens_por_pessoa()
    hospedagens_usadas: set[str] = set()  # evita sugerir a mesma hospedagem pra 2 lancamentos
    pedidos_usados = _pedidos_ja_usados_em_fechamentos()
    candidatos_api: list[dict[str, Any]] | None = None  # so busca na API se precisar, e so 1x
    for pessoa in resultado.get("pessoas", []):
        for lanc in pessoa.get("lancamentos", []):
            localizador = lanc.get("localizador", "")
            passagem = indice.get(localizador) if localizador else None
            lanc["passagem_local"] = passagem
            if passagem:
                valor_local = _to_float_valor(passagem.get("valor_pago"))
                valor_fatura = lanc.get("valor")
                lanc["bate_valor"] = (
                    abs(valor_local - valor_fatura) < 0.01
                    if valor_local is not None and valor_fatura is not None
                    else None
                )
                continue
            hospedagens_disponiveis = [h for h in hospedagens if h.get("id") not in hospedagens_usadas]
            hospedagem = _sugerir_hospedagem(lanc, pessoa.get("nome", ""), hospedagens_disponiveis)
            if not hospedagem:
                # Nome nao bateu com nenhuma - tenta so pelo Valor (cadastro de
                # teste, apelido, nome digitado diferente etc.), antes de
                # desistir e cair pra sugestao generica da API de Pedidos.
                hospedagem = _sugerir_hospedagem_por_valor(lanc, hospedagens_disponiveis)
            lanc["hospedagem_local"] = hospedagem
            if hospedagem:
                if hospedagem.get("id"):
                    hospedagens_usadas.add(hospedagem["id"])
                valor_local = _to_float_valor(hospedagem.get("valor"))
                valor_fatura = lanc.get("valor")
                lanc["bate_valor"] = (
                    abs(valor_local - valor_fatura) < 0.01
                    if valor_local is not None and valor_fatura is not None
                    else None
                )
                continue
            if candidatos_api is None:
                todos = pedidos_api.listar_pedidos().get("encontrados") or []
                # Pedido que ja entrou num fechamento anterior nao pode ser
                # sugerido de novo (pedido dela: "se eu ja usei o pedido pra
                # pagamento dessa fatura na anterior, nao posso mais usar
                # esse pedido, ele nao pode ser buscado").
                candidatos_api = [c for c in todos if _clean(c.get("numero_pedido")) not in pedidos_usados]
            lanc["pedido_sugerido"] = _sugerir_pedido(lanc, candidatos_api)
    return jsonify(resultado)


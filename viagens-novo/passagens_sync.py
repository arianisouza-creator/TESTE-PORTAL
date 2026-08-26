"""Sincronizacao com a API do sistema atual de passagens (hub_mse/api_passagens
- https://portalmse.com.br/microservices/hub_mse/api_passagens). Traz pra
dentro deste projeto as viagens que ja foram registradas la (por padrao, as
compradas - fora da lista2), pra nao ter que redigitar nada.

So roda no servidor (Flask) - o token de acesso (PASSAGENS_API_TOKEN) nunca
sai daqui, nunca vai pro navegador. Fica no .env local da Ariani, nunca no
.env.example nem em nenhum arquivo versionado.

Importante: os nomes exatos dos campos que a API devolve em cada item NAO
foram documentados pra mim - so os parametros de busca (fonte, tipo, obra,
nome, funcao, data_viagem, valor_aereo etc.) foram. Por isso o mapeamento
abaixo tenta varios nomes plausiveis pra cada campo (com base nesses mesmos
nomes de parametro) e guarda o item cru completo tambem, pra nao perder nada
caso algum campo venha com um nome diferente do esperado - se algo aparecer
errado depois de sincronizar, da pra olhar o arquivo de amostra salvo aqui do
lado (passagens_api_ultima_amostra.json) e ajustar o mapeamento.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests

import db

BASE_DIR = Path(__file__).resolve().parent
AMOSTRA_PATH = BASE_DIR / "passagens_api_ultima_amostra.json"
# A API manda "obra"/"funcao" como numero (ex: "13") e separadamente
# "nome_obra"/"nome_funcao" com o nome de verdade - mas nem todo item vem
# com o nome junto do numero. Aqui vamos guardando, aos poucos, a relacao
# numero->nome sempre que os dois vierem juntos num item, e reaproveitando
# isso pros itens que so trazem o numero (nesta sincronizacao e nas
# proximas) - assim o nome so falta mesmo se aquele numero nunca apareceu
# com nome em nenhum item ja sincronizado.
NOMES_PATH = BASE_DIR / "nomes_conhecidos.json"

DEFAULT_BASE_URL = "https://portalmse.com.br/microservices/hub_mse/api_passagens"
BASE_URL = (os.getenv("PASSAGENS_API_BASE_URL", "").strip() or DEFAULT_BASE_URL).rstrip("/")
TOKEN = os.getenv("PASSAGENS_API_TOKEN", "").strip()
TIMEOUT = float(os.getenv("PASSAGENS_API_TIMEOUT_SECONDS", "30"))
MAX_PAGINAS = int(os.getenv("PASSAGENS_API_MAX_PAGINAS", "50"))  # trava de seguranca


def configurado() -> bool:
    return bool(TOKEN)


def _get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    resp = requests.get(
        f"{BASE_URL}{path}",
        params=params,
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def _carregar_nomes_conhecidos() -> dict[str, dict[str, str]]:
    try:
        data = json.loads(NOMES_PATH.read_text(encoding="utf-8"))
        return {"obras": dict(data.get("obras") or {}), "funcoes": dict(data.get("funcoes") or {})}
    except (OSError, ValueError):
        return {"obras": {}, "funcoes": {}}


def _salvar_nomes_conhecidos(nomes: dict[str, dict[str, str]]) -> None:
    try:
        NOMES_PATH.write_text(json.dumps(nomes, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    except OSError:
        pass


def _first(item: dict, *keys: str, default: str = ""):
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return default


def _primeiro_trecho(item: dict, sentido: str) -> dict:
    """Os detalhes de voo (companhia, origem, destino, localizador, horario)
    nao vem soltos no item - vem dentro de item['cotacao_itens'][0]['ida'][0]
    (ou ['volta'][0]), descoberto ao inspecionar uma amostra real da API.
    Defensivo: se a forma vier diferente (outra tabela/tipo), devolve {}."""
    try:
        cotacao_itens = item.get("cotacao_itens") or []
        primeiro = cotacao_itens[0] if cotacao_itens else {}
        trechos = primeiro.get(sentido) or []
        return trechos[0] if trechos else {}
    except (AttributeError, IndexError, TypeError):
        return {}


def _mapear_item(item: dict, obra_nomes: dict[str, str] | None = None, funcao_nomes: dict[str, str] | None = None) -> dict:
    obra_nomes = obra_nomes or {}
    funcao_nomes = funcao_nomes or {}
    tabela_origem = str(_first(item, "tabela", default="passagens"))
    item_id = str(_first(item, "id", "cotacao_item_id", "id_passagem", default=""))
    key = f"{tabela_origem}:{item_id}" if item_id else ""

    valor_aereo = _first(item, "valor_aereo", default="")
    valor_rodoviario = _first(item, "valor_rodoviario", default="")

    # "compra" e um resumo direto (companhia/origem/destino/localizador/pedido
    # ja achatados) que a API manda quando a passagem ja foi comprada - mais
    # simples e mais confiavel que ir atras dos trechos de cotacao. So usa
    # cotacao_itens[].ida/volta como reserva pra quando "compra" nao vier.
    compra = item.get("compra") or {}
    trecho_ida = _primeiro_trecho(item, "ida")
    trecho_volta = _primeiro_trecho(item, "volta")

    row_item = {
        "id": item_id,
        "tabela": tabela_origem,
        "tipo": _first(item, "tipo", default=""),
        "nome_colab": _first(item, "nome", "nome_colaborador", "colaborador", default=""),
        # "nome_obra" e o nome de verdade (ex: "AGUAS DO CERRADO"); "obra" e
        # so o numero/codigo da obra (ex: "13") - tem que checar o nome
        # primeiro, senao mostra numero no lugar do nome. Se este item nao
        # trouxe o nome, tenta o dicionario aprendido (mesmo numero, achado
        # com nome em outro item ja sincronizado); numero cru e ultimo recurso.
        "nome_obra": _first(item, "nome_obra", "obra_nome", default="")
            or obra_nomes.get(str(_first(item, "obra", default="")).strip(), "")
            or _first(item, "obra", default=""),
        # mesmo caso da obra: "funcao" vem como numero/codigo (ex: "488"),
        # "nome_funcao" e que traz o nome de verdade (ex: "Diretor de
        # contratos") - prioriza o nome, depois o dicionario aprendido.
        "nome_funcao": _first(item, "nome_funcao", "funcao_nome", "cargo", default="")
            or funcao_nomes.get(str(_first(item, "funcao", default="")).strip(), "")
            or _first(item, "funcao", default=""),
        "data_prevista": _first(item, "data_viagem", "data_prevista", "data_proxima", default=""),
        "data_ida": _first(item, "data_viagem", "data_prevista", "data_proxima", default=""),
        "data_chegada": _first(item, "data_chegada", default="") or _first(trecho_ida, "data_chegada", default=""),
        "valor_aereo": valor_aereo,
        "valor_rodoviario": valor_rodoviario,
        "valor_pago": _first(item, "valor_pago", default=""),
        "valor_referencia": _first(item, "valor_referencia", default=""),
        "valor_aprovado": _first(item, "valor_aprovado", "valor_aprovado_rafael", default="")
            or _first(compra, "valor_aprovado_rafael", default="")
            or _first(item, "valor_referencia", default=""),
        "tipo_contratacao": _first(item, "tipo_contratacao", default=""),
        "status_concluido": _first(item, "status_concluido", "concluido", default=""),
        "pedido": _first(item, "pedido", "numero_pedido", default="") or _first(compra, "numero_pedido", default=""),
        "localizador": _first(item, "localizador", default="") or _first(compra, "localizador", default="") or _first(trecho_ida, "localizador", default="") or _first(trecho_volta, "localizador", default=""),
        "companhia": _first(item, "companhia", default="") or _first(compra, "companhia", default="") or _first(trecho_ida, "companhia", default="") or _first(trecho_volta, "companhia", default=""),
        "origem": _first(item, "origem", "cidade_origem", "cidade_ida", default="") or _first(compra, "origem", default="") or _first(trecho_ida, "origem", default=""),
        "destino": _first(item, "destino", "cidade_destino", "cidade_volta", default="") or _first(compra, "destino", default="") or _first(trecho_ida, "destino", default=""),
        "horario_ida": _first(item, "horario_ida", "hora_ida", default="") or _first(compra, "horario_trajeto_inicio", default="") or _first(trecho_ida, "horario_trajeto_inicio", default=""),
        "horario_volta": _first(item, "horario_volta", "hora_volta", default="") or _first(trecho_volta, "horario_trajeto_inicio", default=""),
        "data_ida_volta": _first(item, "data_volta", "data_retorno", "data_ida_volta", default=""),
        "centro_custo": _first(item, "centro_custo", "centro_de_custo", "cc", "centro_custo_codigo_s1", default="")
            or _first(compra, "centro_custo", "centroCusto", "centro_custo_nome", "centro_custo_codigo_s1", default=""),
        "observacao": "",
        "origem_api": True,
    }
    return {"key": key, "tabela": tabela_origem, "item": row_item, "valor_aereo": valor_aereo,
            "valor_rodoviario": valor_rodoviario}


def sincronizar(fonte: str = "compradas", tabela: str | None = None) -> dict[str, Any]:
    """Busca as paginas da API externa e grava/atualiza em passagens_rows
    (e cria um passagens_complements vazio se ainda nao existir um pra essa
    chave) - nunca sobrescreve um lancamento feito manualmente aqui dentro
    (tabela == 'manual')."""
    if not configurado():
        raise RuntimeError(
            "PASSAGENS_API_TOKEN nao esta configurado no .env deste projeto. "
            "Adicione a linha PASSAGENS_API_TOKEN=... no arquivo .env (na pasta do projeto) e reinicie o app.py."
        )

    existentes = {row["key"]: row for row in db.fetch_all("passagens_rows")}
    complementos_existentes = {row["key"] for row in db.fetch_all("passagens_complements")}

    page = 1
    total_pages = 1
    novos = 0
    atualizados = 0
    ignorados = 0
    amostra = None
    todos_itens: list[dict] = []

    # 1a passada: so busca as paginas e junta tudo em memoria (nao grava
    # ainda) - precisa de todos os itens juntos antes de mapear, pra poder
    # aprender nome de obra/funcao de um item e usar em outro.
    while page <= total_pages and page <= MAX_PAGINAS:
        params: dict[str, Any] = {
            "fonte": fonte,
            "order_by": "data_viagem",
            "order_dir": "DESC",
            "page": page,
            "per_page": 200,
        }
        if tabela:
            params["tabela"] = tabela
        payload = _get("/v1/passagens", params)
        try:
            total_pages = int(payload.get("total_pages") or 1)
        except (TypeError, ValueError):
            total_pages = page
        itens = payload.get("data") or []
        if amostra is None and itens:
            amostra = itens[0]
        todos_itens.extend(itens)
        page += 1

    # 2a passada: aprende numero->nome de obra/funcao com base em TODOS os
    # itens buscados agora, somado ao que ja tinha sido aprendido em
    # sincronizacoes anteriores (nomes_conhecidos.json).
    nomes = _carregar_nomes_conhecidos()
    for raw_item in todos_itens:
        obra_id = str(_first(raw_item, "obra", default="")).strip()
        obra_nome = _first(raw_item, "nome_obra", "obra_nome", default="")
        if obra_id and obra_nome:
            nomes["obras"][obra_id] = obra_nome
        funcao_id = str(_first(raw_item, "funcao", default="")).strip()
        funcao_nome = _first(raw_item, "nome_funcao", "funcao_nome", "cargo", default="")
        if funcao_id and funcao_nome:
            nomes["funcoes"][funcao_id] = funcao_nome
    _salvar_nomes_conhecidos(nomes)

    # 3a passada: mapeia (ja usando os nomes aprendidos) e grava.
    for raw_item in todos_itens:
        mapeado = _mapear_item(raw_item, obra_nomes=nomes["obras"], funcao_nomes=nomes["funcoes"])
        key = mapeado["key"]
        if not key:
            ignorados += 1
            continue
        existente = existentes.get(key)
        if existente and existente.get("tabela") == "manual":
            ignorados += 1
            continue

        db.upsert_row("passagens_rows", {"key": key, "tabela": mapeado["tabela"], "item": mapeado["item"]})
        if key not in complementos_existentes:
            modalidade = "Aereo" if mapeado["valor_aereo"] else "Rodoviario"
            db.upsert_row("passagens_complements", {"key": key, "data": {"modalidade": modalidade}})
            complementos_existentes.add(key)

        if existente:
            atualizados += 1
        else:
            novos += 1
        existentes[key] = {"tabela": mapeado["tabela"]}

    if amostra is not None:
        try:
            AMOSTRA_PATH.write_text(json.dumps(amostra, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    return {"novos": novos, "atualizados": atualizados, "ignorados": ignorados, "paginas": page - 1}

from typing import Any

from cotacoes.connectors import get_connector
from cotacoes.models import ConnectorConfig, QuoteRequest, model_to_dict, utc_now
from cotacoes.storage import load_store, save_store


def mask_secret(value: str | None) -> str:
    text = value or ""
    if not text:
        return ""
    return "****" if len(text) <= 4 else f"{'*' * max(4, len(text) - 4)}{text[-4:]}"


def public_config(config: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in config.items() if key != "senha"}


def company_key(company: str) -> str:
    normalized = (company or "LATAM").strip().upper()
    if "AZUL" in normalized:
        return "AZUL"
    return "LATAM"


def get_config() -> dict[str, Any]:
    store = load_store()
    configs = store.get("configs") or {}
    if not configs and store.get("config"):
        legacy = store.get("config") or {}
        configs[company_key(legacy.get("companhia", "LATAM"))] = legacy
    return {key: public_config(value) for key, value in configs.items()}


def get_company_config(company: str) -> dict[str, Any]:
    store = load_store()
    configs = store.get("configs") or {}
    if not configs and store.get("config"):
        legacy = store.get("config") or {}
        configs[company_key(legacy.get("companhia", "LATAM"))] = legacy
    return public_config(configs.get(company_key(company), {}))


def save_config(config: ConnectorConfig) -> dict[str, Any]:
    store = load_store()
    payload = model_to_dict(config)
    password = payload.pop("senha", None)
    payload["updatedAt"] = utc_now()
    key = company_key(payload.get("companhia", "LATAM"))
    store.setdefault("configs", {})
    existing = store["configs"].get(key) or {}
    payload["senhaMask"] = mask_secret(password) or payload.get("senhaMask", "") or existing.get("senhaMask", "")
    payload["senha"] = password or existing.get("senha", "")
    store["configs"][key] = payload
    store["config"] = payload
    save_store(store)
    return payload


def quote(request: QuoteRequest) -> dict[str, Any]:
    store = load_store()
    configs = store.get("configs") or {}
    if not configs and store.get("config"):
        legacy = store.get("config") or {}
        configs[company_key(legacy.get("companhia", "LATAM"))] = legacy
    requested_company = request.companhia or "LATAM"
    config_payload = configs.get(company_key(requested_company)) or {}
    config = ConnectorConfig(**config_payload)
    connector = get_connector(config.companhia)
    result = connector.quote(config, request)
    quote_payload = model_to_dict(result)
    store.setdefault("quotes", []).insert(0, quote_payload)
    store["quotes"] = store["quotes"][:50]
    save_store(store)
    return quote_payload


def history() -> list[dict[str, Any]]:
    return load_store().get("quotes", [])

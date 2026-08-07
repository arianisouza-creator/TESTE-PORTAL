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


def get_config() -> dict[str, Any]:
    return public_config(load_store().get("config", {}))


def save_config(config: ConnectorConfig) -> dict[str, Any]:
    store = load_store()
    payload = model_to_dict(config)
    password = payload.pop("senha", None)
    payload["senhaMask"] = mask_secret(password) or payload.get("senhaMask", "")
    payload["updatedAt"] = utc_now()
    store["config"] = payload
    save_store(store)
    return payload


def quote(request: QuoteRequest) -> dict[str, Any]:
    store = load_store()
    config_payload = store.get("config") or {}
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

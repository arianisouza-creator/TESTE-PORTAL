import json
import os
from pathlib import Path
from typing import Any


DATA_FILE = Path(os.getenv("COTACOES_DATA_FILE", Path(__file__).resolve().parents[1] / "cotacoes_data.json"))


def empty_store() -> dict[str, Any]:
    return {"config": {}, "configs": {}, "quotes": []}


def mask_secret(value: str | None) -> str:
    text = value or ""
    if not text:
        return ""
    return "****" if len(text) <= 4 else f"{'*' * max(4, len(text) - 4)}{text[-4:]}"


def normalize_config(config: dict[str, Any]) -> dict[str, Any]:
    payload = dict(config or {})
    if not payload.get("usuario") and payload.get("login"):
        payload["usuario"] = payload.get("login")
    if not payload.get("siteUrl"):
        payload["siteUrl"] = payload.get("site_url") or payload.get("url") or ""
    if not payload.get("companhia"):
        payload["companhia"] = "LATAM"
    if payload.get("senha") and not payload.get("senhaMask"):
        payload["senhaMask"] = mask_secret(str(payload.get("senha") or ""))
    return payload


def env_config(company: str, default_site: str) -> dict[str, Any]:
    prefix = f"COTACOES_{company}_"
    payload = {
        "companhia": company,
        "siteUrl": os.getenv(f"{prefix}SITE_URL", default_site).strip(),
        "usuario": os.getenv(f"{prefix}USUARIO", os.getenv(f"{prefix}LOGIN", "")).strip(),
        "senha": os.getenv(f"{prefix}SENHA", os.getenv(f"{prefix}PASSWORD", "")),
        "ambiente": os.getenv(f"{prefix}AMBIENTE", "Producao").strip() or "Producao",
        "status": os.getenv(f"{prefix}STATUS", "Configurado").strip() or "Configurado",
        "observacao": os.getenv(f"{prefix}OBSERVACAO", "").strip(),
    }
    return {key: value for key, value in payload.items() if value not in ("", None)}


def apply_env_configs(store: dict[str, Any]) -> dict[str, Any]:
    configs = {key: normalize_config(value) for key, value in (store.get("configs") or {}).items()}
    if not configs and store.get("config"):
        legacy = normalize_config(store.get("config") or {})
        configs[legacy.get("companhia", "LATAM").upper()] = legacy

    defaults = {
        "LATAM": "https://www.corporate.latamairlines.com/br/pt",
        "AZUL": "https://apps.voeazul.com.br/PortalEmpresas/?ReturnUrl=%2fPortalEmpresas%2fReserva%2fComprar%2f",
    }
    for company, default_site in defaults.items():
        env_payload = env_config(company, default_site)
        if any(key in env_payload for key in ("usuario", "senha", "siteUrl")):
            merged = normalize_config({**configs.get(company, {}), **env_payload})
            configs[company] = merged

    store["configs"] = configs
    if configs:
        store["config"] = configs.get("LATAM") or next(iter(configs.values()))
    return store


def load_store() -> dict[str, Any]:
    if not DATA_FILE.exists():
        return apply_env_configs(empty_store())
    try:
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return apply_env_configs(empty_store())
    return apply_env_configs({
        "config": payload.get("config") or {},
        "configs": payload.get("configs") or {},
        "quotes": payload.get("quotes") or [],
    })


def save_store(payload: dict[str, Any]) -> None:
    DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

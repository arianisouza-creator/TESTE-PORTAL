import json
import os
from pathlib import Path
from typing import Any


DATA_FILE = Path(os.getenv("COTACOES_DATA_FILE", Path(__file__).resolve().parents[1] / "cotacoes_data.json"))


def empty_store() -> dict[str, Any]:
    return {"config": {}, "configs": {}, "quotes": []}


def load_store() -> dict[str, Any]:
    if not DATA_FILE.exists():
        return empty_store()
    try:
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return empty_store()
    return {
        "config": payload.get("config") or {},
        "configs": payload.get("configs") or {},
        "quotes": payload.get("quotes") or [],
    }


def save_store(payload: dict[str, Any]) -> None:
    DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

import copy
import json
import logging
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any


logger = logging.getLogger("cotacoes.storage")

DATA_FILE = Path(os.getenv("COTACOES_DATA_FILE", Path(__file__).resolve().parents[1] / "cotacoes_data.json"))

# Trava simples baseada em arquivo para evitar que duas cotacoes salvando ao
# mesmo tempo corrompam o cotacoes_data.json. Nao precisa de dependencia nova:
# um arquivo .lock funciona em Windows e Linux.
LOCK_FILE = DATA_FILE.with_name(DATA_FILE.name + ".lock")
LOCK_TIMEOUT_SECONDS = float(os.getenv("COTACOES_LOCK_TIMEOUT", "10"))
LOCK_STALE_SECONDS = float(os.getenv("COTACOES_LOCK_STALE_SECONDS", "30"))

# Criptografia opcional da senha em repouso. So entra em acao se
# COTACOES_SECRET_KEY estiver configurada; sem ela o comportamento continua
# identico ao de antes (senha gravada em texto puro), entao nada quebra numa
# instalacao existente que ainda nao tenha essa variavel.
_SECRET_KEY = os.getenv("COTACOES_SECRET_KEY", "").strip()
_ENCRYPTED_PREFIX = "enc::"

try:
    from cryptography.fernet import Fernet, InvalidToken
except ImportError:  # cryptography ainda nao instalado
    Fernet = None
    InvalidToken = Exception


def _build_cipher():
    if not _SECRET_KEY:
        return None
    if Fernet is None:
        logger.warning(
            "COTACOES_SECRET_KEY configurada, mas o pacote 'cryptography' nao esta instalado "
            "(rode: pip install -r requirements-api.txt). Senha sera salva sem criptografia."
        )
        return None
    try:
        return Fernet(_SECRET_KEY.encode("utf-8"))
    except Exception:
        logger.warning(
            "COTACOES_SECRET_KEY invalida (precisa ser uma chave Fernet valida, 32 bytes em base64). "
            "Senha sera salva sem criptografia ate corrigir a chave.",
            exc_info=True,
        )
        return None


_CIPHER = _build_cipher()


def encrypt_senha(value: str | None) -> str | None:
    if not value or _CIPHER is None or value.startswith(_ENCRYPTED_PREFIX):
        return value
    token = _CIPHER.encrypt(value.encode("utf-8")).decode("utf-8")
    return f"{_ENCRYPTED_PREFIX}{token}"


def decrypt_senha(value: str | None) -> str | None:
    if not value or not value.startswith(_ENCRYPTED_PREFIX):
        return value
    if _CIPHER is None:
        # Foi criptografada em algum momento com uma chave que nao temos mais
        # configurada agora. Devolve como esta (nao quebra, mas tambem nao
        # vai autenticar direito ate a COTACOES_SECRET_KEY ser restaurada).
        return value
    token = value[len(_ENCRYPTED_PREFIX):]
    try:
        return _CIPHER.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        logger.warning("Nao consegui decriptar uma senha salva (chave diferente da usada para salvar?).")
        return value


def _apply_to_senha(configs: dict[str, Any], transform) -> None:
    for payload in configs.values():
        if isinstance(payload, dict) and payload.get("senha"):
            payload["senha"] = transform(payload["senha"])


@contextmanager
def _file_lock():
    """Trava por arquivo (.lock) best-effort: se nao conseguir travar dentro
    do timeout, segue sem travar em vez de derrubar a cotacao."""
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + LOCK_TIMEOUT_SECONDS
    fd = None
    while fd is None and time.time() < deadline:
        try:
            fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                age = time.time() - LOCK_FILE.stat().st_mtime
                if age > LOCK_STALE_SECONDS:
                    # trava de um processo que morreu sem limpar; assume travada
                    LOCK_FILE.unlink(missing_ok=True)
                    continue
            except FileNotFoundError:
                continue
            time.sleep(0.05)
    if fd is None:
        logger.warning("Nao consegui obter o lock de %s a tempo; seguindo sem trava.", DATA_FILE.name)
    try:
        yield
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
            LOCK_FILE.unlink(missing_ok=True)


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
        "senha": os.getenv(f"{prefix}SENHA", os.getenv(f"{prefix}PASSWORD", "")).strip(),
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
    with _file_lock():
        try:
            payload = json.loads(DATA_FILE.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            logger.error("cotacoes_data.json corrompido/ilegivel; iniciando store vazio.", exc_info=True)
            return apply_env_configs(empty_store())

    store = {
        "config": payload.get("config") or {},
        "configs": payload.get("configs") or {},
        "quotes": payload.get("quotes") or [],
    }
    # As senhas gravadas por save_store podem estar criptografadas
    # (enc::...); aqui decripta pra uso interno (login no Playwright).
    _apply_to_senha(store["configs"], decrypt_senha)
    if store["config"]:
        store["config"] = dict(store["config"])
        if store["config"].get("senha"):
            store["config"]["senha"] = decrypt_senha(store["config"]["senha"])
    return apply_env_configs(store)


def save_store(payload: dict[str, Any]) -> None:
    # Copia profunda: quem chamou save_store (cotacoes/service.py) continua
    # usando o dict original com a senha em texto puro na resposta da API,
    # so o que vai pro disco e que fica protegido.
    to_write = {
        "config": copy.deepcopy(payload.get("config") or {}),
        "configs": copy.deepcopy(payload.get("configs") or {}),
        "quotes": payload.get("quotes") or [],
    }
    _apply_to_senha(to_write["configs"], encrypt_senha)
    if to_write["config"].get("senha"):
        to_write["config"]["senha"] = encrypt_senha(to_write["config"]["senha"])
    with _file_lock():
        DATA_FILE.write_text(json.dumps(to_write, ensure_ascii=False, indent=2), encoding="utf-8")

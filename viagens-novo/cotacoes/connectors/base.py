import logging
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, TypeVar

from cotacoes.models import ConnectorConfig, QuoteRequest, QuoteResult


logger = logging.getLogger("cotacoes.connectors")

# Onde ficam os prints de tela tirados automaticamente quando uma etapa falha.
# Mesma pasta que os scripts de debug (debug_latam_flow.py) ja usavam manualmente.
SCREENSHOT_DIR = Path(os.getenv("COTACOES_DEBUG_DIR", "debug-output"))

# Quantos screenshots manter por companhia (os mais antigos sao apagados).
SCREENSHOT_KEEP_PER_COMPANY = int(os.getenv("COTACOES_DEBUG_SCREENSHOT_LIMIT", "40"))

T = TypeVar("T")


class CotacaoStageError(RuntimeError):
    """Erro com a etapa exata onde o fluxo de automacao parou."""

    def __init__(self, etapa: str, mensagem: str, screenshot_path: str | None = None):
        super().__init__(mensagem)
        self.etapa = etapa
        self.mensagem = mensagem
        self.screenshot_path = screenshot_path


class QuoteConnector(ABC):
    def __init__(self, companhia: str):
        self.companhia = companhia

    @abstractmethod
    def quote(self, config: ConnectorConfig, request: QuoteRequest) -> QuoteResult:
        raise NotImplementedError


def capture_debug_screenshot(page, company: str, etapa: str) -> str | None:
    """Tira um print da tela no momento da falha. Nunca lanca excecao: se o
    print falhar, so registra um aviso no log e segue o erro original."""
    if page is None:
        return None
    try:
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        safe_etapa = "".join(ch if ch.isalnum() else "_" for ch in etapa)
        filename = f"{company.lower()}_{safe_etapa}_{stamp}.png"
        path = SCREENSHOT_DIR / filename
        page.screenshot(path=str(path), full_page=True, timeout=8000)
        _prune_old_screenshots(company)
        return str(path)
    except Exception:
        logger.warning("Nao consegui capturar screenshot da etapa %s (%s)", etapa, company, exc_info=True)
        return None


def _prune_old_screenshots(company: str, keep: int = SCREENSHOT_KEEP_PER_COMPANY) -> None:
    try:
        files = sorted(
            SCREENSHOT_DIR.glob(f"{company.lower()}_*.png"),
            key=lambda item: item.stat().st_mtime,
        )
        for stale in files[:-keep] if keep > 0 else files:
            stale.unlink(missing_ok=True)
    except Exception:
        logger.debug("Falha ao limpar screenshots antigos de %s", company, exc_info=True)


def run_stage(
    page,
    company: str,
    etapa: str,
    mensagem_erro: str,
    func: Callable[[], T],
    *,
    retries: int = 0,
    retry_delay: float = 2.0,
) -> T:
    """Executa uma etapa do robo com logging por etapa e screenshot automatico
    quando ela falha de vez.

    - Loga inicio/fim de cada etapa (nivel INFO) para dar visibilidade de onde
      o robo esta parado sem precisar acompanhar a tela.
    - Em caso de erro, tira um print da tela (debug-output/) e loga o
      traceback completo (nivel ERROR) antes de converter em CotacaoStageError,
      preservando a mensagem que a etapa original ja usava.
    - `retries` so deve ser usado em etapas seguras de repetir (abrir site,
      esperar/ler resultados). Etapas que clicam ou preenchem formulario nao
      devem usar retry aqui para nao duplicar uma acao ja realizada.
    """
    attempt = 0
    while True:
        attempt += 1
        logger.info("[%s] etapa=%s tentativa=%s iniciando", company, etapa, attempt)
        try:
            result = func()
            logger.info("[%s] etapa=%s concluida", company, etapa)
            return result
        except Exception as exc:
            if attempt <= retries:
                logger.warning(
                    "[%s] etapa=%s falhou na tentativa %s (%s); tentando de novo",
                    company, etapa, attempt, exc,
                )
                time.sleep(retry_delay)
                continue
            screenshot_path = capture_debug_screenshot(page, company, etapa)
            logger.error(
                "[%s] etapa=%s falhou definitivamente (screenshot=%s): %s",
                company, etapa, screenshot_path or "indisponivel", exc,
                exc_info=True,
            )
            mensagem = f"{mensagem_erro}: {exc}" if mensagem_erro else str(exc)
            raise CotacaoStageError(etapa, mensagem, screenshot_path=screenshot_path) from exc

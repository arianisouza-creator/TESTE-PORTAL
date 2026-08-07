import os
import re
import time

from cotacoes.connectors.sandbox import SandboxConnector
from cotacoes.models import ConnectorConfig, QuoteRequest, QuoteResult, utc_now


LATAM_CORPORATE_URL = "https://b2b.corporate.latamairlines.com/br/pt"


class LatamConnector(SandboxConnector):
    """Conector LATAM.

    Por padrao roda em sandbox. Para testar navegador real, configure:
    COTACOES_LATAM_MODE=browser
    """

    def quote(self, config: ConnectorConfig, request: QuoteRequest) -> QuoteResult:
        if os.getenv("COTACOES_LATAM_MODE", "").strip().lower() != "browser":
            result = super().quote(config, request)
            result.status = "LATAM sandbox. Ative COTACOES_LATAM_MODE=browser para testar automacao real."
            return result
        return self._quote_with_browser(config, request)

    def _quote_with_browser(self, config: ConnectorConfig, request: QuoteRequest) -> QuoteResult:
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright nao instalado. Rode: playwright install chromium") from exc

        target_url = (config.siteUrl or LATAM_CORPORATE_URL).strip() or LATAM_CORPORATE_URL
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(locale="pt-BR")
            try:
                page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
                self._try_click(page, re.compile("Fazer Login|Login|Entrar", re.I), timeout=8000)
                self._fill_login_if_visible(page, config)
                self._stop_if_manual_validation(page)
                self._fill_search(page, request)
                self._stop_if_manual_validation(page)
                prices = self._extract_prices(page)
                if not prices:
                    raise RuntimeError("Nao encontrei precos visiveis na tela de resultados da LATAM.")
                menor_preco = min(prices)
                return QuoteResult(
                    id=int(time.time() * 1000),
                    createdAt=utc_now(),
                    modo="browser",
                    companhia="LATAM",
                    origem=request.origem.upper(),
                    destino=request.destino.upper(),
                    dataIda=request.dataIda,
                    dataVolta=request.dataVolta,
                    adultos=request.adultos,
                    cabine=request.cabine,
                    comando=request.comando,
                    menorPreco=menor_preco,
                    detalhes=[{"preco": price} for price in sorted(prices)[:10]],
                    status="Cotacao lida no site LATAM",
                )
            finally:
                browser.close()

    def _try_click(self, page, name_pattern, timeout: int = 5000) -> bool:
        try:
            page.get_by_role("button", name=name_pattern).first.click(timeout=timeout)
            return True
        except Exception:
            try:
                page.get_by_role("link", name=name_pattern).first.click(timeout=timeout)
                return True
            except Exception:
                return False

    def _fill_login_if_visible(self, page, config: ConnectorConfig) -> None:
        if not config.usuario or not config.senha:
            return
        user_inputs = page.locator("input[type='email'], input[type='text'], input:not([type])")
        password_inputs = page.locator("input[type='password']")
        try:
            if user_inputs.count():
                user_inputs.first.fill(config.usuario, timeout=8000)
            if password_inputs.count():
                password_inputs.first.fill(config.senha, timeout=8000)
                self._try_click(page, re.compile("Entrar|Login|Fazer Login|Iniciar", re.I), timeout=8000)
                page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            return

    def _fill_search(self, page, request: QuoteRequest) -> None:
        self._fill_first_match(page, ["Insira uma origem", "Origem", "De"], request.origem)
        self._fill_first_match(page, ["Insira um destino", "Destino", "Para"], request.destino)
        self._fill_first_match(page, ["Ida", "Data de ida"], request.dataIda)
        if request.dataVolta:
            self._fill_first_match(page, ["Volta", "Data de volta"], request.dataVolta)
        self._try_click(page, re.compile("Procurar voos|Buscar voos|Pesquisar", re.I), timeout=10000)
        page.wait_for_load_state("networkidle", timeout=30000)

    def _fill_first_match(self, page, labels: list[str], value: str) -> None:
        for label in labels:
            try:
                page.get_by_label(re.compile(label, re.I)).first.fill(value, timeout=4000)
                return
            except Exception:
                pass
            try:
                page.get_by_placeholder(re.compile(label, re.I)).first.fill(value, timeout=4000)
                return
            except Exception:
                pass

    def _stop_if_manual_validation(self, page) -> None:
        text = page.locator("body").inner_text(timeout=5000).lower()
        blocked_terms = ["captcha", "recaptcha", "token", "codigo de seguranca", "código de segurança", "verificacao", "verificação"]
        if any(term in text for term in blocked_terms):
            raise RuntimeError("A LATAM pediu validacao manual. A automacao deve parar para intervencao humana.")

    def _extract_prices(self, page) -> list[float]:
        text = page.locator("body").inner_text(timeout=10000)
        matches = re.findall(r"(?:R\$\s*|BRL\s*)(\d{1,3}(?:\.\d{3})*,\d{2})", text, flags=re.I)
        prices = []
        for match in matches:
            normalized = match.replace(".", "").replace(",", ".")
            try:
                prices.append(float(normalized))
            except ValueError:
                continue
        return prices

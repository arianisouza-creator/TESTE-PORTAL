import os
import re
import time
import unicodedata
from pathlib import Path

from cotacoes.connectors.base import CotacaoStageError
from cotacoes.connectors.sandbox import SandboxConnector
from cotacoes.models import ConnectorConfig, QuoteRequest, QuoteResult, utc_now


LATAM_CORPORATE_URL = "https://b2b.corporate.latamairlines.com/br/pt"
LATAM_PROFILE_DIR = Path(os.getenv("COTACOES_LATAM_PROFILE_DIR", ".playwright-latam-profile"))


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
        headless = os.getenv("COTACOES_LATAM_HEADLESS", "true").strip().lower() not in {"0", "false", "nao", "não", "no"}
        LATAM_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch_persistent_context(
                user_data_dir=str(LATAM_PROFILE_DIR),
                headless=headless,
                locale="pt-BR",
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            page = browser.pages[0] if browser.pages else browser.new_page()
            try:
                try:
                    page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
                except Exception as exc:
                    raise CotacaoStageError("abertura_site", f"Nao consegui abrir o site da LATAM: {exc}") from exc

                try:
                    self._try_click(page, re.compile("Fazer Login|Login|Entrar", re.I), timeout=8000)
                    self._fill_login_if_visible(page, config)
                    self._wait_for_search_ready(page, headless=headless)
                except Exception as exc:
                    raise CotacaoStageError("login", f"Parou na etapa de login LATAM: {exc}") from exc

                try:
                    self._stop_if_manual_validation(page)
                except Exception as exc:
                    raise CotacaoStageError("validacao_manual", str(exc)) from exc

                try:
                    self._fill_search(page, request)
                except Exception as exc:
                    raise CotacaoStageError("busca", f"Parou ao preencher origem/destino/datas da LATAM: {exc}") from exc

                try:
                    self._stop_if_manual_validation(page)
                except Exception as exc:
                    raise CotacaoStageError("validacao_manual", str(exc)) from exc

                try:
                    ida_options = self._wait_and_extract_flight_options(page, direction="ida")
                except Exception as exc:
                    raise CotacaoStageError("resultados_ida", f"Parou ao ler os voos de ida: {exc}") from exc

                volta_options = []
                if request.dataVolta:
                    try:
                        self._choose_first_light_fare(page)
                        self._wait_for_results_screen(page, direction="volta", timeout=90000)
                        volta_options = self._wait_and_extract_flight_options(page, direction="volta")
                    except Exception as exc:
                        if ida_options:
                            return self._build_result(
                                request=request,
                                detalhes=ida_options,
                                status=f"Cotacao parcial LATAM: ida lida, volta nao concluida (etapa: resultados_volta) ({exc})",
                            )
                        raise CotacaoStageError("resultados_volta", f"Parou ao ler os voos de volta: {exc}") from exc
                all_options = ida_options + volta_options
                prices = [item["preco"] for item in all_options if item.get("preco") is not None]
                if not prices:
                    raise CotacaoStageError("resultados", "Nao encontrei precos visiveis na tela de resultados da LATAM.")
                return self._build_result(
                    request=request,
                    detalhes=all_options,
                    status="Cotacao lida no site LATAM",
                )
            finally:
                browser.close()

    def _build_result(self, request: QuoteRequest, detalhes: list[dict], status: str) -> QuoteResult:
        prices = [item["preco"] for item in detalhes if item.get("preco") is not None]
        menor_preco = min(prices) if prices else 0
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
            detalhes=detalhes[:20],
            status=status,
        )

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
                self._wait_without_blocking(page, timeout=20000)
        except Exception:
            return

    def _fill_search(self, page, request: QuoteRequest) -> None:
        self._choose_trip_type(page, has_return=bool(request.dataVolta))
        self._fill_airport(page, ["Insira uma origem", "Origem", "De"], request.origem, field_text="De")
        self._fill_airport(page, ["Insira um destino", "Destino", "Para"], request.destino, field_text="Para")
        self._select_calendar_date(page, "Ida", request.dataIda)
        if request.dataVolta:
            self._select_calendar_date(page, "Volta", request.dataVolta)
        self._try_click(page, re.compile("Procurar voos|Buscar voos|Pesquisar", re.I), timeout=10000)
        self._wait_without_blocking(page, timeout=30000)

    def _wait_for_search_ready(self, page, headless: bool) -> None:
        timeout_ms = int(os.getenv("COTACOES_LATAM_MANUAL_LOGIN_TIMEOUT", "240")) * 1000
        selectors = [
            "text=Painel principal",
            "text=Procurar voos",
            "input[placeholder*='origem' i]",
            "input[placeholder*='destino' i]",
        ]
        for selector in selectors:
            try:
                page.locator(selector).first.wait_for(state="visible", timeout=timeout_ms)
                return
            except Exception:
                pass
        if not headless:
            raise RuntimeError("Login manual concluido? Nao encontrei o formulario de busca da LATAM depois da espera.")

    def _fill_airport(self, page, labels: list[str], value: str, field_text: str) -> None:
        self._click_field_box(page, field_text)
        field = self._fill_first_match(page, labels, value, press_enter=False)
        self._select_airport_suggestion(page, value)
        try:
            page.keyboard.press("Escape")
            field.press("Tab", timeout=2000)
        except Exception:
            pass
        self._wait_for_airport_selected(page, value)
        try:
            page.mouse.click(20, 20)
        except Exception:
            pass

    def _choose_trip_type(self, page, has_return: bool) -> None:
        label = "Ida e volta" if has_return else "Somente ida"
        self._try_click(page, re.compile(label, re.I), timeout=5000)

    def _click_field_box(self, page, text: str) -> None:
        try:
            page.get_by_text(re.compile(rf"^{re.escape(text)}$", re.I)).first.click(timeout=5000)
        except Exception:
            try:
                page.locator("body").get_by_text(re.compile(rf"^{re.escape(text)}$", re.I)).first.click(timeout=5000)
            except Exception:
                pass

    def _fill_first_match(self, page, labels: list[str], value: str, press_enter: bool = False):
        for label in labels:
            try:
                field = page.get_by_label(re.compile(label, re.I)).first
                field.fill(value, timeout=4000)
                if press_enter:
                    field.press("Enter", timeout=2000)
                return field
            except Exception:
                pass
            try:
                field = page.get_by_placeholder(re.compile(label, re.I)).first
                field.fill(value, timeout=4000)
                if press_enter:
                    field.press("Enter", timeout=2000)
                return field
            except Exception:
                pass
            try:
                field = page.locator(f"input[placeholder*='{label}' i], textarea[placeholder*='{label}' i]").first
                field.fill(value, timeout=4000)
                if press_enter:
                    field.press("Enter", timeout=2000)
                return field
            except Exception:
                pass
        raise RuntimeError(f"Nao encontrei o campo da LATAM para preencher: {', '.join(labels)}")

    def _select_airport_suggestion(self, page, value: str) -> None:
        code = re.escape(str(value or "").strip())
        patterns = [
            re.compile(rf"\b{code}\b", re.I),
            re.compile("Brasil|Brazil", re.I),
        ]
        for pattern in patterns:
            for role in ("option", "button"):
                try:
                    page.get_by_role(role, name=pattern).first.click(timeout=5000)
                    return
                except Exception:
                    pass
            try:
                page.get_by_text(pattern).first.click(timeout=5000)
                return
            except Exception:
                pass
        try:
            page.locator("[role='option'], li, button").filter(has_text=re.compile(rf"\b{code}\b", re.I)).first.click(timeout=5000)
            return
        except Exception:
            pass
        raise RuntimeError(f"Nao consegui clicar na sugestao de aeroporto da LATAM para {value}.")

    def _select_calendar_date(self, page, field_text: str, value: str) -> None:
        target = self._date_parts(value)
        self._click_date_box(page, field_text)
        try:
            page.locator("text=Menor tarifa").first.wait_for(state="visible", timeout=7000)
        except Exception:
            pass
        month_label = self._ensure_calendar_month(page, target["month"], target["year"])
        clicked_by_label = self._click_calendar_day_by_label(page, target["day"], target["month"], target["year"])
        if clicked_by_label:
            page.wait_for_timeout(700)
            if self._wait_for_date_selected(page, value):
                return
        click_point = self._calendar_day_click_point(page, target["day"], month_label)
        if click_point:
            page.mouse.click(click_point["x"], click_point["y"])
            page.wait_for_timeout(700)
            if self._wait_for_date_selected(page, value):
                return
        script_clicked = self._click_calendar_day_in_month(page, target["day"], month_label)
        if script_clicked:
            page.wait_for_timeout(700)
            if self._wait_for_date_selected(page, value):
                return
        raise RuntimeError(f"Cliquei na data {field_text} {self._latam_date(value)}, mas a LATAM nao confirmou a selecao.")

    def _calendar_day_click_point(self, page, day: int, month_label: str) -> dict | None:
        return page.evaluate(
            """
            ({day, monthLabel}) => {
              const normalize = text => (text || '')
                .normalize('NFD')
                .replace(/[\\u0300-\\u036f]/g, '')
                .toLowerCase();
              const blocked = el => {
                const text = normalize([
                  el.getAttribute('aria-label'),
                  el.getAttribute('class'),
                  el.getAttribute('aria-disabled'),
                  el.getAttribute('disabled'),
                ].filter(Boolean).join(' '));
                return /nao disponivel|não disponível|disabled|desabilitado|true/.test(text);
              };
              const visible = el => {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
              };
              const expected = normalize(monthLabel);
              const titles = [...document.querySelectorAll('body *')]
                .filter(visible)
                .filter(el => normalize(el.innerText || el.textContent).includes(expected));
              const title = titles
                .map(el => ({ el, rect: el.getBoundingClientRect() }))
                .filter(item => item.rect.top > 0 && item.rect.top < window.innerHeight - 80)
                .sort((a, b) => (a.rect.width * a.rect.height) - (b.rect.width * b.rect.height))[0];
              if (!title) return null;
              const titleRect = title.rect;
              const centerX = titleRect.left + titleRect.width / 2;
              const monthBox = {
                left: centerX - 175,
                right: centerX + 175,
                top: titleRect.bottom + 18,
                bottom: titleRect.bottom + 330,
              };
              const candidates = [...document.querySelectorAll('button, [role="button"], td, div, span')]
                .filter(visible)
                .filter(el => {
                  const text = (el.innerText || el.textContent || '').trim();
                  if (!text) return false;
                  const firstLine = text.split(/\\s+/)[0];
                  return firstLine === String(day);
                })
                .filter(el => {
                  const rect = el.getBoundingClientRect();
                  const x = rect.left + rect.width / 2;
                  const y = rect.top + rect.height / 2;
                  return x >= monthBox.left && x <= monthBox.right && y >= monthBox.top && y <= monthBox.bottom;
                })
                .filter(el => !blocked(el))
                .sort((a, b) => {
                  const ar = a.getBoundingClientRect();
                  const br = b.getBoundingClientRect();
                  const aButton = a.tagName.toLowerCase() === 'button' || a.getAttribute('role') === 'button';
                  const bButton = b.tagName.toLowerCase() === 'button' || b.getAttribute('role') === 'button';
                  if (aButton !== bButton) return aButton ? -1 : 1;
                  return (ar.width * ar.height) - (br.width * br.height);
                });
              const target = candidates[0];
              if (!target) return null;
              const rect = target.getBoundingClientRect();
              return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
            }
            """,
            {"day": day, "monthLabel": month_label},
        )

    def _click_calendar_day_in_month(self, page, day: int, month_label: str) -> bool:
        return bool(page.evaluate(
            """
            ({day, monthLabel}) => {
              const normalize = text => (text || '')
                .normalize('NFD')
                .replace(/[\\u0300-\\u036f]/g, '')
                .toLowerCase();
              const visible = el => {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
              };
              const blocked = el => {
                const text = normalize([
                  el.getAttribute('aria-label'),
                  el.getAttribute('class'),
                  el.getAttribute('aria-disabled'),
                  el.getAttribute('disabled'),
                ].filter(Boolean).join(' '));
                return /nao disponivel|não disponível|disabled|desabilitado|true/.test(text);
              };
              const expected = normalize(monthLabel);
              const titles = [...document.querySelectorAll('body *')]
                .filter(visible)
                .map(el => ({ el, rect: el.getBoundingClientRect(), text: normalize(el.innerText || el.textContent || '') }))
                .filter(item => item.text.includes(expected))
                .filter(item => item.rect.top > 0 && item.rect.top < window.innerHeight - 80)
                .sort((a, b) => (a.rect.width * a.rect.height) - (b.rect.width * b.rect.height));
              if (!titles.length) return false;
              for (const title of titles) {
                const centerX = title.rect.left + title.rect.width / 2;
                const monthBox = {
                  left: centerX - 175,
                  right: centerX + 175,
                  top: title.rect.bottom + 18,
                  bottom: title.rect.bottom + 330,
                };
                const candidates = [...document.querySelectorAll('button, [role="button"], td, div, span')]
                  .filter(visible)
                  .filter(el => {
                    const text = (el.innerText || el.textContent || '').trim();
                    const firstLine = text.split(/\\s+/)[0];
                    return firstLine === String(day) && !blocked(el);
                  })
                  .filter(el => {
                    const rect = el.getBoundingClientRect();
                    const x = rect.left + rect.width / 2;
                    const y = rect.top + rect.height / 2;
                    return x >= monthBox.left && x <= monthBox.right && y >= monthBox.top && y <= monthBox.bottom;
                  })
                  .sort((a, b) => {
                    const ar = a.getBoundingClientRect();
                    const br = b.getBoundingClientRect();
                    const aButton = a.tagName.toLowerCase() === 'button' || a.getAttribute('role') === 'button';
                    const bButton = b.tagName.toLowerCase() === 'button' || b.getAttribute('role') === 'button';
                    if (aButton !== bButton) return aButton ? -1 : 1;
                    return (ar.width * ar.height) - (br.width * br.height);
                  });
                const target = candidates[0];
                if (!target) continue;
                const rect = target.getBoundingClientRect();
                target.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window, clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2 }));
                target.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window, clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2 }));
                target.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window, clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2 }));
                return true;
              }
              return false;
            }
            """,
            {"day": day, "monthLabel": month_label},
        ))

    def _wait_for_airport_selected(self, page, value: str) -> None:
        code = re.escape(str(value or "").strip())
        try:
            page.get_by_text(re.compile(rf"\b{code}\b.*Brasil", re.I)).first.wait_for(state="visible", timeout=5000)
        except Exception:
            pass

    def _click_date_box(self, page, field_text: str) -> None:
        label = re.escape(field_text)
        candidates = [
            page.locator("div, button").filter(has_text=re.compile(rf"^{label}$", re.I)).last,
            page.get_by_text(re.compile(rf"^{label}$", re.I)).last,
        ]
        for candidate in candidates:
            try:
                candidate.click(timeout=5000)
                return
            except Exception:
                pass
        try:
            page.locator("svg").nth(1 if field_text.lower().startswith("ida") else 2).click(timeout=5000)
            return
        except Exception:
            pass
        raise RuntimeError(f"Nao consegui clicar no campo de data {field_text} da LATAM.")

    def _ensure_calendar_month(self, page, month: int, year: int) -> str:
        month_names = [
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
        ]
        target = f"{month_names[month - 1]} {year}"
        target_norm = self._norm_text(target)
        seen_months: list[str] = []
        for _ in range(14):
            try:
                visible = page.evaluate(
                    """
                    ({target}) => {
                      const normalize = text => (text || '')
                        .normalize('NFD')
                        .replace(/[\\u0300-\\u036f]/g, '')
                        .toLowerCase();
                      const visible = el => {
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
                      };
                      return [...document.querySelectorAll('body *')]
                        .some(el => {
                          const text = normalize(el.innerText || el.textContent || el.getAttribute('aria-label') || '');
                          return visible(el) && text.includes(target);
                        });
                    }
                    """,
                    {"target": target_norm},
                )
                if visible:
                    return target
            except Exception:
                pass
            seen_months = self._calendar_visible_months(page) or seen_months
            if not self._click_calendar_next(page):
                break
        suffix = f" Meses visiveis: {', '.join(seen_months)}." if seen_months else ""
        raise RuntimeError(f"Nao encontrei o mes {target} no calendario da LATAM.{suffix}")

    def _click_calendar_day_by_label(self, page, day: int, month: int, year: int) -> bool:
        month_names = [
            "janeiro", "fevereiro", "março", "abril", "maio", "junho",
            "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
        ]
        month_name = month_names[month - 1]
        for selector in [
            f"button[aria-label*='{day} de {month_name} de {year}']",
            f"button[aria-label*=', {day} de {month_name} de {year}']",
        ]:
            try:
                locator = page.locator(selector)
                for index in range(min(locator.count(), 8)):
                    target = locator.nth(index)
                    aria = (target.get_attribute("aria-label", timeout=1000) or "").lower()
                    classes = (target.get_attribute("class", timeout=1000) or "").lower()
                    if re.search(r"nao disponivel|não disponível|disabled|desabilitado", aria + " " + classes, re.I):
                        continue
                    target.click(timeout=5000, force=True)
                    return True
            except Exception:
                pass
        clicked = page.evaluate(
            """
            ({day, monthName, year}) => {
              const normalize = text => (text || '')
                .normalize('NFD')
                .replace(/[\\u0300-\\u036f]/g, '')
                .toLowerCase();
              const visible = el => {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
              };
              const expectedMonth = normalize(monthName);
              const buttons = [...document.querySelectorAll('button')]
                .filter(visible)
                .filter(button => {
                  const aria = normalize(button.getAttribute('aria-label') || '');
                  const text = normalize(button.innerText || button.textContent || '');
                  const firstLine = text.split(/\\s+/)[0];
                  return (
                    aria.includes(String(day)) &&
                    aria.includes(expectedMonth) &&
                    aria.includes(String(year))
                  ) || (
                    firstLine === String(day) &&
                    aria.includes(expectedMonth) &&
                    aria.includes(String(year))
                  );
                });
              const target = buttons.find(button => !/nao disponivel|não disponível|disabled|desabilitado/i.test(button.getAttribute('aria-label') || button.className || ''));
              if (!target) return false;
              const rect = target.getBoundingClientRect();
              target.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window, clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2 }));
              target.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window, clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2 }));
              target.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window, clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2 }));
              return true;
            }
            """,
            {"day": day, "monthName": month_name, "year": year},
        )
        return bool(clicked)

    def _wait_for_date_selected(self, page, value: str) -> bool:
        target = self._date_parts(value)
        month_abbr = [
            "jan", "fev", "mar", "abr", "mai", "jun",
            "jul", "ago", "set", "out", "nov", "dez",
        ][target["month"] - 1]
        expected = [
            f"{target['day']:02d}/{target['month']:02d}/{target['year']}",
            f"{target['day']}/{target['month']}/{target['year']}",
            f"{target['day']} {month_abbr}",
            f"{target['day']:02d} {month_abbr}",
        ]
        deadline = time.time() + 4
        while time.time() < deadline:
            try:
                text = self._norm_text(page.locator("body").inner_text(timeout=1000))
                if any(item in text for item in expected):
                    return True
            except Exception:
                pass
            try:
                if page.locator("text=Menor tarifa").count() == 0:
                    return True
            except Exception:
                pass
            page.wait_for_timeout(300)
        return False

    def _click_calendar_next(self, page) -> bool:
        before = self._calendar_visible_months(page)
        for selector in [
            ".cn-button-next",
            "button[aria-label*='Avança ao mês seguinte']",
            "button[aria-label*='Avanca ao mes seguinte']",
        ]:
            try:
                page.locator(selector).last.click(timeout=2000)
                page.wait_for_timeout(1400)
                after = self._calendar_visible_months(page)
                if after and (after != before or not before):
                    return True
            except Exception:
                pass
        points = page.evaluate(
            """
            () => {
              const normalize = text => (text || '')
                .normalize('NFD')
                .replace(/[\\u0300-\\u036f]/g, '')
                .toLowerCase();
              const visible = el => {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
              };
              const monthName = '(janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)';
              const monthTitleRe = new RegExp('^\\\\s*' + monthName + '\\\\s+\\\\d{4}\\\\s*$');
              const titles = [...document.querySelectorAll('body *')]
                .filter(visible)
                .map(el => ({ el, rect: el.getBoundingClientRect(), text: normalize(el.innerText || el.textContent || '') }))
                .filter(item => monthTitleRe.test(item.text))
                .filter(item => item.rect.top > 0 && item.rect.top < window.innerHeight - 80)
                .filter(item => item.rect.width >= 60 && item.rect.width <= 360 && item.rect.height >= 10 && item.rect.height <= 70)
                .sort((a, b) => b.rect.left - a.rect.left);
              const rightTitle = titles[0];
              if (!rightTitle) return [];
              const y = rightTitle.rect.top + rightTitle.rect.height / 2;
              const xs = [
                rightTitle.rect.right + 30,
                rightTitle.rect.right + 55,
                rightTitle.rect.right + 80,
                window.innerWidth - 180,
                window.innerWidth - 130,
                window.innerWidth - 90,
              ];
              const points = xs
                .filter(x => x > rightTitle.rect.right && x < window.innerWidth - 8)
                .map(x => ({ x, y }));
              const elementPoints = [...document.querySelectorAll('button, a, [role="button"], svg, path')]
                .filter(visible)
                .map(el => ({ el, rect: el.getBoundingClientRect(), text: normalize(el.innerText || el.textContent || el.getAttribute('aria-label') || el.getAttribute('title') || '') }))
                .filter(item => item.rect.left > rightTitle.rect.right - 8)
                .filter(item => Math.abs((item.rect.top + item.rect.height / 2) - y) < 50)
                .filter(item => item.rect.width <= 90 && item.rect.height <= 90)
                .sort((a, b) => a.rect.left - b.rect.left)
                .map(item => ({ x: item.rect.left + item.rect.width / 2, y: item.rect.top + item.rect.height / 2 }));
              return [...elementPoints, ...points];
            }
            """
        )
        for point in points or []:
            try:
                page.mouse.click(point["x"], point["y"])
                page.wait_for_timeout(1400)
                after = self._calendar_visible_months(page)
                if after and (after != before or not before):
                    return True
            except Exception:
                pass

        script_clicked = page.evaluate(
            """
            () => {
              const normalize = text => (text || '')
                .normalize('NFD')
                .replace(/[\\u0300-\\u036f]/g, '')
                .toLowerCase();
              const visible = el => {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
              };
              const monthName = '(janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)';
              const monthTitleRe = new RegExp('^\\\\s*' + monthName + '\\\\s+\\\\d{4}\\\\s*$');
              const monthTitles = [...document.querySelectorAll('body *')]
                .filter(visible)
                .map(el => ({ el, rect: el.getBoundingClientRect(), text: normalize(el.innerText || el.textContent || '') }))
                .filter(item => monthTitleRe.test(item.text))
                .filter(item => item.rect.top > 0 && item.rect.top < window.innerHeight - 80)
                .filter(item => item.rect.width >= 60 && item.rect.width <= 360 && item.rect.height >= 10 && item.rect.height <= 70)
                .sort((a, b) => b.rect.left - a.rect.left);
              const rightTitle = monthTitles[0];
              if (!rightTitle) return false;
              const targetY = rightTitle.rect.top + rightTitle.rect.height / 2;
              const candidates = [...document.querySelectorAll('button, a, [role="button"], svg, path, div, span')]
                .filter(visible)
                .map(el => ({ el, rect: el.getBoundingClientRect(), text: normalize(el.innerText || el.textContent || el.getAttribute('aria-label') || el.getAttribute('title') || '') }))
                .filter(item => item.rect.left > rightTitle.rect.right - 5)
                .filter(item => Math.abs((item.rect.top + item.rect.height / 2) - targetY) < 45)
                .filter(item => item.rect.width <= 70 && item.rect.height <= 70)
                .sort((a, b) => a.rect.left - b.rect.left);
              const target = candidates.find(item => /proximo|next|>/.test(item.text)) || candidates[0];
              if (target) {
                let el = target.el;
                for (let i = 0; el && i < 4; i += 1) {
                  el.click();
                  el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
                  el = el.parentElement;
                }
                return true;
              }
              return false;
            }
            """
        )
        if script_clicked:
            page.wait_for_timeout(1400)
            after = self._calendar_visible_months(page)
            if after and (after != before or not before):
                return True
        for pattern in [re.compile("proximo|próximo|next", re.I), re.compile(">", re.I)]:
            for role in ("button", "link"):
                try:
                    page.get_by_role(role, name=pattern).last.click(timeout=1500)
                    page.wait_for_timeout(1400)
                    after = self._calendar_visible_months(page)
                    if after and (after != before or not before):
                        return True
                except Exception:
                    pass
        try:
            page.keyboard.press("ArrowRight")
            page.wait_for_timeout(1400)
            after = self._calendar_visible_months(page)
            if after and (after != before or not before):
                return True
        except Exception:
            pass
        try:
            page.locator("svg").last.click(timeout=1500)
            page.wait_for_timeout(1400)
            after = self._calendar_visible_months(page)
            if after and (after != before or not before):
                return True
        except Exception:
            return False
        return False

    def _calendar_visible_months(self, page) -> list[str]:
        try:
            return page.evaluate(
                """
                () => {
                  const normalize = text => (text || '')
                    .normalize('NFD')
                    .replace(/[\\u0300-\\u036f]/g, '')
                    .toLowerCase();
                  const visible = el => {
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
                  };
                  const monthName = '(janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)';
                  const monthTitleRe = new RegExp('^\\\\s*' + monthName + '\\\\s+\\\\d{4}\\\\s*$');
                  return [...document.querySelectorAll('body *')]
                    .filter(visible)
                    .map(el => ({ rect: el.getBoundingClientRect(), text: (el.innerText || el.textContent || '').trim(), norm: normalize(el.innerText || el.textContent || '') }))
                    .filter(item => monthTitleRe.test(item.norm))
                    .filter(item => item.rect.top > 0 && item.rect.top < window.innerHeight - 80)
                    .filter(item => item.rect.width >= 60 && item.rect.width <= 360 && item.rect.height >= 10 && item.rect.height <= 70)
                    .sort((a, b) => a.rect.left - b.rect.left)
                    .map(item => item.text);
                }
                """
            )
        except Exception:
            return []

    def _date_parts(self, value: str) -> dict[str, int]:
        parts = str(value or "").split("-")
        if len(parts) != 3:
            raise RuntimeError(f"Data invalida para LATAM: {value}")
        return {"year": int(parts[0]), "month": int(parts[1]), "day": int(parts[2])}

    def _norm_text(self, value: str) -> str:
        text = unicodedata.normalize("NFD", value or "")
        return "".join(char for char in text if unicodedata.category(char) != "Mn").lower()

    def _latam_date(self, value: str) -> str:
        parts = str(value or "").split("-")
        if len(parts) == 3:
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
        return value

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

    def _extract_flight_options(self, page, direction: str) -> list[dict]:
        label = "voo de ida" if direction == "ida" else "voo de volta"
        try:
            page.get_by_text(re.compile(label, re.I)).first.wait_for(state="visible", timeout=45000)
        except Exception:
            if direction == "volta":
                return []
        text = page.locator("body").inner_text(timeout=15000)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        options = []
        for index, line in enumerate(lines):
            price_match = re.search(r"BRL\s*(\d{1,3}(?:\.\d{3})*,\d{2})", line, flags=re.I)
            if not price_match:
                continue
            window = lines[max(0, index - 12):index + 2]
            joined = " | ".join(window)
            times = re.findall(r"\b([0-2]?\d:[0-5]\d)\b", joined)
            airports = self._clean_airport_codes(re.findall(r"\b([A-Z]{3})\b", joined))
            if len(times) < 2:
                continue
            price = float(price_match.group(1).replace(".", "").replace(",", "."))
            options.append({
                "tipo": direction,
                "saida": times[0] if len(times) >= 1 else "",
                "chegada": times[1] if len(times) >= 2 else "",
                "origem": airports[0] if len(airports) >= 1 else "",
                "destino": airports[1] if len(airports) >= 2 else "",
                "preco": price,
                "moeda": "BRL",
                "tarifa": "A partir de",
                "descricao": joined[:280],
            })
        return options

    def _clean_airport_codes(self, codes: list[str]) -> list[str]:
        ignored = {
            "BRL", "USD", "EUR", "POR", "COM", "SEM", "IDA", "VIA", "MIN",
            "TAX", "TAXA", "AIR", "CEO", "VIP",
        }
        cleaned = []
        for code in codes:
            value = (code or "").strip().upper()
            if len(value) != 3 or value in ignored:
                continue
            if value not in cleaned:
                cleaned.append(value)
        return cleaned

    def _wait_and_extract_flight_options(self, page, direction: str) -> list[dict]:
        self._wait_for_results_screen(page, direction=direction, timeout=90000 if direction == "volta" else 60000)
        for _ in range(12):
            options = self._extract_flight_options(page, direction=direction)
            if options:
                page.wait_for_timeout(1200)
                stable_options = self._extract_flight_options(page, direction=direction)
                return stable_options or options
            page.wait_for_timeout(1000)
        return []

    def _choose_first_light_fare(self, page) -> None:
        page.wait_for_timeout(2000)
        try:
            page.get_by_text(re.compile(r"BRL\s*\d", re.I)).first.click(timeout=10000)
        except Exception:
            page.locator("body").click(timeout=5000)
        try:
            page.get_by_text(re.compile("Light", re.I)).first.wait_for(state="visible", timeout=15000)
        except Exception:
            pass
        try:
            page.get_by_role("button", name=re.compile("Escolher", re.I)).first.click(timeout=15000)
        except Exception as exc:
            raise RuntimeError("Encontrei os voos de ida, mas nao consegui escolher a tarifa Light.") from exc
        try:
            self._wait_without_blocking(page, timeout=30000)
        except Exception:
            pass

    def _wait_for_results_screen(self, page, direction: str, timeout: int = 60000) -> None:
        patterns = [
            re.compile("voo de volta|voos de volta|escolha um voo de volta", re.I),
        ] if direction == "volta" else [
            re.compile("voo de ida|voos de ida|escolha um voo de ida", re.I),
        ]
        deadline = time.time() + (timeout / 1000)
        last_text = ""
        while time.time() < deadline:
            try:
                text = page.locator("body").inner_text(timeout=5000)
                last_text = text[:500]
                if any(pattern.search(text) for pattern in patterns):
                    page.wait_for_timeout(2500)
                    return
            except Exception:
                pass
            page.wait_for_timeout(1500)
        label = "volta" if direction == "volta" else "ida"
        raise RuntimeError(f"A LATAM ainda nao exibiu a tela de {label} depois da selecao. Ultimo texto visivel: {last_text[:180]}")

    def _wait_without_blocking(self, page, timeout: int = 30000) -> None:
        try:
            page.wait_for_load_state("domcontentloaded", timeout=timeout)
        except Exception:
            pass
        try:
            page.wait_for_timeout(1200)
        except Exception:
            pass

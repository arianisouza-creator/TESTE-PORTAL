import os
import re
import time
import unicodedata
from pathlib import Path

from cotacoes.connectors.base import CotacaoStageError, run_stage
from cotacoes.connectors.sandbox import SandboxConnector
from cotacoes.models import ConnectorConfig, QuoteRequest, QuoteResult, utc_now


AZUL_URL = "https://apps.voeazul.com.br/PortalEmpresas/?ReturnUrl=%2fPortalEmpresas%2fReserva%2fComprar%2f"
AZUL_PROFILE_DIR = Path(os.getenv("COTACOES_AZUL_PROFILE_DIR", ".playwright-azul-empresas-profile"))


class AzulConnector(SandboxConnector):
    """Conector Azul Empresas.

    Por padrao roda em sandbox. Para testar navegador real, configure:
    COTACOES_AZUL_MODE=browser
    """

    def quote(self, config: ConnectorConfig, request: QuoteRequest) -> QuoteResult:
        if os.getenv("COTACOES_AZUL_MODE", "").strip().lower() != "browser":
            result = super().quote(config, request)
            result.companhia = "AZUL"
            result.status = "Azul Empresas sandbox. Ative COTACOES_AZUL_MODE=browser para automacao real."
            return result
        return self._quote_with_browser(config, request)

    def _quote_with_browser(self, config: ConnectorConfig, request: QuoteRequest) -> QuoteResult:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright nao instalado. Rode: playwright install chromium") from exc

        target_url = (config.siteUrl or AZUL_URL).strip() or AZUL_URL
        headless = os.getenv("COTACOES_AZUL_HEADLESS", "true").strip().lower() not in {"0", "false", "nao", "não", "no"}
        AZUL_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch_persistent_context(
                user_data_dir=str(AZUL_PROFILE_DIR),
                headless=headless,
                locale="pt-BR",
                viewport={"width": 1280, "height": 900},
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            page = browser.pages[0] if browser.pages else browser.new_page()
            try:
                run_stage(
                    page, "AZUL", "abertura_site",
                    "Nao consegui abrir o site da Azul Empresas",
                    lambda: page.goto(target_url, wait_until="domcontentloaded", timeout=70000),
                    retries=1,
                )

                run_stage(
                    page, "AZUL", "login",
                    "Parou na etapa de login da Azul Empresas",
                    lambda: self._login_if_needed(page, config),
                )

                run_stage(
                    page, "AZUL", "formulario_compra",
                    "Parou ao abrir o formulario de compra da Azul Empresas",
                    lambda: self._wait_for_buy_form(page),
                    retries=1,
                )

                run_stage(
                    page, "AZUL", "busca",
                    "Parou ao preencher origem/destino/datas da Azul Empresas",
                    lambda: self._fill_search(page, request),
                )

                options = run_stage(
                    page, "AZUL", "resultados",
                    "Parou ao ler os voos da Azul Empresas",
                    lambda: self._wait_and_extract_options(page, request),
                    retries=1,
                )
                prices = [item["preco"] for item in options if item.get("preco") is not None]
                if not prices:
                    raise CotacaoStageError("resultados", "Nao encontrei precos visiveis na tela de resultados da Azul Empresas.")
                return QuoteResult(
                    id=int(time.time() * 1000),
                    createdAt=utc_now(),
                    modo="browser",
                    companhia="AZUL",
                    origem=request.origem.upper(),
                    destino=request.destino.upper(),
                    dataIda=request.dataIda,
                    dataVolta=request.dataVolta,
                    adultos=request.adultos,
                    cabine=request.cabine,
                    comando=request.comando,
                    menorPreco=min(prices),
                    detalhes=options[:40],
                    status="Cotacao lida no Portal Empresas Azul",
                )
            finally:
                browser.close()

    def _login_if_needed(self, page, config: ConnectorConfig) -> None:
        text = self._body_text(page)
        if "Fazer Login" not in text and "Usuario" not in self._norm_text(text):
            return
        if not config.usuario or not config.senha:
            raise RuntimeError("A Azul Empresas pediu login. Salve usuario e senha do conector Azul na aba API.")
        self._fill_any(page, ["#username", "input[name='Usuario']", "input[type='text']"], config.usuario)
        self._fill_any(page, ["#password", "input[name='Senha']", "input[type='password']"], config.senha)
        self._verify_password_field(page, config.senha)
        # Tenta primeiro um clique "de verdade" (via Playwright, evento confiavel do
        # navegador) - alguns formularios ignoram o clique simulado via JS que o
        # _submit_login usa, entao antes esse clique "funcionava" (achava o botao)
        # sem realmente disparar o login, e o robo ficava parado na tela de senha.
        try:
            self._click_button(page, re.compile("Fazer Login|Entrar|Login", re.I), timeout=12000)
        except Exception:
            if not self._submit_login(page):
                raise RuntimeError("Nao consegui clicar no botao de login da Azul Empresas.")
        try:
            page.wait_for_load_state("networkidle", timeout=45000)
        except Exception:
            pass
        page.wait_for_timeout(1500)
        erro = self._norm_text(self._body_text(page))
        if re.search(r"senha (corretamente|incorreta|invalida)|usuario ou senha", erro):
            raise RuntimeError(
                "A Azul Empresas recusou o usuario/senha configurados. Confira se nao ficou "
                "espaco em branco extra no inicio/fim ao salvar a senha (na aba API ou no .env)."
            )

    def _verify_password_field(self, page, expected: str) -> None:
        """Confere que o campo de senha ficou exatamente com o valor esperado
        depois do preenchimento - protege contra espacos extras ou teclas que
        nao chegaram a tempo, que fariam o site recusar a senha em silencio."""
        for selector in ["#password", "input[name='Senha']", "input[type='password']"]:
            try:
                field = page.locator(selector).first
                atual = field.input_value(timeout=2000)
            except Exception:
                continue
            if atual == expected:
                return
            if atual:
                # Achou o campo mas o valor nao bate - tenta corrigir de uma vez
                # com fill() direto (sem simular tecla a tecla) antes de seguir.
                try:
                    field.fill(expected, timeout=3000)
                    field.evaluate(
                        """
                        (el) => {
                          el.dispatchEvent(new Event('input', { bubbles: true }));
                          el.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                        """
                    )
                except Exception:
                    pass
                return

    def _wait_for_buy_form(self, page) -> None:
        target_url = "https://apps.voeazul.com.br/PortalEmpresas/Reserva/Comprar/"
        if "Comprar" not in self._body_text(page):
            try:
                page.goto(target_url, wait_until="domcontentloaded", timeout=70000)
            except Exception:
                pass
        timeout_ms = int(os.getenv("COTACOES_AZUL_READY_TIMEOUT", "70")) * 1000
        for selector in ["text=Partindo de", "text=Indo para", "text=Passageiros qualificados", "text=Compre agora"]:
            try:
                page.locator(selector).first.wait_for(state="visible", timeout=timeout_ms)
                return
            except Exception:
                pass
        raise RuntimeError("Nao encontrei a tela Comprar do Portal Empresas Azul.")

    def _fill_search(self, page, request: QuoteRequest) -> None:
        has_return = bool(request.dataVolta)
        if has_return:
            self._choose_trip_type_robust(page, has_return=True)
        self._fill_airport(page, "Partindo de", request.origem)
        self._fill_airport(page, "Indo para", request.destino)
        self._fill_date(page, "Data ida", request.dataIda)
        if has_return:
            self._fill_date(page, "Data volta", request.dataVolta)
        else:
            self._choose_trip_type_robust(page, has_return=False)
        self._select_first_passenger(page)
        self._click_button(page, re.compile("Compre agora|Comprar agora", re.I), timeout=15000)
        try:
            page.wait_for_load_state("networkidle", timeout=60000)
        except Exception:
            pass

    def _choose_trip_type_robust(self, page, has_return: bool) -> None:
        patterns = [re.compile("Ida e volta", re.I)] if has_return else [re.compile(r"So ida|Só ida|Somente ida", re.I)]
        for pattern in patterns:
            try:
                page.get_by_text(pattern).first.click(timeout=3000)
                page.wait_for_timeout(700)
                return
            except Exception:
                pass
            try:
                page.locator("button, a, label, div, span").filter(has_text=pattern).first.click(timeout=3000)
                page.wait_for_timeout(700)
                return
            except Exception:
                pass
        clicked = page.evaluate(
            """
            ({targetIndex}) => {
              const visible = el => {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
              };
              const norm = text => (text || '')
                .normalize('NFD')
                .replace(/[\\u0300-\\u036f]/g, '')
                .toLowerCase();
              const label = [...document.querySelectorAll('body *')]
                .filter(visible)
                .map(el => ({ el, rect: el.getBoundingClientRect(), text: norm(el.innerText || el.textContent) }))
                .filter(item => item.text.includes('tipo de viagem'))
                .sort((a, b) => (a.rect.width * a.rect.height) - (b.rect.width * b.rect.height))[0];
              if (!label) return false;
              const buttons = [...document.querySelectorAll('button, a, label, div, span')]
                .filter(visible)
                .map(el => ({ el, rect: el.getBoundingClientRect(), text: norm(el.innerText || el.textContent) }))
                .filter(item => item.rect.top >= label.rect.bottom - 5 && item.rect.top <= label.rect.bottom + 90)
                .filter(item => /ida|multitrechos/.test(item.text))
                .sort((a, b) => a.rect.left - b.rect.left);
              const target = buttons[targetIndex];
              if (!target) return false;
              target.el.click();
              return true;
            }
            """,
            {"targetIndex": 0 if has_return else 1},
        )
        if clicked:
            page.wait_for_timeout(900)

    def _choose_trip_type(self, page, has_return: bool) -> None:
        pattern = re.compile("Ida e volta", re.I) if has_return else re.compile(r"So ida|Só ida", re.I)
        try:
            page.get_by_text(pattern).first.click(timeout=4000)
        except Exception:
            pass

    def _fill_airport(self, page, label: str, value: str) -> None:
        field = self._field_after_label(page, label)
        search_value = self._airport_search_value(value)
        for attempt in range(3):
            field.click(timeout=7000)
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            page.wait_for_timeout(250)
            field.type(search_value, delay=120, timeout=10000)
            page.wait_for_timeout(1200 + attempt * 700)
            if self._select_airport_suggestion_slow(page, value, search_value):
                break
            page.wait_for_timeout(700)
        else:
            raise RuntimeError(f"Nao consegui selecionar o aeroporto da Azul Empresas para {value}.")
        try:
            page.keyboard.press("Tab")
        except Exception:
            pass

    def _select_airport_suggestion(self, page, value: str) -> None:
        code = re.escape(str(value or "").strip())
        patterns = [
            re.compile(rf"\b{code}\b", re.I),
            re.compile("Londrina|Sao Paulo|São Paulo|Montes|Guarulhos|Congonhas|Viracopos", re.I),
        ]
        for pattern in patterns:
            try:
                page.locator("li, div, span, a").filter(has_text=pattern).first.click(timeout=5000)
                return
            except Exception:
                pass
            try:
                page.get_by_text(pattern).first.click(timeout=5000)
                return
            except Exception:
                pass
        raise RuntimeError(f"Nao consegui selecionar o aeroporto da Azul Empresas para {value}.")

    def _select_airport_suggestion_slow(self, page, value: str, search_value: str) -> bool:
        raw = str(value or "").strip()
        normalized = self._norm_text(raw).upper()
        aliases = {
            "LONDRINA": "Londrina|LDB",
            "SAO PAULO": "Sao Paulo|São Paulo|SAO|CGH|GRU|VCP",
            "SÃO PAULO": "Sao Paulo|São Paulo|SAO|CGH|GRU|VCP",
            "MONTES CLAROS": "Montes Claros|MOC",
            "GUARULHOS": "Guarulhos|GRU",
            "CONGONHAS": "Congonhas|CGH",
            "VIRACOPOS": "Viracopos|VCP",
        }
        patterns = [
            re.compile(rf"\b{re.escape(search_value.strip())}\b", re.I),
            re.compile(re.escape(raw), re.I),
            re.compile(aliases.get(normalized, ""), re.I) if aliases.get(normalized) else None,
            re.compile("Londrina|Sao Paulo|São Paulo|Montes|Guarulhos|Congonhas|Viracopos", re.I),
        ]
        for pattern in [item for item in patterns if item]:
            try:
                page.locator(".ui-autocomplete li, .ui-menu-item, ul li").filter(has_text=pattern).first.wait_for(state="visible", timeout=7000)
            except Exception:
                pass
            for selector in [".ui-autocomplete li, .ui-menu-item, ul li", "li, div, span, a"]:
                try:
                    page.locator(selector).filter(has_text=pattern).first.click(timeout=7000)
                    return True
                except Exception:
                    pass
            try:
                page.get_by_text(pattern).first.click(timeout=5000)
                return True
            except Exception:
                pass
        return False

    def _airport_search_value(self, value: str) -> str:
        raw = str(value or "").strip()
        normalized = self._norm_text(raw).upper()
        aliases = {
            "LONDRINA": "LDB",
            "SAO PAULO": "SAO",
            "SÃO PAULO": "SAO",
            "MONTES CLAROS": "MOC",
            "GUARULHOS": "GRU",
            "CONGONHAS": "CGH",
            "VIRACOPOS": "VCP",
        }
        if len(raw) == 3:
            return raw.upper()
        return aliases.get(normalized, raw)

    def _fill_date(self, page, label: str, value: str) -> None:
        formatted = self._br_date(value)
        digits = formatted.replace("/", "")
        field = self._date_field(page, label)
        for text in (digits, formatted):
            field.click(timeout=7000)
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            page.wait_for_timeout(250)
            field.type(text, delay=130, timeout=7000)
            page.wait_for_timeout(600)
            field.press("Tab", timeout=2000)
            page.wait_for_timeout(400)
            if self._date_field_has_value(field, formatted):
                return
        if self._set_date_with_datepicker(field, formatted):
            return
        field.click(timeout=7000)
        page.wait_for_timeout(500)
        self._click_calendar_day(page, value)
        page.wait_for_timeout(500)
        if not self._date_field_has_value(field, formatted):
            raise RuntimeError(f"Nao consegui preencher a data {formatted} no campo da Azul Empresas.")

    def _date_field_has_value(self, field, formatted: str) -> bool:
        try:
            current = str(field.evaluate("(el) => el.value || ''"))
        except Exception:
            return False
        expected_digits = re.sub(r"\\D", "", formatted)
        current_digits = re.sub(r"\\D", "", current)
        return current_digits == expected_digits

    def _set_date_with_datepicker(self, field, formatted: str) -> bool:
        try:
            return bool(field.evaluate(
                """
                (el, value) => {
                  el.removeAttribute('readonly');
                  el.focus();
                  if (window.jQuery && window.jQuery.fn && window.jQuery.fn.datepicker) {
                    window.jQuery(el).datepicker('setDate', value);
                  }
                  el.value = value;
                  el.dispatchEvent(new Event('input', { bubbles: true }));
                  el.dispatchEvent(new Event('change', { bubbles: true }));
                  el.blur();
                  const digits = text => String(text || '').replace(/\\D/g, '');
                  return digits(el.value) === digits(value);
                }
                """,
                formatted,
            ))
        except Exception:
            return False

    def _date_field(self, page, label: str):
        selectors = []
        if "volta" in self._norm_text(label):
            selectors = ["#comprar-inicio-ida-volta-data-volta", "input[name='DataIdaVoltaDestino']"]
        else:
            selectors = [
                "#comprar-inicio-ida-volta-data-ida",
                "#comprar-inicio-so-ida-data",
                "#comprar-inicio-somente-ida-data",
                "input[name='DataIdaVoltaOrigem']",
                "input[name='DataSoIda']",
                "input[name='DataSomenteIda']",
                "input[id*='data'][id*='ida']",
                "input[class*='datepicker']",
            ]
        for selector in selectors:
            try:
                field = page.locator(selector).first
                field.wait_for(state="visible", timeout=4000)
                return field
            except Exception:
                pass
        try:
            return self._field_after_label(page, "Data")
        except Exception:
            return self._field_after_label(page, label)

    def _click_calendar_day(self, page, value: str) -> None:
        target = self._date_parts(value)
        day = str(target["day"])
        try:
            page.locator(".ui-datepicker-calendar a, td a, button, [role='button']").filter(has_text=re.compile(rf"^{day}$")).first.click(timeout=5000)
            return
        except Exception as exc:
            raise RuntimeError(f"Nao consegui clicar na data {self._br_date(value)} no calendario da Azul Empresas.") from exc

    def _select_first_passenger(self, page) -> None:
        selected_before = self._selected_passenger_count(page)
        clicked = page.evaluate(
            """
            () => {
              const select = document.querySelector('#passageiroQualificado');
              if (select && select.options && select.options.length) {
                select.selectedIndex = 0;
                select.options[0].selected = true;
                select.dispatchEvent(new Event('change', { bubbles: true }));
                select.dispatchEvent(new Event('click', { bubbles: true }));
                return true;
              }
              const visible = el => {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
              };
              const selects = [...document.querySelectorAll('select, option, li, div')]
                .filter(visible)
                .filter(el => /Adalto|Adam|ADAO|ADELINO|Junior|Costa|Silva/i.test(el.innerText || el.textContent || ''));
              const target = selects.find(el => /option/i.test(el.tagName)) || selects[0];
              if (!target) return false;
              target.selected = true;
              target.click();
              target.dispatchEvent(new Event('change', { bubbles: true }));
              return true;
            }
            """
        )
        if not clicked:
            try:
                page.locator("select").first.select_option(index=0, timeout=5000)
            except Exception:
                pass
        self._click_transfer_arrow(page)
        page.wait_for_timeout(800)
        if self._selected_passenger_count(page) <= selected_before:
            self._click_transfer_arrow(page)

    def _click_transfer_arrow(self, page) -> None:
        try:
            page.locator("#btnTransferir").click(timeout=5000)
            return
        except Exception:
            pass
        selectors = [
            "input[type='button'][value*='>']",
            "input[type='button'][title*='Adicionar' i]",
            "input[type='button'][name*='Adicionar' i]",
            "button",
            "a",
            "input[type='submit']",
        ]
        for selector in selectors:
            try:
                page.locator(selector).filter(has_text=re.compile(r">|→|Adicionar", re.I)).first.click(timeout=3000)
                return
            except Exception:
                pass
        clicked_by_value = page.evaluate(
            """
            () => {
              const visible = el => {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
              };
              const candidates = [...document.querySelectorAll('input, button, a')]
                .filter(visible)
                .filter(el => />|→|adicionar|selecionar/i.test(el.value || el.title || el.alt || el.innerText || ''));
              if (!candidates.length) return false;
              candidates[0].click();
              return true;
            }
            """
        )
        if clicked_by_value:
            return
        clicked_by_layout = page.evaluate(
            """
            () => {
              const visible = el => {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
              };
              const norm = text => (text || '')
                .normalize('NFD')
                .replace(/[\\u0300-\\u036f]/g, '')
                .toLowerCase();
              const labels = [...document.querySelectorAll('body *')]
                .filter(visible)
                .map(el => ({ el, rect: el.getBoundingClientRect(), text: norm(el.innerText || el.textContent) }));
              const leftLabel = labels.find(item => item.text.includes('passageiros qualificados'));
              const rightLabel = labels.find(item => item.text.includes('passageiros selecionados'));
              if (!leftLabel || !rightLabel) return false;
              const leftBox = [...document.querySelectorAll('select, div, textarea')]
                .filter(visible)
                .map(el => ({ el, rect: el.getBoundingClientRect() }))
                .filter(item => item.rect.left >= leftLabel.rect.left - 20 && item.rect.top >= leftLabel.rect.top)
                .sort((a, b) => (a.rect.top - b.rect.top) || (b.rect.width * b.rect.height - a.rect.width * a.rect.height))[0];
              const rightBox = [...document.querySelectorAll('select, div, textarea')]
                .filter(visible)
                .map(el => ({ el, rect: el.getBoundingClientRect() }))
                .filter(item => item.rect.left >= rightLabel.rect.left - 20 && item.rect.top >= rightLabel.rect.top)
                .sort((a, b) => (a.rect.top - b.rect.top) || (b.rect.width * b.rect.height - a.rect.width * a.rect.height))[0];
              if (!leftBox || !rightBox) return false;
              const betweenLeft = leftBox.rect.right;
              const betweenRight = rightBox.rect.left;
              const buttons = [...document.querySelectorAll('button, input, a, div')]
                .filter(visible)
                .map(el => ({ el, rect: el.getBoundingClientRect() }))
                .filter(item => item.rect.left > betweenLeft && item.rect.right < betweenRight)
                .filter(item => item.rect.top >= leftBox.rect.top - 10 && item.rect.top <= leftBox.rect.bottom)
                .filter(item => item.rect.width <= 90 && item.rect.height <= 90)
                .sort((a, b) => a.rect.top - b.rect.top);
              const target = buttons[0];
              if (!target) return false;
              target.el.click();
              return true;
            }
            """
        )
        if clicked_by_layout:
            return
        clicked = page.evaluate(
            """
            () => {
              const visible = el => {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
              };
              const buttons = [...document.querySelectorAll('button, input, a, div')]
                .filter(visible)
                .map(el => ({ el, rect: el.getBoundingClientRect(), text: el.innerText || el.value || el.title || '' }))
                .filter(item => item.rect.width <= 80 && item.rect.height <= 80)
                .filter(item => /#55|rgb\\(.*(70|80|90|100|120).*,.*(170|180|190|200).*,.*(60|70|80|90|100).*/i.test(getComputedStyle(item.el).backgroundColor) || />|→/.test(item.text));
              const target = buttons.sort((a, b) => a.rect.top - b.rect.top)[0];
              if (!target) return false;
              target.el.click();
              return true;
            }
            """
        )
        if not clicked:
            raise RuntimeError("Nao consegui clicar na seta verde para selecionar o passageiro da Azul Empresas.")

    def _selected_passenger_count(self, page) -> int:
        try:
            return int(page.evaluate(
                """
                () => {
                  const selected = document.querySelector('#passageiroSelecionado');
                  if (selected && selected.options) return selected.options.length;
                  const text = document.body.innerText || '';
                  const marker = text.indexOf('Passageiros selecionados');
                  if (marker < 0) return 0;
                  return text.slice(marker, marker + 500).split('\\n').filter(line => /[A-Za-z]{3,}/.test(line) && !/Passageiros selecionados/.test(line)).length;
                }
                """
            ))
        except Exception:
            return 0

    def _wait_and_extract_options(self, page, request: QuoteRequest) -> list[dict]:
        for _ in range(20):
            options = self._extract_options(page, request)
            if options:
                page.wait_for_timeout(1500)
                return self._extract_options(page, request) or options
            page.wait_for_timeout(1500)
        return []

    def _extract_options(self, page, request: QuoteRequest) -> list[dict]:
        text = self._body_text(page)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        requested_origin = self._airport_search_value(request.origem).upper()
        requested_destination = self._airport_search_value(request.destino).upper()
        # So aceita precos depois de reconhecer um cabecalho de rota que bate
        # com a busca (ida: origem->destino, volta: destino->origem). A
        # pagina de resultados as vezes mostra blocos de "outras rotas" ou
        # "outras datas" com precos de trechos completamente diferentes -
        # sem esse filtro, esses precos entravam misturados na lista.
        #
        # O cabecalho "para o trajeto XXX -> YYY" as vezes vem com o codigo
        # do aeroporto e o icone entre eles quebrados em "pilulas"/linhas
        # separadas (cada uma vira uma linha propria no texto da pagina) -
        # entao em vez de exigir os dois codigos na MESMA linha, procura numa
        # janela de poucas linhas ao redor de cada ocorrencia de "trajeto".
        headers: list[tuple[int, str]] = []
        for i, line in enumerate(lines):
            if "trajeto" not in line.lower():
                continue
            window_codes = re.findall(r"\b([A-Z]{3})\b", " ".join(lines[i:i + 6]).upper())
            direction = None
            for j in range(len(window_codes) - 1):
                if window_codes[j] == requested_origin and window_codes[j + 1] == requested_destination:
                    direction = "ida"
                    break
                if window_codes[j] == requested_destination and window_codes[j + 1] == requested_origin:
                    direction = "volta"
                    break
            if direction:
                headers.append((i, direction))
        # Descarta cabecalhos redundantes do mesmo bloco visual (linhas bem
        # proximas, mesma direcao) - fica so a primeira ocorrencia de cada.
        dedup_headers: list[tuple[int, str]] = []
        for idx, direction in headers:
            if dedup_headers and dedup_headers[-1][1] == direction and idx - dedup_headers[-1][0] < 6:
                continue
            dedup_headers.append((idx, direction))
        headers = dedup_headers

        def direction_at(index: int) -> str | None:
            current = None
            for header_index, header_direction in headers:
                if header_index <= index:
                    current = header_direction
                else:
                    break
            return current

        options = []
        for index, line in enumerate(lines):
            direction = direction_at(index)
            if direction is None:
                continue
            price_match = re.search(r"R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})", line)
            if not price_match:
                continue
            window = lines[max(0, index - 14):index + 8]
            joined = " | ".join(window)
            times = re.findall(r"\b([0-2]?\d:[0-5]\d)\b", joined)
            if not re.search("Operado por Azul|Voo|Paradas|Azul", joined, flags=re.I):
                continue
            if re.search(r"Taxas de embarque|Subtotal|Preco total|Preço total|Adulto\\(s\\)|Regras Tarif", joined, flags=re.I):
                continue
            if len(times) < 2:
                continue
            origem = requested_origin if direction == "ida" else requested_destination
            destino = requested_destination if direction == "ida" else requested_origin
            options.append({
                "tipo": direction,
                "saida": times[0],
                "chegada": times[1],
                "origem": origem,
                "destino": destino,
                "preco": float(price_match.group(1).replace(".", "").replace(",", ".")),
                "moeda": "BRL",
                "tarifa": "Azul",
                "descricao": joined[:280],
            })
        return self._dedupe_options(options)

    def _is_return_route(self, route_from: str, route_to: str, request: QuoteRequest, outbound_route: tuple[str, str] | None) -> bool:
        if outbound_route and route_from == outbound_route[1] and route_to == outbound_route[0]:
            return True
        requested_origin = self._airport_search_value(request.origem).upper()
        requested_destination = self._airport_search_value(request.destino).upper()
        return route_from == requested_destination and route_to == requested_origin

    def _dedupe_options(self, options: list[dict]) -> list[dict]:
        seen = set()
        unique = []
        for item in options:
            key = (item.get("tipo"), item.get("saida"), item.get("chegada"), item.get("preco"))
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique

    def _field_after_label(self, page, label: str):
        handle = page.evaluate_handle(
            """
            ({label}) => {
              const normalize = text => (text || '')
                .normalize('NFD')
                .replace(/[\\u0300-\\u036f]/g, '')
                .toLowerCase();
              const visible = el => {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
              };
              const wanted = normalize(label);
              const labels = [...document.querySelectorAll('label, span, div, td, th')]
                .filter(visible)
                .map(el => ({ el, rect: el.getBoundingClientRect(), text: normalize(el.innerText || el.textContent) }))
                .filter(item => item.text.includes(wanted))
                .sort((a, b) => (a.rect.width * a.rect.height) - (b.rect.width * b.rect.height));
              const found = labels[0];
              if (!found) return null;
              const candidates = [...document.querySelectorAll('input')]
                .filter(visible)
                .map(el => ({ el, rect: el.getBoundingClientRect() }))
                .filter(item => item.rect.top >= found.rect.top - 8 && item.rect.top <= found.rect.bottom + 45)
                .filter(item => item.rect.left >= found.rect.left - 25)
                .sort((a, b) => Math.abs(a.rect.left - found.rect.left) - Math.abs(b.rect.left - found.rect.left));
              return candidates[0]?.el || null;
            }
            """,
            {"label": label},
        )
        element = handle.as_element()
        if not element:
            raise RuntimeError(f"Nao encontrei o campo da Azul Empresas: {label}.")
        return element

    def _fill_any(self, page, selectors: list[str], value: str) -> None:
        for selector in selectors:
            try:
                field = page.locator(selector).first
                field.click(timeout=5000)
                field.fill("", timeout=3000)
                field.type(value, delay=70, timeout=8000)
                field.evaluate(
                    """
                    (el) => {
                      el.dispatchEvent(new Event('input', { bubbles: true }));
                      el.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                    """
                )
                return
            except Exception:
                pass
        raise RuntimeError("Nao encontrei campo de login da Azul Empresas.")

    def _submit_login(self, page) -> bool:
        clicked = page.evaluate(
            """
            () => {
              const visible = el => {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
              };
              const norm = text => (text || '')
                .normalize('NFD')
                .replace(/[\\u0300-\\u036f]/g, '')
                .toLowerCase();
              const candidates = [...document.querySelectorAll('button, input[type="button"], input[type="submit"], a')]
                .filter(visible)
                .filter(el => /fazer login|entrar|login|acessar/.test(norm(el.innerText || el.value || el.title || el.getAttribute('aria-label') || '')))
                .sort((a, b) => {
                  const ar = a.getBoundingClientRect();
                  const br = b.getBoundingClientRect();
                  return (br.width * br.height) - (ar.width * ar.height);
                });
              const target = candidates[0];
              if (target) {
                target.click();
                return true;
              }
              const password = document.querySelector('input[type="password"]');
              const form = password && password.closest('form');
              if (form) {
                form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
                if (typeof form.submit === 'function') form.submit();
                return true;
              }
              return false;
            }
            """
        )
        if clicked:
            page.wait_for_timeout(1200)
            return True
        try:
            page.locator("input[type='password']").first.press("Enter", timeout=3000)
            page.wait_for_timeout(1200)
            return True
        except Exception:
            return False

    def _click_button(self, page, pattern, timeout: int) -> None:
        try:
            page.get_by_role("button", name=pattern).first.click(timeout=timeout)
            return
        except Exception:
            pass
        try:
            page.locator("button, input[type='button'], input[type='submit'], a").filter(has_text=pattern).first.click(timeout=timeout)
            return
        except Exception:
            pass
        clicked = page.evaluate(
            """
            ({patternText}) => {
              const rx = new RegExp(patternText, 'i');
              const visible = el => {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
              };
              const candidates = [...document.querySelectorAll('button, input, a')]
                .filter(visible)
                .filter(el => rx.test(el.innerText || el.value || el.title || ''));
              if (!candidates.length) return false;
              candidates[0].click();
              return true;
            }
            """,
            {"patternText": pattern.pattern},
        )
        if not clicked:
            raise RuntimeError(f"Nao consegui clicar no botao da Azul Empresas: {pattern.pattern}")

    def _body_text(self, page) -> str:
        try:
            return page.locator("body").inner_text(timeout=10000)
        except Exception:
            return ""

    def _date_parts(self, value: str) -> dict[str, int]:
        parts = str(value or "").split("-")
        if len(parts) != 3:
            raise RuntimeError(f"Data invalida para Azul: {value}")
        return {"year": int(parts[0]), "month": int(parts[1]), "day": int(parts[2])}

    def _br_date(self, value: str) -> str:
        parts = str(value or "").split("-")
        if len(parts) == 3:
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
        return value

    def _norm_text(self, value: str) -> str:
        text = unicodedata.normalize("NFD", value or "")
        return "".join(char for char in text if unicodedata.category(char) != "Mn").lower()

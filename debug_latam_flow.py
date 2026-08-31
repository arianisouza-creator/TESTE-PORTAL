import os
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

from cotacoes.connectors.latam import LATAM_CORPORATE_URL, LATAM_PROFILE_DIR, LatamConnector
from cotacoes.models import ConnectorConfig, QuoteRequest
from cotacoes.storage import load_store


def save(page, name: str) -> None:
    out = Path("debug-output")
    out.mkdir(exist_ok=True)
    page.screenshot(path=str(out / f"{name}.png"), full_page=True)
    print(f"SCREEN {name}: {(out / f'{name}.png').resolve()}")


def main() -> None:
    store = load_store()
    config = ConnectorConfig(**((store.get("configs") or {}).get("LATAM") or {}))
    request = QuoteRequest(
        companhia="LATAM",
        origem="LDB",
        destino="MOC",
        dataIda="2026-11-24",
        dataVolta="2026-11-26",
        adultos=1,
        cabine="Economica",
    )
    connector = LatamConnector(companhia="LATAM")
    target_url = (config.siteUrl or LATAM_CORPORATE_URL).strip() or LATAM_CORPORATE_URL
    LATAM_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch_persistent_context(
            user_data_dir=str(LATAM_PROFILE_DIR),
            headless=False,
            locale="pt-BR",
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.pages[0] if browser.pages else browser.new_page()
        try:
            print("OPEN", flush=True)
            page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
            print("LOGIN_BUTTON", flush=True)
            connector._try_click(page, re.compile("Fazer Login|Login|Entrar", re.I), timeout=8000)
            print("LOGIN_FILL", flush=True)
            connector._fill_login_if_visible(page, config)
            print("WAIT_SEARCH", flush=True)
            connector._wait_for_search_ready(page, headless=False)
            print("FILL_ORIGIN", flush=True)
            connector._fill_airport(page, ["Insira uma origem", "Origem", "De"], request.origem, field_text="De")
            print("FILL_DEST", flush=True)
            connector._fill_airport(page, ["Insira um destino", "Destino", "Para"], request.destino, field_text="Para")
            print("OPEN_DATE", flush=True)
            connector._click_date_box(page, "Ida")
            page.wait_for_timeout(1200)
            save(page, "01_calendar_open")
            for step in range(1, 8):
                months = connector._calendar_visible_months(page)
                body = page.locator("body").inner_text(timeout=5000)
                print(f"STEP {step} months={months} has_novembro={'Novembro 2026' in body}")
                if "Novembro 2026" in body or any("Novembro 2026" in month for month in months):
                    clicked = connector._click_calendar_day_by_label(page, 24, 11, 2026)
                    print(f"CLICK_DAY_LABEL={clicked}")
                    save(page, "02_after_day_click")
                    break
                moved = connector._click_calendar_next(page)
                print(f"CLICK_NEXT={moved} after={connector._calendar_visible_months(page)}")
                save(page, f"next_{step}")
            page.wait_for_timeout(5000)
            print("SELECT_RETURN", flush=True)
            connector._select_calendar_date(page, "Volta", request.dataVolta)
            save(page, "03_after_return_date")
            print("CLICK_SEARCH", flush=True)
            connector._try_click(page, re.compile("Procurar voos|Buscar voos|Pesquisar", re.I), timeout=10000)
            page.wait_for_timeout(10000)
            save(page, "04_after_search_wait")
            print(page.locator("body").inner_text(timeout=5000)[:1200], flush=True)
        finally:
            if os.getenv("DEBUG_LATAM_KEEP_OPEN", "0") != "1":
                browser.close()


if __name__ == "__main__":
    main()

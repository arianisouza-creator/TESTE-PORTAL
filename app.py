import json
import os
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


st.set_page_config(
    page_title="Portal Administrativo | MSE",
    page_icon=":globe_with_meridians:",
    layout="wide",
    initial_sidebar_state="collapsed",
)


HTML_FILE = Path(__file__).with_name("controle-internet.html")


def get_secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, default)
    except Exception:
        value = default
    return str(value or "").strip()


def load_portal_config() -> dict:
    return {
        "supabase": {
            "url": get_secret("supabase_url", os.getenv("SUPABASE_URL", "")),
            "anonKey": get_secret("supabase_anon_key", os.getenv("SUPABASE_ANON_KEY", "")),
        },
        "exportacao": {
            "baseUrl": get_secret(
                "exportacao_api_base_url",
                os.getenv(
                    "EXPORTACAO_API_BASE_URL",
                    "https://portalmse.com.br/microservices/exportacao_api",
                ),
            ),
            "token": get_secret("exportacao_api_token", os.getenv("EXPORTACAO_API_TOKEN", "")),
        },
        "passagens": {
            "baseUrl": get_secret(
                "passagens_api_base_url",
                os.getenv(
                    "PASSAGENS_API_BASE_URL",
                    "https://portalmse.com.br/microservices/hub_mse/api_passagens",
                ),
            ),
            "token": get_secret("passagens_api_token", os.getenv("PASSAGENS_API_TOKEN", "")),
            "useApiOnly": True,
        },
        "cotacoes": {
            "baseUrl": get_secret(
                "cotacoes_api_base_url",
                os.getenv("COTACOES_API_BASE_URL", ""),
            ).rstrip("/"),
        },
        "googleDrive": {
            "clientId": get_secret(
                "google_drive_client_id",
                os.getenv("GOOGLE_DRIVE_CLIENT_ID", ""),
            ),
            "rootFolderId": get_secret(
                "google_drive_root_folder_id",
                os.getenv("GOOGLE_DRIVE_ROOT_FOLDER_ID", "1LyjXgkF9p9TrWH39TbKly0oCG7HXNfRc"),
            ),
        },
    }


def load_html() -> str:
    if not HTML_FILE.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {HTML_FILE}")
    html = HTML_FILE.read_text(encoding="utf-8")
    config_json = json.dumps(load_portal_config()).replace("</", "<\\/")
    injection = f"<script>window.PORTAL_CONFIG = {config_json};</script>"
    if "</head>" in html:
        return html.replace("</head>", f"  {injection}\n</head>", 1)
    return f"{injection}\n{html}"


def main() -> None:
    st.markdown(
        """
        <style>
          .stApp {
            background: #e8eaee;
          }
          .block-container {
            max-width: 100%;
            padding: 0;
          }
          header[data-testid="stHeader"] {
            background: transparent;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

    try:
        html = load_html()
    except FileNotFoundError as exc:
        st.error(str(exc))
        st.stop()

    components.html(html, height=2400, scrolling=True)


if __name__ == "__main__":
    main()

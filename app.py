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


def load_portal_config() -> dict:
    return {
        "supabase": {
            "url": st.secrets.get("supabase_url", os.getenv("SUPABASE_URL", "")).strip(),
            "anonKey": st.secrets.get("supabase_anon_key", os.getenv("SUPABASE_ANON_KEY", "")).strip(),
        },
        "passagens": {
            "baseUrl": st.secrets.get(
                "passagens_api_base_url",
                os.getenv(
                    "PASSAGENS_API_BASE_URL",
                    "https://portalmse.com.br/microservices/hub_mse/api_passagens",
                ),
            ).strip(),
            "token": st.secrets.get("passagens_api_token", os.getenv("PASSAGENS_API_TOKEN", "")).strip(),
            "useApiOnly": True,
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

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

try:
    # On Streamlit Community Cloud, config is set via st.secrets (Secrets UI)
    # rather than a .env file. Mirror it into os.environ so the rest of the
    # app can keep reading plain env vars either way.
    import streamlit as st

    for _key, _value in st.secrets.items():
        os.environ.setdefault(_key, str(_value))
except Exception:
    pass


@dataclass
class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

    confluence_base_url: str = os.getenv("CONFLUENCE_BASE_URL", "")
    confluence_email: str = os.getenv("CONFLUENCE_EMAIL", "")
    confluence_api_token: str = os.getenv("CONFLUENCE_API_TOKEN", "")
    confluence_space_key: str = os.getenv("CONFLUENCE_SPACE_KEY", "")
    confluence_parent_page_title: str = os.getenv("CONFLUENCE_PARENT_PAGE_TITLE", "101.회의록")

    excel_template_path: str = os.getenv("EXCEL_TEMPLATE_PATH", "templates/meeting_minutes_template.xlsx")
    excel_field_map_path: str = os.getenv("EXCEL_FIELD_MAP_PATH", "templates/field_map.json")


settings = Settings()

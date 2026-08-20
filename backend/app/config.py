import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
DEFAULT_DATA_DIR = str(PROJECT_ROOT / "data")
DEFAULT_CHROMADB_DIR = str(PROJECT_ROOT / "data" / "chroma_db")

# Automatically inject from Streamlit Cloud secrets into os.environ if present
try:
    import streamlit as st
    if hasattr(st, "secrets"):
        for k, v in st.secrets.items():
            if isinstance(v, (str, int, float, bool)):
                os.environ[k] = str(v)
except Exception:
    pass

class Settings(BaseSettings):
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "openai/gpt-oss-20b"

    SMTP_EMAIL: Optional[str] = None
    SMTP_APP_PASSWORD: Optional[str] = None

    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_FROM_WHATSAPP: Optional[str] = "whatsapp:+14155238886"
    TWILIO_FROM_EMAIL: Optional[str] = None

    DRY_RUN: bool = False

    JWT_SECRET_KEY: str = "admin_automation_agent_secure_jwt_secret_key_2026_change_in_prod"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ADMIN_DEFAULT_PASSWORD: str = "admin123"

    DATA_DIR: str = DEFAULT_DATA_DIR
    CHROMADB_DIR: str = DEFAULT_CHROMADB_DIR

    SIMULATED_TODAY: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=(str(PROJECT_ROOT / ".env"), str(BASE_DIR / ".env")),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Direct override from st.secrets if running in Streamlit Cloud
try:
    import streamlit as st
    if hasattr(st, "secrets"):
        for k, v in st.secrets.items():
            if hasattr(settings, k):
                val = v
                if k == "DRY_RUN" and isinstance(v, str):
                    val = v.lower() in ("true", "1", "yes")
                setattr(settings, k, val)
except Exception:
    pass

# Ensure DATA_DIR is absolute
if not os.path.isabs(settings.DATA_DIR):
    settings.DATA_DIR = str((PROJECT_ROOT / settings.DATA_DIR).resolve())
if not os.path.isabs(settings.CHROMADB_DIR):
    settings.CHROMADB_DIR = str((PROJECT_ROOT / settings.CHROMADB_DIR).resolve())

os.makedirs(settings.DATA_DIR, exist_ok=True)
os.makedirs(settings.CHROMADB_DIR, exist_ok=True)

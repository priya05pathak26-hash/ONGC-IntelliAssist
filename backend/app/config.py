from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parent.parent  # .../backend/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "backend/.env"), env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ONGC IntelliAssist"
    secret_key: str
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    access_token_minutes: int = 45
    refresh_token_days: int = 7
    # NOTE: All on-disk paths are resolved ONCE against the *backend directory* (NOT
    # the shell CWD).  This eliminates the "two empty databases" bug where running
    # uvicorn from project-root vs backend/ would create a second, empty SQLite +
    # FAISS tree, causing instant "No Relevant Context" responses (has_kb=False).
    database_url: str = f"sqlite:///{BACKEND_ROOT / 'ongc_intelliassist.db'}"
    upload_dir: Path = BACKEND_ROOT / "storage" / "uploads"
    knowledge_base_dir: Path = BACKEND_ROOT / "storage" / "knowledge_base"
    vector_db_dir: Path = BACKEND_ROOT / "storage" / "vector_db"
    max_upload_mb: int = 100
    ollama_url: str = "http://localhost:11434/api/generate"
    ollama_model: str = "llama3.2"
    cors_origins: str = "*"
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    tavily_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


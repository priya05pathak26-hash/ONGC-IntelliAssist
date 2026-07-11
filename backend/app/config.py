from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "ONGC IntelliAssist"
    secret_key: str
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    access_token_minutes: int = 45
    refresh_token_days: int = 7
    database_url: str = "sqlite:///./ongc_intelliassist.db"
    upload_dir: Path = Path("storage/uploads")
    max_upload_mb: int = 100
    ollama_url: str = "http://localhost:11434/api/generate"
    ollama_model: str = "llama3.2"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,*"


@lru_cache
def get_settings() -> Settings:
    return Settings()

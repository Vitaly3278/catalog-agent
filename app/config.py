from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    imap_host: str = "imap.mail.ru"
    imap_port: int = 993
    imap_user: str = ""
    imap_password: str = ""
    imap_folder: str = "INBOX"

    playwright_headless: bool = True
    playwright_timeout_ms: int = 60_000

    database_path: str = "data/catalog_agent.db"
    secret_key: str = "dev-secret"

    # true = 10 локальных демо-форм (полный цикл без капчи)
    demo_mode: bool = True
    app_base_url: str = "http://127.0.0.1:8000"

    @property
    def db_path(self) -> Path:
        p = Path(self.database_path)
        if not p.is_absolute():
            p = BASE_DIR / p
        return p


@lru_cache
def get_settings() -> Settings:
    return Settings()

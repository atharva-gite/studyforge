from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

API_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://study:study@localhost:5432/study"
    secret_key: str = "dev-only-change-me-before-any-shared-deployment"
    storage_root: str = str(API_ROOT / "storage")
    max_upload_bytes: int = 25 * 1024 * 1024
    cookie_name: str = "studyforge_session"
    cookie_secure: bool = False
    session_days: int = 7


@lru_cache
def get_settings() -> Settings:
    return Settings()

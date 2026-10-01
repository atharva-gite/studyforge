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
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4o-mini"
    openai_timeout_seconds: float = 30
    ingest_max_attempts: int = 3
    job_lease_seconds: int = 120
    retrieval_min_similarity: float = 0.25
    auth_attempts_per_minute: int = 10
    model_requests_per_minute: int = 30
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout_seconds: int = 30
    db_statement_timeout_ms: int = 30000


@lru_cache
def get_settings() -> Settings:
    return Settings()

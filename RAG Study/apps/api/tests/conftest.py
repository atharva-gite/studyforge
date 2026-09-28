import os

os.environ["DATABASE_URL"] = "postgresql+psycopg://study:study@localhost:5432/study_test"
os.environ["SECRET_KEY"] = "test-secret-key-at-least-32-bytes-long"
os.environ["COOKIE_SECURE"] = "false"

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import session_factory
from app.main import app
from app.models import Base

TEST_DATABASE_URL = os.environ["DATABASE_URL"]
ADMIN_URL = "postgresql://study:study@localhost:5432/postgres"


def _ensure_test_database() -> None:
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = 'study_test'").fetchone()
        if exists is None:
            conn.execute("CREATE DATABASE study_test")


def _truncate(session: Session) -> None:
    table_names = session.execute(
        text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename <> 'alembic_version'")
    ).scalars()
    names = list(table_names)
    if not names:
        return
    quoted = ", ".join(f'"{name}"' for name in names)
    session.execute(text(f"TRUNCATE {quoted} RESTART IDENTITY CASCADE"))
    session.commit()


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    if not TEST_DATABASE_URL.endswith("/study_test"):
        raise RuntimeError("Refusing to run tests against a non-test database")
    _ensure_test_database()
    get_settings.cache_clear()
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    engine.dispose()
    yield


@pytest.fixture(autouse=True)
def clean_tables(setup_db):
    get_settings.cache_clear()
    session = session_factory()()
    try:
        _truncate(session)
    finally:
        session.close()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "storage"))
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db() -> Session:
    session = session_factory()()
    try:
        yield session
    finally:
        session.close()

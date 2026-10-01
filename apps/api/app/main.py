import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import get_settings
from app.database import get_engine
from app.logging_config import configure_logging, request_id_var
from app.routers import auth, courses, documents, questions, study

log = logging.getLogger("studyforge.request")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    Path(get_settings().storage_root).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="StudyForge API",
    version="0.1.0",
    summary="Course corpus for grounded retrieval",
    description=(
        "PostgreSQL is the source of truth for application state. "
        "Object storage holds uploaded files. The worker indexes them, and "
        "questions, flashcards, and quizzes stay tied to retrieved chunks."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    token = request_id_var.set(request_id)
    started = time.perf_counter()
    try:
        try:
            response = await call_next(request)
        except Exception:
            log.exception(
                "request failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
            raise
        duration_ms = round((time.perf_counter() - started) * 1000, 1)
        response.headers["x-request-id"] = request_id
        log.info(
            "request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
    finally:
        request_id_var.reset(token)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _storage_writable() -> None:
    root = Path(get_settings().storage_root)
    root.mkdir(parents=True, exist_ok=True)
    probe = root / ".ready"
    probe.write_bytes(b"1")
    probe.unlink(missing_ok=True)


@app.get("/ready")
def ready():
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        _storage_writable()
    except Exception:
        log.exception("readiness check failed")
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(documents.router)
app.include_router(questions.router)
app.include_router(study.router)

import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, courses, documents

log = logging.getLogger("studyforge.request")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Path(get_settings().storage_root).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="StudyForge API",
    version="0.1.0",
    summary="Course corpus for grounded retrieval",
    description=(
        "PostgreSQL is the source of truth for application state. "
        "Object storage holds uploaded files. This phase covers accounts, "
        "courses, and document metadata. Retrieval and planning come later."
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
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    response.headers["x-request-id"] = request_id
    log.info(
        "%s %s %s %.1fms rid=%s",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
        request_id,
    )
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(documents.router)

import uuid
from datetime import timedelta

from sqlalchemy import func, select

from app.database import session_factory
from app.models import DocumentChunk, Job, JobStatus, utcnow
from app.worker import run_once
from tests.pdfs import blank_pdf, text_pdf
from tests.test_auth import register
from tests.test_courses import _create_course
from tests.test_documents import _upload

LECTURE = (
    "Virtual memory maps virtual addresses to physical frames. "
    + " ".join(f"term{index}" for index in range(26))
)


def test_text_pdf_reaches_ready_with_page_numbers(client, db):
    register(client)
    course_id = _create_course(client).json()["id"]
    uploaded = _upload(client, course_id, content=text_pdf([LECTURE]), title="Virtual Memory")
    assert uploaded.status_code == 201

    assert run_once(db).worked

    listed = client.get(f"/courses/{course_id}/documents").json()[0]
    assert listed["status"] == "READY"
    assert listed["error"] is None
    chunks = db.scalars(select(DocumentChunk).order_by(DocumentChunk.chunk_index)).all()
    assert len(chunks) >= 1
    assert chunks[0].page_start == 1
    assert chunks[0].page_end == 1
    assert chunks[0].chunk_index == 0
    assert "virtual memory" in chunks[0].text.lower()
    assert chunks[0].embedding is not None
    assert len(chunks[0].embedding) == 1536


def test_retry_does_not_duplicate_chunks(client, db):
    register(client)
    course_id = _create_course(client).json()["id"]
    _upload(client, course_id, content=text_pdf([LECTURE]))
    assert run_once(db).worked
    count = db.scalar(select(func.count()).select_from(DocumentChunk))

    job = db.scalar(select(Job))
    job.status = JobStatus.PENDING
    job.completed_at = None
    db.commit()

    assert run_once(db).worked
    assert db.scalar(select(func.count()).select_from(DocumentChunk)) == count
    assert client.get(f"/courses/{course_id}/documents").json()[0]["status"] == "READY"


def test_transient_failure_retries_without_duplicating_chunks(client, db, language_model):
    register(client)
    course_id = _create_course(client).json()["id"]
    _upload(client, course_id, content=text_pdf([LECTURE]))
    language_model.fail_embeds = 1

    first = run_once(db)
    assert first.worked
    assert first.retry_after > 0
    assert client.get(f"/courses/{course_id}/documents").json()[0]["status"] == "EMBEDDING"
    assert db.scalar(select(func.count()).select_from(DocumentChunk)) == 0

    assert run_once(db).worked
    assert client.get(f"/courses/{course_id}/documents").json()[0]["status"] == "READY"
    assert db.scalar(select(func.count()).select_from(DocumentChunk)) >= 1


def test_blank_pdf_fails_closed(client, db):
    register(client)
    course_id = _create_course(client).json()["id"]
    _upload(client, course_id, content=blank_pdf())

    assert run_once(db).worked

    listed = client.get(f"/courses/{course_id}/documents").json()[0]
    assert listed["status"] == "FAILED"
    assert "OCR" in listed["error"]
    assert db.scalar(select(func.count()).select_from(DocumentChunk)) == 0
    job = db.scalar(select(Job))
    assert job.status == JobStatus.FAILED


def _pending_job(client, db) -> tuple[str, Job]:
    register(client)
    course_id = _create_course(client).json()["id"]
    _upload(client, course_id, content=text_pdf([LECTURE]))
    job = db.scalar(select(Job))
    assert job is not None
    return course_id, job


def test_expired_running_job_is_reclaimed(client, db):
    course_id, job = _pending_job(client, db)
    job.status = JobStatus.RUNNING
    job.lease_token = uuid.uuid4()
    job.lease_expires_at = utcnow() - timedelta(seconds=5)
    job.started_at = utcnow() - timedelta(minutes=5)
    db.commit()

    assert run_once(db).worked
    assert client.get(f"/courses/{course_id}/documents").json()[0]["status"] == "READY"


def test_running_job_with_a_live_lease_is_left_alone(client, db):
    course_id, job = _pending_job(client, db)
    token = uuid.uuid4()
    job.status = JobStatus.RUNNING
    job.lease_token = token
    job.lease_expires_at = utcnow() + timedelta(minutes=5)
    db.commit()

    assert run_once(db).worked is False
    job = db.scalar(select(Job))
    assert job.status == JobStatus.RUNNING
    assert job.lease_token == token
    assert client.get(f"/courses/{course_id}/documents").json()[0]["status"] != "READY"


def test_lost_lease_does_not_finish_the_job(client, db, language_model):
    _pending_job(client, db)
    stolen = uuid.uuid4()
    original = language_model.embed

    def embed(texts):
        other = session_factory()()
        try:
            job = other.scalar(select(Job))
            job.lease_token = stolen
            job.lease_expires_at = utcnow() + timedelta(minutes=5)
            other.commit()
        finally:
            other.close()
        return original(texts)

    language_model.embed = embed
    assert run_once(db).worked
    job = db.scalar(select(Job))
    assert job.status == JobStatus.RUNNING
    assert job.lease_token == stolen


def test_health_is_live_and_ready_checks_the_database(client, monkeypatch):
    assert client.get("/health").status_code == 200
    assert client.get("/health").json() == {"status": "ok"}
    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ok"}

    def broken():
        raise RuntimeError("database down")

    monkeypatch.setattr("app.main.get_engine", broken)
    down = client.get("/ready")
    assert down.status_code == 503
    assert down.json() == {"status": "unavailable"}

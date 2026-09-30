from sqlalchemy import func, select

from app.models import DocumentChunk, Job, JobStatus
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

    assert run_once(db) is True

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
    assert run_once(db) is True
    count = db.scalar(select(func.count()).select_from(DocumentChunk))

    job = db.scalar(select(Job))
    job.status = JobStatus.PENDING
    job.completed_at = None
    db.commit()

    assert run_once(db) is True
    assert db.scalar(select(func.count()).select_from(DocumentChunk)) == count
    assert client.get(f"/courses/{course_id}/documents").json()[0]["status"] == "READY"


def test_transient_failure_retries_without_duplicating_chunks(client, db, language_model):
    register(client)
    course_id = _create_course(client).json()["id"]
    _upload(client, course_id, content=text_pdf([LECTURE]))
    language_model.fail_embeds = 1

    assert run_once(db, sleep=lambda _seconds: None) is True
    assert client.get(f"/courses/{course_id}/documents").json()[0]["status"] == "EMBEDDING"
    assert db.scalar(select(func.count()).select_from(DocumentChunk)) == 0

    assert run_once(db, sleep=lambda _seconds: None) is True
    assert client.get(f"/courses/{course_id}/documents").json()[0]["status"] == "READY"
    assert db.scalar(select(func.count()).select_from(DocumentChunk)) >= 1


def test_blank_pdf_fails_closed(client, db):
    register(client)
    course_id = _create_course(client).json()["id"]
    _upload(client, course_id, content=blank_pdf())

    assert run_once(db) is True

    listed = client.get(f"/courses/{course_id}/documents").json()[0]
    assert listed["status"] == "FAILED"
    assert "OCR" in listed["error"]
    assert db.scalar(select(func.count()).select_from(DocumentChunk)) == 0
    job = db.scalar(select(Job))
    assert job.status == JobStatus.FAILED

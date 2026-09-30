from sqlalchemy import select

from app.models import DocumentChunk
from app.worker import run_once
from tests.pdfs import text_pdf
from tests.test_auth import register
from tests.test_courses import _create_course
from tests.test_documents import _upload
from tests.test_ingest import LECTURE


def _ready_course(client, db):
    register(client)
    course_id = _create_course(client).json()["id"]
    _upload(client, course_id, content=text_pdf([LECTURE]), title="Virtual Memory")
    assert run_once(db) is True
    return course_id


def test_question_cites_a_real_chunk(client, db):
    course_id = _ready_course(client, db)
    response = client.post(
        f"/courses/{course_id}/questions",
        json={"question": "virtual memory addresses frames"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["answer"]
    real_ids = {str(chunk_id) for chunk_id in db.scalars(select(DocumentChunk.id))}
    assert len(body["citations"]) == 1
    citation = body["citations"][0]
    assert citation["chunk_id"] in real_ids
    assert citation["document_title"] == "Virtual Memory"
    assert citation["page_start"] == 1


def test_question_outside_the_corpus_returns_insufficient_evidence(client, db, language_model):
    course_id = _ready_course(client, db)
    response = client.post(
        f"/courses/{course_id}/questions",
        json={"question": "xylophone"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "insufficient_evidence"
    assert body["answer"] is None
    assert body["citations"] == []
    assert language_model.complete_calls == 0


def test_another_student_cannot_ask(client, db):
    course_id = _ready_course(client, db)
    client.post("/auth/logout")
    register(client, email="grace@university.edu", name="Grace Hopper")
    response = client.post(
        f"/courses/{course_id}/questions",
        json={"question": "virtual memory addresses frames"},
    )
    assert response.status_code == 404

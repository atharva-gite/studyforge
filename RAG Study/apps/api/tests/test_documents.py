import uuid

from sqlalchemy import func, select

from app.config import get_settings
from app.models import Job, JobStatus
from tests.test_auth import register
from tests.test_courses import _create_course

PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<<>>\n%%EOF\n"
OTHER_PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\ntrailer<<>>\n%%EOF\n"


def _upload(client, course_id, content=PDF, filename="lecture-7.pdf", document_type="LECTURE", title=None):
    data = {"document_type": document_type}
    if title is not None:
        data["title"] = title
    return client.post(
        f"/courses/{course_id}/documents",
        files={"file": (filename, content, "application/octet-stream")},
        data=data,
    )


def test_upload_lists_metadata_and_file(client):
    register(client)
    course_id = _create_course(client).json()["id"]
    uploaded = _upload(client, course_id, title="Virtual Memory")
    assert uploaded.status_code == 201
    body = uploaded.json()
    assert body["title"] == "Virtual Memory"
    assert body["document_type"] == "LECTURE"
    assert body["status"] == "UPLOADED"
    assert body["original_filename"] == "lecture-7.pdf"
    assert body["mime_type"] == "application/pdf"
    assert body["size_bytes"] == len(PDF)
    assert len(body["sha256"]) == 64
    assert body["version_number"] == 1
    assert body["duplicate"] is False

    listed = client.get(f"/courses/{course_id}/documents")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == body["id"]
    assert client.get("/courses").json()[0]["document_count"] == 1

    downloaded = client.get(f"/documents/{body['id']}/file")
    assert downloaded.status_code == 200
    assert downloaded.content == PDF


def test_duplicate_upload_is_not_stored_twice(client, db):
    register(client)
    course_id = _create_course(client).json()["id"]
    first = _upload(client, course_id)
    second = _upload(client, course_id)
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert second.json()["id"] == first.json()["id"]
    assert db.scalar(select(func.count()).select_from(Job)) == 1


def test_new_version_replaces_the_active_file(client):
    register(client)
    course_id = _create_course(client).json()["id"]
    document_id = _upload(client, course_id).json()["id"]
    revised = client.post(
        f"/documents/{document_id}/versions",
        files={"file": ("lecture-7-v2.pdf", OTHER_PDF, "application/pdf")},
    )
    assert revised.status_code == 201
    assert revised.json()["version_number"] == 2
    assert revised.json()["id"] == document_id
    assert client.get(f"/documents/{document_id}/file").content == OTHER_PDF

    same = client.post(
        f"/documents/{document_id}/versions",
        files={"file": ("lecture-7-v2.pdf", OTHER_PDF, "application/pdf")},
    )
    assert same.status_code == 200
    assert same.json()["duplicate"] is True
    assert same.json()["version_number"] == 2


def test_reprocess_is_idempotent_until_the_job_is_running(client, db):
    register(client)
    course_id = _create_course(client).json()["id"]
    document_id = _upload(client, course_id).json()["id"]
    first = client.post(f"/documents/{document_id}/reprocess")
    second = client.post(f"/documents/{document_id}/reprocess")
    assert first.status_code == 200
    assert second.json()["job_id"] == first.json()["job_id"]
    assert second.json()["job_status"] == "PENDING"

    job = db.get(Job, uuid.UUID(first.json()["job_id"]))
    job.status = JobStatus.RUNNING
    db.commit()
    conflict = client.post(f"/documents/{document_id}/reprocess")
    assert conflict.status_code == 409


def test_rejects_non_pdf_and_oversize_files(client, monkeypatch):
    register(client)
    course_id = _create_course(client).json()["id"]
    renamed = _upload(client, course_id, content=b"not a pdf", filename="notes.pdf")
    assert renamed.status_code == 400
    wrong_type = _upload(client, course_id, filename="notes.txt")
    assert wrong_type.status_code == 400

    monkeypatch.setenv("MAX_UPLOAD_BYTES", "8")
    get_settings.cache_clear()
    oversized = _upload(client, course_id)
    assert oversized.status_code == 413


def test_other_student_cannot_read_documents(client):
    register(client, email="ada@university.edu")
    course_id = _create_course(client).json()["id"]
    document_id = _upload(client, course_id).json()["id"]

    client.post("/auth/logout")
    register(client, email="alan@university.edu", name="Alan Turing")
    assert client.get(f"/courses/{course_id}/documents").status_code == 404
    assert client.get(f"/documents/{document_id}").status_code == 404
    assert client.get(f"/documents/{document_id}/file").status_code == 404
    assert client.delete(f"/documents/{document_id}").status_code == 404


def test_delete_document_removes_the_file(client):
    register(client)
    course_id = _create_course(client).json()["id"]
    document_id = _upload(client, course_id).json()["id"]
    assert client.delete(f"/documents/{document_id}").status_code == 204
    assert client.get(f"/documents/{document_id}").status_code == 404
    assert client.get(f"/courses/{course_id}/documents").json() == []


def test_delete_course_removes_documents(client):
    register(client)
    course_id = _create_course(client).json()["id"]
    document_id = _upload(client, course_id).json()["id"]
    assert client.delete(f"/courses/{course_id}").status_code == 204
    assert client.get(f"/documents/{document_id}").status_code == 404

import hashlib
import re
import uuid
import zipfile
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    Course,
    Document,
    DocumentStatus,
    DocumentType,
    DocumentVersion,
    Job,
    JobStatus,
    User,
)
from app.schemas import DocumentOut
from app.services.storage import LocalObjectStorage

MIME_BY_SUFFIX = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}
OFFICE_MARKER = {
    ".xlsx": b"spreadsheetml",
    ".docx": b"wordprocessingml",
    ".pptx": b"presentationml",
}
REJECTED_MESSAGE = (
    "Upload a PDF, text file, CSV, Excel workbook, Word document, PowerPoint deck, or image."
)


def read_limited(upload: UploadFile, limit: int) -> bytes:
    data = upload.file.read(limit + 1)
    if not data:
        raise HTTPException(status_code=400, detail="The file is empty")
    if len(data) > limit:
        raise HTTPException(status_code=413, detail="File exceeds the upload size limit")
    return data


def _office_marker(data: bytes, marker: bytes) -> bool:
    if not data.startswith(b"PK"):
        return False
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            content_types = archive.read("[Content_Types].xml")
    except (KeyError, zipfile.BadZipFile, OSError):
        return False
    return marker in content_types


def _matches_header(suffix: str, data: bytes) -> bool:
    if suffix == ".pdf":
        return data.startswith(b"%PDF-")
    if suffix in OFFICE_MARKER:
        return _office_marker(data, OFFICE_MARKER[suffix])
    if suffix == ".png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if suffix in {".jpg", ".jpeg"}:
        return data.startswith(b"\xff\xd8\xff")
    if suffix == ".webp":
        return len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    if suffix in {".txt", ".md", ".csv"}:
        if b"\x00" in data or data.startswith((b"%PDF-", b"PK")):
            return False
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            return False
        return True
    return False


def validate_upload(filename: str, data: bytes) -> str:
    safe_name = sanitize_filename(filename)
    suffix = Path(safe_name).suffix.lower()
    if suffix not in MIME_BY_SUFFIX or not _matches_header(suffix, data):
        raise HTTPException(status_code=400, detail=REJECTED_MESSAGE)
    return safe_name


def sanitize_filename(name: str | None) -> str:
    raw = Path(name or "").name.replace("\x00", "")
    raw = re.sub(r"[\r\n]+", " ", raw).strip()
    if not raw or raw in {".", ".."}:
        return "document.pdf"
    return raw[:255]


def title_from_filename(filename: str, override: str | None) -> str:
    if override and override.strip():
        return override.strip()[:200]
    stem = Path(filename).stem.strip() or "Untitled document"
    return stem[:200]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def storage_key(course_id: uuid.UUID, document_id: uuid.UUID, version_id: uuid.UUID, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in MIME_BY_SUFFIX:
        suffix = ".bin"
    return f"course/{course_id}/documents/{document_id}/versions/{version_id}/original{suffix}"


def to_document_out(document: Document, version: DocumentVersion, *, duplicate: bool = False) -> DocumentOut:
    return DocumentOut(
        id=document.id,
        course_id=document.course_id,
        title=document.title,
        document_type=document.document_type,
        status=version.status,
        original_filename=version.original_filename,
        mime_type=version.mime_type,
        size_bytes=version.size_bytes,
        sha256=version.sha256,
        version_number=version.version_number,
        version_id=version.id,
        error=version.error,
        created_at=version.created_at,
        duplicate=duplicate,
    )


def active_version(document: Document) -> DocumentVersion:
    version = document.active_version
    if version is None:
        raise HTTPException(status_code=500, detail="Document has no active version")
    return version


def find_course_duplicate(db: Session, course_id: uuid.UUID, digest: str) -> DocumentVersion | None:
    return db.scalar(
        select(DocumentVersion)
        .join(Document, Document.id == DocumentVersion.document_id)
        .where(Document.course_id == course_id, DocumentVersion.sha256 == digest)
        .order_by(DocumentVersion.created_at.asc())
        .limit(1)
    )


def enqueue_processing(db: Session, version: DocumentVersion, course_id: uuid.UUID) -> Job:
    key = f"document_processing:{version.id}"
    job = db.scalar(select(Job).where(Job.idempotency_key == key))
    if job is not None and job.status == JobStatus.RUNNING:
        raise HTTPException(status_code=409, detail="Document is already processing")
    if job is None:
        job = Job(
            type="document_processing",
            status=JobStatus.PENDING,
            attempts=0,
            idempotency_key=key,
            document_version_id=version.id,
            payload={"document_version_id": str(version.id), "course_id": str(course_id)},
        )
        db.add(job)
    else:
        job.status = JobStatus.PENDING
        job.attempts = 0
        job.error = None
        job.started_at = None
        job.completed_at = None
    version.status = DocumentStatus.UPLOADED
    version.error = None
    return job


def store_new_document(
    db: Session,
    storage: LocalObjectStorage,
    *,
    course: Course,
    user: User,
    filename: str,
    data: bytes,
    title: str | None,
    document_type: DocumentType,
) -> tuple[DocumentOut, bool]:
    safe_name = validate_upload(filename, data)
    digest = sha256_bytes(data)
    existing = find_course_duplicate(db, course.id, digest)
    if existing is not None:
        document = db.get(Document, existing.document_id)
        if document is None:
            raise HTTPException(status_code=500, detail="Stored document is missing")
        return to_document_out(document, existing, duplicate=True), False

    document = Document(
        course_id=course.id,
        title=title_from_filename(safe_name, title),
        document_type=document_type,
        created_by_id=user.id,
    )
    db.add(document)
    db.flush()

    version_id = uuid.uuid4()
    key = storage_key(course.id, document.id, version_id, safe_name)
    version = DocumentVersion(
        id=version_id,
        document_id=document.id,
        version_number=1,
        storage_key=key,
        original_filename=safe_name,
        mime_type=MIME_BY_SUFFIX[Path(safe_name).suffix.lower()],
        size_bytes=len(data),
        sha256=digest,
        status=DocumentStatus.UPLOADED,
        is_active=True,
    )
    db.add(version)
    db.flush()
    document.active_version_id = version.id
    document.active_version = version
    enqueue_processing(db, version, course.id)
    storage.put(key, data)
    db.commit()
    db.refresh(document)
    db.refresh(version)
    return to_document_out(document, version), True


def store_new_version(
    db: Session,
    storage: LocalObjectStorage,
    *,
    document: Document,
    filename: str,
    data: bytes,
) -> tuple[DocumentOut, bool]:
    safe_name = validate_upload(filename, data)
    digest = sha256_bytes(data)
    current = active_version(document)
    if current.sha256 == digest:
        return to_document_out(document, current, duplicate=True), False

    next_number = max(version.version_number for version in document.versions) + 1
    version_id = uuid.uuid4()
    key = storage_key(document.course_id, document.id, version_id, safe_name)
    version = DocumentVersion(
        id=version_id,
        document_id=document.id,
        version_number=next_number,
        storage_key=key,
        original_filename=safe_name,
        mime_type=MIME_BY_SUFFIX[Path(safe_name).suffix.lower()],
        size_bytes=len(data),
        sha256=digest,
        status=DocumentStatus.UPLOADED,
        is_active=True,
    )
    current.is_active = False
    db.add(version)
    db.flush()
    document.active_version_id = version.id
    document.active_version = version
    enqueue_processing(db, version, document.course_id)
    storage.put(key, data)
    db.commit()
    db.refresh(version)
    return to_document_out(document, version), True


def remove_document(db: Session, storage: LocalObjectStorage, document: Document) -> None:
    keys = [version.storage_key for version in document.versions]
    document.active_version = None
    document.active_version_id = None
    db.flush()
    db.delete(document)
    db.commit()
    for key in keys:
        storage.delete(key)


def upload_byte_limit() -> int:
    return get_settings().max_upload_bytes

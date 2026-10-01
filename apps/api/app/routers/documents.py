import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user
from app.models import Document, DocumentType, User
from app.schemas import DocumentOut, ReprocessOut
from app.services.access import require_course, require_document
from app.services.documents import (
    enqueue_processing,
    read_limited,
    remove_document,
    store_new_document,
    store_new_version,
    to_document_out,
    upload_byte_limit,
)
from app.services.storage import get_storage

router = APIRouter(tags=["documents"])


def _parse_document_type(value: str) -> DocumentType:
    try:
        return DocumentType(value)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in DocumentType)
        raise HTTPException(status_code=400, detail=f"document_type must be one of: {allowed}") from exc


def _json(document: DocumentOut, status_code: int) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=document.model_dump(mode="json"))


@router.get("/courses/{course_id}/documents", response_model=list[DocumentOut])
def list_documents(
    course_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DocumentOut]:
    require_course(db, user, course_id)
    documents = db.scalars(
        select(Document)
        .where(Document.course_id == course_id)
        .options(joinedload(Document.active_version))
        .order_by(Document.created_at.desc())
    ).all()
    return [to_document_out(document, document.active_version) for document in documents if document.active_version]


@router.post("/courses/{course_id}/documents", response_model=DocumentOut)
def upload_document(
    course_id: uuid.UUID,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    document_type: str = Form(default=DocumentType.OTHER.value),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentOut:
    course, _member = require_course(db, user, course_id)
    data = read_limited(file, upload_byte_limit())
    document, created = store_new_document(
        db,
        get_storage(),
        course=course,
        user=user,
        filename=file.filename or "",
        data=data,
        title=title,
        document_type=_parse_document_type(document_type),
    )
    return _json(document, 201 if created else 200)


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentOut:
    document = require_document(db, user, document_id)
    if document.active_version is None:
        raise HTTPException(status_code=500, detail="Document has no active version")
    return to_document_out(document, document.active_version)


@router.get("/documents/{document_id}/file")
def get_document_file(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    document = require_document(db, user, document_id)
    version = document.active_version
    if version is None:
        raise HTTPException(status_code=500, detail="Document has no active version")
    path = get_storage().path_for(version.storage_key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Document file is missing")
    return FileResponse(path, media_type=version.mime_type, filename=version.original_filename)


@router.post("/documents/{document_id}/versions", response_model=DocumentOut)
def upload_version(
    document_id: uuid.UUID,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentOut:
    document = require_document(db, user, document_id)
    data = read_limited(file, upload_byte_limit())
    body, created = store_new_version(
        db,
        get_storage(),
        document=document,
        filename=file.filename or "",
        data=data,
    )
    return _json(body, 201 if created else 200)


@router.post("/documents/{document_id}/reprocess", response_model=ReprocessOut)
def reprocess_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReprocessOut:
    document = require_document(db, user, document_id)
    version = document.active_version
    if version is None:
        raise HTTPException(status_code=500, detail="Document has no active version")
    job = enqueue_processing(db, version, document.course_id)
    db.commit()
    db.refresh(job)
    db.refresh(version)
    return ReprocessOut(
        document=to_document_out(document, version),
        job_id=job.id,
        job_status=job.status,
    )


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    document = require_document(db, user, document_id)
    remove_document(db, get_storage(), document)
    return Response(status_code=204)

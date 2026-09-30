"""Turn one stored file version into page-numbered chunks and embeddings."""

import re
from dataclasses import dataclass

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import Document, DocumentChunk, DocumentStatus, DocumentVersion
from app.services.language import LanguageModel, TransientLanguageError
from app.services.storage import LocalObjectStorage

TARGET_CHARS = 3200
OVERLAP_CHARS = 400
EMBED_BATCH = 64

NO_TEXT_ERROR = "This file has no extractable text."


class PermanentIngestError(Exception):
    """A file or model failure that a retry will not fix."""


@dataclass
class ChunkDraft:
    page_start: int
    page_end: int
    text: str
    heading: str | None
    token_count: int


def _split_long(paragraph: str) -> list[str]:
    if len(paragraph) <= TARGET_CHARS:
        return [paragraph]
    pieces: list[str] = []
    start = 0
    while start < len(paragraph):
        end = min(start + TARGET_CHARS, len(paragraph))
        if end < len(paragraph):
            split_at = paragraph.rfind(" ", start, end)
            if split_at > start:
                end = split_at
        piece = paragraph[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= len(paragraph):
            break
        start = max(end - OVERLAP_CHARS, start + 1)
    return pieces


def chunk_pages(pages: list[tuple[int, str]]) -> list[ChunkDraft]:
    units: list[tuple[int, str]] = []
    for page_number, text in pages:
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
        if not paragraphs and text.strip():
            paragraphs = [text.strip()]
        for paragraph in paragraphs:
            for piece in _split_long(paragraph):
                units.append((page_number, piece))
    if not units:
        raise PermanentIngestError(NO_TEXT_ERROR)

    groups: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    current_len = 0
    for page_number, piece in units:
        extra = len(piece) + (2 if current else 0)
        if current and current_len + extra > TARGET_CHARS:
            groups.append(current)
            overlap = _tail(current, OVERLAP_CHARS)
            current = list(overlap)
            current_len = sum(len(item) + 2 for _, item in current)
        current.append((page_number, piece))
        current_len += extra
    if current:
        groups.append(current)

    drafts: list[ChunkDraft] = []
    for group in groups:
        text = "\n\n".join(piece for _, piece in group).strip()
        if not text:
            continue
        first_line = text.splitlines()[0].strip()
        heading = first_line if len(first_line) <= 80 else None
        drafts.append(
            ChunkDraft(
                page_start=group[0][0],
                page_end=group[-1][0],
                text=text,
                heading=heading,
                token_count=len(text.split()),
            )
        )
    if not drafts:
        raise PermanentIngestError(NO_TEXT_ERROR)
    return drafts


def _tail(group: list[tuple[int, str]], budget: int) -> list[tuple[int, str]]:
    kept: list[tuple[int, str]] = []
    size = 0
    for page_number, piece in reversed(group):
        if kept and size + len(piece) > budget:
            break
        kept.append((page_number, piece))
        size += len(piece)
        if size >= budget:
            break
    kept.reverse()
    return kept


def _mark(db: Session, version: DocumentVersion, status: DocumentStatus) -> None:
    version.status = status
    version.error = None
    db.commit()


def ingest_version(
    db: Session,
    version: DocumentVersion,
    model: LanguageModel,
    storage: LocalObjectStorage,
) -> None:
    document = db.get(Document, version.document_id)
    if document is None:
        raise PermanentIngestError("Document is missing.")

    _mark(db, version, DocumentStatus.EXTRACTING)
    try:
        data = storage.path_for(version.storage_key).read_bytes()
    except (OSError, ValueError) as exc:
        raise PermanentIngestError("The stored file could not be read.") from exc
    from app.services.extract import empty_text_error, extract_document

    pages = extract_document(version.original_filename, data, model)
    version.page_count = len(pages)
    if not any(text.strip() for _, text in pages):
        raise PermanentIngestError(empty_text_error(version.original_filename))

    _mark(db, version, DocumentStatus.CHUNKING)
    drafts = chunk_pages(pages)

    _mark(db, version, DocumentStatus.EMBEDDING)
    vectors: list[list[float]] = []
    texts = [draft.text for draft in drafts]
    try:
        for start in range(0, len(texts), EMBED_BATCH):
            vectors.extend(model.embed(texts[start : start + EMBED_BATCH]))
    except TransientLanguageError:
        raise
    except Exception as exc:
        raise PermanentIngestError("Embeddings could not be created.") from exc
    if len(vectors) != len(drafts):
        raise PermanentIngestError("Embeddings could not be created.")

    _mark(db, version, DocumentStatus.INDEXING)
    db.execute(delete(DocumentChunk).where(DocumentChunk.version_id == version.id))
    db.flush()
    for index, (draft, vector) in enumerate(zip(drafts, vectors, strict=True)):
        db.add(
            DocumentChunk(
                document_id=document.id,
                version_id=version.id,
                course_id=document.course_id,
                page_start=draft.page_start,
                page_end=draft.page_end,
                heading=draft.heading,
                chunk_index=index,
                text=draft.text,
                token_count=draft.token_count,
                embedding=vector,
            )
        )
    version.status = DocumentStatus.READY
    version.error = None
    db.commit()

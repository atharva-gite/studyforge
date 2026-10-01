"""Claim one document job at a time and index that version.

Run with `make worker`. A finished job is left alone. A retry deletes the
previous chunks for that version before inserting again.

A claim holds a lease. A dead worker's lease expires and another worker can
take the job. Writes after that point must still match the claim token, so
the old process cannot mark the job finished.
"""

import logging
import signal
import threading
import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import and_, or_, select, update
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import session_factory
from app.logging_config import configure_logging
from app.models import DocumentStatus, DocumentVersion, Job, JobStatus, utcnow
from app.services.ingest import LostLeaseError, PermanentIngestError, ingest_version
from app.services.language import PermanentLanguageError, get_language_model
from app.services.storage import get_storage

log = logging.getLogger("studyforge.worker")


@dataclass(frozen=True)
class WorkerStep:
    worked: bool
    retry_after: float = 0.0


def claim_job(db: Session) -> Job | None:
    now = utcnow()
    return db.scalar(
        select(Job)
        .where(
            Job.type == "document_processing",
            or_(
                Job.status == JobStatus.PENDING,
                and_(Job.status == JobStatus.RUNNING, Job.lease_expires_at < now),
            ),
        )
        .order_by(Job.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )


def _lease_deadline():
    return utcnow() + timedelta(seconds=get_settings().job_lease_seconds)


def _owned(db: Session, job_id: uuid.UUID, token: uuid.UUID, **values) -> bool:
    result = db.execute(
        update(Job).where(Job.id == job_id, Job.lease_token == token).values(**values),
        execution_options={"synchronize_session": False},
    )
    return result.rowcount == 1


def renew_lease(db: Session, job_id: uuid.UUID, token: uuid.UUID) -> None:
    if not _owned(db, job_id, token, lease_expires_at=_lease_deadline()):
        raise LostLeaseError()


def _fail(db: Session, job_id: uuid.UUID, token: uuid.UUID, version_id, message: str) -> None:
    db.rollback()
    text = message[:2000]
    if not _owned(
        db,
        job_id,
        token,
        status=JobStatus.FAILED,
        error=text,
        completed_at=utcnow(),
        lease_expires_at=None,
    ):
        db.rollback()
        return
    if version_id is not None:
        version = db.get(DocumentVersion, version_id)
        if version is not None:
            version.status = DocumentStatus.FAILED
            version.error = text
    db.commit()


def _release(db: Session, job_id: uuid.UUID, token: uuid.UUID) -> None:
    db.rollback()
    if not _owned(
        db,
        job_id,
        token,
        status=JobStatus.PENDING,
        error="Temporary error. The job will retry.",
        lease_expires_at=None,
    ):
        db.rollback()
        raise LostLeaseError()
    db.commit()


def run_once(db: Session) -> WorkerStep:
    try:
        return _run_once(db)
    finally:
        db.expire_all()


def _run_once(db: Session) -> WorkerStep:
    job = claim_job(db)
    if job is None:
        return WorkerStep(False)
    job_id = job.id
    version_id = job.document_version_id
    token = uuid.uuid4()
    job.status = JobStatus.RUNNING
    job.attempts += 1
    job.started_at = utcnow()
    job.lease_token = token
    job.lease_expires_at = _lease_deadline()
    attempts = job.attempts
    db.commit()

    try:
        version = db.get(DocumentVersion, version_id)
        if version is None:
            raise PermanentIngestError("Document version is missing.")
        ingest_version(
            db,
            version,
            get_language_model(),
            get_storage(),
            renew=lambda: renew_lease(db, job_id, token),
        )
        if not _owned(
            db,
            job_id,
            token,
            status=JobStatus.SUCCEEDED,
            completed_at=utcnow(),
            error=None,
            lease_expires_at=None,
        ):
            db.rollback()
            raise LostLeaseError()
        db.commit()
    except LostLeaseError:
        log.info("lost lease for job %s", job_id)
        db.rollback()
    except (PermanentIngestError, PermanentLanguageError) as exc:
        _fail(db, job_id, token, version_id, str(exc))
    except Exception:
        log.exception("ingest failed for job %s", job_id)
        if attempts >= get_settings().ingest_max_attempts:
            _fail(db, job_id, token, version_id, "Indexing failed after repeated errors.")
        else:
            try:
                _release(db, job_id, token)
            except LostLeaseError:
                log.info("lost lease for job %s", job_id)
                db.rollback()
            else:
                return WorkerStep(True, retry_after=min(2**attempts, 8))
    return WorkerStep(True)


def main() -> None:
    configure_logging()
    stop = threading.Event()

    def _request_stop(_signum, _frame) -> None:
        log.info("worker shutting down")
        stop.set()

    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)
    log.info("worker started")
    while not stop.is_set():
        db = session_factory()()
        try:
            step = run_once(db)
        except Exception:
            log.exception("worker loop error")
            db.rollback()
            step = WorkerStep(False)
        finally:
            db.close()
        if stop.is_set():
            break
        if step.retry_after > 0:
            stop.wait(step.retry_after)
        elif not step.worked:
            stop.wait(1)


if __name__ == "__main__":
    main()

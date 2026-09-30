"""Claim one document job at a time and index that PDF version.

Run with `make worker`. A second run of a finished job is a no-op.
A retry deletes the previous chunks for that version before inserting again.
"""

import logging
import time
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import session_factory
from app.models import DocumentStatus, DocumentVersion, Job, JobStatus, utcnow
from app.services.ingest import PermanentIngestError, ingest_version
from app.services.language import PermanentLanguageError, get_language_model
from app.services.storage import get_storage

log = logging.getLogger("studyforge.worker")


def claim_job(db: Session) -> Job | None:
    return db.scalar(
        select(Job)
        .where(Job.type == "document_processing", Job.status == JobStatus.PENDING)
        .order_by(Job.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )


def _fail(db: Session, job_id, version_id, message: str) -> None:
    db.rollback()
    version = db.get(DocumentVersion, version_id)
    if version is not None:
        version.status = DocumentStatus.FAILED
        version.error = message[:2000]
    job = db.get(Job, job_id)
    if job is not None:
        job.status = JobStatus.FAILED
        job.error = message[:2000]
        job.completed_at = utcnow()
    db.commit()


def run_once(db: Session, *, sleep: Callable[[float], None] = time.sleep) -> bool:
    job = claim_job(db)
    if job is None:
        return False
    job_id = job.id
    version_id = job.document_version_id
    job.status = JobStatus.RUNNING
    job.attempts += 1
    job.started_at = utcnow()
    attempts = job.attempts
    db.commit()

    try:
        version = db.get(DocumentVersion, version_id)
        if version is None:
            raise PermanentIngestError("Document version is missing.")
        ingest_version(db, version, get_language_model(), get_storage())
        finished = db.get(Job, job_id)
        if finished is not None:
            finished.status = JobStatus.SUCCEEDED
            finished.completed_at = utcnow()
            finished.error = None
            db.commit()
    except (PermanentIngestError, PermanentLanguageError) as exc:
        _fail(db, job_id, version_id, str(exc))
    except Exception:
        log.exception("ingest failed for job %s", job_id)
        db.rollback()
        if attempts >= get_settings().ingest_max_attempts:
            _fail(db, job_id, version_id, "Indexing failed after repeated errors.")
        else:
            waiting = db.get(Job, job_id)
            if waiting is not None:
                waiting.status = JobStatus.PENDING
                waiting.error = "Temporary error. The job will retry."
                db.commit()
            sleep(min(2**attempts, 8))
    return True


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    log.info("worker started")
    while True:
        db = session_factory()()
        try:
            worked = run_once(db)
        except Exception:
            log.exception("worker loop error")
            db.rollback()
            worked = False
        finally:
            db.close()
        if not worked:
            time.sleep(1)


if __name__ == "__main__":
    main()

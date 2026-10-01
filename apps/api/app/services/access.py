import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import Course, CourseMember, CourseRole, Document, User


def require_course(db: Session, user: User, course_id: uuid.UUID) -> tuple[Course, CourseMember]:
    """Missing courses and courses the user does not belong to both 404.

    A student must not learn that another student's course exists by editing the URL.
    """
    row = db.execute(
        select(Course, CourseMember)
        .join(CourseMember, CourseMember.course_id == Course.id)
        .where(Course.id == course_id, CourseMember.user_id == user.id)
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return row


def require_owner(member: CourseMember) -> None:
    if member.role != CourseRole.OWNER:
        raise HTTPException(status_code=403, detail="Only the course owner can change this course")


def require_document(db: Session, user: User, document_id: uuid.UUID) -> Document:
    document = db.scalar(
        select(Document)
        .join(CourseMember, CourseMember.course_id == Document.course_id)
        .where(Document.id == document_id, CourseMember.user_id == user.id)
        .options(joinedload(Document.active_version), selectinload(Document.versions))
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document

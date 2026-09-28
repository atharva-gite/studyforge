import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Course, CourseMember, CourseRole, Document, User
from app.schemas import CourseCreate, CourseOut, CourseUpdate
from app.services.access import require_course, require_owner
from app.services.documents import remove_document
from app.services.storage import get_storage

router = APIRouter(tags=["courses"])


def _course_out(course: Course, member: CourseMember, document_count: int) -> CourseOut:
    return CourseOut(
        id=course.id,
        name=course.name,
        code=course.code,
        description=course.description,
        role=member.role,
        document_count=document_count,
        created_at=course.created_at,
        updated_at=course.updated_at,
    )


def _document_counts(db: Session, course_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not course_ids:
        return {}
    rows = db.execute(
        select(Document.course_id, func.count())
        .where(Document.course_id.in_(course_ids))
        .group_by(Document.course_id)
    ).all()
    return {course_id: count for course_id, count in rows}


@router.get("/courses", response_model=list[CourseOut])
def list_courses(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[CourseOut]:
    rows = db.execute(
        select(Course, CourseMember)
        .join(CourseMember, CourseMember.course_id == Course.id)
        .where(CourseMember.user_id == user.id)
        .order_by(Course.created_at.desc())
    ).all()
    counts = _document_counts(db, [course.id for course, _member in rows])
    return [_course_out(course, member, counts.get(course.id, 0)) for course, member in rows]


@router.post("/courses", response_model=CourseOut, status_code=201)
def create_course(
    body: CourseCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CourseOut:
    course = Course(
        name=body.name,
        code=body.code,
        description=body.description,
        created_by_id=user.id,
    )
    db.add(course)
    db.flush()
    member = CourseMember(course_id=course.id, user_id=user.id, role=CourseRole.OWNER)
    db.add(member)
    db.commit()
    db.refresh(course)
    return _course_out(course, member, 0)


@router.get("/courses/{course_id}", response_model=CourseOut)
def get_course(
    course_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CourseOut:
    course, member = require_course(db, user, course_id)
    counts = _document_counts(db, [course.id])
    return _course_out(course, member, counts.get(course.id, 0))


@router.patch("/courses/{course_id}", response_model=CourseOut)
def update_course(
    course_id: uuid.UUID,
    body: CourseUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CourseOut:
    course, member = require_course(db, user, course_id)
    require_owner(member)
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No changes were provided")
    for field, value in updates.items():
        setattr(course, field, value)
    db.commit()
    db.refresh(course)
    counts = _document_counts(db, [course.id])
    return _course_out(course, member, counts.get(course.id, 0))


@router.delete("/courses/{course_id}", status_code=204)
def delete_course(
    course_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    course, member = require_course(db, user, course_id)
    require_owner(member)
    storage = get_storage()
    documents = list(db.scalars(select(Document).where(Document.course_id == course.id)).all())
    for document in documents:
        remove_document(db, storage, document)
    db.delete(course)
    db.commit()
    return Response(status_code=204)

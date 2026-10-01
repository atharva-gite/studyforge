import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import QuestionIn, QuestionOut
from app.services.access import require_course
from app.services.language import PermanentLanguageError, TransientLanguageError, get_language_model
from app.services.limits import require_model_budget, retry_transient
from app.services.retrieval import answer_question

router = APIRouter(tags=["questions"])


@router.post("/courses/{course_id}/questions", response_model=QuestionOut)
def ask_question(
    course_id: uuid.UUID,
    body: QuestionIn,
    user: User = Depends(require_model_budget),
    db: Session = Depends(get_db),
) -> QuestionOut:
    require_course(db, user, course_id)
    try:
        evidence = retry_transient(
            db, lambda: answer_question(db, course_id, body.question, get_language_model())
        )
    except TransientLanguageError as exc:
        raise HTTPException(status_code=503, detail="The language model is unavailable. Try again.") from exc
    except PermanentLanguageError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not evidence.sufficient:
        return QuestionOut(status="insufficient_evidence", answer=None, citations=[])
    return QuestionOut(status="answered", answer=evidence.answer, citations=evidence.citations)

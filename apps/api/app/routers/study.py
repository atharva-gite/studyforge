import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import (
    CardRating,
    CourseMember,
    Document,
    DocumentChunk,
    Exam,
    Flashcard,
    FlashcardDeck,
    Quiz,
    QuizQuestion,
    SessionStatus,
    StudyPlan,
    StudySession,
    User,
)
from app.schemas import (
    AttemptIn,
    AttemptOut,
    DeckCreateOut,
    DeckOut,
    FocusIn,
    PlanIn,
    PlanOut,
    QuizCreateOut,
    QuizOut,
    ReviewIn,
    SessionOut,
)
from app.services.access import require_course
from app.services.language import PermanentLanguageError, TransientLanguageError, get_language_model
from app.services.limits import require_model_budget, retry_transient
from app.services.study import (
    create_deck,
    create_plan,
    create_quiz,
    latest_ratings,
    next_card_id,
    record_review,
    score_attempt,
)

router = APIRouter(tags=["study"])


def _cards(db: Session, deck_id: uuid.UUID) -> list[Flashcard]:
    return list(
        db.scalars(select(Flashcard).where(Flashcard.deck_id == deck_id).order_by(Flashcard.position)).all()
    )


def _deck_out(db: Session, deck: FlashcardDeck) -> DeckOut:
    cards = _cards(db, deck.id)
    ratings = latest_ratings(db, [card.id for card in cards])
    chunk_ids = [card.source_chunk_id for card in cards if card.source_chunk_id]
    sources: dict[uuid.UUID, tuple[DocumentChunk, str]] = {}
    if chunk_ids:
        rows = db.execute(
            select(DocumentChunk, Document.title)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(DocumentChunk.id.in_(chunk_ids))
        ).all()
        sources = {chunk.id: (chunk, title) for chunk, title in rows}
    rendered = []
    for card in cards:
        source = sources.get(card.source_chunk_id) if card.source_chunk_id else None
        chunk, title = source if source else (None, None)
        rating = ratings.get(card.id)
        rendered.append(
            {
                "id": card.id,
                "position": card.position,
                "front": card.front,
                "back": card.back,
                "latest_rating": rating.value if rating else None,
                "chunk_id": card.source_chunk_id,
                "document_id": chunk.document_id if chunk else None,
                "document_title": title,
                "page_start": chunk.page_start if chunk else None,
            }
        )
    return DeckOut(id=deck.id, title=deck.title, next_card_id=next_card_id(cards, ratings), cards=rendered)


def _require_deck(db: Session, user: User, deck_id: uuid.UUID) -> FlashcardDeck:
    deck = db.scalar(
        select(FlashcardDeck)
        .join(CourseMember, CourseMember.course_id == FlashcardDeck.course_id)
        .where(FlashcardDeck.id == deck_id, FlashcardDeck.user_id == user.id, CourseMember.user_id == user.id)
    )
    if deck is None:
        raise HTTPException(status_code=404, detail="Deck not found")
    return deck


def _quiz_out(db: Session, quiz: Quiz) -> QuizOut:
    questions = db.scalars(
        select(QuizQuestion).where(QuizQuestion.quiz_id == quiz.id).order_by(QuizQuestion.position)
    ).all()
    return QuizOut(
        id=quiz.id,
        title=quiz.title,
        questions=[
            {"id": question.id, "position": question.position, "prompt": question.prompt, "options": list(question.options)}
            for question in questions
        ],
    )


def _require_quiz(db: Session, user: User, quiz_id: uuid.UUID) -> Quiz:
    quiz = db.scalar(
        select(Quiz)
        .join(CourseMember, CourseMember.course_id == Quiz.course_id)
        .where(Quiz.id == quiz_id, Quiz.user_id == user.id, CourseMember.user_id == user.id)
    )
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return quiz


def _plan_out(db: Session, plan: StudyPlan) -> PlanOut:
    exam = db.get(Exam, plan.target_exam_id) if plan.target_exam_id else None
    sessions = db.scalars(
        select(StudySession).where(StudySession.plan_id == plan.id).order_by(StudySession.priority)
    ).all()
    return PlanOut(
        id=plan.id,
        exam_title=exam.title if exam else plan_title(plan),
        exam_date=plan.end_date,
        hours_per_day=float(plan.available_hours_per_day),
        sessions=[
            SessionOut(
                id=session.id,
                scheduled_on=session.scheduled_on,
                duration_minutes=session.duration_minutes,
                activity=session.activity,
                focus=session.focus,
                status=session.status.value,
            )
            for session in sessions
        ],
    )


def plan_title(plan: StudyPlan) -> str:
    return "Study plan"


def _language_error(exc: Exception) -> HTTPException:
    if isinstance(exc, TransientLanguageError):
        return HTTPException(status_code=503, detail="The language model is unavailable. Try again.")
    return HTTPException(status_code=503, detail=str(exc))


@router.get("/courses/{course_id}/decks", response_model=list[DeckOut])
def list_decks(
    course_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DeckOut]:
    require_course(db, user, course_id)
    decks = db.scalars(
        select(FlashcardDeck)
        .where(FlashcardDeck.course_id == course_id, FlashcardDeck.user_id == user.id)
        .order_by(FlashcardDeck.created_at.desc())
    ).all()
    return [_deck_out(db, deck) for deck in decks]


@router.post("/courses/{course_id}/decks", response_model=DeckCreateOut)
def generate_deck(
    course_id: uuid.UUID,
    body: FocusIn,
    user: User = Depends(require_model_budget),
    db: Session = Depends(get_db),
) -> DeckCreateOut:
    require_course(db, user, course_id)
    try:
        deck = retry_transient(
            db, lambda: create_deck(db, course_id, user.id, body.focus, get_language_model())
        )
    except (TransientLanguageError, PermanentLanguageError) as exc:
        raise _language_error(exc) from exc
    if deck is None:
        return DeckCreateOut(status="insufficient_evidence", deck=None)
    return DeckCreateOut(status="created", deck=_deck_out(db, deck))


@router.post("/decks/{deck_id}/reviews", response_model=DeckOut)
def review_card(
    deck_id: uuid.UUID,
    body: ReviewIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeckOut:
    deck = _require_deck(db, user, deck_id)
    card = db.scalar(select(Flashcard).where(Flashcard.id == body.card_id, Flashcard.deck_id == deck.id))
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")
    record_review(db, card, user.id, CardRating(body.rating))
    return _deck_out(db, deck)


@router.post("/courses/{course_id}/quizzes", response_model=QuizCreateOut)
def generate_quiz(
    course_id: uuid.UUID,
    body: FocusIn,
    user: User = Depends(require_model_budget),
    db: Session = Depends(get_db),
) -> QuizCreateOut:
    require_course(db, user, course_id)
    try:
        quiz = retry_transient(
            db, lambda: create_quiz(db, course_id, user.id, body.focus, get_language_model())
        )
    except (TransientLanguageError, PermanentLanguageError) as exc:
        raise _language_error(exc) from exc
    if quiz is None:
        return QuizCreateOut(status="insufficient_evidence", quiz=None)
    return QuizCreateOut(status="created", quiz=_quiz_out(db, quiz))


@router.get("/quizzes/{quiz_id}", response_model=QuizOut)
def get_quiz(
    quiz_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizOut:
    return _quiz_out(db, _require_quiz(db, user, quiz_id))


@router.post("/quizzes/{quiz_id}/attempts", response_model=AttemptOut)
def submit_attempt(
    quiz_id: uuid.UUID,
    body: AttemptIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AttemptOut:
    quiz = _require_quiz(db, user, quiz_id)
    question_ids = set(
        db.scalars(select(QuizQuestion.id).where(QuizQuestion.quiz_id == quiz.id)).all()
    )
    answers: dict[uuid.UUID, int] = {}
    for answer in body.answers:
        if answer.question_id not in question_ids:
            raise HTTPException(status_code=400, detail="That question is not part of this quiz")
        answers[answer.question_id] = answer.selected_option_index
    attempt, results = score_attempt(db, quiz, user.id, answers)
    return AttemptOut(score=float(attempt.score or 0), results=results)


@router.get("/courses/{course_id}/plans", response_model=list[PlanOut])
def list_plans(
    course_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PlanOut]:
    require_course(db, user, course_id)
    plans = db.scalars(
        select(StudyPlan)
        .where(StudyPlan.course_id == course_id, StudyPlan.user_id == user.id)
        .order_by(StudyPlan.created_at.desc())
    ).all()
    return [_plan_out(db, plan) for plan in plans]


@router.post("/courses/{course_id}/plans", response_model=PlanOut)
def generate_plan(
    course_id: uuid.UUID,
    body: PlanIn,
    user: User = Depends(require_model_budget),
    db: Session = Depends(get_db),
) -> PlanOut:
    require_course(db, user, course_id)
    today = datetime.now(timezone.utc).date()
    if body.exam_date < today:
        raise HTTPException(status_code=400, detail="The exam date has to be today or later.")
    try:
        plan = retry_transient(
            db,
            lambda: create_plan(
                db,
                course_id,
                user.id,
                body.exam_title,
                body.exam_date,
                body.hours_per_day,
                get_language_model(),
                today=today,
            ),
        )
    except (TransientLanguageError, PermanentLanguageError) as exc:
        raise _language_error(exc) from exc
    return _plan_out(db, plan)


@router.post("/sessions/{session_id}/complete", response_model=SessionOut)
def complete_session(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SessionOut:
    session = db.scalar(
        select(StudySession)
        .join(StudyPlan, StudyPlan.id == StudySession.plan_id)
        .join(CourseMember, CourseMember.course_id == StudyPlan.course_id)
        .where(StudySession.id == session_id, StudyPlan.user_id == user.id, CourseMember.user_id == user.id)
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    session.status = SessionStatus.COMPLETED
    db.commit()
    return SessionOut(
        id=session.id,
        scheduled_on=session.scheduled_on,
        duration_minutes=session.duration_minutes,
        activity=session.activity,
        focus=session.focus,
        status=session.status.value,
    )

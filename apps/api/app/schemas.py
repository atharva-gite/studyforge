import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import CourseRole, DocumentStatus, DocumentType, JobStatus


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str


class RegisterIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=8, max_length=200)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name is required")
        return value


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class CourseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=4000)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Course name is required")
        return value

    @field_validator("code", "description")
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class CourseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    code: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=4000)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Course name is required")
        return value

    @field_validator("code", "description")
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class CourseOut(BaseModel):
    id: uuid.UUID
    name: str
    code: str | None
    description: str | None
    role: CourseRole
    document_count: int
    created_at: datetime
    updated_at: datetime


class DocumentOut(BaseModel):
    id: uuid.UUID
    course_id: uuid.UUID
    title: str
    document_type: DocumentType
    status: DocumentStatus
    original_filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    version_number: int
    version_id: uuid.UUID
    error: str | None
    created_at: datetime
    duplicate: bool = False


class ReprocessOut(BaseModel):
    document: DocumentOut
    job_id: uuid.UUID
    job_status: JobStatus


class QuestionIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class CitationOut(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    page_start: int | None
    page_end: int | None
    section: str | None


class QuestionOut(BaseModel):
    status: Literal["answered", "insufficient_evidence"]
    answer: str | None
    citations: list[CitationOut]


class FocusIn(BaseModel):
    focus: str = Field(min_length=1, max_length=200)


class CardOut(BaseModel):
    id: uuid.UUID
    position: int
    front: str
    back: str
    latest_rating: str | None
    chunk_id: uuid.UUID | None
    document_id: uuid.UUID | None
    document_title: str | None
    page_start: int | None


class DeckOut(BaseModel):
    id: uuid.UUID
    title: str
    next_card_id: uuid.UUID | None
    cards: list[CardOut]


class DeckCreateOut(BaseModel):
    status: Literal["created", "insufficient_evidence"]
    deck: DeckOut | None


class ReviewIn(BaseModel):
    card_id: uuid.UUID
    rating: Literal["AGAIN", "KNOWN"]


class QuizQuestionOut(BaseModel):
    id: uuid.UUID
    position: int
    prompt: str
    options: list[str]


class QuizOut(BaseModel):
    id: uuid.UUID
    title: str
    questions: list[QuizQuestionOut]


class QuizCreateOut(BaseModel):
    status: Literal["created", "insufficient_evidence"]
    quiz: QuizOut | None


class AnswerIn(BaseModel):
    question_id: uuid.UUID
    selected_option_index: int = Field(ge=0, le=20)


class AttemptIn(BaseModel):
    answers: list[AnswerIn]


class AttemptResultOut(BaseModel):
    question_id: uuid.UUID
    prompt: str
    selected_option_index: int | None
    correct_option_index: int
    correct: bool
    explanation: str | None
    citation: CitationOut | None


class AttemptOut(BaseModel):
    score: float
    results: list[AttemptResultOut]


class PlanIn(BaseModel):
    exam_title: str = Field(min_length=1, max_length=200)
    exam_date: date
    hours_per_day: float = Field(gt=0, le=16)


class SessionOut(BaseModel):
    id: uuid.UUID
    scheduled_on: date
    duration_minutes: int
    activity: str
    focus: str | None
    status: str


class PlanOut(BaseModel):
    id: uuid.UUID
    exam_title: str
    exam_date: date
    hours_per_day: float
    sessions: list[SessionOut]

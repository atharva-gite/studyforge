import uuid
from datetime import datetime

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

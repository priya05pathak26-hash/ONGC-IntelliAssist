from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_serializer


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8)
    role: str = "employee"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    session_id: int | None = None
    mode: str = "auto"
    focus_document_id: int | None = None


class SourceCitation(BaseModel):
    file_name: str | None = None
    page_number: int | None = None
    similarity_score: float | None = None
    retrieved_chunk: str | None = None
    source: str


class ChatResponse(BaseModel):
    session_id: int
    user_message_id: int
    assistant_message_id: int
    answer: str
    source: str | None = None
    domain: str | None = None
    response_time_ms: int
    citations: list[SourceCitation]


def _naive_utc_to_iso_z(value: datetime | None) -> str | None:
    """Issue 10 Fix: render stored naive-UTC timestamps with a trailing 'Z'.

    Server writes every timestamp with datetime.utcnow() (naive). Without 'Z',
    JavaScript's `new Date("YYYY-MM-DDTHH:MM:SS")` parses it as LOCAL time,
    which made sidebar session times differ from chat-message times by the
    browser's UTC offset (e.g. 5:30 h in India).  Chat message timestamps
    were being created on the client as .toISOString() (always Z-suffixed),
    so the user perceived a clear mismatch.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{value.microsecond // 1000:03d}Z"


class SessionOut(BaseModel):
    id: int
    title: str
    pinned: bool
    created_at: datetime | None = None
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_serializer("updated_at", "created_at")
    def serialize_dt(self, value: datetime | None, _info) -> str | None:
        return _naive_utc_to_iso_z(value)


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    source: str | None
    domain: str | None
    similarity_score: float | None
    response_time_ms: int | None
    citations: Any | None
    created_at: datetime

    class Config:
        from_attributes = True

    @field_serializer("created_at")
    def serialize_dt(self, value: datetime | None, _info) -> str | None:
        return _naive_utc_to_iso_z(value)


class FeedbackIn(BaseModel):
    message_id: int
    helpful: bool
    comment: str | None = None



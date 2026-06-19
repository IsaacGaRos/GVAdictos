"""Pydantic models for API request/response validation."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Any
from datetime import datetime


# Auth models
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    is_admin: bool
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# Article models
class ArticleResponse(BaseModel):
    id: int
    article_ref: str
    title: Optional[str]
    text: str
    law_id: int


class ArticleDetailResponse(ArticleResponse):
    insights: list[dict] = []
    related: list[dict] = []


# Topic models
class TopicResponse(BaseModel):
    id: int
    topic_number: int
    part: str
    official_text: str
    articles_count: Optional[int] = 0


class TopicDetailResponse(TopicResponse):
    articles: list[ArticleResponse] = []


# Question models
class QuestionOption(BaseModel):
    letra: str
    texto: str


class QuestionResponse(BaseModel):
    id: int
    enunciado: str
    opcion_a: str
    opcion_b: str
    opcion_c: str
    opcion_d: str
    respuesta_correcta: str


class AIQuestionResponse(BaseModel):
    id: int
    enunciado: str
    opciones: list[QuestionOption]
    respuesta_correcta: str
    estilo: str


# Exam models
class ExamConfig(BaseModel):
    title: str
    num_questions: int = Field(default=30, ge=5, le=100)
    time_limit_minutes: Optional[int] = None
    source_kind: str = "mixto"  # oficial, ia, mixto
    topic_id: Optional[int] = None


class ExamResponse(BaseModel):
    id: int
    title: str
    num_questions: int
    started_at: str
    finished_at: Optional[str] = None
    score_percent: Optional[float] = None
    passed: Optional[bool] = None


class ExamAnswerSubmit(BaseModel):
    question_number: int
    source_kind: str
    question_id: int
    user_answer: str
    tiempo_segundos: Optional[float] = None


class ExamResultResponse(BaseModel):
    exam_id: int
    score_percent: float
    correct: int
    total: int
    passed: bool
    time_minutes: float


# Study models
class NoteCreate(BaseModel):
    article_id: int
    note_text: str
    selected_text: Optional[str] = None
    tags: Optional[str] = None


class NoteResponse(BaseModel):
    id: int
    article_id: int
    note_text: str
    selected_text: Optional[str]
    tags: Optional[str]
    created_at: str


class HighlightCreate(BaseModel):
    article_id: int
    selected_text: str
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None


class HighlightResponse(BaseModel):
    id: int
    article_id: int
    selected_text: str
    created_at: str


class ProgressResponse(BaseModel):
    article_id: int
    topic_id: int
    confidence: float
    review_count: int
    last_review: Optional[str]
    next_review: Optional[str]


# Insight models
class InsightResponse(BaseModel):
    id: int
    article_id: int
    insight_type: str
    content: str
    model: str
    requiere_revision: bool
    validation_status: str


# Error models
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    status_code: int

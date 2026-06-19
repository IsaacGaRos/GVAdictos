"""SQLAlchemy ORM models for database abstraction (F4 implementation).

Supports both SQLite (development) and PostgreSQL (production).
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Boolean, BLOB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


# Core entities (global, shared)

class Law(Base):
    __tablename__ = "laws"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    source_path = Column(String)
    source_hash = Column(String)
    imported_at = Column(DateTime, default=datetime.utcnow)
    validation_status = Column(String, default="pendiente_de_validacion")

    articles = relationship("Article", back_populates="law", cascade="all, delete-orphan")


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True)
    law_id = Column(Integer, ForeignKey("laws.id"), nullable=False)
    article_ref = Column(String)
    title = Column(String)
    chapter = Column(String)
    section = Column(String)
    text = Column(Text, nullable=False)
    tags = Column(String)
    source = Column(String, nullable=False)
    original_hash = Column(String, nullable=False)
    imported_at = Column(DateTime, default=datetime.utcnow)
    validation_status = Column(String, default="pendiente_de_validacion")

    law = relationship("Law", back_populates="articles")


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True)
    topic_number = Column(Integer)
    part = Column(String)
    official_text = Column(Text)
    section = Column(String)
    imported_at = Column(DateTime, default=datetime.utcnow)

    sources = relationship("TopicSource", back_populates="topic", cascade="all, delete-orphan")


class TopicSource(Base):
    __tablename__ = "topic_sources"

    id = Column(Integer, primary_key=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    law_id = Column(Integer, ForeignKey("laws.id"), nullable=False)
    article_id = Column(Integer, ForeignKey("articles.id"))
    mapping_basis = Column(String)
    validation_status = Column(String, default="pendiente_de_validacion")

    topic = relationship("Topic", back_populates="sources")


# User-scoped entities

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)

    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    notes = relationship("StudyArticleNote", back_populates="user", cascade="all, delete-orphan")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="sessions")


class StudyArticleNote(Base):
    __tablename__ = "study_article_notes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    article_id = Column(Integer, ForeignKey("articles.id"))
    note_text = Column(Text, nullable=False)
    tags = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="notes")


class AIArticleInsight(Base):
    __tablename__ = "ai_article_insights"

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    insight_type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    model = Column(String, nullable=False)
    prompt_version = Column(String, nullable=False)
    input_hash = Column(String, nullable=False)
    requiere_revision = Column(Boolean, default=True)
    validation_status = Column(String, default="pendiente_de_validacion")
    generated_at = Column(DateTime, default=datetime.utcnow)


class MockExam(Base):
    __tablename__ = "mock_exams"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    num_questions = Column(Integer, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    score_percent = Column(Float)
    passed = Column(Boolean)


class Oposicion(Base):
    __tablename__ = "oposiciones"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    nombre = Column(String, nullable=False)
    administracion = Column(String)
    activa = Column(Boolean, default=True)


class UserOposicionEnrollment(Base):
    __tablename__ = "user_oposicion_enrollment"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    oposicion_id = Column(Integer, ForeignKey("oposiciones.id"), nullable=False)
    enrolled_at = Column(DateTime, default=datetime.utcnow)


# F5 — Billing & Subscriptions
class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stripe_customer_id = Column(String, unique=True)
    stripe_subscription_id = Column(String, unique=True)
    plan = Column(String, nullable=False)  # 'free', 'pro', 'premium'
    status = Column(String, nullable=False)  # 'active', 'canceled', 'past_due'
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    canceled_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Entitlement(Base):
    __tablename__ = "entitlements"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    feature = Column(String, nullable=False)  # 'unlimited_exams', 'ai_insights', 'drive_backup'
    granted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)


# F6 — Drive Backup
class BackupHistory(Base):
    __tablename__ = "backup_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    backup_type = Column(String, nullable=False)  # 'auto', 'manual'
    drive_file_id = Column(String)
    drive_file_name = Column(String)
    backup_size_bytes = Column(Integer)
    status = Column(String, nullable=False)  # 'success', 'failed', 'pending'
    created_at = Column(DateTime, default=datetime.utcnow)
    error_message = Column(Text)


# E5 — Exam Progress & Results
class ExamResult(Base):
    __tablename__ = "exam_results"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    exam_id = Column(Integer, ForeignKey("mock_exams.id"), nullable=False)
    question_id = Column(Integer)
    selected_answer = Column(String)
    is_correct = Column(Boolean)
    time_spent_seconds = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


# Optional: Global source & versioning tables
class SourceVersion(Base):
    __tablename__ = "source_versions"

    id = Column(Integer, primary_key=True)
    source_name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    content_hash = Column(String)
    checked_at = Column(DateTime, default=datetime.utcnow)
    is_current = Column(Boolean, default=True)


class LawVersion(Base):
    __tablename__ = "law_versions"

    id = Column(Integer, primary_key=True)
    law_id = Column(Integer, ForeignKey("laws.id"), nullable=False)
    version = Column(String, nullable=False)
    content_hash = Column(String, nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow)
    is_current = Column(Boolean, default=True)

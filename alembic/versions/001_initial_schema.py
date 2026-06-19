"""Initial schema with all entities from F4-F7.

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-06-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial schema."""

    # Laws table
    op.create_table(
        "laws",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("source_path", sa.String(), nullable=True),
        sa.Column("source_hash", sa.String(), nullable=True),
        sa.Column("imported_at", sa.DateTime(), nullable=True),
        sa.Column("validation_status", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Articles table
    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("law_id", sa.Integer(), nullable=False),
        sa.Column("article_ref", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("chapter", sa.String(), nullable=True),
        sa.Column("section", sa.String(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("tags", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("original_hash", sa.String(), nullable=False),
        sa.Column("imported_at", sa.DateTime(), nullable=True),
        sa.Column("validation_status", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["law_id"], ["laws.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Topics table
    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("topic_number", sa.Integer(), nullable=True),
        sa.Column("part", sa.String(), nullable=True),
        sa.Column("official_text", sa.Text(), nullable=True),
        sa.Column("section", sa.String(), nullable=True),
        sa.Column("imported_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # TopicSources table
    op.create_table(
        "topic_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("law_id", sa.Integer(), nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=True),
        sa.Column("mapping_basis", sa.String(), nullable=True),
        sa.Column("validation_status", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["law_id"], ["laws.id"], ),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("last_login", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("is_admin", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    # UserSessions table
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )

    # StudyArticleNotes table
    op.create_table(
        "study_article_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=True),
        sa.Column("note_text", sa.Text(), nullable=False),
        sa.Column("tags", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )

    # AIArticleInsights table
    op.create_table(
        "ai_article_insights",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("insight_type", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("prompt_version", sa.String(), nullable=False),
        sa.Column("input_hash", sa.String(), nullable=False),
        sa.Column("requiere_revision", sa.Boolean(), nullable=True),
        sa.Column("validation_status", sa.String(), nullable=True),
        sa.Column("generated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )

    # MockExams table
    op.create_table(
        "mock_exams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("num_questions", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("score_percent", sa.Float(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Oposiciones table
    op.create_table(
        "oposiciones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("administracion", sa.String(), nullable=True),
        sa.Column("activa", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    # UserOposicionEnrollment table
    op.create_table(
        "user_oposicion_enrollment",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("oposicion_id", sa.Integer(), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["oposicion_id"], ["oposiciones.id"], ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Subscriptions table (F5)
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("stripe_customer_id", sa.String(), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(), nullable=True),
        sa.Column("plan", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("current_period_start", sa.DateTime(), nullable=True),
        sa.Column("current_period_end", sa.DateTime(), nullable=True),
        sa.Column("canceled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_customer_id"),
        sa.UniqueConstraint("stripe_subscription_id"),
    )

    # Entitlements table (F5)
    op.create_table(
        "entitlements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("feature", sa.String(), nullable=False),
        sa.Column("granted_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )

    # BackupHistory table (F6)
    op.create_table(
        "backup_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("backup_type", sa.String(), nullable=False),
        sa.Column("drive_file_id", sa.String(), nullable=True),
        sa.Column("drive_file_name", sa.String(), nullable=True),
        sa.Column("backup_size_bytes", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ExamResults table (E5)
    op.create_table(
        "exam_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("exam_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=True),
        sa.Column("selected_answer", sa.String(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("time_spent_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["exam_id"], ["mock_exams.id"], ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )

    # SourceVersions table
    op.create_table(
        "source_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=True),
        sa.Column("checked_at", sa.DateTime(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # LawVersions table
    op.create_table(
        "law_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("law_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("changed_at", sa.DateTime(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["law_id"], ["laws.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for performance
    op.create_index("ix_articles_law_id", "articles", ["law_id"])
    op.create_index("ix_articles_source", "articles", ["source"])
    op.create_index("ix_topic_sources_topic_id", "topic_sources", ["topic_id"])
    op.create_index("ix_topic_sources_law_id", "topic_sources", ["law_id"])
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_study_article_notes_user_id", "study_article_notes", ["user_id"])
    op.create_index("ix_mock_exams_user_id", "mock_exams", ["user_id"])
    op.create_index("ix_exam_results_user_id", "exam_results", ["user_id"])
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])
    op.create_index("ix_backup_history_user_id", "backup_history", ["user_id"])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_index("ix_backup_history_user_id")
    op.drop_index("ix_subscriptions_user_id")
    op.drop_index("ix_exam_results_user_id")
    op.drop_index("ix_mock_exams_user_id")
    op.drop_index("ix_study_article_notes_user_id")
    op.drop_index("ix_user_sessions_user_id")
    op.drop_index("ix_topic_sources_law_id")
    op.drop_index("ix_topic_sources_topic_id")
    op.drop_index("ix_articles_source")
    op.drop_index("ix_articles_law_id")

    op.drop_table("law_versions")
    op.drop_table("source_versions")
    op.drop_table("exam_results")
    op.drop_table("backup_history")
    op.drop_table("entitlements")
    op.drop_table("subscriptions")
    op.drop_table("user_oposicion_enrollment")
    op.drop_table("oposiciones")
    op.drop_table("mock_exams")
    op.drop_table("ai_article_insights")
    op.drop_table("study_article_notes")
    op.drop_table("user_sessions")
    op.drop_table("users")
    op.drop_table("topic_sources")
    op.drop_table("topics")
    op.drop_table("articles")
    op.drop_table("laws")

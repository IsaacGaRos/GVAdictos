from __future__ import annotations

import sqlite3
from typing import Any
from datetime import datetime, timedelta

from src.ai.schema import missing_ai_tables

RowDict = dict[str, Any]


class AIStorageError(RuntimeError):
    """Base error for AI storage issues."""


class AISchemaMissingError(AIStorageError):
    """Raised when AI feature tables have not been migrated yet."""


class AIRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.conn.row_factory = sqlite3.Row

    def ensure_storage_ready(self) -> None:
        missing = missing_ai_tables(self.conn)
        if missing:
            raise AISchemaMissingError(
                "AI feature tables are not migrated: " + ", ".join(missing)
            )

    def get_article_snapshot(self, article_id: int) -> RowDict | None:
        row = self.conn.execute(
            "SELECT id, law_id, article_ref, title, text FROM articles WHERE id = ?",
            (article_id,),
        ).fetchone()
        return dict(row) if row else None

    def create_article_insight(
        self,
        *,
        article_id: int,
        insight_type: str,
        content: str,
        model: str,
        prompt_version: str,
        input_hash: str,
        article_version_id: int | None = None,
        requiere_revision: bool = True,
    ) -> int:
        """Create a new AI insight for an article."""
        self.ensure_storage_ready()
        cursor = self.conn.execute(
            """
            INSERT INTO ai_article_insights(
                article_id, article_version_id, insight_type, content, model,
                prompt_version, input_hash, requiere_revision
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                article_id,
                article_version_id,
                insight_type,
                content,
                model,
                prompt_version,
                input_hash,
                1 if requiere_revision else 0,
            ),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def get_article_insight(
        self,
        article_id: int,
        insight_type: str,
        input_hash: str,
    ) -> RowDict | None:
        """Get an existing insight by article, type, and input hash."""
        row = self.conn.execute(
            """
            SELECT * FROM ai_article_insights
            WHERE article_id = ? AND insight_type = ? AND input_hash = ?
            """,
            (article_id, insight_type, input_hash),
        ).fetchone()
        return dict(row) if row else None

    def get_article_insights(
        self,
        article_id: int,
        insight_type: str | None = None,
    ) -> list[RowDict]:
        """Get all insights for an article, optionally filtered by type."""
        if insight_type:
            rows = self.conn.execute(
                """
                SELECT * FROM ai_article_insights
                WHERE article_id = ? AND insight_type = ?
                ORDER BY generated_at DESC
                """,
                (article_id, insight_type),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """
                SELECT * FROM ai_article_insights
                WHERE article_id = ?
                ORDER BY generated_at DESC
                """,
                (article_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def update_insight_validation(
        self,
        insight_id: int,
        validation_status: str,
        requiere_revision: bool = False,
    ) -> None:
        """Update validation status of an insight."""
        self.conn.execute(
            """
            UPDATE ai_article_insights
            SET validation_status = ?, requiere_revision = ?
            WHERE id = ?
            """,
            (validation_status, 1 if requiere_revision else 0, insight_id),
        )
        self.conn.commit()

    def get_prompt_cache(self, input_hash: str) -> RowDict | None:
        """Get cached prompt output by input hash."""
        row = self.conn.execute(
            """
            SELECT * FROM ai_prompt_cache
            WHERE input_hash = ? AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            """,
            (input_hash,),
        ).fetchone()
        return dict(row) if row else None

    def set_prompt_cache(
        self,
        input_hash: str,
        prompt_type: str,
        prompt_version: str,
        input_text: str,
        output_text: str,
        model: str,
        tokens_used: int | None = None,
        cost_usd: float | None = None,
        cache_hours: int = 24,
    ) -> int:
        """Cache a prompt output."""
        expires_at = (datetime.utcnow() + timedelta(hours=cache_hours)).isoformat()
        cursor = self.conn.execute(
            """
            INSERT INTO ai_prompt_cache(
                input_hash, prompt_type, prompt_version, input_text, output_text,
                model, tokens_used, cost_usd, expires_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                input_hash,
                prompt_type,
                prompt_version,
                input_text,
                output_text,
                model,
                tokens_used,
                cost_usd,
                expires_at,
            ),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def clear_expired_cache(self) -> int:
        """Remove expired cache entries."""
        cursor = self.conn.execute(
            """
            DELETE FROM ai_prompt_cache
            WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP
            """
        )
        self.conn.commit()
        return cursor.rowcount

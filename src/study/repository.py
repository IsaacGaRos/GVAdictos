from __future__ import annotations

import sqlite3
from typing import Any

from src.study.schema import STUDY_TABLES, missing_study_tables


RowDict = dict[str, Any]


class StudyStorageError(RuntimeError):
    """Base error for study storage issues."""


class StudySchemaMissingError(StudyStorageError):
    """Raised when study feature tables have not been migrated yet."""


class StudyRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.conn.row_factory = sqlite3.Row

    def get_article_snapshot(self, article_id: int) -> RowDict | None:
        row = self.conn.execute(
            "SELECT id, law_id, article_ref, title FROM articles WHERE id = ?",
            (article_id,),
        ).fetchone()
        return dict(row) if row else None

    def get_topic_snapshot(self, topic_id: int) -> RowDict | None:
        row = self.conn.execute(
            "SELECT id, topic_number, part, official_text FROM topics WHERE id = ?",
            (topic_id,),
        ).fetchone()
        return dict(row) if row else None

    def ensure_storage_ready(self) -> None:
        missing = missing_study_tables(self.conn)
        if missing:
            raise StudySchemaMissingError(
                "Study feature tables are not migrated: " + ", ".join(missing)
            )

    def create_article_note(
        self,
        *,
        article_id: int,
        note_text: str,
        selected_text: str | None = None,
        anchor_key: str | None = None,
        tags: str | None = None,
    ) -> int:
        self.ensure_storage_ready()
        snapshot = self.get_article_snapshot(article_id)
        law_id_snapshot = snapshot["law_id"] if snapshot else None
        article_ref_snapshot = snapshot["article_ref"] if snapshot else None
        cursor = self.conn.execute(
            """
            INSERT INTO study_article_notes(
                article_id, law_id_snapshot, article_ref_snapshot, anchor_key,
                selected_text, note_text, tags
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                article_id,
                law_id_snapshot,
                article_ref_snapshot,
                anchor_key,
                selected_text,
                note_text,
                tags,
            ),
        )
        return int(cursor.lastrowid)

    def update_article_note(
        self,
        *,
        note_id: int,
        note_text: str,
        selected_text: str | None = None,
        anchor_key: str | None = None,
        tags: str | None = None,
    ) -> None:
        self.ensure_storage_ready()
        self.conn.execute(
            """
            UPDATE study_article_notes
            SET note_text = ?,
                selected_text = ?,
                anchor_key = ?,
                tags = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (note_text, selected_text, anchor_key, tags, note_id),
        )

    def list_article_notes(self, article_id: int) -> list[RowDict]:
        self.ensure_storage_ready()
        rows = self.conn.execute(
            """
            SELECT *
            FROM study_article_notes
            WHERE article_id = ? AND archived_at IS NULL
            ORDER BY updated_at DESC, id DESC
            """,
            (article_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def archive_article_note(self, note_id: int) -> None:
        self.ensure_storage_ready()
        self.conn.execute(
            """
            UPDATE study_article_notes
            SET archived_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (note_id,),
        )

    def create_highlight(
        self,
        *,
        article_id: int,
        selected_text: str,
        color: str = "yellow",
        anchor_key: str | None = None,
        start_offset: int | None = None,
        end_offset: int | None = None,
        note_text: str | None = None,
    ) -> int:
        self.ensure_storage_ready()
        snapshot = self.get_article_snapshot(article_id)
        law_id_snapshot = snapshot["law_id"] if snapshot else None
        article_ref_snapshot = snapshot["article_ref"] if snapshot else None
        cursor = self.conn.execute(
            """
            INSERT INTO study_highlights(
                article_id, law_id_snapshot, article_ref_snapshot, anchor_key,
                selected_text, start_offset, end_offset, color, note_text
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                article_id,
                law_id_snapshot,
                article_ref_snapshot,
                anchor_key,
                selected_text,
                start_offset,
                end_offset,
                color,
                note_text,
            ),
        )
        return int(cursor.lastrowid)

    def update_highlight(
        self,
        *,
        highlight_id: int,
        selected_text: str,
        color: str = "yellow",
        anchor_key: str | None = None,
        start_offset: int | None = None,
        end_offset: int | None = None,
        note_text: str | None = None,
    ) -> None:
        self.ensure_storage_ready()
        self.conn.execute(
            """
            UPDATE study_highlights
            SET selected_text = ?,
                color = ?,
                anchor_key = ?,
                start_offset = ?,
                end_offset = ?,
                note_text = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                selected_text,
                color,
                anchor_key,
                start_offset,
                end_offset,
                note_text,
                highlight_id,
            ),
        )

    def list_highlights(self, article_id: int) -> list[RowDict]:
        self.ensure_storage_ready()
        rows = self.conn.execute(
            """
            SELECT *
            FROM study_highlights
            WHERE article_id = ? AND archived_at IS NULL
            ORDER BY updated_at DESC, id DESC
            """,
            (article_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def archive_highlight(self, highlight_id: int) -> None:
        self.ensure_storage_ready()
        self.conn.execute(
            """
            UPDATE study_highlights
            SET archived_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (highlight_id,),
        )

    def upsert_progress(
        self,
        *,
        topic_id: int | None = None,
        article_id: int | None = None,
        status: str,
        completion_percent: int,
        minutes_delta: int = 0,
        pomodoro_delta: int = 0,
    ) -> int:
        self.ensure_storage_ready()
        existing = self._find_progress(topic_id=topic_id, article_id=article_id)
        if existing:
            progress_id = int(existing["id"])
            self.conn.execute(
                """
                UPDATE study_progress
                SET status = ?,
                    completion_percent = ?,
                    total_minutes = total_minutes + ?,
                    pomodoro_count = pomodoro_count + ?,
                    last_activity_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, completion_percent, minutes_delta, pomodoro_delta, progress_id),
            )
            return progress_id

        cursor = self.conn.execute(
            """
            INSERT INTO study_progress(
                topic_id, article_id, status, completion_percent,
                total_minutes, pomodoro_count, last_activity_at
            )
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (topic_id, article_id, status, completion_percent, minutes_delta, pomodoro_delta),
        )
        return int(cursor.lastrowid)

    def _find_progress(self, *, topic_id: int | None, article_id: int | None) -> RowDict | None:
        if article_id is not None:
            row = self.conn.execute(
                "SELECT * FROM study_progress WHERE article_id = ?",
                (article_id,),
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT * FROM study_progress WHERE topic_id = ? AND article_id IS NULL",
                (topic_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_progress(self, *, topic_id: int | None = None, article_id: int | None = None) -> RowDict | None:
        self.ensure_storage_ready()
        return self._find_progress(topic_id=topic_id, article_id=article_id)

    def upsert_mark(
        self,
        *,
        mark_type: str,
        topic_id: int | None = None,
        article_id: int | None = None,
        note_text: str | None = None,
        resolved: bool = False,
    ) -> int:
        self.ensure_storage_ready()
        existing = self._find_mark(topic_id=topic_id, article_id=article_id, mark_type=mark_type)
        resolved_int = 1 if resolved else 0
        if existing:
            mark_id = int(existing["id"])
            self.conn.execute(
                """
                UPDATE study_marks
                SET note_text = ?,
                    resolved = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (note_text, resolved_int, mark_id),
            )
            return mark_id
        cursor = self.conn.execute(
            """
            INSERT INTO study_marks(topic_id, article_id, mark_type, note_text, resolved)
            VALUES (?, ?, ?, ?, ?)
            """,
            (topic_id, article_id, mark_type, note_text, resolved_int),
        )
        return int(cursor.lastrowid)

    def _find_mark(
        self,
        *,
        topic_id: int | None,
        article_id: int | None,
        mark_type: str,
    ) -> RowDict | None:
        if article_id is not None:
            row = self.conn.execute(
                "SELECT * FROM study_marks WHERE article_id = ? AND mark_type = ?",
                (article_id, mark_type),
            ).fetchone()
        else:
            row = self.conn.execute(
                """
                SELECT *
                FROM study_marks
                WHERE topic_id = ? AND article_id IS NULL AND mark_type = ?
                """,
                (topic_id, mark_type),
            ).fetchone()
        return dict(row) if row else None

    def list_marks(
        self,
        *,
        topic_id: int | None = None,
        article_id: int | None = None,
        unresolved_only: bool = False,
    ) -> list[RowDict]:
        self.ensure_storage_ready()
        clauses = []
        params: list[Any] = []
        if topic_id is not None:
            clauses.append("topic_id = ?")
            params.append(topic_id)
        if article_id is not None:
            clauses.append("article_id = ?")
            params.append(article_id)
        if unresolved_only:
            clauses.append("resolved = 0")
        where = " AND ".join(clauses) if clauses else "1 = 1"
        rows = self.conn.execute(
            f"""
            SELECT *
            FROM study_marks
            WHERE {where}
            ORDER BY updated_at DESC, id DESC
            """,
            tuple(params),
        ).fetchall()
        return [dict(row) for row in rows]

    def record_last_review(
        self,
        *,
        topic_id: int | None = None,
        article_id: int | None = None,
        result: str,
        confidence: int | None = None,
        next_review_at: str | None = None,
        notes: str | None = None,
    ) -> int:
        self.ensure_storage_ready()
        existing = self._find_last_review(topic_id=topic_id, article_id=article_id)
        if existing:
            review_id = int(existing["id"])
            self.conn.execute(
                """
                UPDATE study_last_reviews
                SET last_reviewed_at = CURRENT_TIMESTAMP,
                    last_result = ?,
                    confidence = ?,
                    next_review_at = ?,
                    review_count = review_count + 1,
                    notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (result, confidence, next_review_at, notes, review_id),
            )
            return review_id
        cursor = self.conn.execute(
            """
            INSERT INTO study_last_reviews(
                topic_id, article_id, last_result, confidence, next_review_at, notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (topic_id, article_id, result, confidence, next_review_at, notes),
        )
        return int(cursor.lastrowid)

    def _find_last_review(self, *, topic_id: int | None, article_id: int | None) -> RowDict | None:
        if article_id is not None:
            row = self.conn.execute(
                "SELECT * FROM study_last_reviews WHERE article_id = ?",
                (article_id,),
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT * FROM study_last_reviews WHERE topic_id = ? AND article_id IS NULL",
                (topic_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_last_review(
        self,
        *,
        topic_id: int | None = None,
        article_id: int | None = None,
    ) -> RowDict | None:
        self.ensure_storage_ready()
        return self._find_last_review(topic_id=topic_id, article_id=article_id)

    def counts(self) -> RowDict:
        self.ensure_storage_ready()
        table_names = STUDY_TABLES
        return {
            table: int(self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in table_names
        }

    def get_article_study_state(self, article_id: int) -> RowDict:
        self.ensure_storage_ready()
        return {
            "article_id": article_id,
            "notes": self.list_article_notes(article_id),
            "highlights": self.list_highlights(article_id),
            "marks": self.list_marks(article_id=article_id),
            "progress": self.get_progress(article_id=article_id),
            "last_review": self.get_last_review(article_id=article_id),
        }

    def get_topic_summary(self, topic_id: int) -> RowDict:
        self.ensure_storage_ready()
        article_ids = self._article_ids_for_topic(topic_id)
        topic_progress = self.get_progress(topic_id=topic_id)
        topic_marks = self.list_marks(topic_id=topic_id)
        topic_review = self.get_last_review(topic_id=topic_id)
        return {
            "topic_id": topic_id,
            "article_count": len(article_ids),
            "notes": self._count_for_articles("study_article_notes", article_ids, active_only=True),
            "highlights": self._count_for_articles("study_highlights", article_ids, active_only=True),
            "doubt_marks": self._count_marks_for_articles(article_ids, "doubt"),
            "important_marks": self._count_marks_for_articles(article_ids, "important"),
            "progress_average": self._progress_average_for_articles(article_ids),
            "topic_progress": topic_progress,
            "topic_marks": topic_marks,
            "topic_last_review": topic_review,
            "latest_review": self._latest_review_for_articles(article_ids, topic_id=topic_id),
        }

    def get_law_summary(self, law_id: int) -> RowDict:
        self.ensure_storage_ready()
        article_ids = self._article_ids_for_law(law_id)
        return {
            "law_id": law_id,
            "article_count": len(article_ids),
            "notes": self._count_for_articles("study_article_notes", article_ids, active_only=True),
            "highlights": self._count_for_articles("study_highlights", article_ids, active_only=True),
            "doubt_marks": self._count_marks_for_articles(article_ids, "doubt"),
            "important_marks": self._count_marks_for_articles(article_ids, "important"),
            "progress_average": self._progress_average_for_articles(article_ids),
            "latest_review": self._latest_review_for_articles(article_ids),
        }

    def _article_ids_for_topic(self, topic_id: int) -> list[int]:
        if not self._table_exists("topic_sources"):
            return []
        rows = self.conn.execute(
            """
            SELECT DISTINCT article_id
            FROM topic_sources
            WHERE topic_id = ? AND article_id IS NOT NULL
            ORDER BY article_id
            """,
            (topic_id,),
        ).fetchall()
        return [int(row["article_id"]) for row in rows]

    def _article_ids_for_law(self, law_id: int) -> list[int]:
        rows = self.conn.execute(
            "SELECT id FROM articles WHERE law_id = ? ORDER BY id",
            (law_id,),
        ).fetchall()
        return [int(row["id"]) for row in rows]

    def _count_for_articles(self, table: str, article_ids: list[int], *, active_only: bool = False) -> int:
        if not article_ids:
            return 0
        placeholders = ",".join("?" for _ in article_ids)
        archived_filter = " AND archived_at IS NULL" if active_only else ""
        return int(
            self.conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE article_id IN ({placeholders}){archived_filter}",
                tuple(article_ids),
            ).fetchone()[0]
        )

    def _count_marks_for_articles(self, article_ids: list[int], mark_type: str) -> int:
        if not article_ids:
            return 0
        placeholders = ",".join("?" for _ in article_ids)
        return int(
            self.conn.execute(
                f"""
                SELECT COUNT(*)
                FROM study_marks
                WHERE article_id IN ({placeholders})
                  AND mark_type = ?
                  AND resolved = 0
                """,
                (*article_ids, mark_type),
            ).fetchone()[0]
        )

    def _progress_average_for_articles(self, article_ids: list[int]) -> float | None:
        if not article_ids:
            return None
        placeholders = ",".join("?" for _ in article_ids)
        row = self.conn.execute(
            f"""
            SELECT AVG(completion_percent) AS average
            FROM study_progress
            WHERE article_id IN ({placeholders})
            """,
            tuple(article_ids),
        ).fetchone()
        return round(float(row["average"]), 2) if row and row["average"] is not None else None

    def _latest_review_for_articles(self, article_ids: list[int], topic_id: int | None = None) -> RowDict | None:
        clauses = []
        params: list[Any] = []
        if article_ids:
            placeholders = ",".join("?" for _ in article_ids)
            clauses.append(f"article_id IN ({placeholders})")
            params.extend(article_ids)
        if topic_id is not None:
            clauses.append("(topic_id = ? AND article_id IS NULL)")
            params.append(topic_id)
        if not clauses:
            return None
        row = self.conn.execute(
            f"""
            SELECT *
            FROM study_last_reviews
            WHERE {' OR '.join(clauses)}
            ORDER BY last_reviewed_at DESC, id DESC
            LIMIT 1
            """,
            tuple(params),
        ).fetchone()
        return dict(row) if row else None

    def _table_exists(self, table: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        ).fetchone()
        return row is not None

from __future__ import annotations

import sqlite3
from typing import Any
from datetime import datetime

from src.simulacros.schema import missing_simulacros_tables

RowDict = dict[str, Any]


class SimulacrospError(RuntimeError):
    """Base error for simulacros storage issues."""


class SimulacroseemaMissingError(SimulacrospError):
    """Raised when simulacros tables have not been migrated yet."""


class SimulacrpsRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def ensure_storage_ready(self) -> None:
        missing = missing_simulacros_tables(self.conn)
        if missing:
            raise SimulacroseemaMissingError(
                "Simulacros tables are not migrated: " + ", ".join(missing)
            )

    def create_mock_exam(
        self,
        *,
        title: str,
        num_questions: int,
        time_limit_minutes: int | None = None,
        config: str | None = None,
        topic_id: int | None = None,
        source_kind: str = "mixto",
        user_id: int = 1,
    ) -> int:
        """Create a new mock exam."""
        self.ensure_storage_ready()
        cursor = self.conn.execute(
            """
            INSERT INTO mock_exams(
                user_id, topic_id, title, num_questions, time_limit_minutes,
                config, source_kind
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                topic_id,
                title,
                num_questions,
                time_limit_minutes,
                config,
                source_kind,
            ),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def finish_mock_exam(
        self,
        exam_id: int,
        score_percent: float,
        passed: bool = True,
    ) -> None:
        """Mark a mock exam as finished."""
        self.conn.execute(
            """
            UPDATE mock_exams
            SET finished_at = CURRENT_TIMESTAMP, score_percent = ?, passed = ?
            WHERE id = ?
            """,
            (score_percent, 1 if passed else 0, exam_id),
        )
        self.conn.commit()

    def record_answer(
        self,
        *,
        exam_id: int,
        question_number: int,
        source_kind: str,
        question_ref: str,
        user_answer: str,
        correct_answer: str,
        is_correct: bool,
        tiempo_segundos: float | None = None,
        explanation: str | None = None,
    ) -> int:
        """Record an answer in a mock exam."""
        cursor = self.conn.execute(
            """
            INSERT INTO mock_exam_answers(
                mock_exam_id, question_number, source_kind, question_ref,
                user_answer, correct_answer, is_correct, tiempo_segundos,
                explanation
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                exam_id,
                question_number,
                source_kind,
                question_ref,
                user_answer,
                correct_answer,
                1 if is_correct else 0,
                tiempo_segundos,
                explanation,
            ),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def get_mock_exam(self, exam_id: int) -> RowDict | None:
        """Get mock exam details."""
        row = self.conn.execute(
            "SELECT * FROM mock_exams WHERE id = ?",
            (exam_id,),
        ).fetchone()
        return dict(row) if row else None

    def get_mock_exam_answers(self, exam_id: int) -> list[RowDict]:
        """Get all answers for a mock exam."""
        rows = self.conn.execute(
            """
            SELECT * FROM mock_exam_answers
            WHERE mock_exam_id = ?
            ORDER BY question_number
            """,
            (exam_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_user_mock_exams(
        self,
        user_id: int = 1,
        limit: int = 10,
    ) -> list[RowDict]:
        """Get recent mock exams for a user."""
        rows = self.conn.execute(
            """
            SELECT * FROM mock_exams
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    def compute_exam_stats(self, exam_id: int) -> dict[str, Any]:
        """Compute statistics for a completed exam."""
        exam = self.get_mock_exam(exam_id)
        if not exam:
            return {}

        answers = self.get_mock_exam_answers(exam_id)
        if not answers:
            return {"exam_id": exam_id, "total_questions": 0}

        correct_count = sum(1 for a in answers if a["is_correct"])
        total = len(answers)
        percent = (correct_count / total * 100) if total > 0 else 0

        time_total = sum(a["tiempo_segundos"] or 0 for a in answers)
        time_avg = time_total / total if total > 0 else 0

        return {
            "exam_id": exam_id,
            "total_questions": total,
            "correct_count": correct_count,
            "incorrect_count": total - correct_count,
            "score_percent": percent,
            "passed": percent >= 60,
            "time_total_seconds": time_total,
            "time_avg_seconds": time_avg,
            "started_at": exam["started_at"],
            "finished_at": exam["finished_at"],
        }

"""
Calculador SRS: SM-2 algorithm (Spaced Repetition System).

Implementación del algoritmo SM-2 de SuperMemo.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import sqlite3
from typing import Any


class SM2Calculator:
    """Calcular progresión SRS según SM-2."""

    # SM-2 constants
    MIN_EASE = 1.3
    INITIAL_EASE = 2.5

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def record_review(
        self,
        scope_type: str,
        scope_id: int,
        performance: str,
        current_date: str | None = None
    ) -> None:
        """
        Registrar una revisión y actualizar el estado SRS.

        Basado en SM-2 (performance: again|hard|good|easy):
        - again (0): reset al estado 'learning'
        - hard (1): aumentar interval poco
        - good (2): secuencia normal
        - easy (3): aumentar interval mucho
        """
        if current_date is None:
            current_date = datetime.now().date().isoformat()

        # Obtener estado actual
        row = self.conn.execute(
            """
            SELECT id, ease, interval_days, reps, lapses, state
            FROM srs_state
            WHERE scope_type = ? AND scope_id = ?
            """,
            (scope_type, scope_id)
        ).fetchone()

        if not row:
            # Crear nuevo si no existe
            self.conn.execute(
                """
                INSERT INTO srs_state(scope_type, scope_id, ease, interval_days, due_at, state)
                VALUES (?, ?, ?, ?, ?, 'learning')
                """,
                (scope_type, scope_id, self.INITIAL_EASE, 1.0, current_date)
            )
            row = self.conn.execute(
                """
                SELECT id, ease, interval_days, reps, lapses, state
                FROM srs_state
                WHERE scope_type = ? AND scope_id = ?
                """,
                (scope_type, scope_id)
            ).fetchone()

        srs_id, ease, interval_days, reps, lapses, state = row
        performance_values = {"again": 0, "hard": 1, "good": 2, "easy": 3}
        quality = performance_values.get(performance, 0)

        # SM-2 algorithm
        if quality < 3:  # again, hard
            lapses += 1
            reps = 0
            if quality == 0:  # again
                new_interval = 1.0
                new_state = "learning"
            else:  # hard
                new_interval = max(1.0, interval_days * 1.2)
                new_state = "review"
        else:  # good, easy
            reps += 1
            if quality == 2:  # good
                if reps == 1:
                    new_interval = 1.0
                    new_state = "learning"
                elif reps == 2:
                    new_interval = 3.0
                    new_state = "review"
                else:
                    new_interval = interval_days * ease
                    new_state = "review"
            else:  # easy (3)
                if reps == 1:
                    new_interval = 4.0
                else:
                    new_interval = interval_days * ease
                new_state = "review"

        # Actualizar ease (formula SM-2)
        new_ease = max(
            self.MIN_EASE,
            ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        )

        # Calcular next due date
        due_at = (
            datetime.fromisoformat(current_date) + timedelta(days=new_interval)
        ).date().isoformat()

        # Actualizar en BD
        self.conn.execute(
            """
            UPDATE srs_state
            SET ease = ?, interval_days = ?, due_at = ?,
                reps = ?, lapses = ?, state = ?, updated_at = CURRENT_TIMESTAMP
            WHERE scope_type = ? AND scope_id = ?
            """,
            (
                round(new_ease, 2), round(new_interval, 1), due_at,
                reps, lapses, new_state, scope_type, scope_id
            )
        )

        # Registrar también en study_last_reviews para compatibilidad
        self.conn.execute(
            """
            INSERT OR REPLACE INTO study_last_reviews(
                article_id, last_reviewed_at, last_result, confidence,
                next_review_at, review_count
            ) SELECT ?, CURRENT_TIMESTAMP, ?, ?, ?, ?
            FROM articles WHERE id = ?
            """,
            (scope_id, performance, 5 - quality, due_at, reps + 1, scope_id)
            if scope_type == "article" else (None, None, None, None, None, None)
        )

    def get_due_items(self, current_date: str | None = None) -> list[dict[str, Any]]:
        """Obtener items vencidos para hoy."""
        if current_date is None:
            current_date = datetime.now().date().isoformat()

        rows = self.conn.execute(
            """
            SELECT id, scope_type, scope_id, due_at, state, reps, lapses, ease, interval_days
            FROM srs_state
            WHERE due_at <= ?
            ORDER BY due_at ASC, reps DESC
            """,
            (current_date,)
        ).fetchall()
        return [dict(row) for row in rows]

    def get_learning_items(self) -> int:
        """Contar items en estado 'learning'."""
        return int(
            self.conn.execute(
                "SELECT COUNT(*) FROM srs_state WHERE state = 'learning'"
            ).fetchone()[0]
        )

    def get_review_items(self) -> int:
        """Contar items en estado 'review'."""
        return int(
            self.conn.execute(
                "SELECT COUNT(*) FROM srs_state WHERE state = 'review'"
            ).fetchone()[0]
        )

    def get_stats(self) -> dict[str, Any]:
        """Estadísticas globales de SRS."""
        return {
            "new": int(self.conn.execute(
                "SELECT COUNT(*) FROM srs_state WHERE state = 'new'"
            ).fetchone()[0]),
            "learning": self.get_learning_items(),
            "review": self.get_review_items(),
            "relearning": int(self.conn.execute(
                "SELECT COUNT(*) FROM srs_state WHERE state = 'relearning'"
            ).fetchone()[0]),
            "due_today": len(self.get_due_items()),
        }

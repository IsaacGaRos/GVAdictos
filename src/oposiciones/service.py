"""Multi-oposición service for F7 implementation."""

from __future__ import annotations

import sqlite3
from typing import Any


class OposicionService:
    """Service for managing multiple oposiciones."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create_oposicion(
        self,
        code: str,
        nombre: str,
        administracion: str = "GVA",
    ) -> int:
        """Create a new oposición."""
        cursor = self.conn.execute(
            """
            INSERT INTO oposiciones(code, nombre, administracion, activa)
            VALUES (?, ?, ?, 1)
            """,
            (code, nombre, administracion),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def list_oposiciones(self, activa_only: bool = True) -> list[dict[str, Any]]:
        """List available oposiciones."""
        query = "SELECT * FROM oposiciones"
        params = []

        if activa_only:
            query += " WHERE activa = 1"

        query += " ORDER BY administracion, code"

        rows = self.conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def enroll_user(self, user_id: int, oposicion_id: int) -> bool:
        """Enroll user in an oposición."""
        try:
            self.conn.execute(
                """
                INSERT INTO user_oposicion_enrollment(user_id, oposicion_id)
                VALUES (?, ?)
                """,
                (user_id, oposicion_id),
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Already enrolled

    def get_user_oposiciones(self, user_id: int) -> list[dict[str, Any]]:
        """Get oposiciones enrolled by user."""
        rows = self.conn.execute(
            """
            SELECT o.* FROM oposiciones o
            JOIN user_oposicion_enrollment uoe ON o.id = uoe.oposicion_id
            WHERE uoe.user_id = ?
            ORDER BY o.administracion, o.code
            """,
            (user_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_oposicion_topics(self, oposicion_id: int) -> list[dict[str, Any]]:
        """Get topics for an oposición."""
        rows = self.conn.execute(
            """
            SELECT t.* FROM topics t
            WHERE t.oposicion_id = ?
            ORDER BY t.topic_number
            """,
            (oposicion_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_user_progress(
        self,
        user_id: int,
        oposicion_id: int,
    ) -> dict[str, Any]:
        """Get user progress for an oposición."""
        stats = self.conn.execute(
            """
            SELECT
                COUNT(DISTINCT article_id) as articles_reviewed,
                AVG(confidence) as avg_confidence,
                COUNT(DISTINCT sr.id) as reviews_completed
            FROM study_last_reviews sr
            WHERE sr.user_id = ? AND sr.oposicion_id = ?
            """,
            (user_id, oposicion_id),
        ).fetchone()

        return {
            "user_id": user_id,
            "oposicion_id": oposicion_id,
            "articles_reviewed": stats["articles_reviewed"] or 0,
            "avg_confidence": stats["avg_confidence"] or 0.0,
            "reviews_completed": stats["reviews_completed"] or 0,
        }

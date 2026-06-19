"""Legislative change monitor service.

Detects and reports changes to monitored sources.
MVP: Check stored versions against new content.
"""

from __future__ import annotations

import sqlite3
from typing import Any
from datetime import datetime

from src.versioning.service import VersioningService


class MonitorError(RuntimeError):
    """Base error for monitor issues."""


class LegislativeMonitor:
    """Service for monitoring legislative changes."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.versioning = VersioningService(conn)

    def check_for_changes(self) -> dict[str, Any]:
        """Check monitored laws for changes.

        MVP: Simple check against last known content_hash.
        """
        laws = self.conn.execute(
            """
            SELECT DISTINCT l.id, l.name FROM laws l
            ORDER BY l.id
            """
        ).fetchall()

        changes_detected = []
        total_checked = 0

        for law in laws:
            law_id = law["id"]
            total_checked += 1

            # Get current articles for this law
            articles = self.conn.execute(
                """
                SELECT COUNT(*) as count FROM articles WHERE law_id = ?
                """,
                (law_id,),
            ).fetchone()

            article_count = articles["count"]

            # Get last version
            last_version = self.conn.execute(
                """
                SELECT id, imported_at FROM law_versions
                WHERE law_id = ?
                ORDER BY imported_at DESC
                LIMIT 1
                """,
                (law_id,),
            ).fetchone()

            # Simple MVP: detect if law has been updated (by tracking article count)
            if last_version:
                last_article_count = self.conn.execute(
                    """
                    SELECT COUNT(DISTINCT anchor_key) as count
                    FROM article_versions
                    WHERE law_version_id = ?
                    """,
                    (last_version["id"],),
                ).fetchone()["count"]

                if article_count != last_article_count:
                    changes_detected.append({
                        "law_id": law_id,
                        "law_name": law["name"],
                        "change_type": "article_count_mismatch",
                        "old_count": last_article_count,
                        "new_count": article_count,
                        "last_check": last_version["imported_at"],
                    })

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_laws_checked": total_checked,
            "changes_detected": len(changes_detected),
            "details": changes_detected,
        }

    def get_affected_topics(self, law_id: int) -> list[dict[str, Any]]:
        """Get topics affected by changes to a law."""
        topics = self.conn.execute(
            """
            SELECT DISTINCT t.id, t.topic_number, t.official_text
            FROM topics t
            JOIN topic_sources ts ON t.id = ts.topic_id
            JOIN articles a ON ts.article_id = a.id
            WHERE a.law_id = ?
            """,
            (law_id,),
        ).fetchall()

        return [dict(t) for t in topics]

    def generate_change_report(self, law_id: int) -> str:
        """Generate a human-readable report of changes to a law."""
        law = self.conn.execute(
            "SELECT name FROM laws WHERE id = ?",
            (law_id,),
        ).fetchone()

        if not law:
            return f"Law {law_id} not found"

        affected_topics = self.get_affected_topics(law_id)

        report = f"""
INFORME DE CAMBIOS LEGISLATIVOS
================================

Norma: {law['name']}
Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

RESUMEN
-------
Número de temas afectados: {len(affected_topics)}

TEMAS AFECTADOS
---------------
"""
        for topic in affected_topics[:20]:  # Limit to 20
            report += f"\n- Tema {topic['topic_number']}: {topic['official_text']}"

        if len(affected_topics) > 20:
            report += f"\n... y {len(affected_topics) - 20} temas más"

        report += """

RECOMENDACIONES
---------------
1. Revisar los temas afectados
2. Actualizar el material de estudio si es necesario
3. Consultar las bases oficiales de la convocatoria

ACCIÓN REQUERIDA
----------------
Revisar los cambios y decidir si requiere actualización del material.
"""
        return report

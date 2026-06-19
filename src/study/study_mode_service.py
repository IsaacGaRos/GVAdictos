"""
Servicio de modos de estudio (Ola A4).

Orquesta lectura por ley, por tema, y filtros.
Integra: artículos, divisiones, temas, métricas, progreso, SRS.
"""

from __future__ import annotations

import sqlite3
from typing import Any


class StudyModeService:
    """Orquestar modos de estudio: por ley, por tema, "solo importante"."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_law_study_structure(self, law_id: int) -> dict[str, Any]:
        """
        Obtener estructura completa de una ley para estudio.

        Incluye: divisiones, artículos, temas relacionados, progreso, métricas.
        """
        # Ley
        law_row = self.conn.execute(
            "SELECT id, name FROM laws WHERE id = ?",
            (law_id,)
        ).fetchone()
        if not law_row:
            raise ValueError(f"law_id {law_id} no existe")

        # Divisiones (árbol)
        divisions = self._get_law_divisions_tree(law_id)

        # Artículos sin división (si existen)
        unstructured_articles = self._get_law_articles_by_division(law_id, division_id=None)

        # Progreso en la ley
        progress = self.conn.execute(
            """
            SELECT SUM(completion_percent) / COUNT(*) as avg_completion
            FROM study_progress
            WHERE article_id IN (SELECT id FROM articles WHERE law_id = ?)
            """,
            (law_id,)
        ).fetchone()
        avg_completion = progress["avg_completion"] if progress["avg_completion"] else 0

        return {
            "law_id": law_id,
            "law_name": law_row["name"],
            "divisions": divisions,
            "unstructured_articles": unstructured_articles,
            "avg_completion": round(avg_completion, 1),
            "article_count": self._count_articles_in_law(law_id),
        }

    def _get_law_divisions_tree(self, law_id: int, parent_id: int | None = None) -> list[dict[str, Any]]:
        """Obtener árbol de divisiones para una ley."""
        divisions = self.conn.execute(
            """
            SELECT id, division_type, number, label, order_index, full_path
            FROM law_divisions
            WHERE law_id = ? AND parent_id IS ?
            ORDER BY order_index
            """,
            (law_id, parent_id)
        ).fetchall()

        result = []
        for div in divisions:
            # Artículos en esta división
            articles = self._get_law_articles_by_division(law_id, div["id"])

            # Subdivisiones
            children = self._get_law_divisions_tree(law_id, div["id"])

            result.append({
                "id": div["id"],
                "division_type": div["division_type"],
                "number": div["number"],
                "label": div["label"],
                "full_path": div["full_path"],
                "articles": articles,
                "children": children,
            })

        return result

    def _get_law_articles_by_division(
        self,
        law_id: int,
        division_id: int | None
    ) -> list[dict[str, Any]]:
        """Obtener artículos en una división específica."""
        if division_id is None:
            # Artículos sin división asignada
            articles = self.conn.execute(
                """
                SELECT a.id, a.article_ref, a.title, a.law_id,
                       COALESCE(sp.completion_percent, 0) as completion,
                       COALESCE(am.importance_score, 0) as importance,
                       COALESCE(ts.topic_id, 0) as topic_id
                FROM articles a
                LEFT JOIN study_progress sp ON sp.article_id = a.id
                LEFT JOIN article_metrics am ON am.article_id = a.id
                LEFT JOIN topic_sources ts ON ts.article_id = a.id
                WHERE a.law_id = ? AND a.id NOT IN (
                    SELECT article_id FROM article_division
                )
                ORDER BY a.id
                """,
                (law_id,)
            ).fetchall()
        else:
            articles = self.conn.execute(
                """
                SELECT a.id, a.article_ref, a.title, a.law_id,
                       COALESCE(sp.completion_percent, 0) as completion,
                       COALESCE(am.importance_score, 0) as importance,
                       COALESCE(ts.topic_id, 0) as topic_id
                FROM articles a
                INNER JOIN article_division ad ON ad.article_id = a.id
                LEFT JOIN study_progress sp ON sp.article_id = a.id
                LEFT JOIN article_metrics am ON am.article_id = a.id
                LEFT JOIN topic_sources ts ON ts.article_id = a.id
                WHERE a.law_id = ? AND ad.division_id = ?
                ORDER BY a.id
                """,
                (law_id, division_id)
            ).fetchall()

        return [dict(row) for row in articles]

    def _count_articles_in_law(self, law_id: int) -> int:
        """Contar artículos en una ley."""
        return int(
            self.conn.execute(
                "SELECT COUNT(*) FROM articles WHERE law_id = ?",
                (law_id,)
            ).fetchone()[0]
        )

    def get_topic_study_plan(self, topic_id: int) -> dict[str, Any]:
        """
        Obtener plan de estudio por tema (Academia flow).

        Secuencia: artículos → anotaciones → highlights → preguntas → SRS → resumen
        """
        topic_row = self.conn.execute(
            "SELECT id, topic_number, part, official_text FROM topics WHERE id = ?",
            (topic_id,)
        ).fetchone()
        if not topic_row:
            raise ValueError(f"topic_id {topic_id} no existe")

        # Artículos del tema
        articles = self.conn.execute(
            """
            SELECT a.id, a.article_ref, a.title, a.law_id, l.name as law_name,
                   COALESCE(sp.completion_percent, 0) as completion,
                   COALESCE(am.importance_score, 0) as importance,
                   COALESCE(am.exam_count, 0) as exam_count
            FROM topic_sources ts
            INNER JOIN articles a ON a.id = ts.article_id
            INNER JOIN laws l ON l.id = a.law_id
            LEFT JOIN study_progress sp ON sp.article_id = a.id
            LEFT JOIN article_metrics am ON am.article_id = a.id
            WHERE ts.topic_id = ?
            ORDER BY a.id
            """,
            (topic_id,)
        ).fetchall()

        # Resumen de estudio
        study_summary = self.conn.execute(
            """
            SELECT
                COUNT(DISTINCT sa.id) as total_notes,
                COUNT(DISTINCT sh.id) as total_highlights,
                COUNT(DISTINCT sm.id) as total_marks,
                COALESCE(AVG(sp.completion_percent), 0) as avg_completion
            FROM topic_sources ts
            LEFT JOIN articles a ON a.id = ts.article_id
            LEFT JOIN study_article_notes sa ON sa.article_id = a.id
            LEFT JOIN study_highlights sh ON sh.article_id = a.id
            LEFT JOIN study_marks sm ON sm.article_id = a.id
            LEFT JOIN study_progress sp ON sp.article_id = a.id
            WHERE ts.topic_id = ?
            """,
            (topic_id,)
        ).fetchone()

        # Preguntas tipo test vinculadas
        questions_count = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM exam_question_links eql
            INNER JOIN exam_questions eq ON eq.id = eql.exam_question_id
            WHERE eql.topic_id = ?
            """,
            (topic_id,)
        ).fetchone()[0]

        # Progreso SRS
        srs_stats = self.conn.execute(
            """
            SELECT
                COUNT(CASE WHEN state = 'new' THEN 1 END) as new_count,
                COUNT(CASE WHEN state = 'learning' THEN 1 END) as learning_count,
                COUNT(CASE WHEN state = 'review' THEN 1 END) as review_count,
                COUNT(*) as total_srs
            FROM srs_state
            WHERE scope_type = 'article' AND scope_id IN (
                SELECT a.id FROM topic_sources ts
                INNER JOIN articles a ON a.id = ts.article_id
                WHERE ts.topic_id = ?
            )
            """,
            (topic_id,)
        ).fetchone()

        return {
            "topic_id": topic_id,
            "topic_number": topic_row["topic_number"],
            "part": topic_row["part"],
            "official_text": topic_row["official_text"],
            "articles": [dict(row) for row in articles],
            "study_summary": {
                "total_notes": study_summary["total_notes"],
                "total_highlights": study_summary["total_highlights"],
                "total_marks": study_summary["total_marks"],
                "avg_completion": round(study_summary["avg_completion"], 1),
            },
            "questions_linked": questions_count,
            "srs_stats": {
                "new": srs_stats["new_count"],
                "learning": srs_stats["learning_count"],
                "review": srs_stats["review_count"],
                "total": srs_stats["total_srs"],
            },
        }

    def get_important_articles(self, importance_threshold: float = 0.5) -> list[dict[str, Any]]:
        """
        Obtener artículos más importantes (Solo lo importante).

        Filtro por importance_score >= threshold (0.5 por defecto).
        """
        articles = self.conn.execute(
            """
            SELECT a.id, a.article_ref, a.title, l.name as law_name,
                   am.importance_score, am.exam_count, am.difficulty_index,
                   COALESCE(sp.completion_percent, 0) as completion,
                   ts.topic_id
            FROM article_metrics am
            INNER JOIN articles a ON a.id = am.article_id
            INNER JOIN laws l ON l.id = a.law_id
            LEFT JOIN study_progress sp ON sp.article_id = a.id
            LEFT JOIN topic_sources ts ON ts.article_id = a.id
            WHERE am.importance_score >= ?
            ORDER BY am.importance_score DESC
            """,
            (importance_threshold,)
        ).fetchall()

        return [dict(row) for row in articles]

    def get_study_progress_summary(self) -> dict[str, Any]:
        """Resumen general de progreso de estudio."""
        total_progress = self.conn.execute(
            """
            SELECT
                COUNT(*) as total_items,
                SUM(CASE WHEN completion_percent = 100 THEN 1 ELSE 0 END) as completed,
                ROUND(AVG(completion_percent), 1) as avg_completion,
                SUM(total_minutes) as total_minutes,
                SUM(pomodoro_count) as total_pomodoros
            FROM study_progress
            """
        ).fetchone()

        return {
            "total_items": total_progress["total_items"] or 0,
            "completed": total_progress["completed"] or 0,
            "in_progress": (total_progress["total_items"] or 0) - (total_progress["completed"] or 0),
            "avg_completion": total_progress["avg_completion"] or 0,
            "total_minutes": total_progress["total_minutes"] or 0,
            "total_pomodoros": total_progress["total_pomodoros"] or 0,
        }

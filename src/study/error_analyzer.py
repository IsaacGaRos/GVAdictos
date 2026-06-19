"""
Analizador de errores (Ola C4).

Identifica por qué se fallan preguntas y qué repasar.
"""

from __future__ import annotations

import sqlite3
from typing import Any


class ErrorAnalyzerService:
    """Analizar errores y proponer repaso."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row

    def analyze_exam_performance(self, exam_paper_id: int) -> dict[str, Any]:
        """
        Analizar desempeño en un examen.

        Devuelve: respuestas correctas, incorrectas, articulos relacionados.
        """
        exam = self.conn.execute(
            "SELECT id, convocatoria, anio FROM exam_papers WHERE id = ?",
            (exam_paper_id,)
        ).fetchone()

        if not exam:
            raise ValueError(f"exam_paper_id {exam_paper_id} no existe")

        questions = self.conn.execute(
            """
            SELECT eq.id, eq.numero, eq.enunciado, eq.respuesta_oficial, eq.anulada,
                   COUNT(DISTINCT eql.article_id) as linked_articles
            FROM exam_questions eq
            LEFT JOIN exam_question_links eql ON eql.exam_question_id = eq.id
            WHERE eq.exam_paper_id = ?
            GROUP BY eq.id
            """,
            (exam_paper_id,)
        ).fetchall()

        total = len(questions)
        linked = sum(1 for q in questions if q["linked_articles"] > 0)
        unlinked = total - linked
        anuladas = sum(1 for q in questions if q["anulada"])

        return {
            "exam_id": exam["id"],
            "convocatoria": exam["convocatoria"],
            "anio": exam["anio"],
            "total_questions": total,
            "linked_questions": linked,
            "unlinked_questions": unlinked,
            "anuladas": anuladas,
            "coverage_percent": round(100 * linked / (total - anuladas), 1) if (total - anuladas) > 0 else 0,
            "questions": [dict(row) for row in questions],
        }

    def get_failed_topics(self, exam_paper_id: int | None = None) -> list[dict[str, Any]]:
        """
        Obtener temas donde se falló más.

        Si exam_paper_id es None, agregar todas las preguntas falladas.
        """
        if exam_paper_id:
            # Preguntas falladas de un examen específico
            # (placeholder: necesitaría tabla mock_exam_answers)
            pass

        # Por ahora: temas con article_metrics.difficulty_index alto
        topics = self.conn.execute(
            """
            SELECT t.id, t.topic_number, t.part,
                   ROUND(AVG(am.difficulty_index), 2) as avg_difficulty,
                   COUNT(DISTINCT ts.article_id) as article_count,
                   COUNT(DISTINCT CASE WHEN am.exam_count > 0 THEN ts.article_id END) as tested_articles
            FROM topics t
            INNER JOIN topic_sources ts ON ts.topic_id = t.id
            LEFT JOIN article_metrics am ON am.article_id = ts.article_id
            GROUP BY t.id, t.topic_number, t.part
            ORDER BY avg_difficulty DESC
            LIMIT 10
            """
        ).fetchall()

        return [dict(row) for row in topics]

    def get_weak_articles(self) -> list[dict[str, Any]]:
        """Obtener artículos débiles (alto error rate o bajo progreso)."""
        articles = self.conn.execute(
            """
            SELECT a.id, a.article_ref, a.title, l.name as law_name,
                   ROUND(am.user_error_rate, 2) as error_rate,
                   am.exam_count,
                   COALESCE(sp.completion_percent, 0) as completion,
                   CASE
                       WHEN am.user_error_rate >= 0.5 THEN 'Critical'
                       WHEN am.user_error_rate >= 0.3 THEN 'High'
                       WHEN am.user_error_rate >= 0.1 THEN 'Medium'
                       ELSE 'Low'
                   END as severity
            FROM article_metrics am
            INNER JOIN articles a ON a.id = am.article_id
            INNER JOIN laws l ON l.id = a.law_id
            LEFT JOIN study_progress sp ON sp.article_id = a.id
            WHERE am.user_error_rate > 0 OR sp.completion_percent < 50
            ORDER BY am.user_error_rate DESC
            LIMIT 20
            """
        ).fetchall()

        return [dict(row) for row in articles]

    def propose_review_plan(self, days: int = 7) -> dict[str, Any]:
        """
        Proponer plan de repaso por errores.

        Enfoca los próximos N días en temas débiles.
        """
        weak_articles = self.get_weak_articles()
        failed_topics = self.get_failed_topics()

        # Crear items de repaso
        review_items = []

        # Artículos débiles primero
        for art in weak_articles[:10]:
            review_items.append({
                "scope_type": "article",
                "scope_id": art["id"],
                "article_ref": art["article_ref"],
                "reason": "error",
                "severity": art["severity"],
                "estimated_minutes": 10 if art["severity"] == "Critical" else 5,
            })

        # Luego temas débiles
        for topic in failed_topics[:5]:
            review_items.append({
                "scope_type": "topic",
                "scope_id": topic["id"],
                "topic_number": topic["topic_number"],
                "reason": "error",
                "estimated_minutes": 15,
            })

        total_minutes = sum(item["estimated_minutes"] for item in review_items)

        return {
            "review_period_days": days,
            "total_items_to_review": len(review_items),
            "estimated_total_minutes": total_minutes,
            "items": review_items,
        }

    def get_common_error_patterns(self) -> dict[str, Any]:
        """Identificar patrones comunes de error."""
        # Placeholder: necesitaría tabla mock_exam_answers con respuestas del usuario
        # Por ahora: artículos con difficulty alto pero exam_count bajo (nunca preguntados)

        overlooked = self.conn.execute(
            """
            SELECT a.id, a.article_ref, a.title,
                   ROUND(am.importance_score, 3) as importance,
                   am.exam_count,
                   am.difficulty_index
            FROM article_metrics am
            INNER JOIN articles a ON a.id = am.article_id
            WHERE am.importance_score >= 0.5 AND am.exam_count = 0
            ORDER BY am.importance_score DESC
            LIMIT 10
            """
        ).fetchall()

        return {
            "pattern": "Overlooked important articles (never asked but high importance)",
            "articles": [dict(row) for row in overlooked],
            "recommendation": "Focus on these articles before exam",
        }

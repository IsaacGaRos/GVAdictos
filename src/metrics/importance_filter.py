"""
Servicio de filtrado "Solo lo importante" (Ola B4).

Filtra artículos por importance_score y genera badges visuales.
"""

from __future__ import annotations

import sqlite3
from typing import Any


class ImportanceFilterService:
    """Filtrar artículos por importancia y generar badges."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_important_articles(
        self,
        threshold: float = 0.5,
        law_id: int | None = None,
        topic_id: int | None = None,
        limit: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Obtener artículos importantes.

        Filtros opcionales:
        - threshold: importance_score >= threshold (defecto 0.5)
        - law_id: solo de una ley específica
        - topic_id: solo de un tema específico
        - limit: máximo número de resultados
        """
        query = """
            SELECT a.id, a.article_ref, a.title, l.id as law_id, l.name as law_name,
                   am.importance_score, am.exam_count, am.last_exam_year,
                   am.difficulty_index, am.user_error_rate,
                   COALESCE(sp.completion_percent, 0) as completion_percent,
                   ts.topic_id
            FROM article_metrics am
            INNER JOIN articles a ON a.id = am.article_id
            INNER JOIN laws l ON l.id = a.law_id
            LEFT JOIN study_progress sp ON sp.article_id = a.id
            LEFT JOIN topic_sources ts ON ts.article_id = a.id
            WHERE am.importance_score >= ?
        """
        params = [threshold]

        if law_id is not None:
            query += " AND a.law_id = ?"
            params.append(law_id)

        if topic_id is not None:
            query += " AND ts.topic_id = ?"
            params.append(topic_id)

        query += " ORDER BY am.importance_score DESC"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        rows = self.conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get_coverage_report(self, threshold: float = 0.5) -> dict[str, Any]:
        """
        Reporte de cobertura: cuántos artículos son "importantes" vs totales.
        """
        total = int(
            self.conn.execute("SELECT COUNT(*) FROM article_metrics").fetchone()[0]
        )
        important = int(
            self.conn.execute(
                "SELECT COUNT(*) FROM article_metrics WHERE importance_score >= ?",
                (threshold,)
            ).fetchone()[0]
        )
        not_important = total - important

        # Por ley
        by_law = self.conn.execute(
            """
            SELECT l.id, l.name,
                   COUNT(*) as total,
                   SUM(CASE WHEN am.importance_score >= ? THEN 1 ELSE 0 END) as important
            FROM article_metrics am
            INNER JOIN articles a ON a.id = am.article_id
            INNER JOIN laws l ON l.id = a.law_id
            GROUP BY l.id, l.name
            ORDER BY important DESC
            """,
            (threshold,)
        ).fetchall()

        # Por tema
        by_topic = self.conn.execute(
            """
            SELECT t.id, t.topic_number, t.part,
                   COUNT(DISTINCT ts.article_id) as total,
                   SUM(CASE WHEN am.importance_score >= ? THEN 1 ELSE 0 END) as important
            FROM topics t
            INNER JOIN topic_sources ts ON ts.topic_id = t.id
            LEFT JOIN article_metrics am ON am.article_id = ts.article_id
            GROUP BY t.id, t.topic_number, t.part
            ORDER BY important DESC
            """,
            (threshold,)
        ).fetchall()

        return {
            "threshold": threshold,
            "total_articles": total,
            "important_articles": important,
            "not_important_articles": not_important,
            "coverage_percent": round(100 * important / total, 1) if total > 0 else 0,
            "by_law": [
                {
                    "law_id": row[0],
                    "law_name": row[1],
                    "total": row[2],
                    "important": row[3],
                    "coverage": round(100 * row[3] / row[2], 1) if row[2] > 0 else 0,
                }
                for row in by_law
            ],
            "by_topic": [
                {
                    "topic_id": row[0],
                    "topic_number": row[1],
                    "part": row[2],
                    "total": row[3],
                    "important": row[4],
                    "coverage": round(100 * row[4] / row[3], 1) if row[3] > 0 else 0,
                }
                for row in by_topic
            ],
        }

    def generate_importance_badge(self, article: dict[str, Any]) -> str:
        """
        Generar HTML badge mostrando importancia de un artículo.

        Badge muestra: importance_score, exam_count, dificultad, año último examen.
        """
        importance = article.get("importance_score", 0)
        exam_count = article.get("exam_count", 0)
        difficulty = article.get("difficulty_index", 0)
        last_year = article.get("last_exam_year")

        # Determinar color según importancia
        if importance >= 0.75:
            color = "#d32f2f"  # Red - muy importante
            label = "Critical"
        elif importance >= 0.5:
            color = "#f57c00"  # Orange - importante
            label = "Important"
        elif importance >= 0.25:
            color = "#fbc02d"  # Yellow - moderado
            label = "Moderate"
        else:
            color = "#388e3c"  # Green - bajo
            label = "Low"

        year_text = f"{last_year}" if last_year else "Never"

        html = f"""
<div class="importance-badge" style="background-color: {color}; display: inline-block;
     padding: 8px 12px; border-radius: 4px; color: white; font-size: 12px; font-weight: bold;
     margin: 4px 2px;">
    <span title="Importance score">{label}</span>
    <span style="margin-left: 8px; font-size: 11px;">
        Score: {importance:.2f} | Exams: {exam_count} | Last: {year_text}
    </span>
</div>
"""
        return html

    def get_ranked_articles(
        self,
        order_by: str = "importance",
        limit: int = 50
    ) -> list[dict[str, Any]]:
        """
        Obtener artículos ordenados por criterio.

        order_by: 'importance', 'exam_count', 'difficulty', 'recency'
        """
        order_clause = {
            "importance": "ORDER BY am.importance_score DESC",
            "exam_count": "ORDER BY am.exam_count DESC, am.importance_score DESC",
            "difficulty": "ORDER BY am.difficulty_index DESC, am.importance_score DESC",
            "recency": "ORDER BY am.last_exam_year DESC NULLS LAST, am.importance_score DESC",
        }.get(order_by, "ORDER BY am.importance_score DESC")

        query = f"""
            SELECT a.id, a.article_ref, a.title, l.name as law_name,
                   am.importance_score, am.exam_count, am.last_exam_year, am.difficulty_index,
                   COALESCE(sp.completion_percent, 0) as completion_percent
            FROM article_metrics am
            INNER JOIN articles a ON a.id = am.article_id
            INNER JOIN laws l ON l.id = a.law_id
            LEFT JOIN study_progress sp ON sp.article_id = a.id
            {order_clause}
            LIMIT ?
        """

        rows = self.conn.execute(query, (limit,)).fetchall()
        return [dict(row) for row in rows]

    def get_importance_distribution(self) -> dict[str, Any]:
        """
        Obtener distribución de importancia en buckets.
        """
        buckets = [
            (0.0, 0.25, "Very Low"),
            (0.25, 0.5, "Low"),
            (0.5, 0.75, "Medium"),
            (0.75, 1.0, "High"),
        ]

        distribution = []
        for min_val, max_val, label in buckets:
            count = int(
                self.conn.execute(
                    """
                    SELECT COUNT(*) FROM article_metrics
                    WHERE importance_score >= ? AND importance_score < ?
                    """,
                    (min_val, max_val)
                ).fetchone()[0]
            )
            distribution.append({
                "label": label,
                "range": f"{min_val:.2f}-{max_val:.2f}",
                "count": count,
            })

        return {
            "buckets": distribution,
            "total": sum(b["count"] for b in distribution),
        }

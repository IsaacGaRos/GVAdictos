"""
Calculador de métricas de importancia.

Materializa métricas desde datos de exámenes, intentos y SRS.
Fórmula versionada y reproducible.
"""

from __future__ import annotations

import sqlite3
import math
from typing import Any


class MetricsCalculator:
    """Calcular métricas de importancia, frecuencia, dificultad."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_active_weights(self) -> dict[str, float]:
        """Obtener pesos activos actuales."""
        row = self.conn.execute(
            """
            SELECT w_exam_count, w_recencia, w_difficulty, w_modification,
                   w_user_error, w_tema_weight, version
            FROM importance_weights
            WHERE active = 1
            ORDER BY created_at DESC
            LIMIT 1
            """
        ).fetchone()

        if not row:
            # Defaults
            return {
                "w_exam_count": 0.25,
                "w_recencia": 0.15,
                "w_difficulty": 0.25,
                "w_modification": 0.10,
                "w_user_error": 0.15,
                "w_tema_weight": 0.10,
                "version": "v1",
            }

        return {
            "w_exam_count": row[0],
            "w_recencia": row[1],
            "w_difficulty": row[2],
            "w_modification": row[3],
            "w_user_error": row[4],
            "w_tema_weight": row[5],
            "version": row[6],
        }

    def calculate_article_importance(
        self,
        article_id: int,
        exam_count: int,
        last_exam_year: int | None,
        difficulty_index: float,
        modification_count: int,
        user_error_rate: float,
        current_year: int = 2025
    ) -> float:
        """
        Calcular score de importancia de un artículo.

        Fórmula:
        importance = w1·norm(exam_count) + w2·recencia(last_exam_year) +
                    w3·difficulty_index + w4·norm(modification_count) +
                    w5·user_error_rate
        """
        weights = self.get_active_weights()

        # 1. Normalizaciones
        # Si exam_count = 0, normalizamos a 0 también
        max_exams = 10  # escala razonable: máx 10 exámenes por artículo
        norm_exam_count = min(exam_count / max_exams, 1.0) if max_exams > 0 else 0

        # 2. Recencia (años desde última aparición)
        years_since = 0
        if last_exam_year:
            years_since = current_year - last_exam_year
            # Decay: más antiguo = menos importante
            recencia = max(0, 1 - (years_since / 10))
        else:
            recencia = 0

        # 3. Dificultad (ya normalizada 0-1)
        difficulty = min(1.0, max(0.0, difficulty_index))

        # 4. Modificaciones legislativas
        # Escala razonable: máx 5 cambios por artículo
        max_mods = 5
        norm_mods = min(modification_count / max_mods, 1.0) if max_mods > 0 else 0

        # 5. Tasa de error de usuario (ya normalizada 0-1)
        user_error = min(1.0, max(0.0, user_error_rate))

        # Combinar
        importance = (
            weights["w_exam_count"] * norm_exam_count +
            weights["w_recencia"] * recencia +
            weights["w_difficulty"] * difficulty +
            weights["w_modification"] * norm_mods +
            weights["w_user_error"] * user_error
        )

        return round(min(1.0, max(0.0, importance)), 4)

    def materialize_article_metrics(self, article_id: int | None = None) -> dict[str, Any]:
        """
        Materializar métricas de artículos.

        Usa datos de exam_question_links y study_last_reviews.
        Si article_id es None, materializa TODOS.
        """
        weights = self.get_active_weights()

        if article_id:
            articles = [(article_id,)]
        else:
            articles = self.conn.execute(
                "SELECT id FROM articles ORDER BY id"
            ).fetchall()

        updated = 0

        for (aid,) in articles:
            # Obtener métricas base de exámenes
            exam_row = self.conn.execute(
                """
                SELECT COUNT(DISTINCT eq.exam_paper_id), MAX(ep.anio)
                FROM exam_question_links eql
                INNER JOIN exam_questions eq ON eq.id = eql.exam_question_id
                INNER JOIN exam_papers ep ON ep.id = eq.exam_paper_id
                WHERE eql.article_id = ?
                """,
                (aid,)
            ).fetchone()
            exam_count = (exam_row[0] or 0) if exam_row else 0
            last_exam_year = exam_row[1] if exam_row else None

            # Placeholders para métricas futuras (E2, C1, etc.)
            difficulty_index = 0.0
            modification_count = 0
            user_error_rate = 0.0

            # Calcular importancia (solo con datos disponibles)
            importance = self.calculate_article_importance(
                aid, exam_count, last_exam_year, difficulty_index,
                modification_count, user_error_rate
            )

            # Insertar o actualizar
            self.conn.execute(
                """
                INSERT OR REPLACE INTO article_metrics(
                    article_id, exam_count, last_exam_year, difficulty_index,
                    modification_count, user_error_rate, importance_score,
                    importance_weights_version, computed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (aid, exam_count, last_exam_year, difficulty_index,
                 modification_count, user_error_rate, importance, weights["version"])
            )
            updated += 1

        return {
            "articles_updated": updated,
            "weights_version": weights["version"],
        }

    def materialize_law_metrics(self) -> dict[str, Any]:
        """Materializar métricas de leyes."""
        weights = self.get_active_weights()

        laws = self.conn.execute("SELECT id FROM laws ORDER BY id").fetchall()
        updated = 0

        for (law_id,) in laws:
            # Articulos en la ley
            article_count = self.conn.execute(
                "SELECT COUNT(*) FROM articles WHERE law_id = ?",
                (law_id,)
            ).fetchone()[0]

            # Veces preguntado
            exam_count = self.conn.execute(
                """
                SELECT COUNT(DISTINCT eq.exam_paper_id)
                FROM exam_question_links eql
                INNER JOIN exam_questions eq ON eq.id = eql.exam_question_id
                WHERE eql.law_id = ?
                """,
                (law_id,)
            ).fetchone()[0] or 0

            # Importancia promedio
            avg_importance = self.conn.execute(
                """
                SELECT AVG(importance_score) FROM article_metrics
                WHERE article_id IN (SELECT id FROM articles WHERE law_id = ?)
                """,
                (law_id,)
            ).fetchone()[0] or 0.0

            last_year = self.conn.execute(
                """
                SELECT MAX(last_exam_year) FROM article_metrics
                WHERE article_id IN (SELECT id FROM articles WHERE law_id = ?)
                """,
                (law_id,)
            ).fetchone()[0]

            self.conn.execute(
                """
                INSERT OR REPLACE INTO law_metrics(
                    law_id, article_count, exam_count, avg_importance_score,
                    importance_weights_version, last_exam_year, computed_at
                ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (law_id, article_count, exam_count, round(avg_importance, 4),
                 weights["version"], last_year)
            )
            updated += 1

        return {"laws_updated": updated, "weights_version": weights["version"]}

    def materialize_topic_metrics(self) -> dict[str, Any]:
        """Materializar métricas de temas."""
        weights = self.get_active_weights()

        topics = self.conn.execute("SELECT id FROM topics ORDER BY id").fetchall()
        updated = 0

        for (topic_id,) in topics:
            # Articulos del tema
            article_count = self.conn.execute(
                "SELECT COUNT(DISTINCT article_id) FROM topic_sources WHERE topic_id = ?",
                (topic_id,)
            ).fetchone()[0] or 0

            # Veces preguntado
            exam_count = self.conn.execute(
                """
                SELECT COUNT(DISTINCT eq.exam_paper_id)
                FROM exam_question_links eql
                INNER JOIN exam_questions eq ON eq.id = eql.exam_question_id
                WHERE eql.topic_id = ?
                """,
                (topic_id,)
            ).fetchone()[0] or 0

            # Importancia promedio
            avg_importance = self.conn.execute(
                """
                SELECT AVG(am.importance_score)
                FROM article_metrics am
                INNER JOIN topic_sources ts ON ts.article_id = am.article_id
                WHERE ts.topic_id = ?
                """,
                (topic_id,)
            ).fetchone()[0] or 0.0

            last_year = self.conn.execute(
                """
                SELECT MAX(am.last_exam_year)
                FROM article_metrics am
                INNER JOIN topic_sources ts ON ts.article_id = am.article_id
                WHERE ts.topic_id = ?
                """,
                (topic_id,)
            ).fetchone()[0]

            self.conn.execute(
                """
                INSERT OR REPLACE INTO topic_metrics(
                    topic_id, article_count, exam_count, avg_importance_score,
                    importance_weights_version, last_exam_year, computed_at
                ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (topic_id, article_count, exam_count, round(avg_importance, 4),
                 weights["version"], last_year)
            )
            updated += 1

        return {"topics_updated": updated, "weights_version": weights["version"]}

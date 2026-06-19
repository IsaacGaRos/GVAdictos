"""
Servicio de dashboard (Ola C3).

Resumen visual: progreso, fuertes/débiles, predicción, evolución.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Any


class DashboardService:
    """Generar métricas para dashboard."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_overall_progress(self) -> dict[str, Any]:
        """Resumen general de progreso."""
        total_items = int(
            self.conn.execute(
                "SELECT COUNT(*) FROM study_progress"
            ).fetchone()[0]
        )

        completed = int(
            self.conn.execute(
                "SELECT COUNT(*) FROM study_progress WHERE completion_percent = 100"
            ).fetchone()[0]
        )

        in_progress = int(
            self.conn.execute(
                "SELECT COUNT(*) FROM study_progress WHERE completion_percent > 0 AND completion_percent < 100"
            ).fetchone()[0]
        )

        total_minutes = int(
            self.conn.execute(
                "SELECT SUM(total_minutes) FROM study_progress"
            ).fetchone()[0] or 0
        )

        total_pomodoros = int(
            self.conn.execute(
                "SELECT SUM(pomodoro_count) FROM study_progress"
            ).fetchone()[0] or 0
        )

        return {
            "total_items": total_items,
            "completed": completed,
            "in_progress": in_progress,
            "not_started": max(0, total_items - completed - in_progress),
            "completion_percent": round(100 * completed / total_items, 1) if total_items > 0 else 0,
            "total_minutes_studied": total_minutes,
            "total_pomodoros": total_pomodoros,
        }

    def get_strengths_and_weaknesses(self, top_n: int = 5) -> dict[str, Any]:
        """Identificar temas fuertes y débiles."""
        strengths = self.conn.execute(
            """
            SELECT t.id, t.topic_number, t.part,
                   ROUND(AVG(am.importance_score), 3) as avg_importance,
                   COUNT(DISTINCT ts.article_id) as article_count,
                   ROUND(AVG(sp.completion_percent), 1) as completion
            FROM topics t
            INNER JOIN topic_sources ts ON ts.topic_id = t.id
            LEFT JOIN article_metrics am ON am.article_id = ts.article_id
            LEFT JOIN study_progress sp ON sp.article_id = ts.article_id
            GROUP BY t.id, t.topic_number, t.part
            ORDER BY completion DESC
            LIMIT ?
            """,
            (top_n,)
        ).fetchall()

        weaknesses = self.conn.execute(
            """
            SELECT t.id, t.topic_number, t.part,
                   ROUND(AVG(am.importance_score), 3) as avg_importance,
                   COUNT(DISTINCT ts.article_id) as article_count,
                   ROUND(AVG(sp.completion_percent), 1) as completion
            FROM topics t
            INNER JOIN topic_sources ts ON ts.topic_id = t.id
            LEFT JOIN article_metrics am ON am.article_id = ts.article_id
            LEFT JOIN study_progress sp ON sp.article_id = ts.article_id
            GROUP BY t.id, t.topic_number, t.part
            ORDER BY completion ASC
            LIMIT ?
            """,
            (top_n,)
        ).fetchall()

        return {
            "strengths": [dict(row) for row in strengths],
            "weaknesses": [dict(row) for row in weaknesses],
        }

    def get_srs_stats(self) -> dict[str, Any]:
        """Estadísticas de SRS."""
        stats = self.conn.execute(
            """
            SELECT
                COUNT(CASE WHEN state = 'new' THEN 1 END) as new_count,
                COUNT(CASE WHEN state = 'learning' THEN 1 END) as learning_count,
                COUNT(CASE WHEN state = 'review' THEN 1 END) as review_count,
                COUNT(CASE WHEN state = 'relearning' THEN 1 END) as relearning_count,
                COUNT(*) as total
            FROM srs_state
            """
        ).fetchone()

        due_today = int(
            self.conn.execute(
                "SELECT COUNT(*) FROM srs_state WHERE due_at <= date('now')"
            ).fetchone()[0]
        )

        return {
            "new": stats["new_count"],
            "learning": stats["learning_count"],
            "review": stats["review_count"],
            "relearning": stats["relearning_count"],
            "total": stats["total"],
            "due_today": due_today,
        }

    def estimate_approval_chance(self) -> dict[str, Any]:
        """
        Estimar probabilidad de aprobado (heurística simple).

        Basado en:
        - Cobertura de temas importantes
        - Progreso general
        - SRS review (memorización)
        """
        progress = self.get_overall_progress()
        srs = self.get_srs_stats()

        # Heurística simple
        completion_score = progress["completion_percent"] / 100  # 0-1
        srs_score = srs["review"] / max(srs["total"], 1)  # 0-1
        combined = (completion_score * 0.6 + srs_score * 0.4) * 100

        if combined >= 80:
            chance = "Very High (80%+)"
            days_to_exam = 14
        elif combined >= 60:
            chance = "High (60-80%)"
            days_to_exam = 21
        elif combined >= 40:
            chance = "Moderate (40-60%)"
            days_to_exam = 30
        elif combined >= 20:
            chance = "Low (20-40%)"
            days_to_exam = 45
        else:
            chance = "Very Low (<20%)"
            days_to_exam = 60

        return {
            "approval_chance": chance,
            "estimated_approval_score": round(combined, 1),
            "days_to_exam_estimate": days_to_exam,
            "components": {
                "completion_score": round(completion_score * 100, 1),
                "srs_review_score": round(srs_score * 100, 1),
            },
        }

    def get_study_streak(self) -> dict[str, Any]:
        """Calcular racha de días de estudio."""
        today = datetime.now().date()

        # Obtener días con actividad
        days_with_activity = []
        for i in range(30):  # Últimos 30 días
            check_date = (today - timedelta(days=i)).isoformat()
            count = int(
                self.conn.execute(
                    """
                    SELECT COUNT(*) FROM study_plan_items spi
                    INNER JOIN study_plan_days spd ON spd.id = spi.plan_day_id
                    WHERE spd.plan_date = ? AND spi.status = 'done'
                    """,
                    (check_date,)
                ).fetchone()[0]
            )
            if count > 0:
                days_with_activity.append(check_date)

        # Calcular racha actual
        current_streak = 0
        for i in range(30):
            check_date = (today - timedelta(days=i)).isoformat()
            count = int(
                self.conn.execute(
                    """
                    SELECT COUNT(*) FROM study_plan_items spi
                    INNER JOIN study_plan_days spd ON spd.id = spi.plan_day_id
                    WHERE spd.plan_date = ? AND spi.status = 'done'
                    """,
                    (check_date,)
                ).fetchone()[0]
            )
            if count > 0:
                current_streak += 1
            else:
                break

        return {
            "current_streak_days": current_streak,
            "total_days_studied": len(days_with_activity),
            "study_days_list": days_with_activity[:10],  # Últimos 10
        }

    def get_dashboard_summary(self) -> dict[str, Any]:
        """Resumen completo para dashboard."""
        return {
            "timestamp": datetime.now().isoformat(),
            "progress": self.get_overall_progress(),
            "srs": self.get_srs_stats(),
            "strengths_weaknesses": self.get_strengths_and_weaknesses(),
            "approval_estimate": self.estimate_approval_chance(),
            "streak": self.get_study_streak(),
        }

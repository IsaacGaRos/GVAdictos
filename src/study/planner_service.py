"""
Servicio de planificación diaria inteligente (Ola C2).

Genera plan diario combinando:
- SRS vencidas (vencimiento_srs)
- Artículos con alto error (error)
- Artículos importante (frecuencia, importancia)
- Olvidos detectados (olvido)
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Any


class DailyPlannerService:
    """Generar plan de estudio diario inteligente."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row

    def generate_daily_plan(
        self,
        plan_date: str | None = None,
        target_minutes: int = 120,
        user_id: int = 1
    ) -> dict[str, Any]:
        """
        Generar plan diario.

        Combina:
        1. SRS vencidas (prioridad alta)
        2. Artículos frecuentes (prioridad media)
        3. Artículos importantes (prioridad media)
        4. Olvidos recientes (prioridad baja)
        """
        if plan_date is None:
            plan_date = datetime.now().date().isoformat()

        # Crear plan_day
        cursor = self.conn.execute(
            """
            INSERT OR REPLACE INTO study_plan_days(
                plan_date, target_minutes, generated_at
            ) VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
            (plan_date, target_minutes)
        )
        plan_day_id = int(cursor.lastrowid)

        items = []

        # 1. SRS vencidas (prioridad ALTA)
        due_items = self.conn.execute(
            """
            SELECT scope_id, 'article' as scope_type
            FROM srs_state
            WHERE due_at <= ? AND state IN ('learning', 'review')
            ORDER BY due_at ASC
            LIMIT 15
            """,
            (plan_date,)
        ).fetchall()

        for item in due_items:
            items.append({
                "scope_type": item["scope_type"],
                "scope_id": item["scope_id"],
                "reason": "vencimiento_srs",
                "estimated_minutes": 5,
            })

        # 2. Artículos frecuentes (top preguntados) (prioridad MEDIA)
        frequent = self.conn.execute(
            """
            SELECT article_id
            FROM article_metrics
            WHERE exam_count > 0
            ORDER BY exam_count DESC
            LIMIT 10
            """
        ).fetchall()

        for item in frequent:
            # No duplicar si ya está en SRS vencidas
            if not any(i["scope_id"] == item[0] for i in items):
                items.append({
                    "scope_type": "article",
                    "scope_id": item[0],
                    "reason": "frecuencia",
                    "estimated_minutes": 5,
                })

        # 3. Artículos importantes (prioridad MEDIA)
        important = self.conn.execute(
            """
            SELECT article_id
            FROM article_metrics
            WHERE importance_score >= 0.5
            ORDER BY importance_score DESC
            LIMIT 10
            """
        ).fetchall()

        for item in important:
            if not any(i["scope_id"] == item[0] for i in items):
                items.append({
                    "scope_type": "article",
                    "scope_id": item[0],
                    "reason": "importancia",
                    "estimated_minutes": 5,
                })

        # Limitar por tiempo disponible
        remaining_minutes = target_minutes
        final_items = []

        for item in items:
            if remaining_minutes >= item["estimated_minutes"]:
                final_items.append(item)
                remaining_minutes -= item["estimated_minutes"]

        # Insertar items en la BD
        for item in final_items:
            self.conn.execute(
                """
                INSERT INTO study_plan_items(
                    plan_day_id, scope_type, scope_id, reason, estimated_minutes, status
                ) VALUES (?, ?, ?, ?, ?, 'pending')
                """,
                (plan_day_id, item["scope_type"], item["scope_id"],
                 item["reason"], item["estimated_minutes"])
            )

        return {
            "plan_day_id": plan_day_id,
            "plan_date": plan_date,
            "target_minutes": target_minutes,
            "planned_items": len(final_items),
            "estimated_total_minutes": sum(i["estimated_minutes"] for i in final_items),
            "items": final_items,
        }

    def get_daily_plan(self, plan_date: str | None = None) -> dict[str, Any] | None:
        """Obtener plan del día (si existe)."""
        if plan_date is None:
            plan_date = datetime.now().date().isoformat()

        plan = self.conn.execute(
            """
            SELECT id, plan_date, target_minutes, estimated_total_minutes,
                   completed, generated_at
            FROM study_plan_days
            WHERE plan_date = ?
            """,
            (plan_date,)
        ).fetchone()

        if not plan:
            return None

        items = self.conn.execute(
            """
            SELECT id, scope_type, scope_id, reason, estimated_minutes, status
            FROM study_plan_items
            WHERE plan_day_id = ?
            ORDER BY reason DESC, estimated_minutes DESC
            """,
            (plan["id"],)
        ).fetchall()

        return {
            "plan_day_id": plan["id"],
            "plan_date": plan["plan_date"],
            "target_minutes": plan["target_minutes"],
            "estimated_total_minutes": plan["estimated_total_minutes"],
            "completed": bool(plan["completed"]),
            "generated_at": plan["generated_at"],
            "items": [dict(row) for row in items],
        }

    def mark_item_done(self, plan_item_id: int, performance: str = "good") -> None:
        """
        Marcar un item del plan como completado.

        performance: again|hard|good|easy
        """
        self.conn.execute(
            """
            UPDATE study_plan_items
            SET status = 'done', performance = ?, completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (performance, plan_item_id)
        )

    def get_weekly_summary(self, days: int = 7) -> dict[str, Any]:
        """Resumen de estudio semanal."""
        start_date = (datetime.now() - timedelta(days=days)).date().isoformat()

        stats = self.conn.execute(
            """
            SELECT
                COUNT(DISTINCT plan_date) as days_with_plan,
                COUNT(*) as total_items,
                SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) as skipped,
                SUM(estimated_minutes) as total_minutes,
                SUM(CASE WHEN status = 'done' THEN estimated_minutes ELSE 0 END) as completed_minutes
            FROM study_plan_items spi
            INNER JOIN study_plan_days spd ON spd.id = spi.plan_day_id
            WHERE spd.plan_date >= ?
            """,
            (start_date,)
        ).fetchone()

        return {
            "period_days": days,
            "days_with_plan": stats["days_with_plan"] or 0,
            "total_items": stats["total_items"] or 0,
            "completed_items": stats["completed"] or 0,
            "skipped_items": stats["skipped"] or 0,
            "total_planned_minutes": stats["total_minutes"] or 0,
            "completed_minutes": stats["completed_minutes"] or 0,
            "completion_rate": round(
                100 * (stats["completed"] or 0) / (stats["total_items"] or 1), 1
            ),
        }

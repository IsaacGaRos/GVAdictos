"""Academia mode: Guided study flow orchestrator.

Combines all study components (articles, IA, notes, audio, questions, SRS)
into a cohesive workflow for a single topic.
"""

from __future__ import annotations

import sqlite3
from typing import Any


class AcademiaFlowError(RuntimeError):
    """Base error for academia flow issues."""


class AcademiaFlow:
    """Orchestrator for guided study flow through a topic."""

    FLOW_STAGES = [
        "lectura",  # Read articles with TTS
        "notas",    # Take notes and highlights
        "dudas",    # Ask IA for clarifications
        "preguntas", # Take questions (official or IA)
        "repaso",   # SRS review
        "resumen",  # Summary and reflections
    ]

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create_topic_flow(
        self,
        topic_id: int,
        user_id: int = 1,
    ) -> dict[str, Any]:
        """Create a new study flow for a topic."""
        topic = self.conn.execute(
            "SELECT id, topic_number, official_text FROM topics WHERE id = ?",
            (topic_id,),
        ).fetchone()

        if not topic:
            raise AcademiaFlowError(f"Topic {topic_id} not found")

        # Get articles for this topic
        articles = self.conn.execute(
            """
            SELECT DISTINCT a.id, a.article_ref, a.title
            FROM articles a
            JOIN topic_sources ts ON a.id = ts.article_id
            WHERE ts.topic_id = ?
            ORDER BY a.id
            """,
            (topic_id,),
        ).fetchall()

        # Get questions for this topic
        questions = self.conn.execute(
            """
            SELECT COUNT(*) as count FROM questions q
            JOIN topic_sources ts ON q.article_id = ts.article_id
            WHERE ts.topic_id = ?
            """,
            (topic_id,),
        ).fetchone()

        return {
            "topic_id": topic_id,
            "topic_number": topic["topic_number"],
            "topic_title": topic["official_text"],
            "article_count": len(articles),
            "question_count": questions["count"],
            "stages": self.FLOW_STAGES,
            "user_id": user_id,
        }

    def get_flow_progress(
        self,
        topic_id: int,
        user_id: int = 1,
    ) -> dict[str, Any]:
        """Get progress through a topic's study flow."""
        # MVP: Simple progress tracking
        progress = {}
        for stage in self.FLOW_STAGES:
            progress[stage] = {
                "completed": False,
                "data_count": 0,
            }

        # Check notes for "notas" stage
        notes = self.conn.execute(
            """
            SELECT COUNT(*) as count FROM study_article_notes
            WHERE article_id IN (
                SELECT DISTINCT a.id FROM articles a
                JOIN topic_sources ts ON a.id = ts.article_id
                WHERE ts.topic_id = ?
            )
            """,
            (topic_id,),
        ).fetchone()
        if notes and notes["count"] > 0:
            progress["notas"]["data_count"] = notes["count"]

        return {
            "topic_id": topic_id,
            "user_id": user_id,
            "progress": progress,
        }

    def get_next_stage(self, topic_id: int, current_stage: str) -> str | None:
        """Get next stage in flow."""
        try:
            idx = self.FLOW_STAGES.index(current_stage)
            if idx < len(self.FLOW_STAGES) - 1:
                return self.FLOW_STAGES[idx + 1]
        except ValueError:
            pass
        return None

    def recommend_next_action(
        self,
        topic_id: int,
        current_stage: str,
    ) -> dict[str, Any]:
        """Recommend next action based on current flow stage."""
        next_stage = self.get_next_stage(topic_id, current_stage)

        recommendations = {
            "lectura": {
                "action": "Leer artículos con TTS",
                "instructions": "Abre cada artículo y usa el reproductor de audio para escuchar mientras lees",
            },
            "notas": {
                "action": "Tomar apuntes",
                "instructions": "Subraya párrafos y añade notas sobre conceptos clave",
            },
            "dudas": {
                "action": "Preguntar a IA",
                "instructions": "Usa los insights de IA para aclarar conceptos difíciles",
            },
            "preguntas": {
                "action": "Practicar preguntas",
                "instructions": "Resuelve preguntas oficiales o generadas por IA",
            },
            "repaso": {
                "action": "Repetición espaciada",
                "instructions": "Repasa según el sistema SM-2",
            },
            "resumen": {
                "action": "Hacer resumen",
                "instructions": "Escribe un resumen de lo aprendido",
            },
        }

        return {
            "current_stage": current_stage,
            "next_stage": next_stage,
            "recommendation": recommendations.get(current_stage, {}),
        }

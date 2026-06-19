"""Mock exam service for test simulations and analysis.

Handles exam creation, question selection, scoring, and statistics.
"""

from __future__ import annotations

import sqlite3
import random
import time
from typing import Any

from src.simulacros.repository import SimulacrpsRepository


class ExamServiceError(RuntimeError):
    """Base error for exam service issues."""


class ExamService:
    """Service for managing mock exams and exam statistics."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.repo = SimulacrpsRepository(conn)

    def create_exam(
        self,
        title: str,
        topic_id: int | None = None,
        num_questions: int = 30,
        time_limit_minutes: int | None = None,
        source_kind: str = "oficial",
    ) -> int:
        """Create a new mock exam.

        source_kind: 'oficial' (bank), 'ia' (AI-generated), 'mixto' (both)
        """
        return self.repo.create_mock_exam(
            title=title,
            num_questions=num_questions,
            time_limit_minutes=time_limit_minutes,
            topic_id=topic_id,
            source_kind=source_kind,
        )

    def select_exam_questions(
        self,
        exam_id: int,
        num_questions: int = 30,
        source_kind: str = "oficial",
    ) -> list[dict[str, Any]]:
        """Select questions for an exam from available sources.

        Returns list of question dicts with: id, enunciado, opciones, respuesta_correcta
        """
        questions = []

        if source_kind in ["oficial", "mixto"]:
            # From official exam bank (B1)
            official = self.conn.execute(
                """
                SELECT eq.id, eq.enunciado, eq.respuesta_oficial as respuesta_correcta
                FROM exam_questions eq
                WHERE eq.anulada = 0
                ORDER BY RANDOM()
                LIMIT ?
                """,
                (num_questions // 2 if source_kind == "mixto" else num_questions,),
            ).fetchall()
            for q in official:
                options = self.conn.execute(
                    """
                    SELECT letra, texto FROM exam_question_options
                    WHERE exam_question_id = ?
                    ORDER BY letra
                    """,
                    (q["id"],),
                ).fetchall()
                questions.append({
                    "id": q["id"],
                    "source": "oficial",
                    "enunciado": q["enunciado"],
                    "opciones": [dict(o) for o in options],
                    "respuesta_correcta": q["respuesta_correcta"],
                })

        if source_kind in ["ia", "mixto"]:
            # From AI-generated questions (D3)
            ai_q = self.conn.execute(
                """
                SELECT id, enunciado, respuesta_correcta
                FROM ai_questions
                WHERE validation_status = 'validado'
                ORDER BY RANDOM()
                LIMIT ?
                """,
                (num_questions // 2 if source_kind == "mixto" else num_questions,),
            ).fetchall()
            for q in ai_q:
                options = self.conn.execute(
                    """
                    SELECT letra, texto FROM ai_question_options
                    WHERE ai_question_id = ?
                    ORDER BY letra
                    """,
                    (q["id"],),
                ).fetchall()
                questions.append({
                    "id": q["id"],
                    "source": "ia",
                    "enunciado": q["enunciado"],
                    "opciones": [dict(o) for o in options],
                    "respuesta_correcta": q["respuesta_correcta"],
                })

        # Shuffle and limit to exact num_questions
        random.shuffle(questions)
        return questions[:num_questions]

    def record_answer(
        self,
        exam_id: int,
        question_number: int,
        source_kind: str,
        question_id: int,
        user_answer: str,
        correct_answer: str,
        tiempo_segundos: float | None = None,
    ) -> dict[str, Any]:
        """Record an answer and return feedback."""
        is_correct = user_answer == correct_answer

        self.repo.record_answer(
            exam_id=exam_id,
            question_number=question_number,
            source_kind=source_kind,
            question_ref=str(question_id),
            user_answer=user_answer,
            correct_answer=correct_answer,
            is_correct=is_correct,
            tiempo_segundos=tiempo_segundos,
        )

        return {
            "is_correct": is_correct,
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "feedback": "Correcto" if is_correct else f"Respuesta correcta: {correct_answer}",
        }

    def finish_exam(self, exam_id: int) -> dict[str, Any]:
        """Calculate final score and mark exam as finished."""
        stats = self.repo.compute_exam_stats(exam_id)
        if not stats or stats.get("total_questions", 0) == 0:
            raise ExamServiceError(f"No answers recorded for exam {exam_id}")

        passed = stats["score_percent"] >= 60
        self.repo.finish_mock_exam(
            exam_id,
            stats["score_percent"],
            passed=passed,
        )

        return {
            "exam_id": exam_id,
            "score_percent": stats["score_percent"],
            "correct": stats["correct_count"],
            "total": stats["total_questions"],
            "passed": passed,
            "time_minutes": stats["time_total_seconds"] / 60,
        }

    def get_exam_history(self, user_id: int = 1) -> list[dict[str, Any]]:
        """Get user's recent exam history."""
        exams = self.repo.get_user_mock_exams(user_id)
        result = []
        for exam in exams:
            stats = self.repo.compute_exam_stats(exam["id"])
            result.append({
                "id": exam["id"],
                "title": exam["title"],
                "score": stats.get("score_percent", 0),
                "passed": stats.get("passed", False),
                "created_at": exam["created_at"],
                "finished_at": exam["finished_at"],
            })
        return result

    def get_performance_summary(self, user_id: int = 1) -> dict[str, Any]:
        """Get summary statistics of all exams taken."""
        exams = self.repo.get_user_mock_exams(user_id, limit=100)
        if not exams:
            return {
                "total_exams": 0,
                "avg_score": 0,
                "pass_rate": 0,
                "best_score": 0,
                "worst_score": 0,
            }

        all_stats = [self.repo.compute_exam_stats(e["id"]) for e in exams]
        all_scores = [s["score_percent"] for s in all_stats if "score_percent" in s]
        all_passed = [s.get("passed", False) for s in all_stats]

        return {
            "total_exams": len(exams),
            "avg_score": sum(all_scores) / len(all_scores) if all_scores else 0,
            "pass_rate": sum(all_passed) / len(all_passed) * 100 if all_passed else 0,
            "best_score": max(all_scores) if all_scores else 0,
            "worst_score": min(all_scores) if all_scores else 0,
            "trend": "mejorando" if len(all_scores) > 1 and all_scores[-1] > all_scores[0] else "sin cambios",
        }

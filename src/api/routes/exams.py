"""Exam endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
import sqlite3

from src.api.models import ExamConfig, ExamResponse, ExamAnswerSubmit, ExamResultResponse
from src.core.db import connect
from src.core.paths import DB_PATH
from src.simulacros.service import ExamService

router = APIRouter()


def get_db() -> sqlite3.Connection:
    return connect(DB_PATH)


@router.post("", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
async def create_exam(
    config: ExamConfig,
    user_id: int = 1,
    db: sqlite3.Connection = Depends(get_db),
):
    """Create a new mock exam."""
    try:
        service = ExamService(db)
        exam_id = service.create_exam(
            title=config.title,
            num_questions=config.num_questions,
            time_limit_minutes=config.time_limit_minutes,
            source_kind=config.source_kind,
            topic_id=config.topic_id,
        )

        exam = db.execute(
            "SELECT * FROM mock_exams WHERE id = ?",
            (exam_id,),
        ).fetchone()

        return ExamResponse(**dict(exam))

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{exam_id}", response_model=ExamResponse)
async def get_exam(
    exam_id: int,
    db: sqlite3.Connection = Depends(get_db),
):
    """Get exam details."""
    exam = db.execute(
        "SELECT * FROM mock_exams WHERE id = ?",
        (exam_id,),
    ).fetchone()

    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return ExamResponse(**dict(exam))


@router.post("/{exam_id}/answers", status_code=status.HTTP_201_CREATED)
async def submit_answer(
    exam_id: int,
    data: ExamAnswerSubmit,
    db: sqlite3.Connection = Depends(get_db),
):
    """Submit an answer to a question."""
    try:
        service = ExamService(db)
        result = service.record_answer(
            exam_id=exam_id,
            question_number=data.question_number,
            source_kind=data.source_kind,
            question_id=data.question_id,
            user_answer=data.user_answer,
            correct_answer="",  # Would be fetched from question
            tiempo_segundos=data.tiempo_segundos,
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{exam_id}/finish", response_model=ExamResultResponse)
async def finish_exam(
    exam_id: int,
    db: sqlite3.Connection = Depends(get_db),
):
    """Finish an exam and get results."""
    try:
        service = ExamService(db)
        result = service.finish_exam(exam_id)

        return ExamResultResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=list[ExamResponse])
async def get_exam_history(
    user_id: int = 1,
    limit: int = 20,
    db: sqlite3.Connection = Depends(get_db),
):
    """Get exam history for user."""
    exams = db.execute(
        """
        SELECT * FROM mock_exams
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()

    return [ExamResponse(**dict(e)) for e in exams]

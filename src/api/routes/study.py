"""Study endpoints for notes, highlights, and progress."""

from fastapi import APIRouter, Depends, HTTPException, status
import sqlite3

from src.api.models import NoteCreate, NoteResponse, HighlightCreate, HighlightResponse, ProgressResponse
from src.core.db import connect
from src.core.paths import DB_PATH

router = APIRouter()


def get_db() -> sqlite3.Connection:
    return connect(DB_PATH)


@router.post("/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    data: NoteCreate,
    user_id: int = 1,
    db: sqlite3.Connection = Depends(get_db),
):
    """Create a study note on an article."""
    cursor = db.execute(
        """
        INSERT INTO study_article_notes(
            user_id, article_id, selected_text, note_text, tags
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, data.article_id, data.selected_text, data.note_text, data.tags),
    )
    db.commit()
    note_id = cursor.lastrowid

    note = db.execute(
        "SELECT * FROM study_article_notes WHERE id = ?",
        (note_id,),
    ).fetchone()

    return NoteResponse(**dict(note))


@router.get("/notes", response_model=list[NoteResponse])
async def get_notes(
    article_id: int | None = None,
    topic_id: int | None = None,
    user_id: int = 1,
    db: sqlite3.Connection = Depends(get_db),
):
    """Get study notes."""
    query = "SELECT * FROM study_article_notes WHERE user_id = ?"
    params = [user_id]

    if article_id:
        query += " AND article_id = ?"
        params.append(article_id)

    query += " ORDER BY created_at DESC"

    notes = db.execute(query, params).fetchall()
    return [NoteResponse(**dict(n)) for n in notes]


@router.post("/highlights", response_model=HighlightResponse, status_code=status.HTTP_201_CREATED)
async def create_highlight(
    data: HighlightCreate,
    user_id: int = 1,
    db: sqlite3.Connection = Depends(get_db),
):
    """Create a highlight on article text."""
    cursor = db.execute(
        """
        INSERT INTO study_highlights(
            user_id, article_id, selected_text, start_offset, end_offset
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, data.article_id, data.selected_text, data.start_offset, data.end_offset),
    )
    db.commit()
    highlight_id = cursor.lastrowid

    highlight = db.execute(
        "SELECT * FROM study_highlights WHERE id = ?",
        (highlight_id,),
    ).fetchone()

    return HighlightResponse(**dict(highlight))


@router.get("/highlights", response_model=list[HighlightResponse])
async def get_highlights(
    article_id: int | None = None,
    user_id: int = 1,
    db: sqlite3.Connection = Depends(get_db),
):
    """Get highlights for articles."""
    query = "SELECT * FROM study_highlights WHERE user_id = ?"
    params = [user_id]

    if article_id:
        query += " AND article_id = ?"
        params.append(article_id)

    query += " ORDER BY created_at DESC"

    highlights = db.execute(query, params).fetchall()
    return [HighlightResponse(**dict(h)) for h in highlights]


@router.get("/progress", response_model=list[ProgressResponse])
async def get_progress(
    topic_id: int | None = None,
    user_id: int = 1,
    db: sqlite3.Connection = Depends(get_db),
):
    """Get study progress."""
    query = """
        SELECT
            article_id, topic_id, confidence, review_count, last_review, next_review
        FROM study_last_reviews
        WHERE user_id = ?
    """
    params = [user_id]

    if topic_id:
        query += " AND topic_id = ?"
        params.append(topic_id)

    query += " ORDER BY next_review"

    rows = db.execute(query, params).fetchall()
    return [ProgressResponse(**dict(r)) for r in rows]


@router.get("/summary")
async def get_study_summary(
    user_id: int = 1,
    db: sqlite3.Connection = Depends(get_db),
):
    """Get study summary for user."""
    notes_count = db.execute(
        "SELECT COUNT(*) FROM study_article_notes WHERE user_id = ?",
        (user_id,),
    ).fetchone()[0]

    highlights_count = db.execute(
        "SELECT COUNT(*) FROM study_highlights WHERE user_id = ?",
        (user_id,),
    ).fetchone()[0]

    reviews = db.execute(
        "SELECT COUNT(*) FROM study_last_reviews WHERE user_id = ? AND next_review <= datetime('now')",
        (user_id,),
    ).fetchone()[0]

    return {
        "notes": notes_count,
        "highlights": highlights_count,
        "pending_reviews": reviews,
    }

"""Management of study doubts (preguntas/dudas)."""

from __future__ import annotations

import sqlite3
from datetime import datetime


def ensure_doubts_table(conn: sqlite3.Connection) -> None:
    """Create study_doubts table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS study_doubts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            article_id INTEGER NOT NULL,
            topic_id INTEGER,
            doubt_text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(user_id, article_id),
            FOREIGN KEY(article_id) REFERENCES articles(id) ON DELETE CASCADE
        )
    """)
    conn.commit()


def save_doubt(
    conn: sqlite3.Connection,
    article_id: int,
    doubt_text: str,
    user_id: int = 1,
    topic_id: int | None = None,
) -> int:
    """Save or update a doubt for an article."""
    now = datetime.now().isoformat()
    c = conn.cursor()

    # Check if doubt already exists
    existing = c.execute(
        "SELECT id FROM study_doubts WHERE user_id = ? AND article_id = ?",
        (user_id, article_id),
    ).fetchone()

    if existing:
        # Update existing doubt
        c.execute(
            "UPDATE study_doubts SET doubt_text = ?, updated_at = ?, status = ? "
            "WHERE user_id = ? AND article_id = ?",
            (doubt_text, now, "open", user_id, article_id),
        )
        doubt_id = existing[0]
    else:
        # Create new doubt
        c.execute(
            "INSERT INTO study_doubts (user_id, article_id, topic_id, doubt_text, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, article_id, topic_id, doubt_text, now, now),
        )
        doubt_id = c.lastrowid

    conn.commit()
    return doubt_id


def get_doubt(conn: sqlite3.Connection, article_id: int, user_id: int = 1) -> dict | None:
    """Get a doubt for an article."""
    c = conn.cursor()
    row = c.execute(
        "SELECT * FROM study_doubts WHERE user_id = ? AND article_id = ?",
        (user_id, article_id),
    ).fetchone()
    return dict(row) if row else None


def delete_doubt(conn: sqlite3.Connection, article_id: int, user_id: int = 1) -> None:
    """Delete a doubt."""
    c = conn.cursor()
    c.execute(
        "DELETE FROM study_doubts WHERE user_id = ? AND article_id = ?",
        (user_id, article_id),
    )
    conn.commit()


def list_doubts(conn: sqlite3.Connection, user_id: int = 1) -> list[dict]:
    """List all doubts for a user."""
    c = conn.cursor()
    rows = c.execute(
        """SELECT d.*, a.article_ref, l.name as law_name
           FROM study_doubts d
           JOIN articles a ON d.article_id = a.id
           JOIN laws l ON a.law_id = l.id
           WHERE d.user_id = ? AND d.status = 'open'
           ORDER BY d.created_at DESC""",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def resolve_doubt(conn: sqlite3.Connection, article_id: int, user_id: int = 1) -> None:
    """Mark a doubt as resolved."""
    now = datetime.now().isoformat()
    c = conn.cursor()
    c.execute(
        "UPDATE study_doubts SET status = 'resolved', updated_at = ? "
        "WHERE user_id = ? AND article_id = ?",
        (now, user_id, article_id),
    )
    conn.commit()

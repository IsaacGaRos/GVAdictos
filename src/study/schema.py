from __future__ import annotations

import sqlite3


BASE_TABLES = [
    "topics",
    "laws",
    "articles",
]

STUDY_TABLES = [
    "study_article_notes",
    "study_highlights",
    "study_progress",
    "study_marks",
    "study_last_reviews",
]


CREATE_STUDY_FEATURES_SQL = """
CREATE TABLE IF NOT EXISTS study_article_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER REFERENCES articles(id) ON DELETE SET NULL,
    law_id_snapshot INTEGER,
    article_ref_snapshot TEXT,
    anchor_key TEXT,
    selected_text TEXT,
    note_text TEXT NOT NULL,
    tags TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    archived_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_study_article_notes_article
    ON study_article_notes(article_id, updated_at);

CREATE INDEX IF NOT EXISTS idx_study_article_notes_ref_snapshot
    ON study_article_notes(law_id_snapshot, article_ref_snapshot);

CREATE TABLE IF NOT EXISTS study_highlights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER REFERENCES articles(id) ON DELETE SET NULL,
    law_id_snapshot INTEGER,
    article_ref_snapshot TEXT,
    anchor_key TEXT,
    selected_text TEXT NOT NULL,
    start_offset INTEGER,
    end_offset INTEGER,
    color TEXT NOT NULL DEFAULT 'yellow',
    note_text TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    archived_at TEXT,
    CHECK(start_offset IS NULL OR end_offset IS NULL OR start_offset <= end_offset)
);

CREATE INDEX IF NOT EXISTS idx_study_highlights_article
    ON study_highlights(article_id, updated_at);

CREATE INDEX IF NOT EXISTS idx_study_highlights_ref_snapshot
    ON study_highlights(law_id_snapshot, article_ref_snapshot);

CREATE TABLE IF NOT EXISTS study_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,
    article_id INTEGER REFERENCES articles(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'not_started'
        CHECK(status IN ('not_started', 'reading', 'reviewing', 'completed', 'paused')),
    completion_percent INTEGER NOT NULL DEFAULT 0 CHECK(completion_percent BETWEEN 0 AND 100),
    total_minutes INTEGER NOT NULL DEFAULT 0 CHECK(total_minutes >= 0),
    pomodoro_count INTEGER NOT NULL DEFAULT 0 CHECK(pomodoro_count >= 0),
    last_activity_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK(topic_id IS NOT NULL OR article_id IS NOT NULL)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_study_progress_topic_only
    ON study_progress(topic_id)
    WHERE topic_id IS NOT NULL AND article_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_study_progress_article
    ON study_progress(article_id)
    WHERE article_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_study_progress_status
    ON study_progress(status, updated_at);

CREATE TABLE IF NOT EXISTS study_marks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,
    article_id INTEGER REFERENCES articles(id) ON DELETE SET NULL,
    mark_type TEXT NOT NULL CHECK(mark_type IN ('doubt', 'important', 'bookmark')),
    note_text TEXT,
    resolved INTEGER NOT NULL DEFAULT 0 CHECK(resolved IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK(topic_id IS NOT NULL OR article_id IS NOT NULL)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_study_marks_topic_only
    ON study_marks(topic_id, mark_type)
    WHERE topic_id IS NOT NULL AND article_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_study_marks_article
    ON study_marks(article_id, mark_type)
    WHERE article_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_study_marks_unresolved
    ON study_marks(mark_type, resolved, updated_at);

CREATE TABLE IF NOT EXISTS study_last_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,
    article_id INTEGER REFERENCES articles(id) ON DELETE SET NULL,
    last_reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_result TEXT NOT NULL DEFAULT 'unknown'
        CHECK(last_result IN ('unknown', 'again', 'hard', 'good', 'easy')),
    confidence INTEGER CHECK(confidence IS NULL OR confidence BETWEEN 0 AND 5),
    next_review_at TEXT,
    review_count INTEGER NOT NULL DEFAULT 1 CHECK(review_count >= 1),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK(topic_id IS NOT NULL OR article_id IS NOT NULL)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_study_last_reviews_topic_only
    ON study_last_reviews(topic_id)
    WHERE topic_id IS NOT NULL AND article_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_study_last_reviews_article
    ON study_last_reviews(article_id)
    WHERE article_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_study_last_reviews_due
    ON study_last_reviews(next_review_at, last_reviewed_at);
"""


def apply_study_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(CREATE_STUDY_FEATURES_SQL)


def existing_study_tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name LIKE 'study_%'
        ORDER BY name
        """
    ).fetchall()
    return {str(row[0]) for row in rows}


def missing_study_tables(conn: sqlite3.Connection) -> list[str]:
    existing = existing_study_tables(conn)
    return [table for table in STUDY_TABLES if table not in existing]


def existing_base_tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    ).fetchall()
    return {str(row[0]) for row in rows if str(row[0]) in BASE_TABLES}


def missing_base_tables(conn: sqlite3.Connection) -> list[str]:
    existing = existing_base_tables(conn)
    return [table for table in BASE_TABLES if table not in existing]


def schema_status(conn: sqlite3.Connection) -> dict[str, object]:
    missing_base = missing_base_tables(conn)
    missing_study = missing_study_tables(conn)
    return {
        "base_tables": BASE_TABLES,
        "study_tables": STUDY_TABLES,
        "missing_base_tables": missing_base,
        "missing_study_tables": missing_study,
        "base_ready": not missing_base,
        "study_ready": not missing_study,
    }

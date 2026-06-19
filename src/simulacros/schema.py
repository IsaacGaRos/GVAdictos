from __future__ import annotations

import sqlite3


SIMULACROS_TABLES = [
    "mock_exams",
    "mock_exam_answers",
]


CREATE_SIMULACROS_FEATURES_SQL = """
CREATE TABLE IF NOT EXISTS mock_exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1,
    topic_id INTEGER REFERENCES topics(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    config TEXT,
    num_questions INTEGER NOT NULL,
    time_limit_minutes INTEGER,
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT,
    score_percent REAL,
    passed INTEGER,
    source_kind TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mock_exams_user
    ON mock_exams(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_mock_exams_topic
    ON mock_exams(topic_id);

CREATE INDEX IF NOT EXISTS idx_mock_exams_finished
    ON mock_exams(finished_at);


CREATE TABLE IF NOT EXISTS mock_exam_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mock_exam_id INTEGER NOT NULL REFERENCES mock_exams(id) ON DELETE CASCADE,
    question_number INTEGER NOT NULL,
    source_kind TEXT NOT NULL,
    question_ref TEXT,
    user_answer TEXT,
    correct_answer TEXT,
    is_correct INTEGER,
    tiempo_segundos REAL,
    explanation TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mock_exam_answers_exam
    ON mock_exam_answers(mock_exam_id);

CREATE INDEX IF NOT EXISTS idx_mock_exam_answers_correct
    ON mock_exam_answers(is_correct);
"""


def missing_simulacros_tables(conn: sqlite3.Connection) -> list[str]:
    """Check which simulacros tables are missing."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ({})".format(
            ",".join("?" * len(SIMULACROS_TABLES))
        ),
        SIMULACROS_TABLES,
    )
    existing = {row[0] for row in cursor.fetchall()}
    return [table for table in SIMULACROS_TABLES if table not in existing]


def ensure_simulacros_tables(conn: sqlite3.Connection) -> None:
    """Create simulacros tables if they don't exist."""
    conn.executescript(CREATE_SIMULACROS_FEATURES_SQL)
    conn.commit()

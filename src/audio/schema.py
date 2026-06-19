from __future__ import annotations

import sqlite3


AUDIO_TABLES = [
    "tts_audio",
]


CREATE_AUDIO_FEATURES_SQL = """
CREATE TABLE IF NOT EXISTS tts_audio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope_type TEXT NOT NULL,
    scope_id INTEGER NOT NULL,
    voice TEXT,
    speed REAL DEFAULT 1.0,
    format TEXT DEFAULT 'mp3',
    content_hash TEXT NOT NULL,
    storage_url TEXT,
    storage_path TEXT,
    duration_seconds REAL,
    generated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(scope_type, scope_id, voice, speed, format)
);

CREATE INDEX IF NOT EXISTS idx_tts_audio_scope
    ON tts_audio(scope_type, scope_id);

CREATE INDEX IF NOT EXISTS idx_tts_audio_hash
    ON tts_audio(content_hash);
"""


def missing_audio_tables(conn: sqlite3.Connection) -> list[str]:
    """Check which audio feature tables are missing."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ({})".format(
            ",".join("?" * len(AUDIO_TABLES))
        ),
        AUDIO_TABLES,
    )
    existing = {row[0] for row in cursor.fetchall()}
    return [table for table in AUDIO_TABLES if table not in existing]


def ensure_audio_tables(conn: sqlite3.Connection) -> None:
    """Create audio feature tables if they don't exist."""
    conn.executescript(CREATE_AUDIO_FEATURES_SQL)
    conn.commit()

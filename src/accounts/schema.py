from __future__ import annotations

import sqlite3


ACCOUNTS_TABLES = [
    "users",
    "user_sessions",
]


CREATE_ACCOUNTS_FEATURES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    is_admin INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_users_email
    ON users(email);


CREATE TABLE IF NOT EXISTS user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_user_sessions_user
    ON user_sessions(user_id);

CREATE INDEX IF NOT EXISTS idx_user_sessions_token
    ON user_sessions(token);
"""


def missing_accounts_tables(conn: sqlite3.Connection) -> list[str]:
    """Check which accounts tables are missing."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ({})".format(
            ",".join("?" * len(ACCOUNTS_TABLES))
        ),
        ACCOUNTS_TABLES,
    )
    existing = {row[0] for row in cursor.fetchall()}
    return [table for table in ACCOUNTS_TABLES if table not in existing]


def ensure_accounts_tables(conn: sqlite3.Connection) -> None:
    """Create accounts tables if they don't exist."""
    conn.executescript(CREATE_ACCOUNTS_FEATURES_SQL)
    conn.commit()


def add_user_id_column(conn: sqlite3.Connection, table_name: str) -> bool:
    """Add user_id column to an existing table (with default=1)."""
    try:
        conn.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1
            """
        )
        conn.commit()
        return True
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            return False  # Column already exists
        raise

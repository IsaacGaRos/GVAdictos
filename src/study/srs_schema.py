"""
Schema para SRS (Spaced Repetition System) tipo Anki (Ola C1).

Basado en study_last_reviews, extendido con SM-2 algorithm.
Plan diario inteligente.
"""

from __future__ import annotations

import sqlite3


CREATE_SRS_SQL = """
-- Estado SRS completo (SM-2 algorithm)
CREATE TABLE IF NOT EXISTS srs_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope_type TEXT NOT NULL,           -- article | question | topic
    scope_id INTEGER NOT NULL,
    algo TEXT NOT NULL DEFAULT 'sm2',
    ease REAL NOT NULL DEFAULT 2.5,     -- Factor de facilidad (1.3 a 2.5+)
    interval_days REAL NOT NULL DEFAULT 1.0,  -- Intervalo en días
    due_at TEXT NOT NULL,               -- Proxima fecha de repaso
    reps INTEGER NOT NULL DEFAULT 0,    -- Numero de repeticiones
    lapses INTEGER NOT NULL DEFAULT 0,  -- Numero de olvidos
    state TEXT NOT NULL DEFAULT 'new' CHECK(state IN ('new', 'learning', 'review', 'relearning')),
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(scope_type, scope_id)
);

CREATE INDEX IF NOT EXISTS idx_srs_state_due
    ON srs_state(due_at, state);

CREATE INDEX IF NOT EXISTS idx_srs_state_scope
    ON srs_state(scope_type, scope_id);

-- Plan diario
CREATE TABLE IF NOT EXISTS study_plan_days (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_date TEXT NOT NULL,
    generated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    target_minutes INTEGER NOT NULL DEFAULT 120,
    estimated_total_minutes INTEGER,
    completed INTEGER NOT NULL DEFAULT 0 CHECK(completed IN (0, 1)),
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_study_plan_days_date
    ON study_plan_days(plan_date);

-- Items del plan diario
CREATE TABLE IF NOT EXISTS study_plan_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_day_id INTEGER NOT NULL REFERENCES study_plan_days(id) ON DELETE CASCADE,
    scope_type TEXT NOT NULL,                       -- article | question | topic
    scope_id INTEGER NOT NULL,
    reason TEXT NOT NULL,                           -- vencimiento_srs|error|frecuencia|importancia|olvido
    estimated_minutes INTEGER NOT NULL DEFAULT 5,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'done', 'skipped')),
    completed_at TEXT,
    performance TEXT,                               -- again|hard|good|easy (si status=done)
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_study_plan_items_plan_day
    ON study_plan_items(plan_day_id, status);

CREATE INDEX IF NOT EXISTS idx_study_plan_items_scope
    ON study_plan_items(scope_type, scope_id);
"""


def apply_srs_schema(conn: sqlite3.Connection) -> None:
    """Crear tablas de SRS si no existen."""
    conn.executescript(CREATE_SRS_SQL)


def srs_tables_exist(conn: sqlite3.Connection) -> bool:
    """Comprobar si las tablas de SRS existen."""
    tables = {"srs_state", "study_plan_days", "study_plan_items"}
    existing = set(
        row[0]
        for row in conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN (?, ?, ?)
            """,
            tuple(tables)
        ).fetchall()
    )
    return tables == existing

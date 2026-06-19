"""
Schema para métricas de importancia/frecuencia/dificultad (Ola B3).

Tablas materializadas recalculadas por job.
Fórmula de importancia versionada y explicable.
"""

from __future__ import annotations

import sqlite3


CREATE_METRICS_SQL = """
-- Pesos de la fórmula de importancia (versionados)
CREATE TABLE IF NOT EXISTS importance_weights (
    version TEXT PRIMARY KEY,
    w_exam_count REAL NOT NULL DEFAULT 0.25,        -- Frecuencia en exámenes
    w_recencia REAL NOT NULL DEFAULT 0.15,          -- Años desde última aparición
    w_difficulty REAL NOT NULL DEFAULT 0.25,        -- Índice de dificultad
    w_modification REAL NOT NULL DEFAULT 0.10,      -- Cambios legislativos
    w_user_error REAL NOT NULL DEFAULT 0.15,        -- Tasa de error de usuarios
    w_tema_weight REAL NOT NULL DEFAULT 0.10,       -- Peso del tema en el currículo
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- Métricas de artículos
CREATE TABLE IF NOT EXISTS article_metrics (
    article_id INTEGER PRIMARY KEY REFERENCES articles(id) ON DELETE CASCADE,
    exam_count INTEGER NOT NULL DEFAULT 0,          -- Veces preguntado
    last_exam_year INTEGER,                         -- Último año preguntado
    difficulty_index REAL NOT NULL DEFAULT 0.0,    -- % fallo histórico (0-1)
    modification_count INTEGER NOT NULL DEFAULT 0,  -- Cambios legislativos
    user_error_rate REAL NOT NULL DEFAULT 0.0,     -- Agregado de attempts (0-1)
    repetition_count INTEGER NOT NULL DEFAULT 0,    -- Veces estudiado (SRS)
    importance_score REAL NOT NULL DEFAULT 0.0,     -- Score final
    importance_weights_version TEXT REFERENCES importance_weights(version),
    computed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_article_metrics_importance
    ON article_metrics(importance_score DESC);

CREATE INDEX IF NOT EXISTS idx_article_metrics_exam_count
    ON article_metrics(exam_count DESC);

CREATE INDEX IF NOT EXISTS idx_article_metrics_difficulty
    ON article_metrics(difficulty_index DESC);

-- Métricas de leyes
CREATE TABLE IF NOT EXISTS law_metrics (
    law_id INTEGER PRIMARY KEY REFERENCES laws(id) ON DELETE CASCADE,
    article_count INTEGER NOT NULL,
    exam_count INTEGER NOT NULL DEFAULT 0,
    avg_importance_score REAL NOT NULL DEFAULT 0.0,
    median_difficulty REAL NOT NULL DEFAULT 0.0,
    last_exam_year INTEGER,
    importance_weights_version TEXT REFERENCES importance_weights(version),
    computed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_law_metrics_importance
    ON law_metrics(avg_importance_score DESC);

-- Métricas de temas
CREATE TABLE IF NOT EXISTS topic_metrics (
    topic_id INTEGER PRIMARY KEY REFERENCES topics(id) ON DELETE CASCADE,
    article_count INTEGER NOT NULL,
    exam_count INTEGER NOT NULL DEFAULT 0,
    avg_importance_score REAL NOT NULL DEFAULT 0.0,
    median_difficulty REAL NOT NULL DEFAULT 0.0,
    last_exam_year INTEGER,
    curriculum_weight REAL NOT NULL DEFAULT 1.0,   -- Peso en el currículo oficial
    importance_weights_version TEXT REFERENCES importance_weights(version),
    computed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_topic_metrics_importance
    ON topic_metrics(avg_importance_score DESC);
"""


def apply_metrics_schema(conn: sqlite3.Connection) -> None:
    """Crear tablas de métricas si no existen."""
    conn.executescript(CREATE_METRICS_SQL)

    # Insertar pesos por defecto (v1)
    conn.execute(
        """
        INSERT OR IGNORE INTO importance_weights(
            version, w_exam_count, w_recencia, w_difficulty, w_modification,
            w_user_error, w_tema_weight, active, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "v1", 0.25, 0.15, 0.25, 0.10, 0.15, 0.10, 1,
            "Pesos por defecto: equilibrio entre frecuencia, dificultad y recencia"
        )
    )


def metrics_tables_exist(conn: sqlite3.Connection) -> bool:
    """Comprobar si las tablas de métricas existen."""
    tables = {"importance_weights", "article_metrics", "law_metrics", "topic_metrics"}
    existing = set(
        row[0]
        for row in conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN (?, ?, ?, ?)
            """,
            tuple(tables)
        ).fetchall()
    )
    return tables == existing

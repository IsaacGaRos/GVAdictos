from __future__ import annotations

import sqlite3


AI_TABLES = [
    "ai_article_insights",
    "ai_prompt_cache",
    "ai_questions",
    "ai_question_options",
]


CREATE_AI_FEATURES_SQL = """
CREATE TABLE IF NOT EXISTS ai_article_insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    article_version_id INTEGER REFERENCES article_versions(id),
    insight_type TEXT NOT NULL,
    content TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    requiere_revision INTEGER NOT NULL DEFAULT 1,
    validation_status TEXT NOT NULL DEFAULT 'pendiente_de_validacion',
    generated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(article_id, insight_type, input_hash)
);

CREATE INDEX IF NOT EXISTS idx_ai_article_insights_article
    ON ai_article_insights(article_id, insight_type);

CREATE INDEX IF NOT EXISTS idx_ai_article_insights_hash
    ON ai_article_insights(input_hash);

CREATE INDEX IF NOT EXISTS idx_ai_article_insights_validation
    ON ai_article_insights(validation_status);


CREATE TABLE IF NOT EXISTS ai_prompt_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    input_hash TEXT NOT NULL UNIQUE,
    prompt_type TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    input_text TEXT NOT NULL,
    output_text TEXT NOT NULL,
    model TEXT NOT NULL,
    tokens_used INTEGER,
    cost_usd REAL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_ai_prompt_cache_hash
    ON ai_prompt_cache(input_hash);

CREATE INDEX IF NOT EXISTS idx_ai_prompt_cache_type
    ON ai_prompt_cache(prompt_type, prompt_version);


CREATE TABLE IF NOT EXISTS ai_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
    topic_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,
    estilo TEXT NOT NULL,
    enunciado TEXT NOT NULL,
    respuesta_correcta TEXT NOT NULL,
    explicacion_razonada TEXT,
    model TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    requiere_revision INTEGER NOT NULL DEFAULT 1,
    validation_status TEXT NOT NULL DEFAULT 'pendiente_de_validacion',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(article_id, estilo, input_hash)
);

CREATE INDEX IF NOT EXISTS idx_ai_questions_article
    ON ai_questions(article_id);

CREATE INDEX IF NOT EXISTS idx_ai_questions_topic
    ON ai_questions(topic_id);

CREATE INDEX IF NOT EXISTS idx_ai_questions_validation
    ON ai_questions(validation_status);


CREATE TABLE IF NOT EXISTS ai_question_options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ai_question_id INTEGER NOT NULL REFERENCES ai_questions(id) ON DELETE CASCADE,
    letra TEXT NOT NULL,
    texto TEXT NOT NULL,
    es_correcta INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_ai_question_options_question
    ON ai_question_options(ai_question_id);
"""


def missing_ai_tables(conn: sqlite3.Connection) -> list[str]:
    """Check which AI feature tables are missing."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ({})".format(
            ",".join("?" * len(AI_TABLES))
        ),
        AI_TABLES,
    )
    existing = {row[0] for row in cursor.fetchall()}
    return [table for table in AI_TABLES if table not in existing]


def ensure_ai_tables(conn: sqlite3.Connection) -> None:
    """Create AI feature tables if they don't exist."""
    conn.executescript(CREATE_AI_FEATURES_SQL)
    conn.commit()

from __future__ import annotations

import sqlite3


SEARCH_TABLES = [
    "article_embeddings",
    "article_relations",
]


CREATE_SEARCH_FEATURES_SQL = """
CREATE TABLE IF NOT EXISTS article_embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL UNIQUE REFERENCES articles(id) ON DELETE CASCADE,
    model TEXT NOT NULL,
    dimension INTEGER NOT NULL,
    embedding_vector BLOB NOT NULL,
    input_hash TEXT NOT NULL,
    computed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_article_embeddings_article
    ON article_embeddings(article_id);


CREATE TABLE IF NOT EXISTS article_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    to_article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,
    weight REAL DEFAULT 0.5,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(from_article_id, to_article_id, relation_type, source)
);

CREATE INDEX IF NOT EXISTS idx_article_relations_from
    ON article_relations(from_article_id);

CREATE INDEX IF NOT EXISTS idx_article_relations_to
    ON article_relations(to_article_id);

CREATE INDEX IF NOT EXISTS idx_article_relations_type
    ON article_relations(relation_type);
"""


def missing_search_tables(conn: sqlite3.Connection) -> list[str]:
    """Check which search feature tables are missing."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ({})".format(
            ",".join("?" * len(SEARCH_TABLES))
        ),
        SEARCH_TABLES,
    )
    existing = {row[0] for row in cursor.fetchall()}
    return [table for table in SEARCH_TABLES if table not in existing]


def ensure_search_tables(conn: sqlite3.Connection) -> None:
    """Create search feature tables if they don't exist."""
    conn.executescript(CREATE_SEARCH_FEATURES_SQL)
    conn.commit()

from __future__ import annotations

import sqlite3


VERSIONING_TABLES = [
    "law_versions",
    "article_versions",
    "annotation_mappings",
]


CREATE_VERSIONING_FEATURES_SQL = """
CREATE TABLE IF NOT EXISTS law_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    law_id INTEGER NOT NULL REFERENCES laws(id) ON DELETE CASCADE,
    version_label TEXT NOT NULL,
    vigencia_desde TEXT,
    vigencia_hasta TEXT,
    source_document_id INTEGER REFERENCES source_documents(id),
    content_hash TEXT NOT NULL,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_current INTEGER NOT NULL DEFAULT 1,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_law_versions_law
    ON law_versions(law_id, is_current);

CREATE INDEX IF NOT EXISTS idx_law_versions_hash
    ON law_versions(content_hash);


CREATE TABLE IF NOT EXISTS article_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    law_version_id INTEGER NOT NULL REFERENCES law_versions(id) ON DELETE CASCADE,
    article_ref TEXT NOT NULL,
    anchor_key TEXT NOT NULL,
    text TEXT NOT NULL,
    text_hash TEXT NOT NULL,
    change_type TEXT,
    diff_summary TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_article_versions_law_version
    ON article_versions(law_version_id);

CREATE INDEX IF NOT EXISTS idx_article_versions_anchor
    ON article_versions(anchor_key);

CREATE INDEX IF NOT EXISTS idx_article_versions_change
    ON article_versions(change_type);


CREATE TABLE IF NOT EXISTS annotation_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_article_version_id INTEGER NOT NULL REFERENCES article_versions(id),
    to_article_version_id INTEGER NOT NULL REFERENCES article_versions(id),
    mapping_quality TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(from_article_version_id, to_article_version_id)
);

CREATE INDEX IF NOT EXISTS idx_annotation_mappings_from
    ON annotation_mappings(from_article_version_id);

CREATE INDEX IF NOT EXISTS idx_annotation_mappings_to
    ON annotation_mappings(to_article_version_id);
"""


def missing_versioning_tables(conn: sqlite3.Connection) -> list[str]:
    """Check which versioning tables are missing."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ({})".format(
            ",".join("?" * len(VERSIONING_TABLES))
        ),
        VERSIONING_TABLES,
    )
    existing = {row[0] for row in cursor.fetchall()}
    return [table for table in VERSIONING_TABLES if table not in existing]


def ensure_versioning_tables(conn: sqlite3.Connection) -> None:
    """Create versioning tables if they don't exist."""
    conn.executescript(CREATE_VERSIONING_FEATURES_SQL)
    conn.commit()

"""
Schema para references en grupo (Ola A3).

topic_source_segments permite autorizar mappings en grupo:
- division: una división entera (Capítulo III)
- range: rango de artículos (arts. 25-31)
- single: un artículo aislado

El materializador expande estos segmentos a filas individuales en topic_sources.
"""

from __future__ import annotations

import sqlite3


CREATE_SEGMENTS_SQL = """
-- Authoring de mapping "en grupo": un tema puede cubrir una división entera,
-- un rango contiguo de artículos, o un artículo suelto.
CREATE TABLE IF NOT EXISTS topic_source_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    law_id INTEGER NOT NULL REFERENCES laws(id) ON DELETE CASCADE,
    segment_type TEXT NOT NULL CHECK(segment_type IN ('division', 'range', 'single')),

    -- Para segment_type='division'
    division_id INTEGER REFERENCES law_divisions(id) ON DELETE SET NULL,

    -- Para segment_type='range' o 'single'
    from_article_id INTEGER REFERENCES articles(id) ON DELETE SET NULL,
    to_article_id INTEGER REFERENCES articles(id) ON DELETE SET NULL,

    priority TEXT NOT NULL DEFAULT 'core',
    mapping_basis TEXT NOT NULL,
    validation_status TEXT NOT NULL DEFAULT 'pendiente_de_validacion',
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK(
        (segment_type = 'division' AND division_id IS NOT NULL) OR
        (segment_type = 'range' AND from_article_id IS NOT NULL AND to_article_id IS NOT NULL) OR
        (segment_type = 'single' AND from_article_id IS NOT NULL AND to_article_id IS NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_topic_source_segments_topic
    ON topic_source_segments(topic_id, law_id);

CREATE INDEX IF NOT EXISTS idx_topic_source_segments_division
    ON topic_source_segments(division_id);

CREATE INDEX IF NOT EXISTS idx_topic_source_segments_articles
    ON topic_source_segments(from_article_id, to_article_id);

CREATE INDEX IF NOT EXISTS idx_topic_source_segments_validation
    ON topic_source_segments(validation_status, topic_id);
"""


def apply_segments_schema(conn: sqlite3.Connection) -> None:
    """Crear tabla de segmentos si no existe."""
    conn.executescript(CREATE_SEGMENTS_SQL)


def segments_table_exists(conn: sqlite3.Connection) -> bool:
    """Comprobar si la tabla topic_source_segments existe."""
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='topic_source_segments'"
    ).fetchone()
    return row is not None

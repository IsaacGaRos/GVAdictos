"""
Schema para estructura jerárquica de leyes (Ola A2).

Tablas aditivas para reflejar libro > título > capítulo > sección > subsección.
Sin modificar articles ni topic_sources.
"""

from __future__ import annotations

import sqlite3


CREATE_DIVISIONS_SQL = """
-- Árbol de divisiones por ley (libro > título > capítulo > sección > subsección)
CREATE TABLE IF NOT EXISTS law_divisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    law_id INTEGER NOT NULL REFERENCES laws(id) ON DELETE CASCADE,
    parent_id INTEGER REFERENCES law_divisions(id) ON DELETE CASCADE,
    division_type TEXT NOT NULL,      -- libro|titulo|capitulo|seccion|subseccion|disposicion
    number TEXT,                      -- "III", "1", "PRELIMINAR"
    label TEXT,                       -- "De la potestad sancionadora"
    order_index INTEGER NOT NULL,     -- orden dentro del padre
    full_path TEXT,                   -- "Título Preliminar > Capítulo III > Sección 2"
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(law_id, parent_id, division_type, number)
);

CREATE INDEX IF NOT EXISTS idx_law_divisions_law_id
    ON law_divisions(law_id, division_type, order_index);

CREATE INDEX IF NOT EXISTS idx_law_divisions_parent
    ON law_divisions(parent_id, order_index);

-- Pertenencia artículo → división hoja (sin modificar articles)
CREATE TABLE IF NOT EXISTS article_division (
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    division_id INTEGER NOT NULL REFERENCES law_divisions(id) ON DELETE CASCADE,
    is_primary INTEGER NOT NULL DEFAULT 1 CHECK(is_primary IN (0, 1)),
    PRIMARY KEY (article_id, division_id)
);

CREATE INDEX IF NOT EXISTS idx_article_division_article
    ON article_division(article_id);

CREATE INDEX IF NOT EXISTS idx_article_division_division
    ON article_division(division_id);
"""


def apply_divisions_schema(conn: sqlite3.Connection) -> None:
    """Crear tablas de divisiones si no existen."""
    conn.executescript(CREATE_DIVISIONS_SQL)


def divisions_tables_exist(conn: sqlite3.Connection) -> bool:
    """Comprobar si las tablas de divisiones existen."""
    tables = {"law_divisions", "article_division"}
    existing = set(
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN (?, ?)",
            tuple(tables),
        ).fetchall()
    )
    return tables == existing

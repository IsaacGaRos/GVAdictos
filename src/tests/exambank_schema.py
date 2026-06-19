"""
Schema para banco de exámenes oficiales (Ola B1).

Tablas para exámenes oficiales de convocatorias + vinculación a artículos.
"""

from __future__ import annotations

import sqlite3


CREATE_EXAMBANK_SQL = """
-- Exámenes oficiales (convocatorias, bloques, fases)
CREATE TABLE IF NOT EXISTS exam_papers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    oposicion_id INTEGER,
    convocatoria TEXT NOT NULL,           -- "2024/2025", "2023/2024"
    anio INTEGER NOT NULL,                -- 2024, 2025
    bloque TEXT,                          -- "Bloque 1", "Bloque 2"
    fase TEXT,                            -- "OPE", "Proceso de estabilización"
    fuente_oficial_url TEXT,              -- URL del DOGV, BOE, etc.
    fuente_path TEXT,                     -- Ruta local del PDF/DOC original
    answer_key_version TEXT,              -- "oficial_2025", "provisional"
    estado TEXT NOT NULL DEFAULT 'activo', -- activo|retirado|anulado
    validation_status TEXT NOT NULL DEFAULT 'pendiente_de_validacion',
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_exam_papers_convocatoria
    ON exam_papers(convocatoria, anio);

CREATE INDEX IF NOT EXISTS idx_exam_papers_oposicion
    ON exam_papers(oposicion_id, convocatoria);

-- Preguntas de un examen
CREATE TABLE IF NOT EXISTS exam_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_paper_id INTEGER NOT NULL REFERENCES exam_papers(id) ON DELETE CASCADE,
    numero INTEGER NOT NULL,              -- 1, 2, 3, ...
    enunciado TEXT NOT NULL,              -- Texto completo de la pregunta
    es_reserva INTEGER NOT NULL DEFAULT 0,
    respuesta_oficial TEXT,               -- "A", "B", "C", "D" (o NULL si anulada)
    anulada INTEGER NOT NULL DEFAULT 0,
    motivo_anulacion TEXT,                -- Motivo si es anulada
    validation_status TEXT NOT NULL DEFAULT 'pendiente_de_validacion',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(exam_paper_id, numero)
);

CREATE INDEX IF NOT EXISTS idx_exam_questions_paper
    ON exam_questions(exam_paper_id, numero);

CREATE INDEX IF NOT EXISTS idx_exam_questions_status
    ON exam_questions(validation_status, exam_paper_id);

-- Opciones de respuesta
CREATE TABLE IF NOT EXISTS exam_question_options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_question_id INTEGER NOT NULL REFERENCES exam_questions(id) ON DELETE CASCADE,
    letra TEXT NOT NULL,                  -- "A", "B", "C", "D"
    texto TEXT NOT NULL,                  -- Texto de la opción
    es_correcta INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(exam_question_id, letra)
);

CREATE INDEX IF NOT EXISTS idx_exam_question_options_question
    ON exam_question_options(exam_question_id);

-- Vinculación pregunta → artículo → ley → tema
CREATE TABLE IF NOT EXISTS exam_question_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_question_id INTEGER NOT NULL REFERENCES exam_questions(id) ON DELETE CASCADE,
    topic_id INTEGER REFERENCES topics(id) ON DELETE SET NULL,
    law_id INTEGER REFERENCES laws(id) ON DELETE SET NULL,
    article_id INTEGER REFERENCES articles(id) ON DELETE SET NULL,
    tipo_relacion TEXT,                   -- "cita_directa", "aplicacion", "contextual"
    mapping_basis TEXT NOT NULL,          -- "oficial", "curador", "semantica"
    confianza REAL NOT NULL DEFAULT 1.0 CHECK(confianza BETWEEN 0.0 AND 1.0),
    validation_status TEXT NOT NULL DEFAULT 'pendiente_de_validacion',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_exam_question_links_question
    ON exam_question_links(exam_question_id);

CREATE INDEX IF NOT EXISTS idx_exam_question_links_article
    ON exam_question_links(article_id);

CREATE INDEX IF NOT EXISTS idx_exam_question_links_topic
    ON exam_question_links(topic_id);

CREATE INDEX IF NOT EXISTS idx_exam_question_links_validation
    ON exam_question_links(validation_status, exam_question_id);
"""


def apply_exambank_schema(conn: sqlite3.Connection) -> None:
    """Crear tablas de banco de exámenes si no existen."""
    conn.executescript(CREATE_EXAMBANK_SQL)


def exambank_tables_exist(conn: sqlite3.Connection) -> bool:
    """Comprobar si las tablas de exambank existen."""
    tables = {"exam_papers", "exam_questions", "exam_question_options", "exam_question_links"}
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

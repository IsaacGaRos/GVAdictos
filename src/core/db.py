from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from src.core.paths import DB_PATH, ensure_runtime_dirs


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    ensure_runtime_dirs()
    conn = sqlite3.connect(db_path)
    conn.row_factory = lambda cur, row: dict(zip([col[0] for col in cur.description], row))
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path = DB_PATH) -> None:
    with connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS laws (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                source_path TEXT NOT NULL,
                source_hash TEXT NOT NULL,
                imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                validation_status TEXT NOT NULL DEFAULT 'pendiente_de_validacion',
                UNIQUE(name, source_hash)
            );

            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                law_id INTEGER NOT NULL REFERENCES laws(id) ON DELETE CASCADE,
                article_ref TEXT NOT NULL,
                title TEXT,
                chapter TEXT,
                section TEXT,
                text TEXT NOT NULL,
                topic TEXT,
                tags TEXT,
                source TEXT NOT NULL,
                original_hash TEXT NOT NULL,
                imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                validation_status TEXT NOT NULL DEFAULT 'pendiente_de_validacion',
                estimated_weight REAL NOT NULL DEFAULT 1.0
            );

            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                law_id INTEGER,
                article_id INTEGER,
                norma TEXT NOT NULL,
                articulo TEXT NOT NULL,
                tema TEXT,
                enunciado TEXT NOT NULL,
                opcion_a TEXT NOT NULL,
                opcion_b TEXT NOT NULL,
                opcion_c TEXT NOT NULL,
                opcion_d TEXT NOT NULL,
                respuesta_correcta TEXT NOT NULL CHECK(respuesta_correcta IN ('A','B','C','D')),
                explicacion TEXT NOT NULL,
                fuente TEXT NOT NULL,
                dificultad TEXT NOT NULL DEFAULT 'media',
                etiquetas TEXT,
                requiere_revision INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(law_id) REFERENCES laws(id) ON DELETE SET NULL,
                FOREIGN KEY(article_id) REFERENCES articles(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
                attempted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                respuesta_usuario TEXT NOT NULL,
                respuesta_correcta TEXT NOT NULL,
                acierto INTEGER NOT NULL,
                tiempo_respuesta REAL,
                causa_error TEXT,
                comentario TEXT
            );

            CREATE TABLE IF NOT EXISTS study_annotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,
                article_id INTEGER REFERENCES articles(id) ON DELETE SET NULL,
                annotation_type TEXT NOT NULL CHECK(annotation_type IN ('note', 'highlight', 'doubt', 'bookmark')),
                selected_text TEXT,
                manual_reference TEXT,
                note_text TEXT,
                color TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CHECK(topic_id IS NOT NULL OR article_id IS NOT NULL)
            );

            CREATE INDEX IF NOT EXISTS idx_study_annotations_topic
                ON study_annotations(topic_id, updated_at);

            CREATE INDEX IF NOT EXISTS idx_study_annotations_article
                ON study_annotations(article_id, updated_at);

            CREATE TABLE IF NOT EXISTS source_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_kind TEXT NOT NULL,
                external_id TEXT,
                title TEXT NOT NULL,
                path TEXT NOT NULL,
                mime_type TEXT,
                url TEXT,
                created_time TEXT,
                modified_time TEXT,
                priority TEXT NOT NULL DEFAULT 'media',
                status TEXT NOT NULL DEFAULT 'catalogado',
                legal_status TEXT NOT NULL DEFAULT 'pendiente_de_validacion',
                notes TEXT,
                cataloged_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_kind, external_id)
            );

            CREATE TABLE IF NOT EXISTS source_update_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_document_id INTEGER NOT NULL REFERENCES source_documents(id) ON DELETE CASCADE,
                checked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                url TEXT NOT NULL,
                status TEXT NOT NULL,
                content_hash TEXT,
                previous_hash TEXT,
                changed INTEGER NOT NULL DEFAULT 0,
                local_path TEXT,
                error TEXT
            );

            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drive_topic_number INTEGER NOT NULL UNIQUE,
                topic_number INTEGER NOT NULL,
                part TEXT NOT NULL CHECK(part IN ('general', 'especial')),
                section TEXT NOT NULL,
                official_text TEXT NOT NULL,
                normative_refs_raw TEXT,
                validation_status TEXT NOT NULL DEFAULT 'pendiente_de_validacion',
                notes TEXT,
                imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS topic_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
                law_id INTEGER REFERENCES laws(id) ON DELETE SET NULL,
                article_id INTEGER REFERENCES articles(id) ON DELETE SET NULL,
                normative_reference TEXT NOT NULL,
                coverage_status TEXT NOT NULL DEFAULT 'pendiente_de_validacion',
                mapping_basis TEXT NOT NULL DEFAULT 'pendiente_de_validacion',
                priority TEXT NOT NULL DEFAULT 'media',
                validation_status TEXT NOT NULL DEFAULT 'pendiente_de_validacion',
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(topic_id, law_id, article_id, normative_reference, mapping_basis)
            );

            CREATE TABLE IF NOT EXISTS topic_validation_findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
                finding_type TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'media',
                status TEXT NOT NULL DEFAULT 'abierto',
                description TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(topic_id, finding_type, description)
            );
            """
        )


def fetch_all(query: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(query, tuple(params)).fetchall()


def fetch_one(query: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute(query, tuple(params)).fetchone()

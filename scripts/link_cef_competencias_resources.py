"""Vincula el temario CEF (material de academia) a los temas de competencias.

Contexto:
  Los temas PE-51..PE-60 (competencias sectoriales de la Generalitat) se estudian
  del temario del CEF, que desarrolla cada materia mas alla del art. 49 EACV. Los
  PDF estan catalogados en source_documents (Competencias-51.pdf .. Competencias-60.pdf,
  source_kind=google_drive, legal_status=pendiente_de_validacion).

  Este script crea una tabla de ENLACE topic <-> source_document para registrar el
  material de academia como recurso de estudio AUXILIAR, manteniendolo separado de la
  normativa oficial (topic_sources). NO es fuente juridica definitiva: queda marcado
  como pendiente_de_validacion hasta contraste con fuente oficial.

Reglas respetadas:
  - NO toca topic_sources (la regla de IDs protegidos {67,69,70} se refiere a esa tabla;
    aqui solo se crea una tabla nueva y se enlazan recursos, sin alterar mappings).
  - NO modifica articles, parser, importer ni normalizacion.
  - Backup antes de cualquier escritura. Dry-run por defecto; escribe con --apply.
  - Idempotente: re-ejecutar reemplaza solo los enlaces propios (resource_kind dado).

Pendiente (requiere acceso a Drive, no operativo ahora):
  - Extraer texto de cada PDF y contrastar que las normas citadas esten vigentes.
  - Tras contraste, pasar validation_status a validado_* segun corresponda.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "db" / "gvadicto.sqlite"

RESOURCE_KIND = "temario_academia_cef"
RELATION = "tema_principal"
VALIDATION_STATUS = "pendiente_de_validacion"
NOTE = (
    "Temario CEF 2026 (material de academia, NO fuente juridica oficial). "
    "Recurso de estudio auxiliar; contraste de actualizacion con fuente oficial "
    "pendiente de acceso a Google Drive."
)

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS topic_study_resources (
    id INTEGER PRIMARY KEY,
    topic_id INTEGER NOT NULL,
    source_document_id INTEGER NOT NULL,
    resource_kind TEXT NOT NULL,
    relation TEXT,
    validation_status TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(topic_id, source_document_id, resource_kind),
    FOREIGN KEY(topic_id) REFERENCES topics(id),
    FOREIGN KEY(source_document_id) REFERENCES source_documents(id)
)
"""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Link CEF competencias PDFs to topics.")
    p.add_argument("--apply", action="store_true",
                   help="Write changes. Without this flag, dry-run only.")
    return p


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def make_backup() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = ROOT / "db" / f"gvadicto.backup_pre_cef_resources_{ts}.sqlite"
    shutil.copy2(DB, dst)
    return dst


def resolve_links(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Match Competencias-NN.pdf in source_documents to topic esp-NN."""
    docs = conn.execute(
        "SELECT id, title FROM source_documents WHERE title LIKE 'Competencias-%'"
    ).fetchall()
    if not docs:
        raise SystemExit("ABORT: no hay PDFs 'Competencias-*' en source_documents.")

    errors: list[str] = []
    links: list[dict[str, Any]] = []
    for d in docs:
        m = re.match(r"Competencias-(\d+)\.pdf", d["title"])
        if not m:
            errors.append(f"titulo no parseable: {d['title']}")
            continue
        num = m.group(1)
        topic = conn.execute(
            "SELECT id FROM topics WHERE part='especial' AND topic_number=?", (num,)
        ).fetchone()
        if not topic:
            errors.append(f"no existe topic esp-{num} para {d['title']}")
            continue
        links.append({
            "topic_id": int(topic["id"]),
            "source_document_id": int(d["id"]),
            "title": d["title"],
            "topic_number": num,
        })

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        raise SystemExit("ABORT: errores al resolver enlaces (ver arriba).")
    return sorted(links, key=lambda x: int(x["topic_number"]))


def main() -> None:
    args = build_parser().parse_args()
    conn = connect()
    try:
        print("=== Preflight ===")
        # Table may not exist yet on dry-run; create a temp view of intent only.
        table_exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='topic_study_resources'"
        ).fetchone() is not None
        print(f"  Tabla topic_study_resources existe: {table_exists}")

        links = resolve_links(conn)
        print(f"  Enlaces a crear: {len(links)}")
        for l in links:
            print(f"    {l['title']:>20} -> topic_id={l['topic_id']} (esp-{l['topic_number']})")

        if not args.apply:
            print("\n=== DRY-RUN completado (sin escritura). Usa --apply para escribir. ===")
            return

        backup = make_backup()
        print(f"\n  Backup creado: {backup.name}")

        conn.execute(CREATE_TABLE)
        # Idempotent: remove our own links for these topics before reinserting
        topic_ids = [l["topic_id"] for l in links]
        conn.execute(
            f"DELETE FROM topic_study_resources WHERE resource_kind=? AND topic_id IN "
            f"({','.join('?'*len(topic_ids))})",
            (RESOURCE_KIND, *topic_ids),
        )
        now = datetime.now().isoformat(timespec="seconds")
        inserted = 0
        for l in links:
            conn.execute(
                """
                INSERT INTO topic_study_resources(
                    topic_id, source_document_id, resource_kind, relation,
                    validation_status, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (l["topic_id"], l["source_document_id"], RESOURCE_KIND, RELATION,
                 VALIDATION_STATUS, NOTE, now, now),
            )
            inserted += 1
        conn.commit()

        total = conn.execute("SELECT COUNT(*) FROM topic_study_resources").fetchone()[0]
        print(f"\n  Enlaces insertados: {inserted}")
        print(f"  Total en topic_study_resources: {total}")
        print("\n=== APPLY completado con exito. ===")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

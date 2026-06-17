from __future__ import annotations

import csv
from pathlib import Path

from src.core.db import connect, init_db


CATALOG_FIELDS = [
    "source_kind",
    "external_id",
    "title",
    "path",
    "mime_type",
    "url",
    "created_time",
    "modified_time",
    "priority",
    "status",
    "legal_status",
    "notes",
]


def upsert_source_document(row: dict[str, str]) -> None:
    init_db()
    values = {field: row.get(field, "") for field in CATALOG_FIELDS}
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO source_documents(
                source_kind, external_id, title, path, mime_type, url,
                created_time, modified_time, priority, status, legal_status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_kind, external_id) DO UPDATE SET
                title = excluded.title,
                path = excluded.path,
                mime_type = excluded.mime_type,
                url = excluded.url,
                created_time = excluded.created_time,
                modified_time = excluded.modified_time,
                priority = excluded.priority,
                status = excluded.status,
                legal_status = excluded.legal_status,
                notes = excluded.notes
            """,
            tuple(values[field] for field in CATALOG_FIELDS),
        )


def import_source_manifest(path: Path) -> int:
    count = 0
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            upsert_source_document(row)
            count += 1
    return count


def list_source_documents() -> list:
    init_db()
    with connect() as conn:
        return conn.execute(
            """
            SELECT *
            FROM source_documents
            ORDER BY
                CASE priority WHEN 'alta' THEN 1 WHEN 'media' THEN 2 ELSE 3 END,
                path,
                title
            """
        ).fetchall()

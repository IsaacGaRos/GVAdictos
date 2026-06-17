from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.db import connect, init_db


ROOT = Path(__file__).resolve().parents[1]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_url(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "GVAdicto/0.1"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def resolve_local_path(path_value: str) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else ROOT / path


def latest_hash(conn, source_document_id: int) -> str | None:
    row = conn.execute(
        """
        SELECT content_hash
        FROM source_update_checks
        WHERE source_document_id = ? AND content_hash IS NOT NULL
        ORDER BY checked_at DESC, id DESC
        LIMIT 1
        """,
        (source_document_id,),
    ).fetchone()
    return row["content_hash"] if row else None


def check_sources(update_files: bool = False, source_kind: str | None = None) -> dict[str, int]:
    init_db()
    summary = {"checked": 0, "changed": 0, "errors": 0, "updated_files": 0}
    query = "SELECT * FROM source_documents WHERE url IS NOT NULL AND url != ''"
    params: list[str] = []
    if source_kind:
        query += " AND source_kind = ?"
        params.append(source_kind)

    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
        for row in rows:
            summary["checked"] += 1
            previous = latest_hash(conn, row["id"])
            content_hash = None
            changed = 0
            status = "ok"
            error = None
            try:
                data = fetch_url(row["url"])
                content_hash = sha256_bytes(data)
                changed = 1 if previous and previous != content_hash else 0
                if changed:
                    summary["changed"] += 1
                if update_files and row["path"] and not row["source_kind"].startswith("google"):
                    local_path = resolve_local_path(row["path"])
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    if changed or not local_path.exists():
                        local_path.write_bytes(data)
                        summary["updated_files"] += 1
            except Exception as exc:
                status = "error"
                error = str(exc)
                summary["errors"] += 1

            conn.execute(
                """
                INSERT INTO source_update_checks(
                    source_document_id, url, status, content_hash,
                    previous_hash, changed, local_path, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    row["url"],
                    status,
                    content_hash,
                    previous,
                    changed,
                    row["path"],
                    error,
                ),
            )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Comprueba cambios en fuentes oficiales catalogadas.")
    parser.add_argument("--update-files", action="store_true", help="Actualiza copias locales si cambia el contenido.")
    parser.add_argument("--source-kind", help="Filtra por source_kind, por ejemplo boe_consolidado.")
    args = parser.parse_args()
    print(check_sources(update_files=args.update_files, source_kind=args.source_kind))


if __name__ == "__main__":
    main()

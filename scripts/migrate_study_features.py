from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.paths import DB_PATH
from src.study.schema import (
    CREATE_STUDY_FEATURES_SQL,
    apply_study_schema,
    missing_base_tables,
    missing_study_tables,
)


REPORTS_DIR = ROOT / "reports"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def file_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def connect_readonly(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def connect_writable(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_backup(db_path: Path) -> Path:
    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{db_path.stem}_study_features_{timestamp()}{db_path.suffix}"
    shutil.copy2(db_path, backup_path)
    return backup_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create study feature tables; dry-run by default.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Inspect and report only.")
    mode.add_argument("--apply", action="store_true", help="Apply schema changes after backup.")
    parser.add_argument("--db-path", type=Path, default=DB_PATH, help="SQLite DB path; defaults to db/gvadicto.sqlite.")
    return parser


def write_report(payload: dict[str, object]) -> tuple[Path, Path]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    suffix = "apply" if payload["mode"] == "apply" else "dry_run"
    json_path = REPORTS_DIR / f"study_features_migration_{suffix}.json"
    md_path = REPORTS_DIR / f"study_features_migration_{suffix}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Study features migration",
        "",
        f"- Checked at: {payload['checked_at']}",
        f"- Mode: {payload['mode']}",
        f"- DB path: `{payload['db_path']}`",
        f"- Applied: {payload['applied']}",
        f"- Safe to apply: {payload['safe_to_apply']}",
        f"- DB unchanged: {payload['db_unchanged']}",
        f"- DB hash before: `{payload['db_hash_before']}`",
        f"- DB hash after: `{payload['db_hash_after']}`",
        f"- Backup: `{payload['backup_path'] or 'none'}`",
        f"- Missing base before: {', '.join(payload['missing_base_before']) if payload['missing_base_before'] else 'none'}",
        f"- Missing base after: {', '.join(payload['missing_base_after']) if payload['missing_base_after'] else 'none'}",
        f"- Missing before: {', '.join(payload['missing_before']) if payload['missing_before'] else 'none'}",
        f"- Missing after: {', '.join(payload['missing_after']) if payload['missing_after'] else 'none'}",
        "",
        "## SQL planned",
        "",
        "```sql",
        str(payload["sql"]).strip(),
        "```",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path, json_path


def main() -> int:
    args = build_parser().parse_args()
    db_path = args.db_path.resolve()
    dry_run = not args.apply
    checked_at = now_iso()
    db_hash_before = file_sha256(db_path)
    backup_path: Path | None = None

    with connect_readonly(db_path) as conn:
        missing_base_before = missing_base_tables(conn)
        missing_before = missing_study_tables(conn)

    base_ready = not missing_base_before
    applied = False
    if args.apply and base_ready:
        backup_path = create_backup(db_path)
        with connect_writable(db_path) as conn:
            apply_study_schema(conn)
            conn.commit()
        applied = True

    with connect_readonly(db_path) as conn:
        missing_base_after = missing_base_tables(conn)
        missing_after = missing_study_tables(conn)

    db_hash_after = file_sha256(db_path)
    payload = {
        "checked_at": checked_at,
        "mode": "dry-run" if dry_run else "apply",
        "applied": applied,
        "db_path": str(db_path),
        "db_hash_before": db_hash_before,
        "db_hash_after": db_hash_after,
        "db_unchanged": db_hash_before == db_hash_after,
        "missing_base_before": missing_base_before,
        "missing_base_after": missing_base_after,
        "missing_before": missing_before,
        "missing_after": missing_after,
        "safe_to_apply": base_ready,
        "backup_path": str(backup_path) if backup_path else "",
        "sql": CREATE_STUDY_FEATURES_SQL,
    }
    md_path, json_path = write_report(payload)

    print(f"Mode: {payload['mode']}")
    print(f"DB path: {db_path}")
    print(f"Applied: {applied}")
    print(f"Missing base before: {missing_base_before or 'none'}")
    print(f"Missing before: {missing_before or 'none'}")
    print(f"Missing after: {missing_after or 'none'}")
    print(f"DB unchanged: {payload['db_unchanged']}")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    if dry_run and missing_before:
        print("Dry-run only; no schema changes were applied.")
    if missing_base_before:
        print("ERROR: missing required base tables: " + ", ".join(missing_base_before))
        return 2
    if args.apply and not applied:
        print("ERROR: apply requested but migration was not applied.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

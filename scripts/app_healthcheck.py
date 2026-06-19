from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "db" / "gvadicto.sqlite"
REPORTS_DIR = ROOT / "reports"

ESSENTIAL_TABLES = [
    "topics",
    "laws",
    "articles",
    "topic_sources",
    "questions",
    "source_documents",
]


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def file_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def connect_readonly() -> sqlite3.Connection:
    conn = sqlite3.connect(f"{DB_PATH.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    return conn


def run_script(script: str, timeout: int = 180) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, script],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return {
        "command": f"{sys.executable} {script}",
        "exit_code": completed.returncode,
        "ok": completed.returncode == 0,
        "stdout_tail": completed.stdout.splitlines()[-40:],
        "stderr_tail": completed.stderr.splitlines()[-40:],
    }


def http_check(url: str, timeout: float = 5.0) -> dict[str, object]:
    if not url:
        return {"enabled": False, "ok": None, "status": None, "error": ""}
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return {
                "enabled": True,
                "ok": 200 <= response.status < 500,
                "status": response.status,
                "reason": response.reason,
                "error": "",
            }
    except urllib.error.HTTPError as exc:
        return {"enabled": True, "ok": True, "status": exc.code, "reason": exc.reason, "error": ""}
    except Exception as exc:
        return {"enabled": True, "ok": False, "status": None, "reason": "", "error": str(exc)}


def database_snapshot() -> dict[str, object]:
    with connect_readonly() as conn:
        table_rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        existing_tables = {row["name"] for row in table_rows}
        missing_tables = [table for table in ESSENTIAL_TABLES if table not in existing_tables]
        counts = {}
        for table in ESSENTIAL_TABLES:
            if table in existing_tables:
                counts[table] = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        mapping_rows = 0
        fine_mapping_rows = 0
        fine_mapping_topics = 0
        if "topic_sources" in existing_tables:
            mapping_rows = int(conn.execute("SELECT COUNT(*) FROM topic_sources").fetchone()[0])
            fine_mapping_rows = int(
                conn.execute("SELECT COUNT(*) FROM topic_sources WHERE article_id IS NOT NULL").fetchone()[0]
            )
            fine_mapping_topics = int(
                conn.execute(
                    "SELECT COUNT(DISTINCT topic_id) FROM topic_sources WHERE article_id IS NOT NULL"
                ).fetchone()[0]
            )
        return {
            "db_path": str(DB_PATH),
            "accessible": True,
            "missing_tables": missing_tables,
            "counts": counts,
            "mapping_rows": mapping_rows,
            "fine_mapping_rows": fine_mapping_rows,
            "fine_mapping_topics": fine_mapping_topics,
        }


def write_reports(payload: dict[str, object]) -> tuple[Path, Path]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_DIR / "app_healthcheck.json"
    md_path = REPORTS_DIR / "app_healthcheck.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    db = payload["database"]
    checks = payload["checks"]
    http = payload["http"]
    lines = [
        "# App healthcheck",
        "",
        f"- Checked at: {payload['checked_at']}",
        f"- Overall ok: {payload['ok']}",
        f"- DB unchanged during check: {payload['db_unchanged']}",
        f"- DB hash before: `{payload['db_hash_before']}`",
        f"- DB hash after: `{payload['db_hash_after']}`",
        "",
        "## Database",
        "",
        f"- Accessible: {db['accessible']}",
        f"- Missing tables: {', '.join(db['missing_tables']) if db['missing_tables'] else 'none'}",
        f"- Topics: {db['counts'].get('topics', 'n/a')}",
        f"- Laws: {db['counts'].get('laws', 'n/a')}",
        f"- Articles: {db['counts'].get('articles', 'n/a')}",
        f"- Topic mappings: {db['mapping_rows']}",
        f"- Fine mapping rows: {db['fine_mapping_rows']}",
        f"- Fine mapping topics: {db['fine_mapping_topics']}",
        "",
        "## Script checks",
        "",
    ]
    for name, check in checks.items():
        lines.append(f"- {name}: ok={check['ok']} exit_code={check['exit_code']}")
    lines.extend(
        [
            "",
            "## HTTP",
            "",
            f"- Enabled: {http['enabled']}",
            f"- OK: {http['ok']}",
            f"- Status: {http['status']}",
            f"- Error: {http['error']}",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path, json_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only healthcheck for the GVAdictos app stack.")
    parser.add_argument("--url", default="", help="Optional app URL to probe, e.g. http://localhost:8501")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    checked_at = now_iso()
    db_hash_before = file_sha256(DB_PATH)
    failures: list[str] = []

    try:
        db = database_snapshot()
    except Exception as exc:
        db = {
            "db_path": str(DB_PATH),
            "accessible": False,
            "missing_tables": ESSENTIAL_TABLES,
            "counts": {},
            "mapping_rows": 0,
            "fine_mapping_rows": 0,
            "fine_mapping_topics": 0,
            "error": str(exc),
        }
        failures.append(f"database: {exc}")

    if db.get("missing_tables"):
        failures.append("missing_tables: " + ",".join(db["missing_tables"]))

    checks = {
        "validate_article_quality": run_script("scripts/validate_article_quality.py"),
        "report_mapping_status": run_script("scripts/report_mapping_status.py"),
    }
    for name, check in checks.items():
        if not check["ok"]:
            failures.append(f"{name}: exit_code={check['exit_code']}")

    http = http_check(args.url)
    if http["enabled"] and not http["ok"]:
        failures.append(f"http: {http['error']}")

    db_hash_after = file_sha256(DB_PATH)
    db_unchanged = db_hash_before == db_hash_after
    if not db_unchanged:
        failures.append("db_hash_changed")

    payload = {
        "checked_at": checked_at,
        "ok": not failures,
        "failures": failures,
        "db_hash_before": db_hash_before,
        "db_hash_after": db_hash_after,
        "db_unchanged": db_unchanged,
        "database": db,
        "checks": checks,
        "http": http,
    }
    md_path, json_path = write_reports(payload)

    print(f"Healthcheck ok: {payload['ok']}")
    print(f"DB unchanged: {db_unchanged}")
    print(f"Topics: {db['counts'].get('topics', 'n/a')}")
    print(f"Laws: {db['counts'].get('laws', 'n/a')}")
    print(f"Articles: {db['counts'].get('articles', 'n/a')}")
    print(f"Topic mappings: {db['mapping_rows']}")
    print(f"Fine mapping rows: {db['fine_mapping_rows']}")
    print(f"validate_article_quality: {checks['validate_article_quality']['ok']}")
    print(f"report_mapping_status: {checks['report_mapping_status']['ok']}")
    if http["enabled"]:
        print(f"HTTP {args.url}: ok={http['ok']} status={http['status']} error={http['error']}")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    if failures:
        print("Failures:")
        for failure in failures:
            print(f"- {failure}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

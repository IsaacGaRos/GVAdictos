from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.paths import DB_PATH
from src.study.schema import STUDY_TABLES, existing_study_tables, schema_status


REPORTS_DIR = ROOT / "reports"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def file_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def connect_readonly(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    return conn


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        ).fetchone()
        is not None
    )


def table_count(conn: sqlite3.Connection, table: str) -> int | None:
    if not table_exists(conn, table):
        return None
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def scalar(conn: sqlite3.Connection, query: str, params: tuple = ()) -> object:
    row = conn.execute(query, params).fetchone()
    return row[0] if row else None


def referential_issues(conn: sqlite3.Connection) -> dict[str, int | None]:
    checks = {
        "notes_missing_articles": ("study_article_notes", "article_id", "articles"),
        "highlights_missing_articles": ("study_highlights", "article_id", "articles"),
        "progress_missing_articles": ("study_progress", "article_id", "articles"),
        "progress_missing_topics": ("study_progress", "topic_id", "topics"),
        "marks_missing_articles": ("study_marks", "article_id", "articles"),
        "marks_missing_topics": ("study_marks", "topic_id", "topics"),
        "reviews_missing_articles": ("study_last_reviews", "article_id", "articles"),
        "reviews_missing_topics": ("study_last_reviews", "topic_id", "topics"),
    }
    result: dict[str, int | None] = {}
    for name, (table, column, target) in checks.items():
        if not table_exists(conn, table) or not table_exists(conn, target):
            result[name] = None
            continue
        result[name] = int(
            conn.execute(
                f"""
                SELECT COUNT(*)
                FROM {table}
                WHERE {column} IS NOT NULL
                  AND {column} NOT IN (SELECT id FROM {target})
                """
            ).fetchone()[0]
        )
    return result


def progress_average_by_topic(conn: sqlite3.Connection) -> list[dict[str, object]]:
    if not table_exists(conn, "study_progress"):
        return []
    if table_exists(conn, "topic_sources"):
        rows = conn.execute(
            """
            SELECT
                COALESCE(sp.topic_id, ts.topic_id) AS topic_id,
                AVG(sp.completion_percent) AS average_completion,
                COUNT(*) AS progress_rows
            FROM study_progress sp
            LEFT JOIN topic_sources ts ON ts.article_id = sp.article_id
            WHERE COALESCE(sp.topic_id, ts.topic_id) IS NOT NULL
            GROUP BY COALESCE(sp.topic_id, ts.topic_id)
            ORDER BY COALESCE(sp.topic_id, ts.topic_id)
            LIMIT 25
            """
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT
                topic_id,
                AVG(completion_percent) AS average_completion,
                COUNT(*) AS progress_rows
            FROM study_progress
            WHERE topic_id IS NOT NULL
            GROUP BY topic_id
            ORDER BY topic_id
            LIMIT 25
            """
        ).fetchall()
    return [
        {
            "topic_id": row["topic_id"],
            "average_completion": round(float(row["average_completion"]), 2),
            "progress_rows": row["progress_rows"],
        }
        for row in rows
    ]


def latest_review(conn: sqlite3.Connection) -> dict[str, object] | None:
    if not table_exists(conn, "study_last_reviews"):
        return None
    row = conn.execute(
        """
        SELECT *
        FROM study_last_reviews
        ORDER BY last_reviewed_at DESC, id DESC
        LIMIT 1
        """
    ).fetchone()
    return dict(row) if row else None


def write_reports(payload: dict[str, object]) -> tuple[Path, Path]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_DIR / "study_features_status.json"
    md_path = REPORTS_DIR / "study_features_status.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Study features backend status",
        "",
        f"- Checked at: {payload['checked_at']}",
        f"- DB unchanged during report: {payload['db_unchanged']}",
        f"- Ready for UI: {payload['ready_for_ui']}",
        f"- Migration status: {payload['migration_status']}",
        f"- Missing base tables: {', '.join(payload['missing_base_tables']) if payload['missing_base_tables'] else 'none'}",
        f"- Existing study tables: {', '.join(payload['existing_tables']) if payload['existing_tables'] else 'none'}",
        f"- Missing study feature tables: {', '.join(payload['missing_tables']) if payload['missing_tables'] else 'none'}",
        "",
        "## Counts",
        "",
    ]
    for table, count in payload["counts"].items():
        lines.append(f"- {table}: {count if count is not None else 'missing'}")
    lines.extend(
        [
            f"- doubt marks: {payload['doubt_marks'] if payload['doubt_marks'] is not None else 'missing'}",
            f"- important marks: {payload['important_marks'] if payload['important_marks'] is not None else 'missing'}",
            f"- latest review: {payload['latest_review']['last_reviewed_at'] if payload['latest_review'] else 'none'}",
            "",
            "## Referential integrity",
            "",
        ]
    )
    for name, count in payload["referential_issues"].items():
        lines.append(f"- {name}: {count if count is not None else 'not checked'}")
    lines.extend(
        [
            "",
            "## Progress Average By Topic",
            "",
        ]
    )
    if payload["progress_average_by_topic"]:
        for row in payload["progress_average_by_topic"]:
            lines.append(
                f"- topic_id={row['topic_id']}: average={row['average_completion']} rows={row['progress_rows']}"
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            str(payload["recommendation"]),
            "",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path, json_path


def main() -> int:
    db_hash_before = file_sha256(DB_PATH)
    with connect_readonly() as conn:
        existing = sorted(existing_study_tables(conn))
        status = schema_status(conn)
        missing = status["missing_study_tables"]
        counts = {table: table_count(conn, table) for table in STUDY_TABLES}
        doubt_marks = (
            scalar(conn, "SELECT COUNT(*) FROM study_marks WHERE mark_type = 'doubt' AND resolved = 0")
            if table_exists(conn, "study_marks")
            else None
        )
        important_marks = (
            scalar(conn, "SELECT COUNT(*) FROM study_marks WHERE mark_type = 'important' AND resolved = 0")
            if table_exists(conn, "study_marks")
            else None
        )
        integrity = referential_issues(conn)
        progress_rows = progress_average_by_topic(conn)
        latest = latest_review(conn)
    db_hash_after = file_sha256(DB_PATH)

    ready_for_ui = bool(status["base_ready"] and status["study_ready"])
    migration_status = "applied" if status["study_ready"] else "pending"
    problems = [
        name
        for name, value in integrity.items()
        if value not in (None, 0)
    ]
    if status["missing_base_tables"]:
        problems.append("missing_base_tables")
    recommendation = (
        "Backend tables are present; UI can integrate repository/service helpers."
        if ready_for_ui
        else "Run scripts/migrate_study_features.py --dry-run first; apply only after explicit approval."
    )
    payload = {
        "checked_at": now_iso(),
        "db_hash_before": db_hash_before,
        "db_hash_after": db_hash_after,
        "db_unchanged": db_hash_before == db_hash_after,
        "ready_for_ui": ready_for_ui,
        "migration_status": migration_status,
        "existing_tables": existing,
        "missing_tables": missing,
        "missing_base_tables": status["missing_base_tables"],
        "counts": counts,
        "doubt_marks": doubt_marks,
        "important_marks": important_marks,
        "progress_average_by_topic": progress_rows,
        "latest_review": latest,
        "referential_issues": integrity,
        "problems": problems,
        "recommendation": recommendation,
    }
    md_path, json_path = write_reports(payload)
    print(f"Ready for UI: {ready_for_ui}")
    print(f"Migration status: {migration_status}")
    print(f"Missing tables: {missing or 'none'}")
    print(f"DB unchanged: {payload['db_unchanged']}")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

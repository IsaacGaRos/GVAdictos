from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mapping_tools import DB_PATH, REVIEW_COLUMNS, connect_readonly, file_sha256


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"


FIELDNAMES = [
    "topic_id",
    *REVIEW_COLUMNS[:7],
    "normative_reference",
    "candidate_article_count",
    "current_linked_article_ids",
    *REVIEW_COLUMNS[7:],
    "mapping_basis",
]


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def write_case(path: Path, row: dict[str, object]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerow({name: row.get(name, "") for name in FIELDNAMES})


def base_row() -> dict[str, object]:
    with connect_readonly() as conn:
        row = conn.execute(
            """
            SELECT
                t.id AS topic_id,
                t.part,
                t.topic_number,
                t.official_text AS topic_title,
                ts.law_id,
                l.name AS law_title,
                ts.normative_reference
            FROM topic_sources ts
            JOIN topics t ON t.id = ts.topic_id
            JOIN laws l ON l.id = ts.law_id
            WHERE ts.law_id IS NOT NULL
            ORDER BY t.id, ts.law_id
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        raise RuntimeError("No topic_sources rows available for tests.")
    return {
        "topic_id": row["topic_id"],
        "part": row["part"],
        "topic_number": row["topic_number"],
        "topic_title": row["topic_title"],
        "law_id": row["law_id"],
        "law_title": row["law_title"],
        "current_status": "test",
        "candidate_article_refs": "",
        "normative_reference": row["normative_reference"],
        "candidate_article_count": "",
        "current_linked_article_ids": "",
        "autentica_reference": "Autentica test reference",
        "confidence": "test",
        "review_notes": "Synthetic validator test row.",
        "approved": "1",
        "article_ids_to_apply": "",
        "mapping_basis": "test_mapping_tools",
    }


def max_article_id() -> int:
    with connect_readonly() as conn:
        return int(conn.execute("SELECT MAX(id) AS max_id FROM articles").fetchone()["max_id"])


def wrong_law_article_id(law_id: int) -> int:
    with connect_readonly() as conn:
        row = conn.execute(
            "SELECT id FROM articles WHERE law_id != ? ORDER BY id LIMIT 1",
            (law_id,),
        ).fetchone()
    if row is None:
        raise RuntimeError("No article from another law available for tests.")
    return int(row["id"])


def protected_overwrite_case() -> dict[str, object] | None:
    with connect_readonly() as conn:
        protected = conn.execute(
            """
            SELECT topic_id, law_id, GROUP_CONCAT(article_id) AS ids
            FROM topic_sources
            WHERE article_id IS NOT NULL
              AND mapping_basis = 'validacion_articulos_codex_2026_06_18'
            GROUP BY topic_id, law_id
            LIMIT 1
            """
        ).fetchone()
        if protected is None:
            return None
        protected_ids = {int(value) for value in protected["ids"].split(",") if value}
        placeholders = ",".join("?" for _ in protected_ids)
        alt = conn.execute(
            f"""
            SELECT id
            FROM articles
            WHERE law_id = ?
              AND id NOT IN ({placeholders})
            ORDER BY id
            LIMIT 1
            """,
            (protected["law_id"], *protected_ids),
        ).fetchone()
        if alt is None:
            return None
        topic = conn.execute(
            "SELECT part, topic_number, official_text FROM topics WHERE id = ?",
            (protected["topic_id"],),
        ).fetchone()
        law = conn.execute("SELECT name FROM laws WHERE id = ?", (protected["law_id"],)).fetchone()
        norm = conn.execute(
            """
            SELECT normative_reference
            FROM topic_sources
            WHERE topic_id = ? AND law_id = ?
            LIMIT 1
            """,
            (protected["topic_id"], protected["law_id"]),
        ).fetchone()

    return {
        "topic_id": protected["topic_id"],
        "part": topic["part"],
        "topic_number": topic["topic_number"],
        "topic_title": topic["official_text"],
        "law_id": protected["law_id"],
        "law_title": law["name"],
        "current_status": "mapped",
        "candidate_article_refs": "",
        "normative_reference": norm["normative_reference"],
        "candidate_article_count": "",
        "current_linked_article_ids": protected["ids"],
        "autentica_reference": "Autentica test reference",
        "confidence": "test",
        "review_notes": "Synthetic protected overwrite test row.",
        "approved": "1",
        "article_ids_to_apply": alt["id"],
        "mapping_basis": "test_mapping_tools",
    }


def expect_failure(case_name: str, csv_path: Path, expected_code: str) -> None:
    completed = run_command(["scripts/validate_mapping_review.py", str(csv_path)])
    combined = completed.stdout + completed.stderr
    if completed.returncode == 0:
        raise AssertionError(f"{case_name}: expected failure, got exit 0\n{combined}")
    if expected_code not in combined:
        raise AssertionError(f"{case_name}: expected {expected_code!r}\n{combined}")
    print(f"ok {case_name}: detected {expected_code}")


def main() -> int:
    before_hash = file_sha256(DB_PATH)
    row = base_row()

    with tempfile.TemporaryDirectory(prefix="gvadicto_mapping_tests_") as tmp:
        tmp_path = Path(tmp)

        missing = dict(row)
        missing["article_ids_to_apply"] = str(max_article_id() + 100000)
        missing_csv = tmp_path / "missing_article.csv"
        write_case(missing_csv, missing)
        expect_failure("missing article_id", missing_csv, "article_not_found")

        wrong = dict(row)
        wrong["article_ids_to_apply"] = str(wrong_law_article_id(int(row["law_id"])))
        wrong_csv = tmp_path / "wrong_law.csv"
        write_case(wrong_csv, wrong)
        expect_failure("wrong law", wrong_csv, "article_wrong_law")

        no_articles = dict(row)
        no_articles["article_ids_to_apply"] = ""
        no_articles_csv = tmp_path / "approved_without_articles.csv"
        write_case(no_articles_csv, no_articles)
        expect_failure("approved without articles", no_articles_csv, "approved_without_articles")

        protected = protected_overwrite_case()
        if protected:
            protected_csv = tmp_path / "protected_overwrite.csv"
            write_case(protected_csv, protected)
            expect_failure("protected overwrite", protected_csv, "protected_mapping_overwrite")
        else:
            print("skip protected overwrite: no suitable protected mapping found")

        dry_run = dict(row)
        dry_run["approved"] = ""
        dry_run["article_ids_to_apply"] = ""
        dry_run_csv = tmp_path / "dry_run_noop.csv"
        write_case(dry_run_csv, dry_run)
        completed = run_command(["scripts/apply_mapping_review.py", str(dry_run_csv), "--dry-run"])
        if completed.returncode != 0:
            raise AssertionError("dry-run no-op failed\n" + completed.stdout + completed.stderr)
        print("ok dry-run no-op")

    after_hash = file_sha256(DB_PATH)
    if before_hash != after_hash:
        raise AssertionError(f"DB hash changed: before={before_hash} after={after_hash}")
    print("ok DB hash unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

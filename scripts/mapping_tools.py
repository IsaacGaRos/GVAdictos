from __future__ import annotations

import csv
import hashlib
import re
import shutil
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "db" / "gvadicto.sqlite"
REPORTS_DIR = ROOT / "reports"

PROTECTED_MAPPING_BASES = {"validacion_articulos_codex_2026_06_18"}
DEFAULT_APPLY_BASIS_PREFIX = "mapping_review_aprobado"

REVIEW_COLUMNS = [
    "part",
    "topic_number",
    "topic_title",
    "law_id",
    "law_title",
    "current_status",
    "candidate_article_refs",
    "autentica_reference",
    "confidence",
    "review_notes",
    "approved",
    "article_ids_to_apply",
]

REVIEW_EXTRA_COLUMNS = [
    "topic_id",
    "normative_reference",
    "candidate_article_count",
    "current_linked_article_ids",
    "mapping_basis",
]

TRUTHY = {"1", "true", "yes", "y", "si", "s", "aprobado", "approved", "x"}
FALSY = {"", "0", "false", "no", "n", "pendiente", "pending"}


@dataclass(frozen=True)
class ValidationIssue:
    level: str
    row_number: int | None
    code: str
    message: str


@dataclass(frozen=True)
class PlannedMapping:
    row_number: int
    topic_id: int
    law_id: int
    article_id: int
    normative_reference: str
    mapping_basis: str
    source_note: str


@dataclass
class ValidationResult:
    csv_path: Path
    checked_rows: int
    planned_mappings: list[PlannedMapping]
    issues: list[ValidationIssue]
    protected_topic_law_pairs: int

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.level == "ERROR"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.level == "WARNING"]

    @property
    def ok(self) -> bool:
        return not self.errors


def ensure_reports_dir() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR


def db_uri(path: Path = DB_PATH, mode: str = "ro") -> str:
    return f"{path.resolve().as_uri()}?mode={mode}"


def connect_readonly(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_uri(db_path, "ro"), uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def connect_writable(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def file_sha256(path: Path = DB_PATH) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def create_db_backup(db_path: Path = DB_PATH) -> Path:
    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{db_path.stem}_mapping_review_{timestamp()}{db_path.suffix}"
    shutil.copy2(db_path, backup_path)
    return backup_path


def clean_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def md_escape(value: Any) -> str:
    return clean_cell(value).replace("|", "\\|")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: clean_cell(row.get(key, "")) for key in fieldnames})


def render_md_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    if not rows:
        return "_Sin filas._\n"
    header = "| " + " | ".join(label for _, label in columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, separator]
    for row in rows:
        lines.append("| " + " | ".join(md_escape(row.get(key, "")) for key, _ in columns) + " |")
    return "\n".join(lines) + "\n"


def fetch_topic_source_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            ts.id AS topic_source_id,
            ts.topic_id,
            ts.law_id,
            ts.article_id,
            ts.normative_reference,
            ts.coverage_status,
            ts.mapping_basis,
            ts.priority,
            ts.validation_status,
            ts.notes,
            t.drive_topic_number,
            t.topic_number,
            t.part,
            t.section,
            t.official_text AS topic_title,
            l.name AS law_title,
            a.article_ref,
            a.title AS article_title,
            a.law_id AS article_law_id
        FROM topic_sources ts
        JOIN topics t ON t.id = ts.topic_id
        LEFT JOIN laws l ON l.id = ts.law_id
        LEFT JOIN articles a ON a.id = ts.article_id
        ORDER BY
            CASE t.part WHEN 'general' THEN 0 ELSE 1 END,
            t.topic_number,
            COALESCE(l.name, ''),
            ts.id
        """
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_topics(conn: sqlite3.Connection) -> dict[int, dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, drive_topic_number, topic_number, part, section, official_text AS topic_title
        FROM topics
        ORDER BY CASE part WHEN 'general' THEN 0 ELSE 1 END, topic_number
        """
    ).fetchall()
    return {int(row["id"]): dict(row) for row in rows}


def fetch_laws(conn: sqlite3.Connection) -> dict[int, dict[str, Any]]:
    rows = conn.execute("SELECT id, name AS law_title FROM laws ORDER BY name").fetchall()
    return {int(row["id"]): dict(row) for row in rows}


def fetch_articles_by_law(conn: sqlite3.Connection) -> dict[int, list[dict[str, Any]]]:
    rows = conn.execute(
        """
        SELECT id, law_id, article_ref, title
        FROM articles
        ORDER BY law_id, id
        """
    ).fetchall()
    articles: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        articles[int(row["law_id"])].append(dict(row))
    return dict(articles)


def fetch_article_counts(conn: sqlite3.Connection) -> dict[int, int]:
    rows = conn.execute("SELECT law_id, COUNT(*) AS total FROM articles GROUP BY law_id").fetchall()
    return {int(row["law_id"]): int(row["total"]) for row in rows}


def _csv_list(values: set[str]) -> str:
    return "; ".join(sorted(clean_cell(value) for value in values if clean_cell(value)))


def _ids_csv(values: set[int] | list[int]) -> str:
    return ";".join(str(value) for value in sorted(set(values)))


def build_topic_law_groups(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    topics = fetch_topics(conn)
    article_counts = fetch_article_counts(conn)
    grouped: dict[tuple[int, int | None], dict[str, Any]] = {}

    for row in fetch_topic_source_rows(conn):
        key = (int(row["topic_id"]), int(row["law_id"]) if row["law_id"] is not None else None)
        group = grouped.setdefault(
            key,
            {
                "topic_id": int(row["topic_id"]),
                "drive_topic_number": row["drive_topic_number"],
                "part": row["part"],
                "section": row["section"],
                "topic_number": row["topic_number"],
                "topic_title": row["topic_title"],
                "law_id": int(row["law_id"]) if row["law_id"] is not None else None,
                "law_title": row["law_title"] or "",
                "normative_references_set": set(),
                "mapping_bases_set": set(),
                "coverage_statuses_set": set(),
                "validation_statuses_set": set(),
                "source_rows": 0,
                "null_article_rows": 0,
                "linked_article_ids_set": set(),
                "linked_article_refs_set": set(),
                "broken_article_ids_set": set(),
                "article_law_mismatch_ids_set": set(),
            },
        )
        group["source_rows"] += 1
        group["normative_references_set"].add(row.get("normative_reference"))
        group["mapping_bases_set"].add(row.get("mapping_basis"))
        group["coverage_statuses_set"].add(row.get("coverage_status"))
        group["validation_statuses_set"].add(row.get("validation_status"))
        article_id = row.get("article_id")
        if article_id is None:
            group["null_article_rows"] += 1
            continue
        article_id = int(article_id)
        if row.get("article_ref") is None:
            group["broken_article_ids_set"].add(article_id)
            continue
        group["linked_article_ids_set"].add(article_id)
        group["linked_article_refs_set"].add(row.get("article_ref"))
        if row.get("law_id") is not None and row.get("article_law_id") != row.get("law_id"):
            group["article_law_mismatch_ids_set"].add(article_id)

    for topic_id, topic in topics.items():
        if not any(key[0] == topic_id for key in grouped):
            grouped[(topic_id, None)] = {
                "topic_id": topic_id,
                "drive_topic_number": topic["drive_topic_number"],
                "part": topic["part"],
                "section": topic["section"],
                "topic_number": topic["topic_number"],
                "topic_title": topic["topic_title"],
                "law_id": None,
                "law_title": "",
                "normative_references_set": set(),
                "mapping_bases_set": set(),
                "coverage_statuses_set": set(),
                "validation_statuses_set": set(),
                "source_rows": 0,
                "null_article_rows": 0,
                "linked_article_ids_set": set(),
                "linked_article_refs_set": set(),
                "broken_article_ids_set": set(),
                "article_law_mismatch_ids_set": set(),
            }

    groups = []
    for group in grouped.values():
        linked_count = len(group["linked_article_ids_set"])
        ambiguous = (
            group["law_id"] is None
            or bool(group["broken_article_ids_set"])
            or bool(group["article_law_mismatch_ids_set"])
        )
        if ambiguous:
            law_status = "ambiguous"
        elif linked_count:
            law_status = "mapped"
        else:
            law_status = "fallback"

        law_id = group["law_id"]
        group["law_status"] = law_status
        group["linked_article_count"] = linked_count
        group["has_specific_articles"] = "yes" if linked_count else "no"
        group["total_articles_in_law"] = article_counts.get(law_id, 0) if law_id is not None else 0
        group["normative_references"] = _csv_list(group.pop("normative_references_set"))
        group["mapping_bases"] = _csv_list(group.pop("mapping_bases_set"))
        group["coverage_statuses"] = _csv_list(group.pop("coverage_statuses_set"))
        group["validation_statuses"] = _csv_list(group.pop("validation_statuses_set"))
        group["linked_article_ids"] = _ids_csv(group.pop("linked_article_ids_set"))
        group["linked_article_refs"] = _csv_list(group.pop("linked_article_refs_set"))
        group["broken_article_ids"] = _ids_csv(group.pop("broken_article_ids_set"))
        group["article_law_mismatch_ids"] = _ids_csv(group.pop("article_law_mismatch_ids_set"))
        groups.append(group)

    topic_group_map: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for group in groups:
        topic_group_map[int(group["topic_id"])].append(group)

    topic_statuses: dict[int, str] = {}
    for topic_id, topic_groups in topic_group_map.items():
        if any(group["law_status"] == "ambiguous" for group in topic_groups):
            topic_status = "ambiguous"
        elif any(group["linked_article_count"] for group in topic_groups) and any(
            not group["linked_article_count"] for group in topic_groups
        ):
            topic_status = "partial"
        elif any(group["linked_article_count"] for group in topic_groups):
            topic_status = "mapped"
        else:
            topic_status = "fallback"
        topic_statuses[topic_id] = topic_status

    for group in groups:
        group["topic_status"] = topic_statuses[int(group["topic_id"])]

    return sorted(
        groups,
        key=lambda item: (
            0 if item["part"] == "general" else 1,
            int(item["topic_number"]),
            clean_cell(item.get("law_title")),
        ),
    )


def build_topic_status_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    groups = build_topic_law_groups(conn)
    by_topic: dict[int, dict[str, Any]] = {}
    for group in groups:
        row = by_topic.setdefault(
            int(group["topic_id"]),
            {
                "topic_id": group["topic_id"],
                "part": group["part"],
                "topic_number": group["topic_number"],
                "topic_title": group["topic_title"],
                "topic_status": group["topic_status"],
                "law_count": 0,
                "unresolved_law_count": 0,
                "unresolved_article_total": 0,
                "linked_article_count": 0,
                "law_titles": [],
            },
        )
        row["law_count"] += 1
        row["linked_article_count"] += int(group["linked_article_count"])
        if group["law_status"] != "mapped":
            row["unresolved_law_count"] += 1
            row["unresolved_article_total"] += int(group["total_articles_in_law"])
        if group.get("law_title"):
            row["law_titles"].append(group["law_title"])

    for row in by_topic.values():
        row["law_titles"] = "; ".join(row["law_titles"])
    return sorted(
        by_topic.values(),
        key=lambda item: (0 if item["part"] == "general" else 1, int(item["topic_number"])),
    )


def build_status_snapshot(conn: sqlite3.Connection) -> dict[str, Any]:
    topic_rows = build_topic_status_rows(conn)
    groups = build_topic_law_groups(conn)
    status_counts = Counter(row["topic_status"] for row in topic_rows)
    fine_topics = sum(1 for row in topic_rows if int(row["linked_article_count"]) > 0)
    fallback_topics = sum(1 for row in topic_rows if int(row["linked_article_count"]) == 0)
    total_topics = len(topic_rows)
    affected_laws = {
        int(group["law_id"])
        for group in groups
        if group["law_id"] is not None and group["law_status"] != "mapped"
    }
    risks = {
        "broken_article_links": sum(1 for group in groups if group["broken_article_ids"]),
        "article_law_mismatches": sum(1 for group in groups if group["article_law_mismatch_ids"]),
        "topic_law_groups_without_law_id": sum(1 for group in groups if group["law_id"] is None),
        "topic_law_groups_without_article_mapping": sum(
            1 for group in groups if group["law_status"] == "fallback"
        ),
    }
    urgent = [
        row
        for row in topic_rows
        if int(row["unresolved_law_count"]) > 0
    ]
    urgent.sort(
        key=lambda item: (
            int(item["unresolved_article_total"]),
            int(item["unresolved_law_count"]),
        ),
        reverse=True,
    )
    return {
        "total_topics": total_topics,
        "fine_mapping_topics": fine_topics,
        "fallback_topics": fallback_topics,
        "partial_topics": status_counts.get("partial", 0),
        "mapped_topics": status_counts.get("mapped", 0),
        "ambiguous_topics": status_counts.get("ambiguous", 0),
        "topic_status_counts": dict(status_counts),
        "affected_law_count": len(affected_laws),
        "progress_percent": round((fine_topics / total_topics * 100) if total_topics else 0, 2),
        "top_urgent_topics": urgent[:15],
        "risks": risks,
    }


def build_existing_fine_mapping_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            t.id AS topic_id,
            t.part,
            t.topic_number,
            t.official_text AS topic_title,
            ts.id AS topic_source_id,
            ts.law_id,
            l.name AS law_title,
            ts.article_id,
            a.article_ref,
            a.title AS article_title,
            ts.normative_reference,
            ts.coverage_status,
            ts.mapping_basis,
            ts.priority,
            ts.validation_status,
            ts.notes,
            CASE
                WHEN a.id IS NULL THEN 'missing_article'
                WHEN a.law_id != ts.law_id THEN 'wrong_law'
                ELSE 'ok'
            END AS integrity_status
        FROM topic_sources ts
        JOIN topics t ON t.id = ts.topic_id
        LEFT JOIN laws l ON l.id = ts.law_id
        LEFT JOIN articles a ON a.id = ts.article_id
        WHERE ts.article_id IS NOT NULL
        ORDER BY
            CASE t.part WHEN 'general' THEN 0 ELSE 1 END,
            t.topic_number,
            l.name,
            a.id
        """
    ).fetchall()
    return [dict(row) for row in rows]


def candidate_article_refs(articles: list[dict[str, Any]], linked_ids: set[int]) -> str:
    if not articles:
        return ""
    if linked_ids:
        selected = [article for article in articles if int(article["id"]) in linked_ids]
        prefix = "CURRENT_LINKED_CANDIDATES"
    else:
        selected = articles
        prefix = "TECHNICAL_CANDIDATES_FROM_ARTICLES_TABLE"
    pairs = [f"{article['id']}:{clean_cell(article['article_ref'])}" for article in selected]
    return f"{prefix}: " + "; ".join(pairs)


def template_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    articles_by_law = fetch_articles_by_law(conn)
    rows = []
    for group in build_topic_law_groups(conn):
        law_id = group["law_id"]
        articles = articles_by_law.get(int(law_id), []) if law_id is not None else []
        linked_ids = {
            int(value)
            for value in str(group.get("linked_article_ids") or "").split(";")
            if value.strip().isdigit()
        }
        rows.append(
            {
                "topic_id": group["topic_id"],
                "part": group["part"],
                "topic_number": group["topic_number"],
                "topic_title": group["topic_title"],
                "law_id": law_id or "",
                "law_title": group["law_title"],
                "normative_reference": group["normative_references"],
                "current_status": group["topic_status"],
                "candidate_article_count": len(articles),
                "candidate_article_refs": candidate_article_refs(articles, linked_ids),
                "current_linked_article_ids": group["linked_article_ids"],
                "autentica_reference": "",
                "confidence": "",
                "review_notes": "",
                "approved": "",
                "article_ids_to_apply": "",
                "mapping_basis": "",
            }
        )
    return rows


def parse_approved(value: str) -> bool:
    cleaned = clean_cell(value).lower()
    if cleaned in TRUTHY:
        return True
    if cleaned in FALSY:
        return False
    return False


def parse_article_ids(raw: str) -> tuple[list[int], str | None]:
    raw = clean_cell(raw)
    if not raw:
        return [], None
    if re.search(r"\d+\s*[-–]\s*\d+", raw):
        return [], "Rangos no permitidos: lista article_id explicitos separados por ; o ,."
    ids = [int(match.group(0)) for match in re.finditer(r"\d+", raw)]
    return ids, None


def row_source_note(row: dict[str, str], csv_path: Path, row_number: int) -> str:
    parts = [f"mapping_review_csv={csv_path.name}", f"row={row_number}"]
    if clean_cell(row.get("autentica_reference")):
        parts.append(f"autentica_reference={clean_cell(row.get('autentica_reference'))}")
    if clean_cell(row.get("review_notes")):
        parts.append(f"review_notes={clean_cell(row.get('review_notes'))}")
    return "; ".join(parts)


def default_mapping_basis() -> str:
    return f"{DEFAULT_APPLY_BASIS_PREFIX}_{datetime.now().strftime('%Y_%m_%d')}"


def mapping_basis_for_row(row: dict[str, str]) -> str:
    return clean_cell(row.get("mapping_basis")) or default_mapping_basis()


def _resolve_topic(
    conn: sqlite3.Connection,
    row: dict[str, str],
) -> sqlite3.Row | None:
    topic_id = clean_cell(row.get("topic_id"))
    if topic_id.isdigit():
        return conn.execute("SELECT * FROM topics WHERE id = ?", (int(topic_id),)).fetchone()
    part = clean_cell(row.get("part")).lower()
    topic_number = clean_cell(row.get("topic_number"))
    if not part or not topic_number.isdigit():
        return None
    return conn.execute(
        "SELECT * FROM topics WHERE part = ? AND topic_number = ?",
        (part, int(topic_number)),
    ).fetchone()


def _first_normative_reference(conn: sqlite3.Connection, topic_id: int, law_id: int) -> str:
    row = conn.execute(
        """
        SELECT normative_reference
        FROM topic_sources
        WHERE topic_id = ? AND law_id = ?
        ORDER BY CASE WHEN article_id IS NULL THEN 0 ELSE 1 END, id
        LIMIT 1
        """,
        (topic_id, law_id),
    ).fetchone()
    return clean_cell(row["normative_reference"] if row else "")


def _protected_baseline_issues(conn: sqlite3.Connection) -> tuple[list[ValidationIssue], int]:
    placeholders = ",".join("?" for _ in PROTECTED_MAPPING_BASES)
    rows = conn.execute(
        f"""
        SELECT
            ts.id,
            ts.topic_id,
            ts.law_id,
            ts.article_id,
            ts.mapping_basis,
            a.id AS real_article_id,
            a.law_id AS article_law_id
        FROM topic_sources ts
        LEFT JOIN articles a ON a.id = ts.article_id
        WHERE ts.article_id IS NOT NULL
          AND ts.mapping_basis IN ({placeholders})
        """,
        tuple(PROTECTED_MAPPING_BASES),
    ).fetchall()
    issues = []
    topic_law_pairs = {(int(row["topic_id"]), int(row["law_id"])) for row in rows}
    for row in rows:
        if row["real_article_id"] is None:
            issues.append(
                ValidationIssue(
                    "ERROR",
                    None,
                    "protected_missing_article",
                    f"Protected mapping topic_sources.id={row['id']} points to missing article_id={row['article_id']}",
                )
            )
        elif row["article_law_id"] != row["law_id"]:
            issues.append(
                ValidationIssue(
                    "ERROR",
                    None,
                    "protected_wrong_law",
                    f"Protected mapping topic_sources.id={row['id']} points outside law_id={row['law_id']}",
                )
            )
    return issues, len(topic_law_pairs)


def _existing_article_mappings(conn: sqlite3.Connection, topic_id: int, law_id: int) -> set[int]:
    rows = conn.execute(
        """
        SELECT DISTINCT article_id
        FROM topic_sources
        WHERE topic_id = ? AND law_id = ? AND article_id IS NOT NULL
        """,
        (topic_id, law_id),
    ).fetchall()
    return {int(row["article_id"]) for row in rows}


def _protected_article_mappings(conn: sqlite3.Connection, topic_id: int, law_id: int) -> set[int]:
    placeholders = ",".join("?" for _ in PROTECTED_MAPPING_BASES)
    rows = conn.execute(
        f"""
        SELECT DISTINCT article_id
        FROM topic_sources
        WHERE topic_id = ? AND law_id = ? AND article_id IS NOT NULL
          AND mapping_basis IN ({placeholders})
        """,
        (topic_id, law_id, *PROTECTED_MAPPING_BASES),
    ).fetchall()
    return {int(row["article_id"]) for row in rows}


def validate_review_template(csv_path: Path, db_path: Path = DB_PATH) -> ValidationResult:
    csv_path = csv_path.resolve()
    issues: list[ValidationIssue] = []
    planned: list[PlannedMapping] = []
    checked_rows = 0

    with connect_readonly(db_path) as conn:
        baseline_issues, protected_pairs = _protected_baseline_issues(conn)
        issues.extend(baseline_issues)

        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            missing_columns = [column for column in REVIEW_COLUMNS if column not in (reader.fieldnames or [])]
            if missing_columns:
                issues.append(
                    ValidationIssue(
                        "ERROR",
                        None,
                        "missing_columns",
                        "Missing required columns: " + ", ".join(missing_columns),
                    )
                )
                return ValidationResult(csv_path, checked_rows, planned, issues, protected_pairs)

            for row_number, row in enumerate(reader, start=2):
                checked_rows += 1
                before_errors = len([issue for issue in issues if issue.level == "ERROR"])

                topic = _resolve_topic(conn, row)
                if topic is None:
                    issues.append(
                        ValidationIssue("ERROR", row_number, "topic_not_found", "Topic not found.")
                    )
                    continue
                topic_id = int(topic["id"])

                approved = parse_approved(row.get("approved", ""))
                article_ids, parse_error = parse_article_ids(row.get("article_ids_to_apply", ""))
                if parse_error:
                    issues.append(ValidationIssue("ERROR", row_number, "article_id_parse_error", parse_error))

                duplicates = sorted({article_id for article_id in article_ids if article_ids.count(article_id) > 1})
                if duplicates:
                    issues.append(
                        ValidationIssue(
                            "ERROR",
                            row_number,
                            "duplicate_article_ids_in_row",
                            "Duplicated article_id values in row: " + ",".join(map(str, duplicates)),
                        )
                    )

                if approved and not article_ids:
                    issues.append(
                        ValidationIssue(
                            "ERROR",
                            row_number,
                            "approved_without_articles",
                            "approved is true but article_ids_to_apply is empty.",
                        )
                    )

                if approved and not (
                    clean_cell(row.get("autentica_reference")) or clean_cell(row.get("review_notes"))
                ):
                    issues.append(
                        ValidationIssue(
                            "ERROR",
                            row_number,
                            "approved_without_source_or_note",
                            "approved row needs autentica_reference or review_notes.",
                        )
                    )

                if article_ids and not approved:
                    issues.append(
                        ValidationIssue(
                            "WARNING",
                            row_number,
                            "ids_on_unapproved_row",
                            "article_ids_to_apply is filled but approved is not true; dry-run will ignore it.",
                        )
                    )

                law_id_raw = clean_cell(row.get("law_id"))
                if not law_id_raw.isdigit():
                    level = "ERROR" if approved or article_ids else "WARNING"
                    issues.append(
                        ValidationIssue(level, row_number, "law_id_invalid", "law_id must be numeric.")
                    )
                    continue
                law_id = int(law_id_raw)
                law = conn.execute("SELECT id FROM laws WHERE id = ?", (law_id,)).fetchone()
                if law is None:
                    issues.append(
                        ValidationIssue("ERROR", row_number, "law_not_found", f"law_id={law_id} not found.")
                    )
                    continue

                linked = conn.execute(
                    "SELECT COUNT(*) AS total FROM topic_sources WHERE topic_id = ? AND law_id = ?",
                    (topic_id, law_id),
                ).fetchone()["total"]
                if not linked:
                    issues.append(
                        ValidationIssue(
                            "ERROR",
                            row_number,
                            "law_not_linked_to_topic",
                            f"law_id={law_id} is not currently linked to topic_id={topic_id}.",
                        )
                    )

                for article_id in article_ids:
                    article = conn.execute(
                        "SELECT id, law_id FROM articles WHERE id = ?",
                        (article_id,),
                    ).fetchone()
                    if article is None:
                        issues.append(
                            ValidationIssue(
                                "ERROR",
                                row_number,
                                "article_not_found",
                                f"article_id={article_id} does not exist.",
                            )
                        )
                    elif int(article["law_id"]) != law_id:
                        issues.append(
                            ValidationIssue(
                                "ERROR",
                                row_number,
                                "article_wrong_law",
                                f"article_id={article_id} belongs to law_id={article['law_id']}, not law_id={law_id}.",
                            )
                        )

                existing_ids = _existing_article_mappings(conn, topic_id, law_id)
                duplicate_existing = sorted(existing_ids.intersection(article_ids))
                if approved and duplicate_existing:
                    issues.append(
                        ValidationIssue(
                            "ERROR",
                            row_number,
                            "duplicate_existing_mapping",
                            "These article ids are already mapped for this topic-law: "
                            + ",".join(map(str, duplicate_existing)),
                        )
                    )

                protected_ids = _protected_article_mappings(conn, topic_id, law_id)
                if approved and protected_ids:
                    if set(article_ids) != protected_ids:
                        issues.append(
                            ValidationIssue(
                                "ERROR",
                                row_number,
                                "protected_mapping_overwrite",
                                "Approved ids differ from protected mapping basis "
                                + ",".join(sorted(PROTECTED_MAPPING_BASES)),
                            )
                        )
                    else:
                        issues.append(
                            ValidationIssue(
                                "ERROR",
                                row_number,
                                "duplicate_protected_mapping",
                                "This row repeats an already protected fine mapping.",
                            )
                        )

                after_errors = len([issue for issue in issues if issue.level == "ERROR"])
                if approved and article_ids and after_errors == before_errors:
                    normative_reference = clean_cell(row.get("normative_reference")) or _first_normative_reference(
                        conn, topic_id, law_id
                    )
                    basis = mapping_basis_for_row(row)
                    note = row_source_note(row, csv_path, row_number)
                    for article_id in sorted(set(article_ids)):
                        planned.append(
                            PlannedMapping(
                                row_number=row_number,
                                topic_id=topic_id,
                                law_id=law_id,
                                article_id=article_id,
                                normative_reference=normative_reference,
                                mapping_basis=basis,
                                source_note=note,
                            )
                        )

    return ValidationResult(csv_path, checked_rows, planned, issues, protected_pairs)


def validation_report_rows(result: ValidationResult) -> list[dict[str, Any]]:
    return [
        {
            "level": issue.level,
            "row_number": issue.row_number or "",
            "code": issue.code,
            "message": issue.message,
        }
        for issue in result.issues
    ]


def format_validation_summary(result: ValidationResult) -> str:
    return (
        f"rows={result.checked_rows} "
        f"errors={len(result.errors)} "
        f"warnings={len(result.warnings)} "
        f"planned_mappings={len(result.planned_mappings)} "
        f"protected_topic_law_pairs={result.protected_topic_law_pairs}"
    )

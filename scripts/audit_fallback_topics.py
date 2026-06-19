from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mapping_tools import (
    connect_readonly,
    ensure_reports_dir,
    render_md_table,
    write_csv,
    build_topic_law_groups,
    build_topic_status_rows,
)


CSV_FIELDS = [
    "part",
    "topic_number",
    "topic_title",
    "topic_status",
    "law_status",
    "law_id",
    "law_title",
    "normative_references",
    "total_articles_in_law",
    "has_specific_articles",
    "linked_article_count",
    "linked_article_refs",
    "linked_article_ids",
    "source_rows",
    "null_article_rows",
    "mapping_bases",
    "coverage_statuses",
    "validation_statuses",
    "broken_article_ids",
    "article_law_mismatch_ids",
]


MD_COLUMNS = [
    ("part", "Parte"),
    ("topic_number", "Tema"),
    ("topic_status", "Estado tema"),
    ("law_status", "Estado norma"),
    ("law_id", "law_id"),
    ("law_title", "Norma"),
    ("total_articles_in_law", "Arts norma"),
    ("linked_article_count", "Arts vinculados"),
    ("mapping_bases", "mapping_basis"),
]


def main() -> int:
    reports_dir = ensure_reports_dir()
    csv_path = reports_dir / "fallback_topics.csv"
    md_path = reports_dir / "fallback_topics.md"

    with connect_readonly() as conn:
        groups = build_topic_law_groups(conn)
        topic_rows = build_topic_status_rows(conn)

    topic_status_counts = Counter(row["topic_status"] for row in topic_rows)
    law_status_counts = Counter(group["law_status"] for group in groups)
    fallback_or_partial = [
        group
        for group in groups
        if group["topic_status"] in {"fallback", "partial", "ambiguous"}
        or group["law_status"] in {"fallback", "ambiguous"}
    ]

    write_csv(csv_path, groups, CSV_FIELDS)

    lines = [
        "# Auditoria de fallback de temas",
        "",
        "Informe generado en modo read-only. No aplica delimitaciones juridicas.",
        "",
        "## Resumen",
        "",
        f"- Temas auditados: {len(topic_rows)}",
        f"- Grupos tema-norma auditados: {len(groups)}",
        "- Estados de tema: "
        + ", ".join(f"{status}={count}" for status, count in sorted(topic_status_counts.items())),
        "- Estados de norma: "
        + ", ".join(f"{status}={count}" for status, count in sorted(law_status_counts.items())),
        "",
        "## Temas que requieren delimitacion o revision",
        "",
        render_md_table(fallback_or_partial, MD_COLUMNS),
        "",
        "## Todos los grupos tema-norma",
        "",
        render_md_table(groups, MD_COLUMNS),
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {md_path}")
    print(f"Wrote {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mapping_tools import (
    build_existing_fine_mapping_rows,
    connect_readonly,
    ensure_reports_dir,
    render_md_table,
    write_csv,
)


CSV_FIELDS = [
    "part",
    "topic_number",
    "topic_title",
    "topic_id",
    "topic_source_id",
    "law_id",
    "law_title",
    "article_id",
    "article_ref",
    "article_title",
    "normative_reference",
    "coverage_status",
    "mapping_basis",
    "priority",
    "validation_status",
    "notes",
    "integrity_status",
]


MD_COLUMNS = [
    ("part", "Parte"),
    ("topic_number", "Tema"),
    ("law_id", "law_id"),
    ("law_title", "Norma"),
    ("article_id", "article_id"),
    ("article_ref", "Art."),
    ("article_title", "Titulo articulo"),
    ("mapping_basis", "mapping_basis"),
    ("integrity_status", "Integridad"),
]


def main() -> int:
    reports_dir = ensure_reports_dir()
    csv_path = reports_dir / "existing_fine_mappings.csv"
    md_path = reports_dir / "existing_fine_mappings.md"

    with connect_readonly() as conn:
        rows = build_existing_fine_mapping_rows(conn)

    topics = {(row["part"], row["topic_number"]) for row in rows}
    integrity_counts = Counter(row["integrity_status"] for row in rows)
    basis_counts = Counter(row["mapping_basis"] for row in rows)

    write_csv(csv_path, rows, CSV_FIELDS)

    lines = [
        "# Auditoria de mappings finos existentes",
        "",
        "Baseline generado en modo read-only. No modifica `topic_sources` ni `articles`.",
        "",
        "## Resumen",
        "",
        f"- Filas con article_id: {len(rows)}",
        f"- Temas con mapping fino: {len(topics)}",
        "- Integridad: " + ", ".join(f"{key}={value}" for key, value in sorted(integrity_counts.items())),
        "- mapping_basis: " + ", ".join(f"{key}={value}" for key, value in sorted(basis_counts.items())),
        "",
        "## Mappings",
        "",
        render_md_table(rows, MD_COLUMNS),
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {md_path}")
    print(f"Wrote {csv_path}")
    if any(row["integrity_status"] != "ok" for row in rows):
        print("ERROR: fine mapping integrity issues detected")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

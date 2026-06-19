from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mapping_tools import (
    build_status_snapshot,
    connect_readonly,
    connect_writable,
    create_db_backup,
    ensure_reports_dir,
    format_validation_summary,
    render_md_table,
    timestamp,
    validate_review_template,
    validation_report_rows,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Dry-run or apply a reviewed topic-law-article mapping CSV."
    )
    parser.add_argument("csv_path", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Validate and report without DB writes.")
    mode.add_argument("--apply", action="store_true", help="Write approved mappings after backup.")
    return parser


def has_mapping_basis_column() -> bool:
    with connect_readonly() as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(topic_sources)").fetchall()}
    return "mapping_basis" in columns


def write_report(
    *,
    csv_path: Path,
    dry_run: bool,
    validation_summary: str,
    validation_issues: list[dict[str, object]],
    planned_mappings: list[dict[str, object]],
    before: dict[str, object],
    after: dict[str, object],
    backup_path: Path | None,
    inserted: int,
    skipped: int,
) -> tuple[Path, Path]:
    reports_dir = ensure_reports_dir()
    stamp = timestamp()
    md_path = reports_dir / f"apply_mapping_review_{stamp}.md"
    json_path = reports_dir / f"apply_mapping_review_{stamp}.json"

    payload = {
        "csv_path": str(csv_path),
        "mode": "dry-run" if dry_run else "apply",
        "validation_summary": validation_summary,
        "validation_issues": validation_issues,
        "planned_mappings": planned_mappings,
        "before": before,
        "after": after,
        "backup_path": str(backup_path) if backup_path else None,
        "inserted": inserted,
        "skipped": skipped,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    issue_table = render_md_table(
        validation_issues,
        [
            ("level", "Nivel"),
            ("row_number", "Fila"),
            ("code", "Codigo"),
            ("message", "Mensaje"),
        ],
    )
    planned_table = render_md_table(
        planned_mappings,
        [
            ("row_number", "Fila"),
            ("topic_id", "topic_id"),
            ("law_id", "law_id"),
            ("article_id", "article_id"),
            ("mapping_basis", "mapping_basis"),
        ],
    )
    lines = [
        "# Apply mapping review",
        "",
        f"- CSV: `{csv_path}`",
        f"- Mode: {'dry-run' if dry_run else 'apply'}",
        f"- Validation: {validation_summary}",
        f"- Backup: `{backup_path}`" if backup_path else "- Backup: no creado",
        f"- Inserted: {inserted}",
        f"- Skipped: {skipped}",
        "",
        "## Planned mappings",
        "",
        planned_table,
        "",
        "## Validation issues",
        "",
        issue_table,
        "",
        "## Before",
        "",
        "```json",
        json.dumps(before, ensure_ascii=False, indent=2),
        "```",
        "",
        "## After",
        "",
        "```json",
        json.dumps(after, ensure_ascii=False, indent=2),
        "```",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path, json_path


def apply_mappings(planned_mappings: list[dict[str, object]]) -> tuple[int, int]:
    inserted = 0
    skipped = 0
    with connect_writable() as conn:
        for mapping in planned_mappings:
            exists = conn.execute(
                """
                SELECT id
                FROM topic_sources
                WHERE topic_id = ? AND law_id = ? AND article_id = ?
                LIMIT 1
                """,
                (mapping["topic_id"], mapping["law_id"], mapping["article_id"]),
            ).fetchone()
            if exists:
                skipped += 1
                continue

            conn.execute(
                """
                INSERT INTO topic_sources(
                    topic_id,
                    law_id,
                    article_id,
                    normative_reference,
                    coverage_status,
                    mapping_basis,
                    priority,
                    validation_status,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mapping["topic_id"],
                    mapping["law_id"],
                    mapping["article_id"],
                    mapping["normative_reference"],
                    "delimitacion_fina_aprobada",
                    mapping["mapping_basis"],
                    "alta",
                    "aprobado_revision_humana_pendiente_fuente_oficial",
                    mapping["source_note"],
                ),
            )
            inserted += 1
        conn.commit()
    return inserted, skipped


def main() -> int:
    args = build_parser().parse_args()
    dry_run = not args.apply

    with connect_readonly() as conn:
        before = build_status_snapshot(conn)

    if not has_mapping_basis_column():
        reports_dir = ensure_reports_dir()
        report = reports_dir / f"mapping_basis_migration_needed_{timestamp()}.md"
        report.write_text(
            "# Migracion requerida\n\n"
            "`topic_sources.mapping_basis` no existe. No se aplica nada. "
            "Propuesta: anadir una columna TEXT NOT NULL con valor por defecto "
            "`pendiente_de_validacion` antes de permitir aplicacion automatica.\n",
            encoding="utf-8",
        )
        print(f"ERROR: mapping_basis missing. Wrote {report}")
        return 2

    result = validate_review_template(args.csv_path)
    validation_summary = format_validation_summary(result)
    planned = [asdict(mapping) for mapping in result.planned_mappings]
    issues = validation_report_rows(result)

    backup_path = None
    inserted = 0
    skipped = 0

    if result.ok and args.apply and planned:
        backup_path = create_db_backup()
        inserted, skipped = apply_mappings(planned)

    with connect_readonly() as conn:
        after = build_status_snapshot(conn)

    md_path, json_path = write_report(
        csv_path=args.csv_path,
        dry_run=dry_run,
        validation_summary=validation_summary,
        validation_issues=issues,
        planned_mappings=planned,
        before=before,
        after=after,
        backup_path=backup_path,
        inserted=inserted,
        skipped=skipped,
    )

    print("Validation:", validation_summary)
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    if not result.ok:
        print("ERROR: validation failed; no DB changes were made.")
        return 1
    if dry_run:
        print("Dry-run only; no DB changes were made.")
    elif not planned:
        print("No approved mappings to apply.")
    else:
        print(f"Applied mappings: inserted={inserted}, skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

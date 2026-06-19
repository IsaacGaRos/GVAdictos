"""Fase 2E: delimitacion fina de PE-13 tras fix de Ley 40/2015 arts. 24-27.

Alcance:
  - PE-13 = topic_id 28, parte especial tema 13.
  - Ley 40/2015 (law_id=4): Titulo Preliminar arts. 1-53 + Titulo III arts. 140-158.
  - Decreto 176/2014 (law_id=27): arts. 1-21.

Garantias:
  - Dry-run por defecto. Solo escribe con --apply.
  - NO modifica articles, parser, importer ni normalizacion.
  - NO borra mappings ajenos: elimina solo filas propias con este mapping_basis.
  - Aborta si PE-13 ya tiene mapping fino ajeno para evitar duplicados silenciosos.
  - Crea backup antes de cualquier escritura real.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "db" / "gvadicto.sqlite"
REPORTS = ROOT / "reports"

TOPIC_ID = 28
MAPPING_BASIS = "validacion_articulos_claude_fase2e_pe13_2026_06_18"
VALIDATION_STATUS = "validado_fuente_oficial_pendiente_revision_humana"
NOTE = (
    "PE-13 delimitado tras Fase 2D: Ley 40/2015 law_id=4 limpia en arts. 24-27. "
    "Rangos segun enunciado oficial A1-01 2025 y estructura BOE/DOGV: Ley 40/2015 "
    "Titulo Preliminar arts. 1-53 y Titulo III arts. 140-158; Decreto 176/2014 "
    "arts. 1-21. Pendiente revision humana."
)

PLAN = [
    {
        "label": "PE-13 Ley 40/2015 Titulo Preliminar",
        "law_id": 4,
        "law_label": "Ley 40/2015",
        "ranges": [(1, 53)],
        "expected_count": 54,  # incluye art. 46 bis en la BD normalizada
    },
    {
        "label": "PE-13 Ley 40/2015 Titulo III",
        "law_id": 4,
        "law_label": "Ley 40/2015",
        "ranges": [(140, 158)],
        "expected_count": 19,
    },
    {
        "label": "PE-13 Decreto 176/2014 convenios Generalitat",
        "law_id": 27,
        "law_label": "Decreto 176/2014",
        "ranges": [(1, 21)],
        "expected_count": 21,
    },
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply PE-13 fine article mapping.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes to db/gvadicto.sqlite. Without this flag, dry-run only.",
    )
    return parser


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    return conn


def base_number(article_ref: str) -> int:
    match = re.match(r"\s*(\d+)", article_ref or "")
    if not match:
        raise ValueError(f"article_ref without leading number: {article_ref!r}")
    return int(match.group(1))


def articles_in_range(conn: sqlite3.Connection, law_id: int, start: int, end: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT id, law_id, article_ref, title
        FROM articles
        WHERE law_id = ?
          AND CAST(article_ref AS INTEGER) BETWEEN ? AND ?
        ORDER BY CAST(article_ref AS INTEGER), article_ref
        """,
        (law_id, start, end),
    ).fetchall()


def make_backup() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = ROOT / "db" / f"gvadicto.backup_pre2e_pe13_{ts}.sqlite"
    shutil.copy2(DB, dst)
    return dst


def count(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> int:
    return int(conn.execute(sql, params).fetchone()[0])


def preflight(conn: sqlite3.Connection) -> dict[str, Any]:
    topic = conn.execute(
        "SELECT id, topic_number, part, official_text FROM topics WHERE id = ?",
        (TOPIC_ID,),
    ).fetchone()
    if not topic:
        raise SystemExit(f"ABORT: no existe topic_id={TOPIC_ID}.")
    if int(topic["topic_number"]) != 13 or topic["part"] != "especial":
        raise SystemExit(f"ABORT: topic_id={TOPIC_ID} no es PE-13: {dict(topic)}")
    if "Ley 40/2015" not in topic["official_text"] or "Decreto 176/2014" not in topic["official_text"]:
        raise SystemExit("ABORT: el texto oficial de PE-13 no contiene ambas normas esperadas.")

    for law_id in {int(item["law_id"]) for item in PLAN}:
        law = conn.execute("SELECT id, name FROM laws WHERE id = ?", (law_id,)).fetchone()
        if not law:
            raise SystemExit(f"ABORT: no existe law_id={law_id}.")

    marker_count = count(
        conn,
        "SELECT COUNT(*) FROM articles WHERE law_id=4 AND text LIKE ?",
        ("%Plan Anual Normativo%",),
    )
    if marker_count:
        raise SystemExit("ABORT: Ley 40/2015 sigue contaminada con 'Plan Anual Normativo'.")

    broken_fk = count(
        conn,
        "SELECT COUNT(*) FROM topic_sources WHERE article_id IS NOT NULL "
        "AND article_id NOT IN (SELECT id FROM articles)",
    )
    if broken_fk:
        raise SystemExit(f"ABORT: hay FKs rotas antes de aplicar: {broken_fk}.")

    foreign_fine = conn.execute(
        """
        SELECT id, mapping_basis, article_id
        FROM topic_sources
        WHERE topic_id = ?
          AND article_id IS NOT NULL
          AND mapping_basis <> ?
        """,
        (TOPIC_ID, MAPPING_BASIS),
    ).fetchall()
    if foreign_fine:
        sample = [dict(row) for row in foreign_fine[:5]]
        raise SystemExit(f"ABORT: PE-13 ya tiene mapping fino ajeno: {sample}")

    planned: list[dict[str, Any]] = []
    seen_article_ids: set[int] = set()
    segments: list[dict[str, Any]] = []

    for item in PLAN:
        item_rows: list[sqlite3.Row] = []
        expected_bases: set[int] = set()
        for start, end in item["ranges"]:
            rows = articles_in_range(conn, int(item["law_id"]), start, end)
            item_rows.extend(rows)
            expected_bases.update(range(start, end + 1))

        found_bases = {base_number(row["article_ref"]) for row in item_rows}
        missing_bases = sorted(expected_bases - found_bases)
        if missing_bases:
            raise SystemExit(
                f"ABORT: faltan bases de articulo en {item['label']}: {missing_bases}"
            )
        if len(item_rows) != int(item["expected_count"]):
            raise SystemExit(
                f"ABORT: conteo inesperado en {item['label']}: "
                f"{len(item_rows)} != {item['expected_count']}"
            )

        for row in item_rows:
            article_id = int(row["id"])
            if article_id in seen_article_ids:
                raise SystemExit(f"ABORT: articulo duplicado en plan: article_id={article_id}")
            seen_article_ids.add(article_id)
            planned.append(
                {
                    "topic_id": TOPIC_ID,
                    "law_id": int(item["law_id"]),
                    "article_id": article_id,
                    "article_ref": row["article_ref"],
                    "title": row["title"],
                    "normative_reference": f"{item['law_label']} art. {row['article_ref']}",
                }
            )

        segments.append(
            {
                "label": item["label"],
                "law_id": int(item["law_id"]),
                "count": len(item_rows),
                "ranges": item["ranges"],
                "first": item_rows[0]["article_ref"],
                "last": item_rows[-1]["article_ref"],
            }
        )

    own_existing = count(
        conn,
        "SELECT COUNT(*) FROM topic_sources WHERE topic_id=? AND mapping_basis=?",
        (TOPIC_ID, MAPPING_BASIS),
    )
    total_before = count(conn, "SELECT COUNT(*) FROM topic_sources")
    fine_before = count(conn, "SELECT COUNT(*) FROM topic_sources WHERE article_id IS NOT NULL")

    return {
        "topic": dict(topic),
        "segments": segments,
        "planned_rows": planned,
        "own_existing": own_existing,
        "total_before": total_before,
        "fine_before": fine_before,
        "broken_fk_before": broken_fk,
    }


def write_reports(result: dict[str, Any], stamp: str) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS / f"apply_fase2e_pe13_delimitation_{stamp}.json"
    md_path = REPORTS / f"apply_fase2e_pe13_delimitation_{stamp}.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Fase 2E PE-13",
        "",
        f"- Mode: {'APPLY' if result['applied'] else 'DRY-RUN'}",
        f"- Topic: PE-13 / topic_id={TOPIC_ID}",
        f"- mapping_basis: `{MAPPING_BASIS}`",
        f"- Planned rows: {result['planned_count']}",
        f"- Backup: {result.get('backup') or 'n/a'}",
        "",
        "## Segments",
        "",
        "| Segment | law_id | Ranges | Count | First | Last |",
        "| --- | ---: | --- | ---: | --- | --- |",
    ]
    for segment in result["segments"]:
        ranges = ", ".join(f"{start}-{end}" for start, end in segment["ranges"])
        lines.append(
            f"| {segment['label']} | {segment['law_id']} | {ranges} | "
            f"{segment['count']} | {segment['first']} | {segment['last']} |"
        )
    lines.extend(
        [
            "",
            "## Counts",
            "",
            f"- topic_sources before: {result['total_before']}",
            f"- topic_sources after: {result.get('total_after', 'n/a')}",
            f"- fine mappings before: {result['fine_before']}",
            f"- fine mappings after: {result.get('fine_after', 'n/a')}",
            f"- own rows deleted: {result.get('own_deleted', 0)}",
            f"- own rows inserted: {result.get('inserted', 0)}",
            f"- broken FK after: {result.get('broken_fk_after', 'n/a')}",
            "",
            "No modifica `articles`, parser, importer ni normalizacion.",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report JSON: {json_path}")
    print(f"Report MD: {md_path}")


def apply_mapping(conn: sqlite3.Connection, planned_rows: list[dict[str, Any]]) -> tuple[int, int]:
    deleted = conn.execute(
        "DELETE FROM topic_sources WHERE topic_id=? AND mapping_basis=?",
        (TOPIC_ID, MAPPING_BASIS),
    ).rowcount
    inserted = 0
    for row in planned_rows:
        conn.execute(
            """
            INSERT INTO topic_sources(
                topic_id, law_id, article_id, normative_reference,
                coverage_status, mapping_basis, priority, validation_status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                TOPIC_ID,
                row["law_id"],
                row["article_id"],
                row["normative_reference"],
                "articulo_delimitado",
                MAPPING_BASIS,
                "alta",
                VALIDATION_STATUS,
                NOTE,
            ),
        )
        inserted += 1
    return int(deleted), inserted


def main() -> None:
    args = build_parser().parse_args()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    conn = connect()
    try:
        state = preflight(conn)
    finally:
        conn.close()

    planned_rows = state["planned_rows"]
    result: dict[str, Any] = {
        "applied": bool(args.apply),
        "mapping_basis": MAPPING_BASIS,
        "topic": state["topic"],
        "segments": state["segments"],
        "planned_count": len(planned_rows),
        "own_existing": state["own_existing"],
        "total_before": state["total_before"],
        "fine_before": state["fine_before"],
        "broken_fk_before": state["broken_fk_before"],
    }

    print(f"Topic confirmado: PE-13 topic_id={TOPIC_ID}")
    print(f"Filas planificadas: {len(planned_rows)}")
    for segment in state["segments"]:
        print(
            f"  {segment['label']}: {segment['count']} articulos "
            f"({segment['first']}-{segment['last']})"
        )

    if not args.apply:
        print("\nDRY-RUN: no se modifica la BD. Ejecuta con --apply para escribir.")
        write_reports(result, stamp)
        return

    backup = make_backup()
    result["backup"] = str(backup)
    print(f"\nBackup creado: {backup.name}")

    conn = connect()
    try:
        # Revalidar despues del backup y con una conexion nueva. Esto evita
        # problemas intermitentes de Windows si hubo lecturas concurrentes.
        state = preflight(conn)
        planned_rows = state["planned_rows"]
        result["own_existing"] = state["own_existing"]
        result["total_before"] = state["total_before"]
        result["fine_before"] = state["fine_before"]
        result["broken_fk_before"] = state["broken_fk_before"]

        deleted, inserted = apply_mapping(conn, planned_rows)
        conn.commit()

        result["own_deleted"] = deleted
        result["inserted"] = inserted
        result["total_after"] = count(conn, "SELECT COUNT(*) FROM topic_sources")
        result["fine_after"] = count(conn, "SELECT COUNT(*) FROM topic_sources WHERE article_id IS NOT NULL")
        result["broken_fk_after"] = count(
            conn,
            "SELECT COUNT(*) FROM topic_sources WHERE article_id IS NOT NULL "
            "AND article_id NOT IN (SELECT id FROM articles)",
        )
        result["own_after"] = count(
            conn,
            "SELECT COUNT(*) FROM topic_sources WHERE topic_id=? AND mapping_basis=?",
            (TOPIC_ID, MAPPING_BASIS),
        )

        if result["broken_fk_after"]:
            raise SystemExit(f"ABORT: FKs rotas despues de aplicar: {result['broken_fk_after']}")
        if result["own_after"] != len(planned_rows):
            raise SystemExit(
                f"ABORT: filas propias inesperadas: {result['own_after']} != {len(planned_rows)}"
            )

        print(
            f"\nAPPLY OK: deleted own={deleted}, inserted={inserted}, "
            f"topic_sources {result['total_before']} -> {result['total_after']}, "
            f"fine {result['fine_before']} -> {result['fine_after']}, "
            f"FK rotas={result['broken_fk_after']}"
        )
        write_reports(result, stamp)
    finally:
        conn.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

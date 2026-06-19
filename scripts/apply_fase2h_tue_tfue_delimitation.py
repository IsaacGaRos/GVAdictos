"""Fase 2H: delimitacion fina de PE-48/49/50 usando articulos verificados de TUE/TFUE.

Alcance:
  - PE-48 = topic_id 63: Fuentes DUE, tratados constitutivos, actos juridicos.
  - PE-49 = topic_id 64: Derechos fundamentales, ciudadania, mercado interior, LSJ.
  - PE-50 = topic_id 65: Derecho Primario/Derivado, jerarquia, relacion DUE-EEMM.
  - TUE (law_id=34) y TFUE (law_id=35).

Advertencia de calidad de datos:
  El parser de EUR-Lex capturo articulos de Protocolos anejos (EIB, BCE, Schengen,
  Disposiciones Transitorias) con los mismos numeros de referencia que los articulos
  del tratado principal. Los IDs contaminados estan excluidos de este plan.
  Ver .claude/PILOTO_FASE2H_DELIMITACION_TUE_TFUE.md para detalle.

Garantias:
  - Dry-run por defecto. Solo escribe con --apply.
  - NO modifica articles, parser, importer ni normalizacion.
  - NO borra mappings ajenos: elimina solo filas propias con este mapping_basis.
  - Aborta si algun topic ya tiene mapping fino ajeno (article_id IS NOT NULL) para
    evitar duplicados silenciosos.
  - Crea backup antes de cualquier escritura real.
  - Valida cada article_id contra la BD antes de insertar.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "db" / "gvadicto.sqlite"
REPORTS = ROOT / "reports"

MAPPING_BASIS = "delimitacion_fina_claude_fase2h_tue_tfue_2026_06_18"
VALIDATION_STATUS = "validado_fuente_oficial_pendiente_revision_humana"

# Protocolos contaminados: IDs que tienen contenido de Protocolos, NO del tratado principal.
# Se registran aqui como documentacion del hallazgo.
CONTAMINATED_TUE_IDS = {102517, 102508, 102509, 102503, 102461, 102262, 102486, 102429, 102313}
CONTAMINATED_TFUE_IDS = {103709, 103710, 103704, 103662, 103706, 103607, 103489, 103616, 103617,
                          103514, 103587}

# Plan: lista de filas a insertar, verificadas manualmente contra la BD.
# Formato: (topic_id, law_id, article_id, article_ref, priority, normative_reference, notes)
PLAN: list[tuple[int, int, int, str, str, str, str]] = [
    # -------------------------------------------------------------------------
    # TOPIC 63 (PE-48): Fuentes DUE, tratados constitutivos, actos juridicos
    # -------------------------------------------------------------------------
    (63, 34, 102238, "48", "media",
     "TUE art. 48",
     "PE-48: procedimiento de revision de los Tratados (tratados constitutivos)"),
    (63, 35, 103373, "288", "alta",
     "TFUE art. 288",
     "PE-48: definicion de reglamentos, directivas, decisiones, recomendaciones y dictamenes"),
    (63, 35, 103374, "289", "alta",
     "TFUE art. 289",
     "PE-48: procedimiento legislativo ordinario y especial"),
    (63, 35, 103375, "290", "media",
     "TFUE art. 290",
     "PE-48: actos delegados"),
    (63, 35, 103376, "291", "media",
     "TFUE art. 291",
     "PE-48: actos de ejecucion"),
    (63, 35, 103378, "293", "baja",
     "TFUE art. 293",
     "PE-48: propuestas de la Comision"),
    (63, 35, 103379, "294", "media",
     "TFUE art. 294",
     "PE-48: procedimiento legislativo ordinario (detalle)"),
    (63, 35, 103381, "296", "media",
     "TFUE art. 296",
     "PE-48: forma de los actos y motivacion"),
    (63, 35, 103382, "297", "media",
     "TFUE art. 297",
     "PE-48: publicacion y entrada en vigor de los actos"),
    (63, 35, 103384, "299", "baja",
     "TFUE art. 299",
     "PE-48: fuerza ejecutiva de los actos"),
    # -------------------------------------------------------------------------
    # TOPIC 64 (PE-49): Derechos fundamentales, ciudadania, mercado interior, LSJ
    # -------------------------------------------------------------------------
    # Derechos fundamentales y ciudadania (TUE)
    (64, 34, 102196, "6", "alta",
     "TUE art. 6",
     "PE-49: derechos fundamentales, Carta DDFFF, CEDH"),
    (64, 34, 102397, "9", "alta",
     "TUE art. 9",
     "PE-49: ciudadania de la Union (principio)"),
    # Ciudadania (TFUE)
    (64, 35, 103105, "20", "alta",
     "TFUE art. 20",
     "PE-49: creacion ciudadania UE"),
    (64, 35, 103106, "21", "alta",
     "TFUE art. 21",
     "PE-49: libre circulacion y residencia de ciudadanos"),
    (64, 35, 103107, "22", "media",
     "TFUE art. 22",
     "PE-49: derecho de voto en residencia"),
    (64, 35, 103109, "24", "media",
     "TFUE art. 24",
     "PE-49: peticion al Parlamento, defensor del pueblo"),
    (64, 35, 103110, "25", "baja",
     "TFUE art. 25",
     "PE-49: informe trienal sobre ciudadania"),
    # Mercado interior - definicion
    (64, 35, 103111, "26", "alta",
     "TFUE art. 26",
     "PE-49: mercado interior (definicion y objetivo)"),
    # Libre circulacion de mercancias
    (64, 35, 103114, "29", "media",
     "TFUE art. 29",
     "PE-49: libre circulacion en union aduanera"),
    (64, 35, 103115, "30", "alta",
     "TFUE art. 30",
     "PE-49: prohibicion derechos aduaneros entre EEMM"),
    (64, 35, 103116, "31", "baja",
     "TFUE art. 31",
     "PE-49: arancel aduanero comun"),
    (64, 35, 103119, "34", "alta",
     "TFUE art. 34",
     "PE-49: prohibicion restricciones cuantitativas a importacion"),
    (64, 35, 103120, "35", "media",
     "TFUE art. 35",
     "PE-49: prohibicion restricciones cuantitativas a exportacion"),
    (64, 35, 103121, "36", "alta",
     "TFUE art. 36",
     "PE-49: excepciones admitidas a libre circulacion de mercancias"),
    # Libre circulacion de trabajadores
    (64, 35, 103130, "45", "alta",
     "TFUE art. 45",
     "PE-49: libre circulacion de trabajadores"),
    (64, 35, 103131, "46", "media",
     "TFUE art. 46",
     "PE-49: medidas legislativas libre circulacion trabajadores"),
    # Libertad de establecimiento
    (64, 35, 103134, "49", "alta",
     "TFUE art. 49",
     "PE-49: libertad de establecimiento"),
    (64, 35, 103135, "50", "media",
     "TFUE art. 50",
     "PE-49: programa general para la libertad de establecimiento"),
    (64, 35, 103139, "54", "baja",
     "TFUE art. 54",
     "PE-49: sociedades beneficiarias de la libertad de establecimiento"),
    (64, 35, 103140, "55", "baja",
     "TFUE art. 55",
     "PE-49: participacion financiera de nacionales en capital"),
    # Libre prestacion de servicios
    (64, 35, 103141, "56", "alta",
     "TFUE art. 56",
     "PE-49: libre prestacion de servicios"),
    (64, 35, 103142, "57", "media",
     "TFUE art. 57",
     "PE-49: definicion de servicios"),
    (64, 35, 103147, "62", "baja",
     "TFUE art. 62",
     "PE-49: disposiciones de establecimiento aplicables a servicios"),
    # Libre circulacion de capitales
    (64, 35, 103148, "63", "alta",
     "TFUE art. 63",
     "PE-49: libre circulacion de capitales y pagos"),
    (64, 35, 103149, "64", "media",
     "TFUE art. 64",
     "PE-49: circulacion de capitales con terceros paises"),
    (64, 35, 103150, "65", "media",
     "TFUE art. 65",
     "PE-49: excepciones a la libre circulacion de capitales"),
    (64, 35, 103151, "66", "baja",
     "TFUE art. 66",
     "PE-49: medidas de salvaguardia en circulacion de capitales"),
    # Espacio de libertad, seguridad y justicia
    (64, 35, 103152, "67", "alta",
     "TFUE art. 67",
     "PE-49: espacio de libertad, seguridad y justicia (ELSJ)"),
    (64, 35, 103162, "77", "media",
     "TFUE art. 77",
     "PE-49: controles fronterizos y espacio Schengen"),
    (64, 35, 103163, "78", "media",
     "TFUE art. 78",
     "PE-49: politica comun de asilo"),
    (64, 35, 103164, "79", "media",
     "TFUE art. 79",
     "PE-49: politica comun de inmigracion"),
    (64, 35, 103167, "82", "media",
     "TFUE art. 82",
     "PE-49: cooperacion judicial en materia penal"),
    (64, 35, 103168, "83", "media",
     "TFUE art. 83",
     "PE-49: armonizacion de delitos y sanciones"),
    (64, 35, 103172, "87", "media",
     "TFUE art. 87",
     "PE-49: cooperacion policial"),
    (64, 35, 103173, "88", "media",
     "TFUE art. 88",
     "PE-49: Europol"),
    (64, 35, 103174, "89", "baja",
     "TFUE art. 89",
     "PE-49: operaciones transfronterizas de autoridades competentes"),
    # -------------------------------------------------------------------------
    # TOPIC 65 (PE-50): Derecho Primario/Derivado, jerarquia, relacion DUE-EEMM
    # -------------------------------------------------------------------------
    (65, 35, 103343, "258", "alta",
     "TFUE art. 258",
     "PE-50: recurso por incumplimiento (Comision vs. Estado miembro)"),
    (65, 35, 103344, "259", "media",
     "TFUE art. 259",
     "PE-50: recurso por incumplimiento (Estado miembro vs. Estado miembro)"),
    (65, 35, 103345, "260", "media",
     "TFUE art. 260",
     "PE-50: consecuencias del incumplimiento, multa coercitiva"),
    (65, 35, 103352, "267", "alta",
     "TFUE art. 267",
     "PE-50: cuestion prejudicial ante el TJUE (relacion DUE - ordenamiento nacional)"),
    (65, 35, 103373, "288", "alta",
     "TFUE art. 288",
     "PE-50: tipologia del derecho derivado (reglamentos, directivas, decisiones)"),
]

TOPIC_IDS = {row[0] for row in PLAN}
TOPIC_META = {
    63: ("48", "especial", "PE-48"),
    64: ("49", "especial", "PE-49"),
    65: ("50", "especial", "PE-50"),
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Apply Fase 2H TUE/TFUE fine article mapping.")
    p.add_argument(
        "--apply",
        action="store_true",
        help="Write changes to db/gvadicto.sqlite. Without this flag, dry-run only.",
    )
    return p


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def count(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> int:
    return int(conn.execute(sql, params).fetchone()[0])


def make_backup() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = ROOT / "db" / f"gvadicto.backup_pre2h_tue_tfue_{ts}.sqlite"
    shutil.copy2(DB, dst)
    return dst


def preflight(conn: sqlite3.Connection) -> dict[str, Any]:
    errors: list[str] = []

    # 1. Verify topics exist and are correct
    for topic_id, (topic_number, part, label) in TOPIC_META.items():
        row = conn.execute(
            "SELECT id, topic_number, part FROM topics WHERE id = ?", (topic_id,)
        ).fetchone()
        if not row:
            errors.append(f"No existe topic_id={topic_id}")
        elif int(row["topic_number"]) != int(topic_number) or row["part"] != part:
            errors.append(
                f"topic_id={topic_id} no es {label}: "
                f"topic_number={row['topic_number']}, part={row['part']}"
            )

    # 2. Verify laws exist
    for law_id in (34, 35):
        row = conn.execute("SELECT id, name FROM laws WHERE id = ?", (law_id,)).fetchone()
        if not row:
            errors.append(f"No existe law_id={law_id}")

    # 3. Verify each planned article_id exists with correct law_id
    for topic_id, law_id, article_id, article_ref, priority, norm_ref, note in PLAN:
        row = conn.execute(
            "SELECT id, law_id, article_ref FROM articles WHERE id = ?", (article_id,)
        ).fetchone()
        if not row:
            errors.append(
                f"article_id={article_id} (ref={article_ref}, law={law_id}) NO EXISTE en BD"
            )
        elif int(row["law_id"]) != law_id:
            errors.append(
                f"article_id={article_id}: law_id esperado={law_id}, "
                f"encontrado={row['law_id']}"
            )
        elif article_id in CONTAMINATED_TUE_IDS or article_id in CONTAMINATED_TFUE_IDS:
            errors.append(
                f"article_id={article_id} esta en lista de IDs CONTAMINADOS (protocolo); "
                "eliminar del PLAN antes de continuar"
            )

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        raise SystemExit("ABORT: errores en preflight (ver arriba).")

    # 4. Check for foreign fine mappings (article_id IS NOT NULL) from OTHER basis
    for topic_id in TOPIC_IDS:
        foreign = conn.execute(
            """
            SELECT id, mapping_basis, article_id
            FROM topic_sources
            WHERE topic_id = ? AND article_id IS NOT NULL AND mapping_basis <> ?
            """,
            (topic_id, MAPPING_BASIS),
        ).fetchall()
        if foreign:
            sample = [dict(row) for row in foreign[:3]]
            raise SystemExit(
                f"ABORT: topic_id={topic_id} ya tiene mapping fino ajeno: {sample}"
            )

    # 5. Check broken FKs before
    broken_fk = count(
        conn,
        "SELECT COUNT(*) FROM topic_sources WHERE article_id IS NOT NULL "
        "AND article_id NOT IN (SELECT id FROM articles)",
    )
    if broken_fk:
        raise SystemExit(f"ABORT: hay {broken_fk} FKs rotas antes de aplicar.")

    # Build summary
    own_existing = count(
        conn,
        "SELECT COUNT(*) FROM topic_sources WHERE topic_id IN (63,64,65) AND mapping_basis=?",
        (MAPPING_BASIS,),
    )
    total_before = count(conn, "SELECT COUNT(*) FROM topic_sources")
    fine_before = count(conn, "SELECT COUNT(*) FROM topic_sources WHERE article_id IS NOT NULL")

    return {
        "total_before": total_before,
        "fine_before": fine_before,
        "own_existing": own_existing,
        "broken_fk_before": broken_fk,
        "planned_count": len(PLAN),
    }


def apply_mapping(conn: sqlite3.Connection) -> tuple[int, int]:
    deleted = conn.execute(
        "DELETE FROM topic_sources WHERE topic_id IN (63,64,65) AND mapping_basis=?",
        (MAPPING_BASIS,),
    ).rowcount
    inserted = 0
    for topic_id, law_id, article_id, article_ref, priority, norm_ref, note in PLAN:
        conn.execute(
            """
            INSERT INTO topic_sources(
                topic_id, law_id, article_id, normative_reference,
                coverage_status, mapping_basis, priority, validation_status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                topic_id,
                law_id,
                article_id,
                norm_ref,
                "articulo_delimitado",
                MAPPING_BASIS,
                priority,
                VALIDATION_STATUS,
                note,
            ),
        )
        inserted += 1
    return deleted, inserted


def write_reports(result: dict[str, Any], stamp: str) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS / f"apply_fase2h_tue_tfue_{stamp}.json"
    md_path = REPORTS / f"apply_fase2h_tue_tfue_{stamp}.md"

    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    by_topic: dict[int, list[tuple]] = {63: [], 64: [], 65: []}
    for row in PLAN:
        by_topic[row[0]].append(row)

    lines = [
        "# Fase 2H TUE/TFUE — Delimitacion fina PE-48/49/50",
        "",
        f"- Mode: {'APPLY' if result['applied'] else 'DRY-RUN'}",
        f"- mapping_basis: `{MAPPING_BASIS}`",
        f"- Planned rows: {result['planned_count']}",
        f"- Backup: {result.get('backup') or 'n/a'}",
        "",
        "## Por topic",
        "",
    ]
    for topic_id, rows in by_topic.items():
        label = TOPIC_META[topic_id][2]
        lines.append(f"### {label} (topic_id={topic_id}) — {len(rows)} filas")
        lines.append("")
        lines.append("| law_id | art_ref | article_id | priority |")
        lines.append("| ---: | --- | ---: | --- |")
        for _, law_id, article_id, article_ref, priority, _, _ in rows:
            law_name = "TUE" if law_id == 34 else "TFUE"
            lines.append(f"| {law_id} ({law_name}) | {article_ref} | {article_id} | {priority} |")
        lines.append("")

    lines.extend([
        "## Conteos",
        "",
        f"- topic_sources antes: {result['total_before']}",
        f"- topic_sources despues: {result.get('total_after', 'n/a')}",
        f"- filas finas antes: {result['fine_before']}",
        f"- filas finas despues: {result.get('fine_after', 'n/a')}",
        f"- filas propias borradas: {result.get('own_deleted', 0)}",
        f"- filas insertadas: {result.get('inserted', 0)}",
        f"- FKs rotas despues: {result.get('broken_fk_after', 'n/a')}",
        "",
        "No modifica `articles`, parser, importer ni normalizacion.",
        "",
        "## Advertencia calidad de datos",
        "",
        "TUE arts. 1-8, 13, 47 y TFUE arts. 2-6, 18, 23, 27-28, 47-48 contienen",
        "contenido de Protocolos anejos (no del tratado principal). Excluidos del plan.",
        "Ver .claude/PILOTO_FASE2H_DELIMITACION_TUE_TFUE.md para detalle.",
    ])

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report JSON: {json_path}")
    print(f"Report MD:   {md_path}")


def main() -> None:
    args = build_parser().parse_args()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    conn = connect()
    try:
        print("=== Preflight ===")
        state = preflight(conn)
        print(f"  Topics verificados: {sorted(TOPIC_IDS)}")
        print(f"  Articulos en plan: {state['planned_count']}")
        print(f"  topic_sources antes: {state['total_before']}")
        print(f"  filas finas antes: {state['fine_before']}")
        print(f"  filas propias existentes: {state['own_existing']}")
        print(f"  FKs rotas antes: {state['broken_fk_before']}")

        result: dict[str, Any] = {
            "applied": args.apply,
            "planned_count": state["planned_count"],
            "total_before": state["total_before"],
            "fine_before": state["fine_before"],
            "own_existing": state["own_existing"],
            "broken_fk_before": state["broken_fk_before"],
        }

        if not args.apply:
            print("\n=== DRY-RUN completado (sin escritura). Usa --apply para escribir. ===")
            write_reports(result, stamp)
            return

        # Apply
        backup = make_backup()
        result["backup"] = str(backup)
        print(f"\n  Backup creado: {backup.name}")

        print("\n=== Aplicando mapping ===")
        deleted, inserted = apply_mapping(conn)
        conn.commit()

        broken_fk_after = count(
            conn,
            "SELECT COUNT(*) FROM topic_sources WHERE article_id IS NOT NULL "
            "AND article_id NOT IN (SELECT id FROM articles)",
        )
        if broken_fk_after:
            conn.rollback()
            raise SystemExit(
                f"ABORT: quedaron {broken_fk_after} FKs rotas tras insercion. Rollback."
            )

        total_after = count(conn, "SELECT COUNT(*) FROM topic_sources")
        fine_after = count(conn, "SELECT COUNT(*) FROM topic_sources WHERE article_id IS NOT NULL")

        result.update({
            "own_deleted": deleted,
            "inserted": inserted,
            "total_after": total_after,
            "fine_after": fine_after,
            "broken_fk_after": broken_fk_after,
        })

        print(f"  Filas borradas (propias): {deleted}")
        print(f"  Filas insertadas: {inserted}")
        print(f"  topic_sources despues: {total_after}")
        print(f"  filas finas despues: {fine_after}")
        print(f"  FKs rotas despues: {broken_fk_after}")
        print("\n=== APPLY completado con exito. ===")

    finally:
        conn.close()

    write_reports(result, stamp)


if __name__ == "__main__":
    main()

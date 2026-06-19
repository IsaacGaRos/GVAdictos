"""Fase 2H (continuacion): delimitacion fina de gen-12 (instituciones UE).

Alcance:
  - gen-12 = topic_id 12: instituciones y organismos de la Union Europea.
  - TUE (law_id=34): arts. 14 (Parlamento), 15 (Consejo Europeo), 17 (Comision).
  - TFUE (law_id=35): bloque institucional Parte Sexta Titulo I (arts. 223-307).

Advertencia de calidad de datos:
  El parser de EUR-Lex capturo articulos de Protocolos anejos con numeros de
  referencia bajos. En el TUE estan contaminados los arts. del marco institucional
  con contenido del Banco Europeo de Inversiones: TUE 13, 16, 18, 19. Por eso el
  Consejo de la UE, el Alto Representante y el TJUE NO se mapean desde el TUE, sino
  desde su desarrollo en el TFUE (limpio). Ver lista CONTAMINATED_*_IDS y el doc
  .claude/PILOTO_FASE2H_DELIMITACION_TUE_TFUE.md.

Diseno:
  - El PLAN se define por (law_id, article_ref) y el script resuelve el article_id
    en tiempo de ejecucion, validando existencia, law_id y no-contaminacion.

Garantias:
  - Dry-run por defecto. Solo escribe con --apply.
  - NO modifica articles, parser, importer ni normalizacion.
  - NO borra mappings ajenos: elimina solo filas propias con este mapping_basis.
  - Aborta si gen-12 ya tiene mapping fino ajeno (article_id IS NOT NULL).
  - Crea backup antes de cualquier escritura real.
  - Rechaza cualquier article_id en la lista de IDs contaminados conocidos.
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

TOPIC_ID = 12
TOPIC_NUMBER = "12"
TOPIC_PART = "general"
MAPPING_BASIS = "delimitacion_fina_claude_fase2h_gen12_instituciones_2026_06_18"
VALIDATION_STATUS = "validado_fuente_oficial_pendiente_revision_humana"

# IDs con contenido de Protocolos anejos (NO del tratado principal). Cualquier
# article_id resuelto que caiga aqui aborta el script. Ampliado respecto a Fase 2H
# inicial: se anaden TUE 16/18/19 (Estatuto EIB) detectados en este survey.
CONTAMINATED_TUE_IDS = {
    102517, 102508, 102509, 102503, 102461, 102262, 102486, 102429, 102313,
    102404, 102406, 102407,  # TUE 16, 18, 19 (Banco Europeo de Inversiones)
}
CONTAMINATED_TFUE_IDS = {
    103709, 103710, 103704, 103662, 103706, 103607, 103489, 103616, 103617,
    103514, 103587,
}
TUE, TFUE = 34, 35

# PLAN: (law_id, article_ref, priority, normative_reference, note)
PLAN: list[tuple[int, str, str, str, str]] = [
    # --- Parlamento Europeo ---
    (TUE, "14", "alta", "TUE art. 14", "gen-12 Parlamento Europeo: composicion y funciones"),
    (TFUE, "223", "media", "TFUE art. 223", "gen-12 Parlamento: eleccion por sufragio universal"),
    (TFUE, "224", "baja", "TFUE art. 224", "gen-12 Parlamento: estatuto de los partidos politicos europeos"),
    (TFUE, "225", "media", "TFUE art. 225", "gen-12 Parlamento: iniciativa de solicitud legislativa"),
    (TFUE, "226", "baja", "TFUE art. 226", "gen-12 Parlamento: comisiones de investigacion"),
    (TFUE, "227", "baja", "TFUE art. 227", "gen-12 Parlamento: derecho de peticion"),
    (TFUE, "228", "media", "TFUE art. 228", "gen-12 Parlamento: Defensor del Pueblo Europeo"),
    (TFUE, "229", "baja", "TFUE art. 229", "gen-12 Parlamento: periodos de sesiones"),
    (TFUE, "230", "baja", "TFUE art. 230", "gen-12 Parlamento: relaciones con la Comision"),
    (TFUE, "231", "baja", "TFUE art. 231", "gen-12 Parlamento: regla de mayoria"),
    (TFUE, "232", "baja", "TFUE art. 232", "gen-12 Parlamento: reglamento interno"),
    (TFUE, "233", "baja", "TFUE art. 233", "gen-12 Parlamento: informe general anual"),
    (TFUE, "234", "media", "TFUE art. 234", "gen-12 Parlamento: mocion de censura a la Comision"),
    # --- Consejo Europeo ---
    (TUE, "15", "alta", "TUE art. 15", "gen-12 Consejo Europeo: composicion y funciones"),
    (TFUE, "235", "media", "TFUE art. 235", "gen-12 Consejo Europeo: votacion y presidencia"),
    # --- Consejo de la Union Europea (TUE 16 contaminado-EIB, excluido) ---
    (TFUE, "237", "media", "TFUE art. 237", "gen-12 Consejo: convocatoria"),
    (TFUE, "238", "alta", "TFUE art. 238", "gen-12 Consejo: mayoria cualificada"),
    (TFUE, "239", "baja", "TFUE art. 239", "gen-12 Consejo: delegacion de voto"),
    (TFUE, "240", "media", "TFUE art. 240", "gen-12 Consejo: COREPER y secretaria general"),
    (TFUE, "241", "baja", "TFUE art. 241", "gen-12 Consejo: peticion de estudios a la Comision"),
    (TFUE, "242", "baja", "TFUE art. 242", "gen-12 Consejo: estatutos de comites"),
    (TFUE, "243", "baja", "TFUE art. 243", "gen-12 Consejo: sueldos y dietas"),
    # --- Comision Europea ---
    (TUE, "17", "alta", "TUE art. 17", "gen-12 Comision: composicion y funciones"),
    (TFUE, "245", "media", "TFUE art. 245", "gen-12 Comision: independencia y deberes"),
    (TFUE, "246", "baja", "TFUE art. 246", "gen-12 Comision: cese y sustitucion"),
    (TFUE, "247", "baja", "TFUE art. 247", "gen-12 Comision: cese por el TJUE"),
    (TFUE, "248", "baja", "TFUE art. 248", "gen-12 Comision: reparto de responsabilidades"),
    (TFUE, "249", "baja", "TFUE art. 249", "gen-12 Comision: reglamento interno e informe"),
    (TFUE, "250", "baja", "TFUE art. 250", "gen-12 Comision: acuerdos por mayoria"),
    # --- Tribunal de Justicia de la UE (TUE 19 contaminado-EIB, excluido) ---
    (TFUE, "251", "media", "TFUE art. 251", "gen-12 TJUE: Salas y Gran Sala"),
    (TFUE, "252", "media", "TFUE art. 252", "gen-12 TJUE: abogados generales"),
    (TFUE, "253", "baja", "TFUE art. 253", "gen-12 TJUE: jueces y abogados generales del TJ"),
    (TFUE, "254", "baja", "TFUE art. 254", "gen-12 TJUE: Tribunal General"),
    (TFUE, "256", "media", "TFUE art. 256", "gen-12 TJUE: competencias del Tribunal General"),
    (TFUE, "257", "baja", "TFUE art. 257", "gen-12 TJUE: tribunales especializados"),
    (TFUE, "263", "media", "TFUE art. 263", "gen-12 TJUE: recurso de anulacion (funcion de control)"),
    (TFUE, "265", "baja", "TFUE art. 265", "gen-12 TJUE: recurso por omision"),
    (TFUE, "267", "media", "TFUE art. 267", "gen-12 TJUE: cuestion prejudicial"),
    (TFUE, "268", "baja", "TFUE art. 268", "gen-12 TJUE: responsabilidad extracontractual"),
    (TFUE, "281", "baja", "TFUE art. 281", "gen-12 TJUE: Estatuto en protocolo independiente"),
    # --- Banco Central Europeo ---
    (TFUE, "282", "alta", "TFUE art. 282", "gen-12 BCE: SEBC y objetivos"),
    (TFUE, "283", "media", "TFUE art. 283", "gen-12 BCE: Consejo de Gobierno y Comite Ejecutivo"),
    (TFUE, "284", "baja", "TFUE art. 284", "gen-12 BCE: participacion del Consejo y la Comision"),
    # --- Tribunal de Cuentas ---
    (TFUE, "285", "alta", "TFUE art. 285", "gen-12 Tribunal de Cuentas: funcion fiscalizadora"),
    (TFUE, "286", "media", "TFUE art. 286", "gen-12 Tribunal de Cuentas: miembros e independencia"),
    (TFUE, "287", "media", "TFUE art. 287", "gen-12 Tribunal de Cuentas: examen de cuentas"),
    # --- Comite Economico y Social Europeo ---
    (TFUE, "300", "media", "TFUE art. 300", "gen-12 CESE/CdR: disposiciones comunes organos consultivos"),
    (TFUE, "301", "media", "TFUE art. 301", "gen-12 CESE: numero de miembros"),
    (TFUE, "302", "baja", "TFUE art. 302", "gen-12 CESE: nombramiento de miembros"),
    (TFUE, "303", "baja", "TFUE art. 303", "gen-12 CESE: presidencia y reglamento interno"),
    (TFUE, "304", "media", "TFUE art. 304", "gen-12 CESE: consulta"),
    # --- Comite de las Regiones ---
    (TFUE, "305", "media", "TFUE art. 305", "gen-12 CdR: numero de miembros"),
    (TFUE, "306", "baja", "TFUE art. 306", "gen-12 CdR: presidencia y reglamento interno"),
    (TFUE, "307", "media", "TFUE art. 307", "gen-12 CdR: consulta"),
]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Apply gen-12 (instituciones UE) fine article mapping.")
    p.add_argument("--apply", action="store_true",
                   help="Write changes. Without this flag, dry-run only.")
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
    dst = ROOT / "db" / f"gvadicto.backup_pre2h_gen12_{ts}.sqlite"
    shutil.copy2(DB, dst)
    return dst


def resolve_plan(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Resolve each PLAN row to a concrete article_id, validating everything."""
    errors: list[str] = []
    resolved: list[dict[str, Any]] = []
    seen_ids: set[int] = set()

    for law_id, article_ref, priority, norm_ref, note in PLAN:
        row = conn.execute(
            "SELECT id, law_id FROM articles WHERE law_id=? AND article_ref=?",
            (law_id, article_ref),
        ).fetchone()
        if not row:
            errors.append(f"{norm_ref}: no existe (law_id={law_id}, ref={article_ref})")
            continue
        article_id = int(row["id"])
        if int(row["law_id"]) != law_id:
            errors.append(f"{norm_ref}: law_id mismatch ({row['law_id']} != {law_id})")
            continue
        if article_id in CONTAMINATED_TUE_IDS or article_id in CONTAMINATED_TFUE_IDS:
            errors.append(f"{norm_ref}: article_id={article_id} CONTAMINADO (protocolo)")
            continue
        if article_id in seen_ids:
            errors.append(f"{norm_ref}: article_id={article_id} duplicado en PLAN")
            continue
        seen_ids.add(article_id)
        resolved.append({
            "law_id": law_id,
            "article_id": article_id,
            "article_ref": article_ref,
            "priority": priority,
            "normative_reference": norm_ref,
            "note": note,
        })

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        raise SystemExit("ABORT: errores al resolver el PLAN (ver arriba).")
    return resolved


def preflight(conn: sqlite3.Connection) -> dict[str, Any]:
    topic = conn.execute(
        "SELECT id, topic_number, part FROM topics WHERE id=?", (TOPIC_ID,)
    ).fetchone()
    if not topic:
        raise SystemExit(f"ABORT: no existe topic_id={TOPIC_ID}.")
    if int(topic["topic_number"]) != int(TOPIC_NUMBER) or topic["part"] != TOPIC_PART:
        raise SystemExit(
            f"ABORT: topic_id={TOPIC_ID} no es gen-12: "
            f"topic_number={topic['topic_number']}, part={topic['part']}"
        )

    for law_id in (TUE, TFUE):
        if not conn.execute("SELECT id FROM laws WHERE id=?", (law_id,)).fetchone():
            raise SystemExit(f"ABORT: no existe law_id={law_id}.")

    foreign = conn.execute(
        """
        SELECT id, mapping_basis, article_id FROM topic_sources
        WHERE topic_id=? AND article_id IS NOT NULL AND mapping_basis <> ?
        """,
        (TOPIC_ID, MAPPING_BASIS),
    ).fetchall()
    if foreign:
        sample = [dict(r) for r in foreign[:3]]
        raise SystemExit(f"ABORT: gen-12 ya tiene mapping fino ajeno: {sample}")

    broken_fk = count(
        conn,
        "SELECT COUNT(*) FROM topic_sources WHERE article_id IS NOT NULL "
        "AND article_id NOT IN (SELECT id FROM articles)",
    )
    if broken_fk:
        raise SystemExit(f"ABORT: hay {broken_fk} FKs rotas antes de aplicar.")

    resolved = resolve_plan(conn)

    return {
        "resolved": resolved,
        "planned_count": len(resolved),
        "own_existing": count(
            conn,
            "SELECT COUNT(*) FROM topic_sources WHERE topic_id=? AND mapping_basis=?",
            (TOPIC_ID, MAPPING_BASIS),
        ),
        "total_before": count(conn, "SELECT COUNT(*) FROM topic_sources"),
        "fine_before": count(conn, "SELECT COUNT(*) FROM topic_sources WHERE article_id IS NOT NULL"),
        "broken_fk_before": broken_fk,
    }


def apply_mapping(conn: sqlite3.Connection, resolved: list[dict[str, Any]]) -> tuple[int, int]:
    deleted = conn.execute(
        "DELETE FROM topic_sources WHERE topic_id=? AND mapping_basis=?",
        (TOPIC_ID, MAPPING_BASIS),
    ).rowcount
    inserted = 0
    for r in resolved:
        conn.execute(
            """
            INSERT INTO topic_sources(
                topic_id, law_id, article_id, normative_reference,
                coverage_status, mapping_basis, priority, validation_status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                TOPIC_ID, r["law_id"], r["article_id"], r["normative_reference"],
                "articulo_delimitado", MAPPING_BASIS, r["priority"],
                VALIDATION_STATUS, r["note"],
            ),
        )
        inserted += 1
    return deleted, inserted


def write_reports(result: dict[str, Any], stamp: str) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS / f"apply_fase2h_gen12_{stamp}.json"
    md_path = REPORTS / f"apply_fase2h_gen12_{stamp}.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Fase 2H gen-12 — Instituciones UE",
        "",
        f"- Mode: {'APPLY' if result['applied'] else 'DRY-RUN'}",
        f"- Topic: gen-12 / topic_id={TOPIC_ID}",
        f"- mapping_basis: `{MAPPING_BASIS}`",
        f"- Planned rows: {result['planned_count']}",
        f"- Backup: {result.get('backup') or 'n/a'}",
        "",
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
        "TUE 13/16/18/19 excluidos por contaminacion de protocolo (EIB).",
    ]
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
        print(f"  Topic: gen-12 (topic_id={TOPIC_ID})")
        print(f"  Articulos resueltos en plan: {state['planned_count']}")
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

        backup = make_backup()
        result["backup"] = str(backup)
        print(f"\n  Backup creado: {backup.name}")

        print("\n=== Aplicando mapping ===")
        deleted, inserted = apply_mapping(conn, state["resolved"])
        conn.commit()

        broken_fk_after = count(
            conn,
            "SELECT COUNT(*) FROM topic_sources WHERE article_id IS NOT NULL "
            "AND article_id NOT IN (SELECT id FROM articles)",
        )
        if broken_fk_after:
            conn.rollback()
            raise SystemExit(f"ABORT: quedaron {broken_fk_after} FKs rotas. Rollback.")

        result.update({
            "own_deleted": deleted,
            "inserted": inserted,
            "total_after": count(conn, "SELECT COUNT(*) FROM topic_sources"),
            "fine_after": count(conn, "SELECT COUNT(*) FROM topic_sources WHERE article_id IS NOT NULL"),
            "broken_fk_after": broken_fk_after,
        })
        print(f"  Filas borradas (propias): {deleted}")
        print(f"  Filas insertadas: {inserted}")
        print(f"  topic_sources despues: {result['total_after']}")
        print(f"  filas finas despues: {result['fine_after']}")
        print(f"  FKs rotas despues: {broken_fk_after}")
        print("\n=== APPLY completado con exito. ===")
    finally:
        conn.close()
    write_reports(result, stamp)


if __name__ == "__main__":
    main()

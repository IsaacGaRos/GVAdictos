"""Fase 2J: delimitacion fina de temas multinorma (2-3 leyes por tema).

Alcance:
  - gen-3 (topic_id 3): CE (Admin Publica, Gobierno, economia/hacienda, Tribunal
    de Cuentas) + Ley 50/1997 (Gobierno) + Ley 40/2015 (organizacion AGE).
  - gen-4 (topic_id 4): CE (Poder Judicial, TC, Defensor del Pueblo) + LOPJ (CGPJ).
    Nota: LO 2/1979 (TC) y LO 3/1981 (Defensor) tienen 0 articulos importados; su
    contenido se cubre via CE.
  - gen-14 (topic_id 14): LO 3/2007 + Ley 9/2003 (GV) + Ley 4/2023 (esta ultima
    acotada a deber de proteccion y medidas en el ambito administrativo).
  - esp-15 (topic_id 30): Ley 40/2015 (principios potestad sancionadora, arts 25-31)
    + Ley 39/2015 (especialidades del procedimiento sancionador).
  - esp-16 (topic_id 31): Ley 40/2015 (responsabilidad patrimonial, arts 32-37)
    + Ley 39/2015 (especialidades del procedimiento de responsabilidad patrimonial).

Diseno:
  - El PLAN se define por (topic_id, law_id, article_ref, priority, note) y el
    script resuelve el article_id en tiempo de ejecucion.

Garantias:
  - Dry-run por defecto. Solo escribe con --apply.
  - NO modifica articles, parser, importer ni normalizacion.
  - NO borra mappings ajenos: elimina solo filas propias con este mapping_basis.
  - Aborta si algun topic ya tiene mapping fino ajeno (article_id IS NOT NULL).
  - Crea backup antes de cualquier escritura real.
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

MAPPING_BASIS = "delimitacion_fina_claude_fase2j_multinorma_2026_06_18"
VALIDATION_STATUS = "validado_fuente_oficial_pendiente_revision_humana"

TOPIC_META = {
    3: ("3", "general", "gen-3"),
    4: ("4", "general", "gen-4"),
    14: ("14", "general", "gen-14"),
    30: ("15", "especial", "esp-15"),
    31: ("16", "especial", "esp-16"),
}
LAW_LABEL = {
    2: "CE", 3: "Ley 39/2015", 4: "Ley 40/2015", 7: "LO 3/2007",
    16: "Ley 4/2023", 20: "Ley 9/2003", 36: "Ley 50/1997", 37: "LOPJ",
}

# PLAN: (topic_id, law_id, article_ref, priority, note)
PLAN: list[tuple[int, int, str, str, str]] = [
    # =====================================================================
    # gen-3 (topic_id=3) — Administracion Publica, Gobierno, economia/hacienda
    # =====================================================================
    # CE - principios constitucionales de la Administracion
    (3, 2, "103", "alta", "gen-3 CE: principios de la Administracion Publica"),
    (3, 2, "104", "baja", "gen-3 CE: Fuerzas y Cuerpos de Seguridad"),
    (3, 2, "105", "media", "gen-3 CE: audiencia del ciudadano y acceso a archivos"),
    (3, 2, "106", "media", "gen-3 CE: control judicial de la Administracion"),
    (3, 2, "107", "baja", "gen-3 CE: Consejo de Estado"),
    (3, 2, "97", "alta", "gen-3 CE: el Gobierno (funciones)"),
    # CE - economia y hacienda
    (3, 2, "128", "media", "gen-3 CE: subordinacion de la riqueza al interes general"),
    (3, 2, "131", "baja", "gen-3 CE: planificacion de la actividad economica"),
    (3, 2, "133", "media", "gen-3 CE: potestad tributaria"),
    (3, 2, "134", "alta", "gen-3 CE: Presupuestos Generales del Estado"),
    (3, 2, "135", "media", "gen-3 CE: estabilidad presupuestaria"),
    (3, 2, "136", "alta", "gen-3 CE: el Tribunal de Cuentas"),
    (3, 2, "137", "baja", "gen-3 CE: organizacion territorial del Estado"),
    (3, 2, "154", "media", "gen-3 CE: Delegado del Gobierno en las CCAA"),
    # Ley 50/1997 - Gobierno
    (3, 36, "1", "alta", "gen-3 Ley 50/1997: del Gobierno"),
    (3, 36, "2", "media", "gen-3 Ley 50/1997: del Presidente del Gobierno"),
    (3, 36, "3", "baja", "gen-3 Ley 50/1997: de los Vicepresidentes"),
    (3, 36, "4", "media", "gen-3 Ley 50/1997: de los Ministros"),
    (3, 36, "5", "media", "gen-3 Ley 50/1997: del Consejo de Ministros"),
    (3, 36, "6", "baja", "gen-3 Ley 50/1997: de las Comisiones Delegadas"),
    # Ley 40/2015 - organizacion AGE
    (3, 4, "54", "alta", "gen-3 Ley 40/2015: principios de organizacion de la AGE"),
    (3, 4, "55", "alta", "gen-3 Ley 40/2015: estructura de la AGE"),
    (3, 4, "56", "media", "gen-3 Ley 40/2015: elementos organizativos basicos"),
    (3, 4, "57", "alta", "gen-3 Ley 40/2015: los Ministerios"),
    (3, 4, "58", "media", "gen-3 Ley 40/2015: organizacion interna de los Ministerios"),
    (3, 4, "61", "media", "gen-3 Ley 40/2015: los Ministros"),
    (3, 4, "66", "baja", "gen-3 Ley 40/2015: los Directores generales"),
    (3, 4, "69", "media", "gen-3 Ley 40/2015: Delegaciones y Subdelegaciones del Gobierno"),
    (3, 4, "72", "media", "gen-3 Ley 40/2015: Delegados del Gobierno en las CCAA"),
    (3, 4, "74", "baja", "gen-3 Ley 40/2015: Subdelegados del Gobierno"),
    # =====================================================================
    # gen-4 (topic_id=4) — Poder Judicial, CGPJ, TC, Defensor del Pueblo
    # =====================================================================
    # CE - Poder Judicial
    (4, 2, "117", "alta", "gen-4 CE: principios del Poder Judicial"),
    (4, 2, "118", "media", "gen-4 CE: cumplimiento de sentencias"),
    (4, 2, "119", "baja", "gen-4 CE: justicia gratuita"),
    (4, 2, "120", "baja", "gen-4 CE: publicidad de las actuaciones judiciales"),
    (4, 2, "122", "alta", "gen-4 CE: CGPJ y LOPJ (remision)"),
    (4, 2, "123", "media", "gen-4 CE: Tribunal Supremo"),
    (4, 2, "124", "media", "gen-4 CE: Ministerio Fiscal"),
    (4, 2, "125", "baja", "gen-4 CE: accion popular y Jurado"),
    (4, 2, "127", "baja", "gen-4 CE: incompatibilidades de Jueces y Magistrados"),
    # CE - Tribunal Constitucional
    (4, 2, "159", "alta", "gen-4 CE: composicion del Tribunal Constitucional"),
    (4, 2, "160", "baja", "gen-4 CE: Presidente del Tribunal Constitucional"),
    (4, 2, "161", "alta", "gen-4 CE: competencias del Tribunal Constitucional"),
    (4, 2, "162", "media", "gen-4 CE: legitimacion ante el TC"),
    (4, 2, "163", "media", "gen-4 CE: cuestion de inconstitucionalidad"),
    (4, 2, "164", "media", "gen-4 CE: efectos de las sentencias del TC"),
    (4, 2, "165", "baja", "gen-4 CE: Ley Organica del Tribunal Constitucional"),
    # CE - Defensor del Pueblo
    (4, 2, "54", "alta", "gen-4 CE: el Defensor del Pueblo"),
    # LOPJ - CGPJ
    (4, 37, "558", "alta", "gen-4 LOPJ: el CGPJ, gobierno del Poder Judicial"),
    (4, 37, "560", "alta", "gen-4 LOPJ: atribuciones del CGPJ"),
    (4, 37, "561", "media", "gen-4 LOPJ: informe sobre anteproyectos normativos"),
    (4, 37, "566", "alta", "gen-4 LOPJ: composicion del CGPJ"),
    (4, 37, "567", "media", "gen-4 LOPJ: designacion de Vocales"),
    (4, 37, "595", "media", "gen-4 LOPJ: funciones del CGPJ"),
    (4, 37, "598", "media", "gen-4 LOPJ: la Presidencia del CGPJ"),
    (4, 37, "599", "media", "gen-4 LOPJ: el Pleno del CGPJ"),
    # =====================================================================
    # gen-14 (topic_id=14) — Igualdad (LO 3/2007 + Ley 9/2003 + Ley 4/2023)
    # =====================================================================
    # LO 3/2007
    (14, 7, "1", "alta", "gen-14 LO 3/2007: objeto de la ley"),
    (14, 7, "2", "media", "gen-14 LO 3/2007: ambito de aplicacion"),
    (14, 7, "3", "alta", "gen-14 LO 3/2007: principio de igualdad de trato"),
    (14, 7, "4", "media", "gen-14 LO 3/2007: integracion del principio de igualdad"),
    (14, 7, "6", "alta", "gen-14 LO 3/2007: discriminacion directa e indirecta"),
    (14, 7, "7", "alta", "gen-14 LO 3/2007: acoso sexual y por razon de sexo"),
    (14, 7, "8", "media", "gen-14 LO 3/2007: discriminacion por embarazo o maternidad"),
    (14, 7, "11", "alta", "gen-14 LO 3/2007: acciones positivas"),
    (14, 7, "14", "alta", "gen-14 LO 3/2007: criterios de actuacion de los poderes publicos"),
    (14, 7, "15", "alta", "gen-14 LO 3/2007: transversalidad del principio de igualdad"),
    (14, 7, "17", "media", "gen-14 LO 3/2007: Plan Estrategico de Igualdad de Oportunidades"),
    (14, 7, "19", "media", "gen-14 LO 3/2007: informes de impacto de genero"),
    # Ley 9/2003 (GV)
    (14, 20, "1", "alta", "gen-14 Ley 9/2003: objeto"),
    (14, 20, "2", "alta", "gen-14 Ley 9/2003: principios generales"),
    (14, 20, "3", "media", "gen-14 Ley 9/2003: ambito de la ley"),
    (14, 20, "4", "alta", "gen-14 Ley 9/2003: principios rectores de la accion administrativa"),
    (14, 20, "4 b", "media", "gen-14 Ley 9/2003: informes de impacto de genero"),
    (14, 20, "13", "media", "gen-14 Ley 9/2003: acceso al empleo en condiciones de igualdad"),
    (14, 20, "16", "baja", "gen-14 Ley 9/2003: Red Valenciana de Igualdad"),
    # Ley 4/2023 (acotada: deber de proteccion + ambito administrativo)
    (14, 16, "4", "alta", "gen-14 Ley 4/2023: deber de proteccion"),
    (14, 16, "5", "media", "gen-14 Ley 4/2023: reconocimiento y apoyo institucional"),
    (14, 16, "8", "media", "gen-14 Ley 4/2023: colaboracion entre Administraciones publicas"),
    (14, 16, "11", "media", "gen-14 Ley 4/2023: empleo publico"),
    (14, 16, "12", "media", "gen-14 Ley 4/2023: formacion del personal de las Administraciones"),
    (14, 16, "13", "media", "gen-14 Ley 4/2023: documentacion administrativa"),
    (14, 16, "63", "media", "gen-14 Ley 4/2023: actuacion administrativa contra la discriminacion"),
    # =====================================================================
    # esp-15 (topic_id=30) — Potestad sancionadora
    # =====================================================================
    # Ley 40/2015 - principios de la potestad sancionadora
    (30, 4, "25", "alta", "esp-15 Ley 40/2015: principio de legalidad"),
    (30, 4, "26", "media", "esp-15 Ley 40/2015: irretroactividad"),
    (30, 4, "27", "alta", "esp-15 Ley 40/2015: principio de tipicidad"),
    (30, 4, "28", "alta", "esp-15 Ley 40/2015: responsabilidad"),
    (30, 4, "29", "alta", "esp-15 Ley 40/2015: principio de proporcionalidad"),
    (30, 4, "30", "media", "esp-15 Ley 40/2015: prescripcion"),
    (30, 4, "31", "media", "esp-15 Ley 40/2015: concurrencia de sanciones"),
    # Ley 39/2015 - especialidades del procedimiento sancionador
    (30, 3, "53", "media", "esp-15 Ley 39/2015: derechos del presunto responsable (53.2)"),
    (30, 3, "63", "alta", "esp-15 Ley 39/2015: especialidades en el inicio de sancionadores"),
    (30, 3, "64", "alta", "esp-15 Ley 39/2015: acuerdo de iniciacion en sancionadores"),
    (30, 3, "77", "media", "esp-15 Ley 39/2015: medios y periodo de prueba"),
    (30, 3, "85", "alta", "esp-15 Ley 39/2015: terminacion en los procedimientos sancionadores"),
    (30, 3, "89", "alta", "esp-15 Ley 39/2015: propuesta de resolucion en sancionadores"),
    (30, 3, "90", "alta", "esp-15 Ley 39/2015: especialidades de la resolucion sancionadora"),
    # =====================================================================
    # esp-16 (topic_id=31) — Responsabilidad patrimonial
    # =====================================================================
    # Ley 40/2015 - responsabilidad patrimonial
    (31, 4, "32", "alta", "esp-16 Ley 40/2015: principios de la responsabilidad"),
    (31, 4, "33", "media", "esp-16 Ley 40/2015: responsabilidad concurrente de las AAPP"),
    (31, 4, "34", "alta", "esp-16 Ley 40/2015: indemnizacion"),
    (31, 4, "35", "media", "esp-16 Ley 40/2015: responsabilidad de Derecho Privado"),
    (31, 4, "36", "alta", "esp-16 Ley 40/2015: exigencia de RP a autoridades y personal"),
    (31, 4, "37", "baja", "esp-16 Ley 40/2015: responsabilidad penal"),
    # Ley 39/2015 - especialidades del procedimiento de RP
    (31, 3, "65", "alta", "esp-16 Ley 39/2015: especialidades en inicio de oficio de RP"),
    (31, 3, "67", "alta", "esp-16 Ley 39/2015: solicitudes de iniciacion en RP"),
    (31, 3, "81", "alta", "esp-16 Ley 39/2015: solicitud de informes y dictamenes en RP"),
    (31, 3, "82", "media", "esp-16 Ley 39/2015: tramite de audiencia"),
    (31, 3, "91", "alta", "esp-16 Ley 39/2015: especialidades de la resolucion en RP"),
    (31, 3, "92", "media", "esp-16 Ley 39/2015: competencia para la resolucion de RP"),
    (31, 3, "96", "media", "esp-16 Ley 39/2015: tramitacion simplificada"),
]

TOPIC_IDS = sorted({row[0] for row in PLAN})


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Apply Fase 2J multinorma fine article mapping.")
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
    dst = ROOT / "db" / f"gvadicto.backup_pre2j_multinorma_{ts}.sqlite"
    shutil.copy2(DB, dst)
    return dst


def resolve_plan(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    errors: list[str] = []
    resolved: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()

    for topic_id, law_id, article_ref, priority, note in PLAN:
        row = conn.execute(
            "SELECT id, law_id FROM articles WHERE law_id=? AND article_ref=?",
            (law_id, article_ref),
        ).fetchone()
        label = f"{LAW_LABEL.get(law_id, law_id)} art. {article_ref} (topic {topic_id})"
        if not row:
            errors.append(f"{label}: no existe")
            continue
        article_id = int(row["id"])
        if int(row["law_id"]) != law_id:
            errors.append(f"{label}: law_id mismatch")
            continue
        key = (topic_id, article_id)
        if key in seen:
            errors.append(f"{label}: duplicado en PLAN")
            continue
        seen.add(key)
        resolved.append({
            "topic_id": topic_id,
            "law_id": law_id,
            "article_id": article_id,
            "article_ref": article_ref,
            "priority": priority,
            "normative_reference": f"{LAW_LABEL.get(law_id, law_id)} art. {article_ref}",
            "note": note,
        })

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        raise SystemExit("ABORT: errores al resolver el PLAN (ver arriba).")
    return resolved


def preflight(conn: sqlite3.Connection) -> dict[str, Any]:
    for topic_id, (topic_number, part, label) in TOPIC_META.items():
        row = conn.execute(
            "SELECT id, topic_number, part FROM topics WHERE id=?", (topic_id,)
        ).fetchone()
        if not row:
            raise SystemExit(f"ABORT: no existe topic_id={topic_id}")
        if int(row["topic_number"]) != int(topic_number) or row["part"] != part:
            raise SystemExit(
                f"ABORT: topic_id={topic_id} no es {label}: "
                f"topic_number={row['topic_number']}, part={row['part']}"
            )

    for law_id in {row[1] for row in PLAN}:
        if not conn.execute("SELECT id FROM laws WHERE id=?", (law_id,)).fetchone():
            raise SystemExit(f"ABORT: no existe law_id={law_id}")

    for topic_id in TOPIC_IDS:
        foreign = conn.execute(
            """
            SELECT id, mapping_basis, article_id FROM topic_sources
            WHERE topic_id=? AND article_id IS NOT NULL AND mapping_basis <> ?
            """,
            (topic_id, MAPPING_BASIS),
        ).fetchall()
        if foreign:
            sample = [dict(r) for r in foreign[:3]]
            raise SystemExit(f"ABORT: topic_id={topic_id} ya tiene mapping fino ajeno: {sample}")

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
            f"SELECT COUNT(*) FROM topic_sources WHERE topic_id IN "
            f"({','.join('?'*len(TOPIC_IDS))}) AND mapping_basis=?",
            (*TOPIC_IDS, MAPPING_BASIS),
        ),
        "total_before": count(conn, "SELECT COUNT(*) FROM topic_sources"),
        "fine_before": count(conn, "SELECT COUNT(*) FROM topic_sources WHERE article_id IS NOT NULL"),
        "broken_fk_before": broken_fk,
    }


def apply_mapping(conn: sqlite3.Connection, resolved: list[dict[str, Any]]) -> tuple[int, int]:
    deleted = conn.execute(
        f"DELETE FROM topic_sources WHERE topic_id IN "
        f"({','.join('?'*len(TOPIC_IDS))}) AND mapping_basis=?",
        (*TOPIC_IDS, MAPPING_BASIS),
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
                r["topic_id"], r["law_id"], r["article_id"], r["normative_reference"],
                "articulo_delimitado", MAPPING_BASIS, r["priority"],
                VALIDATION_STATUS, r["note"],
            ),
        )
        inserted += 1
    return deleted, inserted


def write_reports(result: dict[str, Any], stamp: str) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS / f"apply_fase2j_multinorma_{stamp}.json"
    md_path = REPORTS / f"apply_fase2j_multinorma_{stamp}.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    by_topic: dict[int, int] = {}
    for row in PLAN:
        by_topic[row[0]] = by_topic.get(row[0], 0) + 1

    lines = [
        "# Fase 2J — Delimitacion fina de temas multinorma",
        "",
        f"- Mode: {'APPLY' if result['applied'] else 'DRY-RUN'}",
        f"- mapping_basis: `{MAPPING_BASIS}`",
        f"- Planned rows: {result['planned_count']}",
        f"- Backup: {result.get('backup') or 'n/a'}",
        "",
        "## Por topic",
        "",
        "| Topic | Filas |",
        "| --- | ---: |",
    ]
    for topic_id in TOPIC_IDS:
        lines.append(f"| {TOPIC_META[topic_id][2]} (id={topic_id}) | {by_topic[topic_id]} |")
    lines.extend([
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
        print(f"  Topics: {TOPIC_IDS}")
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

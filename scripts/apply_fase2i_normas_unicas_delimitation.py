"""Fase 2I: delimitacion fina de temas de norma unica.

Alcance (3 temas con una sola ley vinculada y estructura clara):
  - gen-15 = topic_id 15: LO 1/2004 (law_id=8) violencia de genero.
      Titulos Preliminar a III (arts. 1-32): objeto, sensibilizacion, derechos
      de las victimas y tutela institucional. Se EXCLUYEN los Titulos IV y V
      (tutela penal y judicial, arts. 33-72), que son reformas del CP/LECrim
      fuera del enunciado.
  - esp-2 = topic_id 17: Ley 5/1983 (law_id=17) Gobierno Valenciano.
      Bloque de potestad reglamentaria del Consell (arts. 13, 18, 31-34, 37, 39).
  - esp-4 = topic_id 19: Ley 39/2015 (law_id=3) LPAC.
      Acto administrativo: concepto y elementos (34-36), eficacia basica (38-39),
      clases de recursos (112) y fin de la via administrativa (114).

Temas evaluados y DESCARTADOS por falta de anclaje en la ley vinculada (fallback honesto):
  - esp-5 (topic_id 20): "eficacia temporal de las normas". La LPAC regula la
    eficacia de los ACTOS (art. 39 = Efectos del acto), no de las NORMAS. La
    materia (entrada en vigor, derogacion tacita, derecho transitorio,
    irretroactividad) es teoria general (CC art. 2, CE art. 9.3) ausente de la BD.
  - esp-28 (topic_id 43): "planificacion estrategica". La Ley 6/2024 es de
    simplificacion administrativa; no tiene titulo de planificacion estrategica.
    Tema metodologico sin articulado concreto en la ley vinculada.

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

MAPPING_BASIS = "delimitacion_fina_claude_fase2i_normas_unicas_2026_06_18"
VALIDATION_STATUS = "validado_fuente_oficial_pendiente_revision_humana"

# topic_id -> (topic_number, part, etiqueta legible)
TOPIC_META = {
    15: ("15", "general", "gen-15"),
    17: ("2", "especial", "esp-2"),
    19: ("4", "especial", "esp-4"),
}
# law_id -> etiqueta para normative_reference
LAW_LABEL = {8: "LO 1/2004", 17: "Ley 5/1983", 3: "Ley 39/2015"}

# PLAN: (topic_id, law_id, article_ref, priority, note)
PLAN: list[tuple[int, int, str, str, str]] = [
    # =====================================================================
    # gen-15 (topic_id=15) — LO 1/2004 (law_id=8), arts. 1-32
    # =====================================================================
    # Titulo Preliminar
    (15, 8, "1", "alta", "gen-15 LO 1/2004: objeto de la ley"),
    (15, 8, "2", "alta", "gen-15 LO 1/2004: principios rectores"),
    # Titulo I - sensibilizacion, prevencion y deteccion
    (15, 8, "3", "media", "gen-15 LO 1/2004: planes de sensibilizacion"),
    (15, 8, "4", "media", "gen-15 LO 1/2004: ambito educativo - principios y valores"),
    (15, 8, "5", "baja", "gen-15 LO 1/2004: escolarizacion inmediata"),
    (15, 8, "6", "baja", "gen-15 LO 1/2004: fomento de la igualdad en educacion"),
    (15, 8, "7", "baja", "gen-15 LO 1/2004: formacion del profesorado"),
    (15, 8, "8", "baja", "gen-15 LO 1/2004: participacion en consejos escolares"),
    (15, 8, "9", "baja", "gen-15 LO 1/2004: inspeccion educativa"),
    (15, 8, "10", "baja", "gen-15 LO 1/2004: publicidad ilicita"),
    (15, 8, "11", "baja", "gen-15 LO 1/2004: Delegacion Especial del Gobierno"),
    (15, 8, "12", "baja", "gen-15 LO 1/2004: titulares de la accion de cesacion"),
    (15, 8, "13", "baja", "gen-15 LO 1/2004: medios de comunicacion"),
    (15, 8, "14", "baja", "gen-15 LO 1/2004: imagen de la mujer en los medios"),
    (15, 8, "15", "media", "gen-15 LO 1/2004: sensibilizacion en el ambito sanitario"),
    (15, 8, "16", "baja", "gen-15 LO 1/2004: Comision contra la Violencia (sanidad)"),
    # Titulo II - derechos de las mujeres victimas
    (15, 8, "17", "alta", "gen-15 LO 1/2004: garantia de los derechos de las victimas"),
    (15, 8, "18", "alta", "gen-15 LO 1/2004: derecho a la informacion"),
    (15, 8, "19", "alta", "gen-15 LO 1/2004: derecho a asistencia social integral"),
    (15, 8, "19 b", "media", "gen-15 LO 1/2004: derecho a la atencion sanitaria"),
    (15, 8, "20", "media", "gen-15 LO 1/2004: derecho a la asistencia juridica"),
    (15, 8, "21", "media", "gen-15 LO 1/2004: derechos laborales y de Seguridad Social"),
    (15, 8, "22", "baja", "gen-15 LO 1/2004: programa especifico de empleo"),
    (15, 8, "23", "media", "gen-15 LO 1/2004: acreditacion de la situacion (trabajadoras)"),
    (15, 8, "24", "baja", "gen-15 LO 1/2004: ambito de los derechos (funcionarias)"),
    (15, 8, "25", "baja", "gen-15 LO 1/2004: justificacion de faltas de asistencia"),
    (15, 8, "26", "baja", "gen-15 LO 1/2004: acreditacion de la situacion (funcionarias)"),
    (15, 8, "27", "media", "gen-15 LO 1/2004: ayudas sociales"),
    (15, 8, "28", "baja", "gen-15 LO 1/2004: acceso a vivienda y residencias publicas"),
    (15, 8, "28 b", "media", "gen-15 LO 1/2004: alcance y garantia del derecho a reparacion"),
    (15, 8, "28 t", "baja", "gen-15 LO 1/2004: medidas para garantizar la reparacion"),
    # Titulo III - tutela institucional
    (15, 8, "29", "alta", "gen-15 LO 1/2004: Delegacion del Gobierno contra la Violencia"),
    (15, 8, "30", "media", "gen-15 LO 1/2004: Observatorio Estatal de Violencia sobre la Mujer"),
    (15, 8, "31", "media", "gen-15 LO 1/2004: Fuerzas y Cuerpos de Seguridad"),
    (15, 8, "32", "media", "gen-15 LO 1/2004: planes de colaboracion y coordinacion"),
    # =====================================================================
    # esp-2 (topic_id=17) — Ley 5/1983 (law_id=17), potestad reglamentaria
    # =====================================================================
    (17, 17, "13", "alta", "esp-2 Ley 5/1983: el Consell ostenta la potestad reglamentaria"),
    (17, 17, "18", "media", "esp-2 Ley 5/1983: funciones del Consell en materia normativa"),
    (17, 17, "31", "alta", "esp-2 Ley 5/1983: ejercicio de la potestad reglamentaria"),
    (17, 17, "32", "alta", "esp-2 Ley 5/1983: clases y jerarquia de las normas reglamentarias"),
    (17, 17, "33", "media", "esp-2 Ley 5/1983: forma de Decreto del Consell"),
    (17, 17, "34", "media", "esp-2 Ley 5/1983: forma de Decreto del President"),
    (17, 17, "37", "media", "esp-2 Ley 5/1983: forma de Orden de Conselleria"),
    (17, 17, "39", "alta", "esp-2 Ley 5/1983: limites de la potestad reglamentaria"),
    # =====================================================================
    # esp-4 (topic_id=19) — Ley 39/2015 (law_id=3), acto administrativo
    # =====================================================================
    (19, 3, "34", "alta", "esp-4 Ley 39/2015: produccion y contenido del acto"),
    (19, 3, "35", "alta", "esp-4 Ley 39/2015: motivacion"),
    (19, 3, "36", "alta", "esp-4 Ley 39/2015: forma"),
    (19, 3, "38", "media", "esp-4 Ley 39/2015: ejecutividad"),
    (19, 3, "39", "media", "esp-4 Ley 39/2015: efectos del acto"),
    (19, 3, "112", "media", "esp-4 Ley 39/2015: objeto y clases de recursos"),
    (19, 3, "114", "alta", "esp-4 Ley 39/2015: fin de la via administrativa"),
]

TOPIC_IDS = sorted({row[0] for row in PLAN})


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Apply Fase 2I norma-unica fine article mapping.")
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
    dst = ROOT / "db" / f"gvadicto.backup_pre2i_normas_unicas_{ts}.sqlite"
    shutil.copy2(DB, dst)
    return dst


def resolve_plan(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    errors: list[str] = []
    resolved: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()  # (topic_id, article_id)

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
    json_path = REPORTS / f"apply_fase2i_normas_unicas_{stamp}.json"
    md_path = REPORTS / f"apply_fase2i_normas_unicas_{stamp}.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    by_topic: dict[int, int] = {}
    for row in PLAN:
        by_topic[row[0]] = by_topic.get(row[0], 0) + 1

    lines = [
        "# Fase 2I — Delimitacion fina de temas de norma unica",
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
        "Descartados por falta de anclaje: esp-5 (id=20), esp-28 (id=43).",
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

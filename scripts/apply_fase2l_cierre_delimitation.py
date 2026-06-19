"""Fase 2L: cierre de la delimitacion fina de los temas abordables restantes.

Alcance (8 temas con normativa importada y anclaje claro):
  - gen-1 (id=1): CE 1978 (panoramica): Titulo Preliminar, derechos, Corona, Cortes,
    funcion legislativa, tratados internacionales, reforma constitucional.
  - gen-5 (id=5): CE Titulo VIII (organizacion territorial) + EACV.
  - esp-1 (id=16): fuentes del derecho administrativo (nucleo constitucional: tipos de
    ley, rango, tratados internacionales). La primacia del DUE queda pendiente por
    contaminacion de protocolos en TUE/TFUE (ver gen-13).
  - esp-6 (id=21): iniciativa legislativa y potestad reglamentaria (LPAC Titulo VI +
    Ley 5/1983 procedimiento normativo del Consell).
  - esp-8 (id=23): Tribunal Constitucional (regulacion constitucional, CE 159-165). Los
    procedimientos (LOTC) no estan importados: cobertura parcial honesta.
  - esp-24 (id=39): expropiacion forzosa (Reglamento LEF 1957; la Ley LEF 1954 tiene 0
    articulos importados, se usa su reglamento de desarrollo).
  - esp-30 (id=45): proteccion de informantes y conflicto de interes (Ley 2/2023 estatal
    + Ley 4/2021 FPV + Ley 8/2016 + Ley 1/2022).
  - esp-39 (id=54): financiacion de las CCAA (LOFCA + Ley 22/2009 + Ley 13/1997 + Ley 22/2001).

NO se delimitan (bloqueados, documentados; quedan en fallback honesto):
  - gen-13 (id=13): valores/competencias UE -> TUE/TFUE contaminados con protocolos.
  - esp-3 (id=18): Admin como persona juridica -> fuente real (LRJSP art 3) no vinculada;
    LOPJ no es la fuente; tema doctrinal.
  - esp-5 (id=20): eficacia temporal de las normas -> sin anclaje en ley vinculada.
  - esp-26 (id=41): gobernanza/buena administracion -> Carta DDFF UE art 41 NO importado
    (solo art 51); nucleo doctrinal (libro blanco UE, Agenda 2030).
  - esp-28 (id=43): planificacion estrategica -> sin articulado concreto en Ley 6/2024.

Garantias: dry-run por defecto; backup; no toca articles/parser/importer; no borra
mappings ajenos; aborta si hay mapping fino ajeno; valida unicidad de conjuntos (check 6).
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

MAPPING_BASIS = "delimitacion_fina_claude_fase2l_cierre_2026_06_19"
VALIDATION_STATUS = "validado_fuente_oficial_pendiente_revision_humana"

TOPIC_META = {
    1: ("1", "general", "gen-1"),
    5: ("5", "general", "gen-5"),
    16: ("1", "especial", "esp-1"),
    21: ("6", "especial", "esp-6"),
    23: ("8", "especial", "esp-8"),
    39: ("24", "especial", "esp-24"),
    45: ("30", "especial", "esp-30"),
    54: ("39", "especial", "esp-39"),
}
LAW_LABEL = {
    2: "CE", 3: "Ley 39/2015", 15: "Ley 4/2021", 17: "Ley 5/1983", 42: "EACV",
    53: "Reglamento LEF", 57: "Ley 1/2022", 60: "Ley 2/2023", 63: "LOFCA",
    64: "Ley 22/2009", 70: "Ley 13/1997", 71: "Ley 22/2001", 74: "Ley 8/2016",
}
CE = 2

# PLAN: (topic_id, law_id, article_ref, priority, note)
PLAN: list[tuple[int, int, str, str, str]] = [
    # ============ gen-1 (id=1) — CE 1978 (panoramica) ============
    (1, CE, "1", "alta", "gen-1 CE: Estado social y democratico; valores superiores"),
    (1, CE, "2", "alta", "gen-1 CE: unidad de la Nacion y autonomias"),
    (1, CE, "3", "baja", "gen-1 CE: lenguas oficiales"),
    (1, CE, "9", "alta", "gen-1 CE: sujecion a la Constitucion; principios (jerarquia, legalidad)"),
    (1, CE, "10", "alta", "gen-1 CE: dignidad y derechos; interpretacion conforme a tratados"),
    (1, CE, "14", "alta", "gen-1 CE: igualdad ante la ley"),
    (1, CE, "15", "media", "gen-1 CE: derecho a la vida"),
    (1, CE, "16", "media", "gen-1 CE: libertad ideologica y religiosa"),
    (1, CE, "20", "media", "gen-1 CE: libertad de expresion e informacion"),
    (1, CE, "23", "media", "gen-1 CE: derecho de participacion y acceso a funciones publicas"),
    (1, CE, "27", "media", "gen-1 CE: derecho a la educacion"),
    (1, CE, "53", "alta", "gen-1 CE: garantias de los derechos fundamentales"),
    (1, CE, "55", "baja", "gen-1 CE: suspension de derechos"),
    (1, CE, "56", "alta", "gen-1 CE: la Corona; el Rey como Jefe del Estado"),
    (1, CE, "62", "alta", "gen-1 CE: funciones del Rey"),
    (1, CE, "63", "baja", "gen-1 CE: el Rey y las relaciones internacionales"),
    (1, CE, "64", "baja", "gen-1 CE: refrendo de los actos del Rey"),
    (1, CE, "66", "alta", "gen-1 CE: las Cortes Generales"),
    (1, CE, "68", "media", "gen-1 CE: composicion del Congreso"),
    (1, CE, "69", "media", "gen-1 CE: composicion del Senado"),
    (1, CE, "72", "baja", "gen-1 CE: autonomia de las camaras"),
    (1, CE, "81", "alta", "gen-1 CE: leyes organicas"),
    (1, CE, "82", "media", "gen-1 CE: legislacion delegada"),
    (1, CE, "86", "alta", "gen-1 CE: decretos-leyes"),
    (1, CE, "87", "alta", "gen-1 CE: iniciativa legislativa"),
    (1, CE, "90", "baja", "gen-1 CE: relaciones entre camaras (tramitacion en el Senado)"),
    (1, CE, "93", "alta", "gen-1 CE: tratados que ceden competencias"),
    (1, CE, "94", "media", "gen-1 CE: tratados que requieren autorizacion de las Cortes"),
    (1, CE, "95", "media", "gen-1 CE: tratados contrarios a la Constitucion"),
    (1, CE, "96", "media", "gen-1 CE: integracion de los tratados en el ordenamiento"),
    (1, CE, "166", "media", "gen-1 CE: iniciativa de reforma constitucional"),
    (1, CE, "167", "media", "gen-1 CE: procedimiento ordinario de reforma"),
    (1, CE, "168", "alta", "gen-1 CE: procedimiento agravado de reforma"),
    (1, CE, "169", "baja", "gen-1 CE: limites temporales a la reforma"),
    # ============ gen-5 (id=5) — CE Titulo VIII + EACV ============
    (5, CE, "137", "alta", "gen-5 CE: organizacion territorial; principios generales"),
    (5, CE, "138", "media", "gen-5 CE: principio de solidaridad"),
    (5, CE, "139", "media", "gen-5 CE: igualdad de derechos en todo el territorio"),
    (5, CE, "140", "alta", "gen-5 CE: autonomia municipal"),
    (5, CE, "141", "media", "gen-5 CE: la provincia"),
    (5, CE, "142", "media", "gen-5 CE: haciendas locales"),
    (5, CE, "143", "alta", "gen-5 CE: derecho a la autonomia (CCAA)"),
    (5, CE, "147", "alta", "gen-5 CE: los Estatutos de Autonomia"),
    (5, CE, "148", "alta", "gen-5 CE: competencias de las CCAA"),
    (5, CE, "149", "alta", "gen-5 CE: competencias exclusivas del Estado"),
    (5, CE, "150", "media", "gen-5 CE: leyes marco, de transferencia y de armonizacion"),
    (5, CE, "152", "media", "gen-5 CE: organizacion institucional de las CCAA"),
    (5, CE, "153", "media", "gen-5 CE: control de la actividad de las CCAA"),
    (5, CE, "155", "alta", "gen-5 CE: coercion estatal"),
    (5, CE, "156", "media", "gen-5 CE: autonomia financiera de las CCAA"),
    (5, CE, "157", "media", "gen-5 CE: recursos de las CCAA"),
    (5, 42, "1", "media", "gen-5 EACV: la Comunitat Valenciana como nacionalidad historica"),
    # ============ esp-1 (id=16) — fuentes del derecho administrativo ============
    (16, CE, "9", "alta", "esp-1 CE: jerarquia normativa, legalidad, seguridad juridica"),
    (16, CE, "81", "alta", "esp-1 CE: leyes organicas (clases de ley)"),
    (16, CE, "82", "media", "esp-1 CE: decretos legislativos (legislacion delegada)"),
    (16, CE, "83", "baja", "esp-1 CE: limites de las leyes de bases"),
    (16, CE, "85", "media", "esp-1 CE: disposiciones del Gobierno con rango de ley"),
    (16, CE, "86", "alta", "esp-1 CE: decretos-leyes"),
    (16, CE, "93", "media", "esp-1 CE: tratados que atribuyen competencias (Derecho de la UE)"),
    (16, CE, "96", "media", "esp-1 CE: tratados internacionales en el ordenamiento interno"),
    # ============ esp-6 (id=21) — iniciativa legislativa y potestad reglamentaria ============
    (21, 3, "127", "alta", "esp-6 LPAC: iniciativa legislativa y potestad para dictar normas"),
    (21, 3, "128", "alta", "esp-6 LPAC: potestad reglamentaria"),
    (21, 3, "129", "alta", "esp-6 LPAC: principios de buena regulacion"),
    (21, 3, "130", "media", "esp-6 LPAC: evaluacion y adaptacion de la normativa"),
    (21, 3, "131", "media", "esp-6 LPAC: publicidad de las normas"),
    (21, 3, "132", "alta", "esp-6 LPAC: planificacion normativa"),
    (21, 3, "133", "media", "esp-6 LPAC: participacion de los ciudadanos en la elaboracion"),
    (21, 17, "18", "media", "esp-6 Ley 5/1983: funciones del Consell en materia normativa"),
    (21, 17, "43", "media", "esp-6 Ley 5/1983: procedimiento de elaboracion de disposiciones"),
    (21, 17, "44", "baja", "esp-6 Ley 5/1983: tramitacion de proyectos normativos"),
    (21, 17, "45", "baja", "esp-6 Ley 5/1983: aprobacion de disposiciones generales"),
    # ============ esp-8 (id=23) — Tribunal Constitucional (regulacion constitucional) ============
    (23, CE, "159", "alta", "esp-8 CE: composicion del Tribunal Constitucional"),
    (23, CE, "160", "baja", "esp-8 CE: Presidencia del TC"),
    (23, CE, "161", "alta", "esp-8 CE: competencias del TC (recursos y conflictos)"),
    (23, CE, "162", "media", "esp-8 CE: legitimacion ante el TC"),
    (23, CE, "163", "media", "esp-8 CE: cuestion de inconstitucionalidad"),
    (23, CE, "164", "media", "esp-8 CE: efectos de las sentencias del TC"),
    (23, CE, "165", "baja", "esp-8 CE: remision a la Ley Organica del TC"),
    # ============ esp-24 (id=39) — expropiacion forzosa (Reglamento LEF 1957) ============
    (39, 53, "1", "alta", "esp-24 RLEF: concepto y fundamento de la expropiacion"),
    (39, 53, "2", "media", "esp-24 RLEF: expropiacion de facultades parciales del dominio"),
    (39, 53, "3", "alta", "esp-24 RLEF: sujetos (expropiante, beneficiario, expropiado)"),
    (39, 53, "4", "media", "esp-24 RLEF: beneficiario distinto del expropiante"),
    (39, 53, "5", "baja", "esp-24 RLEF: facultades del beneficiario"),
    (39, 53, "10", "alta", "esp-24 RLEF: declaracion de utilidad publica o interes social (causa)"),
    (39, 53, "15", "media", "esp-24 RLEF: objeto; necesidad de ocupacion"),
    (39, 53, "16", "media", "esp-24 RLEF: relacion de bienes y derechos a expropiar"),
    (39, 53, "17", "media", "esp-24 RLEF: informacion publica de la relacion"),
    (39, 53, "20", "alta", "esp-24 RLEF: acuerdo de necesidad de ocupacion"),
    (39, 53, "29", "media", "esp-24 RLEF: justiprecio; pieza separada"),
    (39, 53, "30", "media", "esp-24 RLEF: hoja de aprecio"),
    (39, 53, "31", "baja", "esp-24 RLEF: tasacion pericial"),
    (39, 53, "48", "media", "esp-24 RLEF: pago del justiprecio"),
    (39, 53, "49", "baja", "esp-24 RLEF: libramiento para el pago"),
    (39, 53, "51", "baja", "esp-24 RLEF: consignacion del justiprecio"),
    (39, 53, "52", "media", "esp-24 RLEF: efectos sobre arrendamientos; ocupacion"),
    (39, 53, "56", "alta", "esp-24 RLEF: procedimiento de urgencia (urgente ocupacion)"),
    # ============ esp-30 (id=45) — proteccion de informantes y conflicto de interes ============
    (45, 60, "16", "media", "esp-30 Ley 2/2023: comunicacion por canal externo de informacion"),
    (45, 60, "21", "alta", "esp-30 Ley 2/2023: derechos y garantias del informante"),
    (45, 60, "23", "baja", "esp-30 Ley 2/2023: traslado de la comunicacion"),
    (45, 60, "24", "baja", "esp-30 Ley 2/2023: informaciones de competencia de las autoridades"),
    (45, 15, "76", "media", "esp-30 Ley 4/2021 FPV: derechos individuales del personal"),
    (45, 15, "78", "alta", "esp-30 Ley 4/2021 FPV: derecho a la proteccion del personal informante"),
    (45, 74, "6", "alta", "esp-30 Ley 8/2016: inhibicion y abstencion (conflicto de interes)"),
    (45, 74, "9", "media", "esp-30 Ley 8/2016: Registro de Control de Conflictos de Intereses"),
    (45, 74, "10", "media", "esp-30 Ley 8/2016: Oficina de Control del Conflicto de Intereses"),
    (45, 74, "14", "media", "esp-30 Ley 8/2016: tramitacion y consecuencias del conflicto"),
    # ============ esp-39 (id=54) — financiacion de las CCAA ============
    (54, 63, "1", "alta", "esp-39 LOFCA: autonomia financiera de las CCAA"),
    (54, 63, "2", "media", "esp-39 LOFCA: principios de coordinacion"),
    (54, 63, "4", "alta", "esp-39 LOFCA: recursos de las CCAA"),
    (54, 63, "5", "baja", "esp-39 LOFCA: ingresos de Derecho privado"),
    (54, 63, "6", "media", "esp-39 LOFCA: tributos propios de las CCAA"),
    (54, 63, "7", "baja", "esp-39 LOFCA: tasas"),
    (54, 63, "10", "alta", "esp-39 LOFCA: tributos cedidos"),
    (54, 63, "11", "media", "esp-39 LOFCA: tributos susceptibles de cesion"),
    (54, 63, "12", "baja", "esp-39 LOFCA: recargos sobre tributos del Estado"),
    (54, 64, "1", "media", "esp-39 Ley 22/2009: objeto del sistema de financiacion"),
    (54, 64, "2", "alta", "esp-39 Ley 22/2009: necesidades globales de financiacion"),
    (54, 64, "4", "media", "esp-39 Ley 22/2009: recursos adicionales que se integran"),
    (54, 64, "7", "media", "esp-39 Ley 22/2009: recursos financieros del sistema"),
    (54, 64, "8", "alta", "esp-39 Ley 22/2009: capacidad tributaria"),
    (54, 70, "1", "media", "esp-39 Ley 13/1997: ambito (tramo autonomico CV)"),
    (54, 70, "2", "media", "esp-39 Ley 13/1997: escala autonomica del IRPF"),
    (54, 70, "3", "baja", "esp-39 Ley 13/1997: cuotas autonomicas"),
    (54, 71, "1", "baja", "esp-39 Ley 22/2001: fundamento del Fondo de Compensacion Interterritorial"),
    (54, 71, "2", "media", "esp-39 Ley 22/2001: cuantia y destino del FCI"),
    (54, 71, "4", "baja", "esp-39 Ley 22/2001: criterios de distribucion del FCI"),
]

TOPIC_IDS = sorted({row[0] for row in PLAN})


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Apply Fase 2L cierre fine article mapping.")
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
    dst = ROOT / "db" / f"gvadicto.backup_pre2l_cierre_{ts}.sqlite"
    shutil.copy2(DB, dst)
    return dst


def resolve_plan(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    errors: list[str] = []
    resolved: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    sets_by_topic: dict[int, set[int]] = {}

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
        key = (topic_id, article_id)
        if key in seen:
            errors.append(f"{label}: duplicado en PLAN")
            continue
        seen.add(key)
        sets_by_topic.setdefault(topic_id, set()).add(article_id)
        resolved.append({
            "topic_id": topic_id, "law_id": law_id, "article_id": article_id,
            "article_ref": article_ref, "priority": priority,
            "normative_reference": f"{LAW_LABEL.get(law_id, law_id)} art. {article_ref}",
            "note": note,
        })

    # unicidad interna
    frozen: dict[frozenset[int], list[int]] = {}
    for tid, ids in sets_by_topic.items():
        frozen.setdefault(frozenset(ids), []).append(tid)
    for ids, topics in frozen.items():
        if len(topics) > 1:
            errors.append(f"conjunto identico entre topics {topics}")

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        raise SystemExit("ABORT: errores al resolver el PLAN (ver arriba).")
    return resolved


def preflight(conn: sqlite3.Connection) -> dict[str, Any]:
    for topic_id, (topic_number, part, label) in TOPIC_META.items():
        row = conn.execute("SELECT topic_number, part FROM topics WHERE id=?", (topic_id,)).fetchone()
        if not row:
            raise SystemExit(f"ABORT: no existe topic_id={topic_id}")
        if int(row["topic_number"]) != int(topic_number) or row["part"] != part:
            raise SystemExit(f"ABORT: topic_id={topic_id} no es {label}: {dict(row)}")

    for law_id in {row[1] for row in PLAN}:
        if not conn.execute("SELECT id FROM laws WHERE id=?", (law_id,)).fetchone():
            raise SystemExit(f"ABORT: no existe law_id={law_id}")

    for topic_id in TOPIC_IDS:
        foreign = conn.execute(
            "SELECT id FROM topic_sources WHERE topic_id=? AND article_id IS NOT NULL AND mapping_basis<>?",
            (topic_id, MAPPING_BASIS),
        ).fetchall()
        if foreign:
            raise SystemExit(f"ABORT: topic_id={topic_id} ya tiene mapping fino ajeno ({len(foreign)} filas)")

    broken_fk = count(conn,
        "SELECT COUNT(*) FROM topic_sources WHERE article_id IS NOT NULL AND article_id NOT IN (SELECT id FROM articles)")
    if broken_fk:
        raise SystemExit(f"ABORT: hay {broken_fk} FKs rotas antes de aplicar.")

    resolved = resolve_plan(conn)

    # unicidad cruzada contra temas existentes fuera del plan
    planned: dict[int, set[int]] = {}
    for r in resolved:
        planned.setdefault(r["topic_id"], set()).add(r["article_id"])
    existing = {}
    for row in conn.execute(
        f"SELECT topic_id, GROUP_CONCAT(article_id) g FROM topic_sources "
        f"WHERE article_id IS NOT NULL AND topic_id NOT IN ({','.join('?'*len(TOPIC_IDS))}) GROUP BY topic_id",
        tuple(TOPIC_IDS)).fetchall():
        existing[tuple(sorted(int(x) for x in row["g"].split(",")))] = row["topic_id"]
    for tid, ids in planned.items():
        key = tuple(sorted(ids))
        if key in existing:
            raise SystemExit(f"ABORT: topic {tid} tendria conjunto identico al topic {existing[key]}")

    return {
        "resolved": resolved, "planned_count": len(resolved),
        "total_before": count(conn, "SELECT COUNT(*) FROM topic_sources"),
        "fine_before": count(conn, "SELECT COUNT(*) FROM topic_sources WHERE article_id IS NOT NULL"),
        "broken_fk_before": broken_fk,
    }


def apply_mapping(conn: sqlite3.Connection, resolved: list[dict[str, Any]]) -> tuple[int, int]:
    deleted = conn.execute(
        f"DELETE FROM topic_sources WHERE topic_id IN ({','.join('?'*len(TOPIC_IDS))}) AND mapping_basis=?",
        (*TOPIC_IDS, MAPPING_BASIS)).rowcount
    inserted = 0
    for r in resolved:
        conn.execute(
            """INSERT INTO topic_sources(topic_id, law_id, article_id, normative_reference,
               coverage_status, mapping_basis, priority, validation_status, notes)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (r["topic_id"], r["law_id"], r["article_id"], r["normative_reference"],
             "articulo_delimitado", MAPPING_BASIS, r["priority"], VALIDATION_STATUS, r["note"]))
        inserted += 1
    return deleted, inserted


def write_reports(result: dict[str, Any], stamp: str) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / f"apply_fase2l_cierre_{stamp}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    by_topic: dict[int, int] = {}
    for row in PLAN:
        by_topic[row[0]] = by_topic.get(row[0], 0) + 1
    lines = ["# Fase 2L — Cierre de delimitacion fina", "",
             f"- Mode: {'APPLY' if result['applied'] else 'DRY-RUN'}",
             f"- mapping_basis: `{MAPPING_BASIS}`",
             f"- Planned rows: {result['planned_count']}",
             f"- Backup: {result.get('backup') or 'n/a'}", "", "## Por topic", "",
             "| Topic | Filas |", "| --- | ---: |"]
    for tid in TOPIC_IDS:
        lines.append(f"| {TOPIC_META[tid][2]} (id={tid}) | {by_topic[tid]} |")
    lines += ["", "## Conteos", "",
              f"- topic_sources antes: {result['total_before']}",
              f"- topic_sources despues: {result.get('total_after','n/a')}",
              f"- filas finas antes: {result['fine_before']}",
              f"- filas finas despues: {result.get('fine_after','n/a')}",
              f"- filas insertadas: {result.get('inserted',0)}",
              f"- FKs rotas despues: {result.get('broken_fk_after','n/a')}", "",
              "Bloqueados (fallback documentado): gen-13 (protocolos UE), esp-3 (sin fuente),",
              "esp-5 (sin anclaje), esp-26 (Carta UE art 41 no importado), esp-28 (sin anclaje)."]
    (REPORTS / f"apply_fase2l_cierre_{stamp}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report: reports/apply_fase2l_cierre_{stamp}.md")


def main() -> None:
    args = build_parser().parse_args()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    conn = connect()
    try:
        print("=== Preflight ===")
        state = preflight(conn)
        print(f"  Topics: {TOPIC_IDS}")
        print(f"  Articulos resueltos: {state['planned_count']}")
        print(f"  topic_sources antes: {state['total_before']} (finas {state['fine_before']})")
        result: dict[str, Any] = {"applied": args.apply, "planned_count": state["planned_count"],
                                  "total_before": state["total_before"], "fine_before": state["fine_before"],
                                  "broken_fk_before": state["broken_fk_before"]}
        if not args.apply:
            print("\n=== DRY-RUN OK. Usa --apply para escribir. ===")
            write_reports(result, stamp)
            return
        backup = make_backup()
        result["backup"] = str(backup)
        print(f"\n  Backup: {backup.name}")
        deleted, inserted = apply_mapping(conn, state["resolved"])
        conn.commit()
        broken_after = count(conn,
            "SELECT COUNT(*) FROM topic_sources WHERE article_id IS NOT NULL AND article_id NOT IN (SELECT id FROM articles)")
        if broken_after:
            conn.rollback()
            raise SystemExit(f"ABORT: {broken_after} FKs rotas. Rollback.")
        result.update({"own_deleted": deleted, "inserted": inserted,
                       "total_after": count(conn, "SELECT COUNT(*) FROM topic_sources"),
                       "fine_after": count(conn, "SELECT COUNT(*) FROM topic_sources WHERE article_id IS NOT NULL"),
                       "broken_fk_after": broken_after})
        print(f"  Insertadas: {inserted} | topic_sources: {result['total_after']} | finas: {result['fine_after']} | FK rotas: {broken_after}")
        print("\n=== APPLY OK. ===")
    finally:
        conn.close()
    write_reports(result, stamp)


if __name__ == "__main__":
    main()

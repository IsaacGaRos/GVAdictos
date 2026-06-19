"""Fase 2K: delimitacion fina de temas de competencias sectoriales de la Generalitat.

Alcance (7 temas; la fuente comun es el Titulo IV del EACV, law_id=42):
  - esp-51 (topic_id 66): politicas de prestacion social, servicios sociales,
    dependencia, discapacidad, familias, infancia, juventud, mujer, voluntariado.
    EACV arts 49, 54 + Ley 3/2019 (servicios sociales) + Ley 26/2018 (infancia).
  - esp-53 (topic_id 68): educacion, FP, universidades, ciencia, I+D+i. EACV 49,52,53.
  - esp-56 (topic_id 71): industria, energia, comercio, turismo, artesania, consumo.
    EACV 49,50,51,52.
  - esp-57 (topic_id 72): agricultura, ganaderia, pesca, alimentacion, PAC. EACV 49,50,51.
  - esp-58 (topic_id 73): medio ambiente, montes, recursos hidricos, incendios. EACV 49,50.
  - esp-59 (topic_id 74): ordenacion territorio, litoral, urbanismo, obras publicas,
    vivienda, transportes, puertos, costas, aeropuertos. EACV 49,51.
  - esp-60 (topic_id 75): cultura, patrimonio historico, archivos, bibliotecas, deporte.
    EACV 49,57.

Nota de granularidad:
  El art. 49 del EACV (competencias exclusivas) esta importado como un unico articulo
  con todos sus apartados (1.1a-36a, 3.1a-16a). No se puede apuntar a un apartado
  concreto, por lo que la nota de cada fila indica los apartados relevantes por materia.
  Los conjuntos de articulos asignados a cada tema son DISTINTOS entre si para no
  generar conjuntos identicos (check 6 del validador); el script verifica esa unicidad.

Garantias:
  - Dry-run por defecto. Solo escribe con --apply.
  - NO modifica articles, parser, importer ni normalizacion.
  - NO borra mappings ajenos: elimina solo filas propias con este mapping_basis.
  - Aborta si algun topic ya tiene mapping fino ajeno (article_id IS NOT NULL).
  - Aborta si dos topics del plan resultan con el mismo conjunto de article_ids.
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

MAPPING_BASIS = "delimitacion_fina_claude_fase2k_competencias_sectoriales_2026_06_18"
VALIDATION_STATUS = "validado_fuente_oficial_pendiente_revision_humana"

TOPIC_META = {
    66: ("51", "especial", "esp-51"),
    68: ("53", "especial", "esp-53"),
    71: ("56", "especial", "esp-56"),
    72: ("57", "especial", "esp-57"),
    73: ("58", "especial", "esp-58"),
    74: ("59", "especial", "esp-59"),
    75: ("60", "especial", "esp-60"),
}
LAW_LABEL = {42: "EACV", 65: "Ley 3/2019", 66: "Ley 26/2018"}
EACV = 42

# PLAN: (topic_id, law_id, article_ref, priority, note)
PLAN: list[tuple[int, int, str, str, str]] = [
    # =====================================================================
    # esp-51 (topic_id=66) — prestacion social, servicios sociales, infancia...
    # =====================================================================
    (66, EACV, "49", "alta", "esp-51 EACV: 1.23a voluntariado, 1.24a servicios sociales, 1.25a juventud, 1.26a mujer, 1.27a proteccion menores/discapacidad/tercera edad/migrantes"),
    (66, EACV, "54", "media", "esp-51 EACV: sanidad y Seguridad Social (dependencia)"),
    (66, 65, "1", "alta", "esp-51 Ley 3/2019: objeto"),
    (66, 65, "4", "media", "esp-51 Ley 3/2019: los servicios sociales valencianos"),
    (66, 65, "5", "alta", "esp-51 Ley 3/2019: Sistema Publico Valenciano de Servicios Sociales"),
    (66, 65, "6", "media", "esp-51 Ley 3/2019: principios rectores"),
    (66, 65, "8", "media", "esp-51 Ley 3/2019: objetivos del Sistema Publico"),
    (66, 65, "9", "media", "esp-51 Ley 3/2019: titulares de derechos"),
    (66, 65, "10", "media", "esp-51 Ley 3/2019: derechos de las personas usuarias"),
    (66, 65, "14", "media", "esp-51 Ley 3/2019: estructura funcional del Sistema"),
    (66, 65, "15", "media", "esp-51 Ley 3/2019: atencion primaria"),
    (66, 65, "16", "media", "esp-51 Ley 3/2019: atencion secundaria"),
    (66, 66, "1", "alta", "esp-51 Ley 26/2018: objeto (infancia y adolescencia)"),
    (66, 66, "3", "media", "esp-51 Ley 26/2018: principios rectores"),
    (66, 66, "4", "media", "esp-51 Ley 26/2018: lineas de actuacion"),
    (66, 66, "5", "media", "esp-51 Ley 26/2018: politicas integrales"),
    (66, 66, "9", "media", "esp-51 Ley 26/2018: derecho al buen trato y proteccion de la integridad"),
    # =====================================================================
    # esp-53 (topic_id=68) — educacion, FP, universidades, ciencia, I+D+i
    # =====================================================================
    (68, EACV, "49", "alta", "esp-53 EACV: 1.7a investigacion, Academias, I+D+i"),
    (68, EACV, "52", "media", "esp-53 EACV: 52.2 ciencia, tecnologia y empresa (I+D+i)"),
    (68, EACV, "53", "alta", "esp-53 EACV: ensenanza en toda su extension y FP (competencia exclusiva)"),
    # =====================================================================
    # esp-56 (topic_id=71) — industria, energia, comercio, turismo, artesania
    # =====================================================================
    (71, EACV, "49", "alta", "esp-56 EACV: 1.12a turismo, 1.16a energia, 1.18a artesania, 1.35a comercio interior/consumo"),
    (71, EACV, "50", "media", "esp-56 EACV: 50.5 regimen minero y energetico (desarrollo legislativo)"),
    (71, EACV, "51", "media", "esp-56 EACV: 51.4a ferias internacionales (ejecucion)"),
    (71, EACV, "52", "alta", "esp-56 EACV: 52.2 industria, 52.1 planificacion economica"),
    # =====================================================================
    # esp-57 (topic_id=72) — agricultura, ganaderia, pesca, alimentacion, PAC
    # =====================================================================
    (72, EACV, "49", "alta", "esp-57 EACV: 1.17a pesca/marisqueo/acuicultura, 3.1a calidad agroalimentaria, 3.3a agricultura/ganaderia, 3.4a sanidad agraria, 3.15a denominaciones de origen"),
    (72, EACV, "50", "media", "esp-57 EACV: 50.7 ordenacion del sector pesquero (desarrollo)"),
    (72, EACV, "51", "media", "esp-57 EACV: 51.10a FEGA agrario (ejecucion)"),
    # =====================================================================
    # esp-58 (topic_id=73) — medio ambiente, montes, recursos hidricos, incendios
    # =====================================================================
    (73, EACV, "49", "alta", "esp-58 EACV: 1.10a montes/espacios naturales protegidos, 1.16a aprovechamientos hidraulicos/canales/riegos"),
    (73, EACV, "50", "alta", "esp-58 EACV: 50.6 proteccion del medio ambiente (desarrollo, normas adicionales)"),
    # =====================================================================
    # esp-59 (topic_id=74) — territorio, urbanismo, vivienda, transportes, costas
    # =====================================================================
    (74, EACV, "49", "alta", "esp-59 EACV: 1.9a ordenacion territorio/litoral/urbanismo/vivienda, 1.13a obras publicas, 1.14a carreteras, 1.15a transportes/puertos/aeropuertos, 3.12a vivienda"),
    (74, EACV, "51", "media", "esp-59 EACV: 51.6a salvamento maritimo, 51.9a costas y playas (ejecucion)"),
    # =====================================================================
    # esp-60 (topic_id=75) — cultura, patrimonio historico, archivos, deporte
    # =====================================================================
    (75, EACV, "49", "alta", "esp-60 EACV: 1.4a cultura, 1.5a patrimonio historico/artistico, 1.6a archivos/bibliotecas/museos/conservatorios, 1.28a deportes y ocio"),
    (75, EACV, "57", "baja", "esp-60 EACV: Real Monasterio de Santa Maria de la Valldigna (patrimonio cultural)"),
]

TOPIC_IDS = sorted({row[0] for row in PLAN})


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Apply Fase 2K competencias sectoriales fine mapping.")
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
    dst = ROOT / "db" / f"gvadicto.backup_pre2k_sectoriales_{ts}.sqlite"
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
        if int(row["law_id"]) != law_id:
            errors.append(f"{label}: law_id mismatch")
            continue
        key = (topic_id, article_id)
        if key in seen:
            errors.append(f"{label}: duplicado en PLAN")
            continue
        seen.add(key)
        sets_by_topic.setdefault(topic_id, set()).add(article_id)
        resolved.append({
            "topic_id": topic_id,
            "law_id": law_id,
            "article_id": article_id,
            "article_ref": article_ref,
            "priority": priority,
            "normative_reference": f"{LAW_LABEL.get(law_id, law_id)} art. {article_ref}",
            "note": note,
        })

    # Internal uniqueness check (avoid feeding check 6 of the validator)
    frozen: dict[frozenset[int], list[int]] = {}
    for topic_id, ids in sets_by_topic.items():
        frozen.setdefault(frozenset(ids), []).append(topic_id)
    dupes = {k: v for k, v in frozen.items() if len(v) > 1}
    if dupes:
        for ids, topics in dupes.items():
            errors.append(f"conjunto identico entre topics {topics}: {sorted(ids)}")

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

    # Cross-check: ensure planned sets are unique also against OTHER topics already
    # mapped in the DB (so we don't create an identical set with a topic outside this plan).
    planned_sets: dict[int, frozenset[int]] = {}
    for row in PLAN:
        planned_sets.setdefault(row[0], set())
    resolved = resolve_plan(conn)
    for r in resolved:
        planned_sets[r["topic_id"]].add(r["article_id"])
    planned_frozen = {tid: frozenset(ids) for tid, ids in planned_sets.items()}

    existing = {}
    for row in conn.execute(
        "SELECT topic_id, GROUP_CONCAT(article_id) g FROM topic_sources "
        "WHERE article_id IS NOT NULL AND topic_id NOT IN "
        f"({','.join('?'*len(TOPIC_IDS))}) GROUP BY topic_id",
        tuple(TOPIC_IDS),
    ).fetchall():
        existing[tuple(sorted(int(x) for x in row["g"].split(",")))] = row["topic_id"]
    for tid, fs in planned_frozen.items():
        key = tuple(sorted(fs))
        if key in existing:
            raise SystemExit(
                f"ABORT: topic {tid} tendria conjunto identico al topic existente "
                f"{existing[key]}: {key}"
            )

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
    json_path = REPORTS / f"apply_fase2k_sectoriales_{stamp}.json"
    md_path = REPORTS / f"apply_fase2k_sectoriales_{stamp}.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    by_topic: dict[int, int] = {}
    for row in PLAN:
        by_topic[row[0]] = by_topic.get(row[0], 0) + 1

    lines = [
        "# Fase 2K — Delimitacion fina de competencias sectoriales",
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
        "Fuente comun: Titulo IV del EACV (law_id=42). El art. 49 esta importado como",
        "un unico articulo; la nota de cada fila precisa los apartados relevantes.",
        "Conjuntos de articulos distintos por tema (check 6 del validador se mantiene en 0).",
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

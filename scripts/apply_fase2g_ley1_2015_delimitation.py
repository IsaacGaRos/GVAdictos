"""Fase 2G: delimitacion fina de Ley 1/2015 GV hacienda publica (law_id=14)
entre los 7 temas que la referencian, mas temas complementarios.

Topics cubiertos:
  - PE-20 (id=35): Ley 38/2003 subvenciones estatales + Ley 1/2015 GV arts 159-177 (subvenciones)
  - PE-41 (id=56): Ley 1/2015 arts 1-23 (ambito+Hacienda Publica) + arts 152-158 (sector publico instrumental)
  - PE-42 (id=57): Ley 1/2015 arts 24-38 (principios+programacion) + arts 56-66 (gestion presupuestaria)
  - PE-43 (id=58): Ley 1/2015 arts 39-55 (modificaciones creditos + presupuesto sector publico)
  - PE-44 (id=59): Ley 1/2015 arts 67-91 (tesoreria + deuda publica + avales)
  - PE-46 (id=61): Ley 1/2015 arts 124-151 (contabilidad + responsabilidades)
  - PE-47 (id=62): Ley 1/2015 arts 92-123 (control interno + funcion interventora + auditoria)
                 + Ley 7/1988 arts 1-144 (Tribunal de Cuentas)

Los 180 arts de Ley 1/2015 quedan cubiertos sin solapamiento:
  1-23 PE-41 | 24-38 PE-42 | 39-55 PE-43 | 56-66 PE-42 | 67-91 PE-44
  92-123 PE-47 | 124-151 PE-46 | 152-158 PE-41 | 159-177 PE-20

Garantias identicas a scripts de fases anteriores:
  - NO reimporta normas. NO modifica `articles`.
  - Solo inserta en `topic_sources` con mapping_basis propio.
  - Idempotente: borra SUS propias filas antes de reinsertar.
  - Aborta si algun topic coincide con IDs protegidos.
  - Backup automatico antes de cualquier escritura.
  - --dry-run imprime conteos sin escribir.
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "db" / "gvadicto.sqlite"

MAPPING_BASIS = "delimitacion_fase2g_ley1_2015_claudecode_2026_06_18"
VALIDATION_STATUS = "validado_fuente_oficial_pendiente_revision_humana"
NOTE = (
    "Delimitacion Fase 2G: Ley 1/2015 GV (law_id=14) repartida por titulos "
    "segun enunciado oficial convocatoria A1-01 2025 (bases DOGV). "
    "Cobertura completa: 180/180 arts sin solapamiento. Pendiente revision humana."
)

PROTECTED_TOPIC_IDS = {
    8, 32, 33, 36, 47, 67, 69, 70,   # Codex
    24, 25, 26, 27,                    # LPAC Fase 2A
    29, 37, 38,                        # LRJSP+LCSP Fase 2B
    28,                                # PE-13 Fase 2E
    2, 6, 7, 9, 10, 11, 22, 34, 40, 42, 44, 46, 48, 49, 50, 51, 52, 53, 55, 60,  # Fase 2F
}

LAW_LABEL = {
    11: "Ley 38/2003 subvenciones",
    14: "Ley 1/2015 GV hacienda publica",
    41: "Ley 7/1988 Tribunal de Cuentas",
}

# (topic_id, law_id, ranges_or_None, etiqueta)
#   ranges=None  => todos los articulos de esa ley
#   ranges=[(start,end),...]  => CAST(article_ref AS INTEGER) BETWEEN start AND end
PLAN = [
    # PE-20 (id=35): Subvenciones estatales + GV
    (35, 11, None,          "PE-20 Ley 38/2003 Subvenciones estatales (completa)"),
    (35, 14, [(159, 177)],  "PE-20 Ley 1/2015 GV Titulo IX subvenciones GV"),

    # PE-41 (id=56): Ambito + Hacienda Publica + Sector publico instrumental
    (56, 14, [(1, 23), (152, 158)],
             "PE-41 Ley 1/2015 GV: ambito+Hacienda Publica + sector publico instrumental"),

    # PE-42 (id=57): Presupuesto (I): principios, programacion, contenido, gestion
    (57, 14, [(24, 38), (56, 66)],
             "PE-42 Ley 1/2015 GV: principios+programacion+contenido presup + gestion"),

    # PE-43 (id=58): Presupuesto (II): modificaciones creditos + presup sector publico
    (58, 14, [(39, 55)],
             "PE-43 Ley 1/2015 GV: modificaciones creditos + presup sector publico instrumental"),

    # PE-44 (id=59): Tesoreria + Deuda publica + Avales
    (59, 14, [(67, 91)],
             "PE-44 Ley 1/2015 GV: tesoreria + deuda publica + avales"),

    # PE-46 (id=61): Contabilidad + Responsabilidades
    (61, 14, [(124, 151)],
             "PE-46 Ley 1/2015 GV: contabilidad sector publico + responsabilidades"),

    # PE-47 (id=62): Control interno + funcion interventora + auditoria + Tribunal Cuentas
    (62, 14, [(92, 123)],
             "PE-47 Ley 1/2015 GV: control interno + funcion interventora + auditoria"),
    (62, 41, None,
             "PE-47 Ley 7/1988 Tribunal de Cuentas (completa)"),
]


def make_backup() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = ROOT / "db" / f"gvadicto.backup_pre2g_ley1_2015_{ts}.sqlite"
    shutil.copy2(DB, dst)
    return dst


def get_articles(conn, law_id: int, ranges):
    if ranges is None:
        return conn.execute(
            "SELECT id, article_ref FROM articles WHERE law_id=? "
            "ORDER BY CAST(article_ref AS INTEGER), article_ref",
            (law_id,),
        ).fetchall()
    seen: set[int] = set()
    result = []
    for start, end in ranges:
        rows = conn.execute(
            "SELECT id, article_ref FROM articles WHERE law_id=? "
            "AND CAST(article_ref AS INTEGER) BETWEEN ? AND ? "
            "ORDER BY CAST(article_ref AS INTEGER), article_ref",
            (law_id, start, end),
        ).fetchall()
        for row in rows:
            if row[0] not in seen:
                seen.add(row[0])
                result.append(row)
    return result


def preflight(conn) -> bool:
    ok = True
    plan_topics = {t for t, _, _, _ in PLAN}

    conflict = plan_topics & PROTECTED_TOPIC_IDS
    if conflict:
        print(f"ABORT: topic IDs {sorted(conflict)} coinciden con IDs protegidos.")
        ok = False

    for tid in plan_topics:
        if not conn.execute("SELECT 1 FROM topics WHERE id=?", (tid,)).fetchone():
            print(f"ABORT: topic_id={tid} no existe.")
            ok = False

    for law_id in {law for _, law, _, _ in PLAN}:
        if not conn.execute("SELECT 1 FROM laws WHERE id=?", (law_id,)).fetchone():
            print(f"ABORT: law_id={law_id} no existe.")
            ok = False

    seen_combos: set[tuple[int, int]] = set()
    for topic_id, law_id, ranges, label in PLAN:
        combo = (topic_id, law_id)
        if combo in seen_combos:
            continue
        seen_combos.add(combo)
        arts = get_articles(conn, law_id, ranges)
        if not arts:
            print(f"WARN: 0 articulos para topic_id={topic_id} law_id={law_id} '{label}'")
            ok = False

    # Sanidad especifica: Ley 1/2015 cubierta al 100%
    covered_14 = set()
    for topic_id, law_id, ranges, _ in PLAN:
        if law_id != 14:
            continue
        for art in get_articles(conn, 14, ranges):
            covered_14.add(art[0])
    total_14 = conn.execute("SELECT COUNT(*) FROM articles WHERE law_id=14").fetchone()[0]
    if len(covered_14) != total_14:
        print(f"WARN: Ley 1/2015 cubre {len(covered_14)}/{total_14} articulos (no es 100%)")

    return ok


def main(dry_run: bool = False) -> None:
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row

    plan_topics = sorted({t for t, _, _, _ in PLAN})

    total_before = conn.execute("SELECT COUNT(*) FROM topic_sources").fetchone()[0]
    own_before = conn.execute(
        "SELECT COUNT(*) FROM topic_sources WHERE mapping_basis=?",
        (MAPPING_BASIS,),
    ).fetchone()[0]

    print(f"topic_sources total antes: {total_before} (propias {own_before})")
    print(f"Topics en plan: {plan_topics}")
    print()

    print("=== PREFLIGHT ===")
    if not preflight(conn):
        conn.close()
        raise SystemExit("ABORT: preflight fallido.")
    print("Preflight OK.")
    print()

    if dry_run:
        print("=== DRY-RUN: conteos por entrada ===")
        for topic_id, law_id, ranges, label in PLAN:
            arts = get_articles(conn, law_id, ranges)
            print(f"  topic_id={topic_id} law_id={law_id:2d} => {len(arts):4d} arts | {label}")
        total_dry = sum(
            len(get_articles(conn, law_id, ranges))
            for _, law_id, ranges, _ in PLAN
        )
        print(f"\nTotal a insertar: {total_dry}")
        conn.close()
        return

    backup = make_backup()
    print(f"Backup creado: {backup.name}")
    print()

    placeholders = ",".join("?" for _ in plan_topics)
    conn.execute(
        f"DELETE FROM topic_sources WHERE mapping_basis=? AND topic_id IN ({placeholders})",
        (MAPPING_BASIS, *plan_topics),
    )

    inserted = 0
    summary: dict[int, int] = {}
    for topic_id, law_id, ranges, label in PLAN:
        arts = get_articles(conn, law_id, ranges)
        for art in arts:
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
                    int(art["id"]),
                    f"{LAW_LABEL[law_id]} art. {art['article_ref']}",
                    "articulo_delimitado",
                    MAPPING_BASIS,
                    "alta",
                    VALIDATION_STATUS,
                    NOTE,
                ),
            )
            inserted += 1
        summary[topic_id] = summary.get(topic_id, 0) + len(arts)
        print(f"  topic_id={topic_id:3d} law_id={law_id:2d} => {len(arts):4d} arts | {label}")

    conn.commit()

    print()
    print("=== RESUMEN POR TOPIC ===")
    for tid in sorted(summary):
        print(f"  topic_id={tid:3d}: {summary[tid]:4d} articulos totales")

    broken = conn.execute(
        "SELECT COUNT(*) FROM topic_sources WHERE article_id IS NOT NULL "
        "AND article_id NOT IN (SELECT id FROM articles)"
    ).fetchone()[0]
    total_after = conn.execute("SELECT COUNT(*) FROM topic_sources").fetchone()[0]
    own_after = conn.execute(
        "SELECT COUNT(*) FROM topic_sources WHERE mapping_basis=?",
        (MAPPING_BASIS,),
    ).fetchone()[0]

    codex_rows = conn.execute(
        "SELECT COUNT(*) FROM topic_sources "
        "WHERE mapping_basis='validacion_articulos_codex_2026_06_18'"
    ).fetchone()[0]
    fase2f_rows = conn.execute(
        "SELECT COUNT(*) FROM topic_sources "
        "WHERE mapping_basis='delimitacion_fase2f_batch_claudecode_2026_06_18'"
    ).fetchone()[0]

    conn.close()

    print()
    print(f"topic_sources total antes={total_before} => despues={total_after}")
    print(f"Filas propias antes={own_before} => despues={own_after}")
    print(f"Filas insertadas: {inserted}")
    print(f"FK rotas: {broken}")
    print(f"Codex intactas: {codex_rows} | Fase2F intactas: {fase2f_rows}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)

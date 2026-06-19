"""Fase 2F: delimitacion fina batch de 20 temas (PG y PE) con normativa ya importada.

Cubre los temas mas claros donde la ley referenciada ya esta en BD y el rango
de articulos se puede determinar sin ambiguedad desde el enunciado oficial:

  - PG-02, PG-06, PG-07, PG-09, PG-10, PG-11 (general)
  - PE-07, PE-19, PE-25, PE-27, PE-29, PE-31, PE-33..37, PE-38, PE-40, PE-45 (especial)

Dejan para Fase 2G: Ley 1/2015 GV (split presupuestario), TUE/TFUE (split tematico),
y temas de competencias GV sin normativa importada.

Garantias:
  - NO reimporta normas. NO modifica `articles`.
  - Solo inserta en `topic_sources` con mapping_basis propio.
  - Idempotente: borra SUS PROPIAS filas (mismo mapping_basis) para SUS topics.
  - Aborta si algun topic coincide con IDs protegidos (Codex, LPAC, 2B, 2E).
  - Backup automatico antes de cualquier escritura.
  - Dry-run con --dry-run: imprime conteos sin escribir ni hacer backup.
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "db" / "gvadicto.sqlite"

MAPPING_BASIS = "delimitacion_fase2f_batch_claudecode_2026_06_18"
VALIDATION_STATUS = "validado_fuente_oficial_pendiente_revision_humana"
NOTE = (
    "Delimitacion batch Fase 2F segun enunciado oficial convocatoria A1-01 2025 "
    "(bases DOGV) y estructura BOE/DOGV; rangos documentados en "
    ".claude/PILOTO_FASE2E_PE13_DELIMITACION.md; pendiente revision humana."
)

# IDs de topics con mapeos ya protegidos - nunca tocar
PROTECTED_TOPIC_IDS = {
    8, 32, 33, 36, 47, 67, 69, 70,   # Codex
    24, 25, 26, 27,                    # LPAC piloto Fase 2A
    29, 37, 38,                        # LRJSP+LCSP Fase 2B
    28,                                # PE-13 Fase 2E
}

LAW_LABEL = {
    5:  "RDL 5/2015 TREBEP",
    9:  "RDL 2/2015 ET",
    12: "RD 203/2021 sector publico electronico",
    15: "Ley 4/2021 FPV",
    17: "Ley 5/1983 Consell",
    19: "Ley 8/2010 RLCV",
    22: "Ley 20/2017 Tasas GV",
    28: "Decreto 41/2016 calidad servicios",
    29: "Decreto 54/2025 simplificacion",
    31: "Decreto 103/2014 precios publicos",
    32: "Ley 7/1985 LBRL",
    33: "LO 2/2012 Estabilidad Presupuestaria",
    36: "Ley 50/1997 Gobierno",
    42: "LO 5/1982 EACV",
    45: "Ley 2/2021 Sindic Greuges CV",
    46: "Ley 6/1985 Sindicatura Comptes",
    47: "Ley 10/1994 Consell Juridic Consultiu",
    48: "Ley 12/1985 Consell Valencia Cultura",
    49: "Ley 7/1998 Academia Valenciana Llengua",
    50: "Ley 1/2014 Comite Economic i Social",
    51: "Ley 29/1998 LJCA",
    56: "Ley 19/2013 Transparencia",
    57: "Ley 1/2022 Transparencia CV",
    58: "Ley 4/2023 Participacion Ciudadana CV",
    59: "LO 3/2018 LOPDGDD",
    73: "Ley 25/2018 Grupos de Interes CV",
}

# (topic_id, law_id, ranges_or_None, etiqueta)
#   ranges=None  => todos los articulos de esa ley
#   ranges=[(start,end), ...]  => CAST(article_ref AS INTEGER) BETWEEN start AND end
PLAN = [
    # --- PARTE GENERAL ---
    # PG-02 Ley 50/1997 del Gobierno (ley completa)
    (2,  36, None,             "PG-02 Ley 50/1997 Gobierno"),

    # PG-06 EACV: La CV, derechos valencianos, Generalitat + art 81 reforma
    (6,  42, [(1, 43), (81, 81)], "PG-06 EACV La CV+derechos+instituciones+reforma"),

    # PG-07 EACV: competencias, relaciones Estado/UE, Adm local, Economia y Hacienda
    (7,  42, [(44, 80)],       "PG-07 EACV competencias+relaciones+hacienda"),

    # PG-09 Ley 5/1983: President, Consell (composicion+atribuciones),
    #                   potestad reglamentaria, relaciones Les Corts
    (9,  17, [(1, 26), (31, 59)], "PG-09 Ley 5/1983 President+Consell+reglamentaria+LesCorts"),

    # PG-10 Ley 5/1983: consellers, Administracion publica GV
    (10, 17, [(27, 30), (60, 79)], "PG-10 Ley 5/1983 consellers+Administracion"),

    # PG-11 Instituciones auxiliares GV (6 leyes)
    (11, 45, None,             "PG-11 Sindic Greuges CV"),
    (11, 46, None,             "PG-11 Sindicatura Comptes"),
    (11, 47, None,             "PG-11 Consell Juridic Consultiu"),
    (11, 48, None,             "PG-11 Consell Valencia Cultura"),
    (11, 49, None,             "PG-11 Academia Valenciana Llengua"),
    (11, 50, None,             "PG-11 Comite Economic i Social"),

    # --- PARTE ESPECIAL ---
    # PE-07 LJCA completa
    (22, 51, None,             "PE-07 Ley 29/1998 LJCA"),

    # PE-19 Administracion electronica: RD 203/2021 completo + D54/2025 Titulo II
    (34, 12, None,             "PE-19 RD 203/2021 sector publico electronico"),
    (34, 29, [(7, 62)],        "PE-19 Decreto 54/2025 Titulo II transformacion digital"),

    # PE-25 Administracion local: LBRL completa + Ley 8/2010 RLCV completa
    (40, 32, None,             "PE-25 Ley 7/1985 LBRL"),
    (40, 19, None,             "PE-25 Ley 8/2010 RLCV"),

    # PE-27 Gestion calidad: Decreto 41/2016 completo
    (42, 28, None,             "PE-27 Decreto 41/2016 calidad servicios"),

    # PE-29 Transparencia + participacion + datos personales (5 leyes)
    (44, 56, None,             "PE-29 Ley 19/2013 Transparencia estatal"),
    (44, 57, None,             "PE-29 Ley 1/2022 Transparencia CV"),
    (44, 58, None,             "PE-29 Ley 4/2023 Participacion Ciudadana CV"),
    (44, 73, None,             "PE-29 Ley 25/2018 Grupos Interes CV"),
    (44, 59, None,             "PE-29 LO 3/2018 LOPDGDD"),

    # PE-31 TREBEP completo
    (46, 5,  None,             "PE-31 RDL 5/2015 TREBEP"),

    # PE-33..37 Ley 4/2021 FPV - 5 temas, rangos no solapantes
    # PE-33: Objeto, principios, ambito, organizacion FP, clases de personal
    (48, 15, [(1, 35)],        "PE-33 FPV Titulo I-III objeto+org+clases personal"),
    # PE-34: Estructuracion empleo publico, puestos, planificacion, registros
    (49, 15, [(36, 59)],       "PE-34 FPV Titulo IV-VI estructuracion+puestos+planificacion"),
    # PE-35: Seleccion, nacimiento/extincion condicion, provision+movilidad, carrera, evaluacion
    (50, 15, [(60, 75), (107, 137)], "PE-35 FPV seleccion+nacimiento/extincion+provision+carrera"),
    # PE-36: Derechos+deberes+jornada+retribuciones+formacion + situaciones admin + disciplinario
    (51, 15, [(76, 106), (138, 181)], "PE-36 FPV derechos+deberes+situaciones+disciplinario"),
    # PE-37: Representacion, negociacion colectiva, participacion institucional
    (52, 15, [(182, 190)],     "PE-37 FPV representacion+negociacion colectiva"),

    # PE-38 Estatuto Trabajadores completo
    (53, 9,  None,             "PE-38 RDL 2/2015 ET"),

    # PE-40 LO 2/2012 Estabilidad Presupuestaria completa
    (55, 33, None,             "PE-40 LO 2/2012 Estabilidad Presupuestaria"),

    # PE-45 Tasas GV: Ley 20/2017 + Decreto 103/2014 precios publicos
    (60, 22, None,             "PE-45 Ley 20/2017 Tasas GV"),
    (60, 31, None,             "PE-45 Decreto 103/2014 Precios Publicos GV"),
]


def make_backup() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = ROOT / "db" / f"gvadicto.backup_pre2f_batch_{ts}.sqlite"
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

    # Verificar que cada (topic_id, law_id) tiene articulos
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

    # Verificar topics existen en la BD
    for tid in plan_topics:
        row = conn.execute("SELECT id FROM topics WHERE id=?", (tid,)).fetchone()
        if not row:
            print(f"ABORT: topic_id={tid} no existe en topics.")
            ok = False

    # Verificar laws existen
    for law_id in {law for _, law, _, _ in PLAN}:
        row = conn.execute("SELECT id FROM laws WHERE id=?", (law_id,)).fetchone()
        if not row:
            print(f"ABORT: law_id={law_id} no existe en laws.")
            ok = False

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
            print(f"  topic_id={topic_id} law_id={law_id} => {len(arts):4d} arts | {label}")
        conn.close()
        return

    backup = make_backup()
    print(f"Backup creado: {backup.name}")
    print()

    # Idempotente: borrar filas previas de este mapping_basis para estos topics
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
        print(f"  topic_id={topic_id:3d} law_id={law_id:3d} => {len(arts):4d} arts | {label}")

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

    # Verificar que mappings protegidos siguen intactos
    codex_rows = conn.execute(
        "SELECT COUNT(*) FROM topic_sources "
        "WHERE mapping_basis='validacion_articulos_codex_2026_06_18'"
    ).fetchone()[0]
    fase2b_rows = conn.execute(
        "SELECT COUNT(*) FROM topic_sources "
        "WHERE mapping_basis='delimitacion_convocatoria_titulos_claudecode_2026_06_18'"
    ).fetchone()[0]
    fase2e_rows = conn.execute(
        "SELECT COUNT(*) FROM topic_sources "
        "WHERE mapping_basis='validacion_articulos_claude_fase2e_pe13_2026_06_18'"
    ).fetchone()[0]

    conn.close()

    print()
    print(f"topic_sources total antes={total_before} => despues={total_after}")
    print(f"Filas propias antes={own_before} => despues={own_after}")
    print(f"Filas insertadas esta ejecucion: {inserted}")
    print(f"FK rotas: {broken}")
    print(f"Codex intactas: {codex_rows} | Fase2B intactas: {fase2b_rows} | Fase2E intactas: {fase2e_rows}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)

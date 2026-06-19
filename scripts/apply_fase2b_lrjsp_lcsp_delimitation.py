"""Fase 2B: delimitacion fina de PE-14 (LRJSP) y PE-22/23 (LCSP) por titulos/libros.

Fuente de delimitacion: enunciado oficial de la convocatoria A1-01 2025 (bases
DOGV), cuyo titulo de tema nombra verbatim el titulo/libro de la norma, contrastado
con la estructura oficial BOE. Documentado en
.claude/PILOTO_FASE2B_DELIMITACION_LRJSP_LCSP.md.

PE-13 queda DIFERIDO: la Ley 40/2015 (law_id=4) tiene los arts 24-27 contaminados
con texto de la Ley 50/1997 del Gobierno; mapearlo seria un tema dudoso. Se reporta
para que la importacion se corrija (fuera de alcance: no se toca `articles`).

Garantias:
  - NO reimporta normas. NO modifica `articles`.
  - Solo inserta filas en `topic_sources` con article_id, bajo mapping_basis propio.
  - Idempotente: borra primero SUS PROPIAS filas (mismo mapping_basis) para SUS topics.
  - Aborta si algun topic coincidiera con los 8 de Codex o con el piloto LPAC.
  - Crea backup de la BD antes de cualquier escritura.

Seleccion por rango directo (CAST(article_ref AS INTEGER) BETWEEN ...): refs unicos
en la BD normalizada e incluye correctamente los articulos bis por su numero base
(el helper de Codex `best_articles_in_range` los descartaria por su filtro de titulo).
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "db" / "gvadicto.sqlite"

MAPPING_BASIS = "delimitacion_convocatoria_titulos_claudecode_2026_06_18"
VALIDATION_STATUS = "validado_fuente_oficial_pendiente_revision_humana"
NOTE = (
    "Delimitacion por titulos/libros segun enunciado oficial de la convocatoria "
    "A1-01 2025 (bases DOGV) y estructura BOE; documentado en "
    ".claude/PILOTO_FASE2B_DELIMITACION_LRJSP_LCSP.md; pendiente revision humana."
)

LAW_LABEL = {4: "Ley 40/2015", 13: "Ley 9/2017 LCSP"}

CODEX_TOPIC_IDS = {8, 32, 33, 36, 47, 67, 69, 70}
LPAC_PILOT_IDS = {24, 25, 26, 27}

# (topic_id, law_id, [(start, end), ...], etiqueta)
PLAN = [
    (29, 4, [(54, 139)], "PE-14 LRJSP Titulo I+II (AGE + sector publico institucional)"),
    (37, 13, [(115, 315)], "PE-22 LCSP Libro II (contratos de las AAPP)"),
    (38, 13, [(316, 346)], "PE-23 LCSP Libro III+IV (otros entes + organizacion)"),
]


def make_backup() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = ROOT / "db" / f"gvadicto.backup_prepilot_{ts}.sqlite"
    shutil.copy2(DB, dst)
    return dst


def articles_in_range(conn, law_id: int, start: int, end: int):
    return conn.execute(
        "SELECT id, article_ref FROM articles WHERE law_id=? "
        "AND CAST(article_ref AS INTEGER) BETWEEN ? AND ? "
        "ORDER BY CAST(article_ref AS INTEGER), article_ref",
        (law_id, start, end),
    ).fetchall()


def main() -> None:
    plan_topics = {t for t, _, _, _ in PLAN}
    if plan_topics & CODEX_TOPIC_IDS or plan_topics & LPAC_PILOT_IDS:
        raise SystemExit("ABORT: un topic coincide con Codex o con el piloto LPAC.")

    backup = make_backup()
    print(f"Backup creado: {backup.name}")

    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row

    placeholders = ",".join("?" for _ in plan_topics)
    conn.execute(
        f"DELETE FROM topic_sources WHERE mapping_basis = ? AND topic_id IN ({placeholders})",
        (MAPPING_BASIS, *sorted(plan_topics)),
    )

    inserted = 0
    for topic_id, law_id, ranges, label in PLAN:
        n_topic = 0
        for start, end in ranges:
            for art in articles_in_range(conn, law_id, start, end):
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
                n_topic += 1
                inserted += 1
        print(f"  topic_id={topic_id} ({label}): {n_topic} articulos")

    conn.commit()

    broken = conn.execute(
        "SELECT COUNT(*) FROM topic_sources WHERE article_id IS NOT NULL "
        "AND article_id NOT IN (SELECT id FROM articles)"
    ).fetchone()[0]
    codex_rows = conn.execute(
        "SELECT COUNT(*) FROM topic_sources WHERE mapping_basis='validacion_articulos_codex_2026_06_18'"
    ).fetchone()[0]
    lpac_rows = conn.execute(
        "SELECT COUNT(*) FROM topic_sources WHERE mapping_basis=? AND topic_id IN (24,25,26,27)",
        (MAPPING_BASIS,),
    ).fetchone()[0]
    print(
        f"Filas insertadas: {inserted} | FKs rotas: {broken} | "
        f"Codex intactas: {codex_rows} | LPAC intactas: {lpac_rows}"
    )
    conn.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

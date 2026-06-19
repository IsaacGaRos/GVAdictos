"""Piloto Fase 2A: delimitacion fina de los 4 temas LPAC (Ley 39/2015) por titulos.

Fuente de delimitacion: enunciado oficial de la convocatoria A1-01 2025 (bases
DOGV), que describe funcionalmente los titulos de la Ley 39/2015, contrastado con
la estructura oficial BOE-A-2015-10565 y con Autentica (PE-06 -> titulo VI, que
queda fuera de estos 4 temas). Documentado en
.claude/PILOTO_FASE2A_DELIMITACION_LPAC.md.

Garantias:
  - NO reimporta normas. NO modifica `articles`.
  - Solo inserta filas en `topic_sources` con article_id, bajo un mapping_basis
    propio y trazable.
  - Idempotente: borra primero SUS PROPIAS filas (mismo mapping_basis) y reinserta.
  - Aborta si algun tema piloto coincidiera con los 8 mapeos validados de Codex.
  - Crea backup de la BD antes de cualquier escritura.

Reutiliza `best_articles_in_range` y `canonical_ref` del script de Codex
(scripts/apply_a1_article_validation.py) para seleccionar el mejor articulo por
ref, con la misma logica con que se aplicaron los 8 mapeos validados. Importar
ese modulo NO ejecuta su main() (esta protegido por __main__), por lo que no se
dispara ninguna reimportacion.
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DB = ROOT / "db" / "gvadicto.sqlite"

from scripts.apply_a1_article_validation import best_articles_in_range, canonical_ref

MAPPING_BASIS = "delimitacion_convocatoria_titulos_claudecode_2026_06_18"
VALIDATION_STATUS = "validado_fuente_oficial_pendiente_revision_humana"
NOTE = (
    "Delimitacion por titulos de la Ley 39/2015 segun enunciado oficial de la "
    "convocatoria A1-01 2025 (bases DOGV) y estructura BOE-A-2015-10565; "
    "documentado en .claude/PILOTO_FASE2A_DELIMITACION_LPAC.md; pendiente "
    "revision humana."
)

LAW_ID_LPAC = 3
LAW_LABEL = "Ley 39/2015"

# Los 8 mapeos validados por Codex (NUNCA tocar). Por id de topics.
CODEX_TOPIC_IDS = {8, 32, 33, 36, 47, 67, 69, 70}

# (topic_id, start, end, etiqueta_titulo)
PILOT = [
    (24, 1, 33, "Titulos Preliminar+I+II"),
    (25, 34, 52, "Titulo III"),
    (26, 53, 105, "Titulo IV"),
    (27, 106, 126, "Titulo V"),
]


def make_backup() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = ROOT / "db" / f"gvadicto.backup_prepilot_{ts}.sqlite"
    shutil.copy2(DB, dst)
    return dst


def main() -> None:
    pilot_topics = {t for t, _, _, _ in PILOT}
    if not pilot_topics.isdisjoint(CODEX_TOPIC_IDS):
        raise SystemExit("ABORT: un tema piloto coincide con un mapeo validado de Codex.")

    backup = make_backup()
    print(f"Backup creado: {backup.name}")

    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row

    # Idempotencia: eliminar solo las filas de ESTE piloto (mismo mapping_basis).
    placeholders = ",".join("?" for _ in pilot_topics)
    conn.execute(
        f"DELETE FROM topic_sources WHERE mapping_basis = ? AND topic_id IN ({placeholders})",
        (MAPPING_BASIS, *sorted(pilot_topics)),
    )

    inserted = 0
    for topic_id, start, end, label in PILOT:
        arts = best_articles_in_range(conn, LAW_ID_LPAC, start, end)
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
                    LAW_ID_LPAC,
                    int(art["id"]),
                    f"{LAW_LABEL} art. {canonical_ref(art)}",
                    "articulo_delimitado",
                    MAPPING_BASIS,
                    "alta",
                    VALIDATION_STATUS,
                    NOTE,
                ),
            )
            inserted += 1
        print(f"  topic_id={topic_id} ({label}): {len(arts)} articulos (arts {start}-{end})")

    conn.commit()

    broken = conn.execute(
        "SELECT COUNT(*) FROM topic_sources WHERE article_id IS NOT NULL "
        "AND article_id NOT IN (SELECT id FROM articles)"
    ).fetchone()[0]
    # Verificar que no se han tocado los mapeos de Codex
    codex_rows = conn.execute(
        "SELECT COUNT(*) FROM topic_sources WHERE mapping_basis = 'validacion_articulos_codex_2026_06_18'"
    ).fetchone()[0]
    print(f"Filas insertadas: {inserted} | FKs rotas: {broken} | filas Codex intactas: {codex_rows}")
    conn.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

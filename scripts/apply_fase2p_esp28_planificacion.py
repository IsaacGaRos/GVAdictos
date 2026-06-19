"""
Fase 2P: Mapeo esp-28 (planificacion estrategica) a articulos existentes

El tema T28 especial no tiene una ley especifica de planificacion estrategica.
Se mapea a los articulos mas cercanos disponibles en BD:
  - Ley 50/1997 art. 25 (Plan Anual Normativo)
  - Ley 19/2013 art. 6 (informacion institucional y de planificacion)

El topic_sources existente (law_id=18, Ley 6/2024) pasa a tener article_id
apuntando al art de gestion de procesos (art 38) como referencia de simplificacion/
mejora continua, complementando las anteriores.

Uso:
    python scripts/apply_fase2p_esp28_planificacion.py          # dry-run
    python scripts/apply_fase2p_esp28_planificacion.py --apply  # aplica
"""

import sys
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

DRY_RUN = "--apply" not in sys.argv
DB_PATH = Path("db/gvadicto.sqlite")
ESP28_TOPIC_ID = 43  # topic id=43, T28 especial

# Articulos a mapear (ya verificados en BD)
MAPPINGS = [
    # (law_id, article_id, normative_reference, notes)
    (36, 97080, "Ley 50/1997 art. 25 Plan Anual Normativo",
     "Planificacion normativa anual del Gobierno; referencia mas proxima a planificacion estrategica"),
    (56, 99855, "Ley 19/2013 art. 6 informacion institucional y de planificacion",
     "Obligacion de publicar planes y programas; dimension de transparencia"),
    (18, 95233, "Ley 6/2024 art. 38 Gestion por procesos",
     "Mejora y racionalizacion de la gestion; dimension de simplificacion GVA"),
]


def backup_db():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = DB_PATH.parent / f"gvadicto.backup_pre2p_esp28_{ts}.sqlite"
    shutil.copy2(DB_PATH, backup)
    print(f"[backup] {backup}")


def main():
    print(
        f"=== Fase 2P: mapeo esp-28 planificacion estrategica "
        f"({'DRY-RUN' if DRY_RUN else 'APPLY'}) ===\n"
    )

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Estado actual esp-28
    c.execute(
        "SELECT id, law_id, article_id, normative_reference, mapping_basis "
        "FROM topic_sources WHERE topic_id=?",
        (ESP28_TOPIC_ID,),
    )
    current = c.fetchall()
    print(f"[check] topic_sources esp-28 actuales ({len(current)}):")
    for row in current:
        print(f"  ts_id={row[0]} law_id={row[1]} article_id={row[2]} ref={row[3]}")

    c.execute(
        "SELECT COUNT(*) FROM topic_sources WHERE topic_id=? AND article_id IS NOT NULL",
        (ESP28_TOPIC_ID,),
    )
    fine_before = c.fetchone()[0]
    print(f"  fine-mapped antes: {fine_before}")
    print()

    # Verificar articulos objetivo
    print("=== Articulos objetivo ===")
    for law_id, art_id, ref, notes in MAPPINGS:
        c.execute("SELECT article_ref, title FROM articles WHERE id=?", (art_id,))
        r = c.fetchone()
        if r:
            print(f"  OK id={art_id}: law_id={law_id} ref={r[0]} | {r[1][:60]}")
        else:
            print(f"  ERROR: article_id={art_id} NO existe en BD")
    print()

    # Determinar operaciones: UPDATE el existente (law_id=18) y INSERT los nuevos
    existing_law_ids = {row[1]: row[0] for row in current}  # law_id -> ts_id

    print("=== Operaciones previstas ===")
    for law_id, art_id, ref, notes in MAPPINGS:
        if law_id in existing_law_ids:
            ts_id = existing_law_ids[law_id]
            print(f"  UPDATE ts_id={ts_id} (law_id={law_id}): article_id -> {art_id}")
        else:
            print(f"  INSERT: topic_id={ESP28_TOPIC_ID} law_id={law_id} article_id={art_id}")

    if DRY_RUN:
        print("\n[DRY-RUN] Sin cambios. Usa --apply para ejecutar.")
        conn.close()
        return

    # === APLICAR ===
    backup_db()
    now = datetime.now().isoformat()

    for law_id, art_id, ref, notes in MAPPINGS:
        if law_id in existing_law_ids:
            ts_id = existing_law_ids[law_id]
            c.execute(
                """UPDATE topic_sources
                   SET article_id=?, normative_reference=?, mapping_basis=?, notes=?, updated_at=?
                   WHERE id=?""",
                (art_id, ref, "fase2p_planificacion_arts_proximos", notes, now, ts_id),
            )
            print(f"[UPDATE] ts_id={ts_id} law_id={law_id} -> article_id={art_id}")
        else:
            c.execute(
                """INSERT INTO topic_sources
                   (topic_id, law_id, article_id, normative_reference, coverage_status,
                    mapping_basis, priority, validation_status, notes, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    ESP28_TOPIC_ID, law_id, art_id, ref,
                    "covered",
                    "fase2p_planificacion_arts_proximos",
                    2,
                    "pendiente_de_validacion",
                    notes,
                    now, now,
                ),
            )
            print(f"[INSERT] topic_sources esp-28 law_id={law_id} -> article_id={art_id}")

    conn.commit()
    conn.close()
    print("\n[OK] Fase 2P aplicada. Ejecuta: python scripts/validate_article_quality.py")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Ola C1: SRS tipo Anki (SM-2 algorithm) + Plan diario.

Pasos:
1. Crear tablas de SRS
2. Inicializar artículos en SRS
3. Generar plan diario de ejemplo
4. Validar

DRY RUN: ejecutar con --dry-run para ver qué pasaría sin hacer cambios.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta

from src.core.db import connect
from src.study.srs_schema import apply_srs_schema, srs_tables_exist
from src.study.srs_calculator import SM2Calculator


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ola C1: SRS tipo Anki + Plan diario"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostrar que pasaria sin hacer cambios"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("OLA C1: SRS tipo Anki (SM-2) + Plan diario")
    print("=" * 70)

    if args.dry_run:
        print("\n[DRY-RUN] Modo simulacion (sin cambios reales)\n")

    try:
        with connect() as conn:
            print("\nPaso 1: Crear tablas de SRS...")
            apply_srs_schema(conn)
            if srs_tables_exist(conn):
                print("[OK] Tablas srs_state, study_plan_days, study_plan_items creadas")
            else:
                print("[ERROR] Las tablas no se crearon correctamente")
                return 1

            print("\nPaso 2: Inicializar articulos en SRS...")
            if not args.dry_run:
                # Obtener articulos de topic_sources (los que están mapeados)
                articles = conn.execute(
                    """
                    SELECT DISTINCT article_id
                    FROM topic_sources
                    WHERE article_id IS NOT NULL
                    LIMIT 100
                    """
                ).fetchall()

                for (article_id,) in articles:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO srs_state(
                            scope_type, scope_id, due_at, state
                        ) VALUES (?, ?, ?, ?)
                        """,
                        (
                            "article", article_id,
                            datetime.now().date().isoformat(),
                            "new"
                        )
                    )

                print(f"     {len(articles)} articulos inicializados en SRS")

            print("\nPaso 3: Generar plan diario de ejemplo...")
            if not args.dry_run:
                today = datetime.now().date().isoformat()
                plan_day_id = None

                # Crear plan para hoy
                cursor = conn.execute(
                    """
                    INSERT INTO study_plan_days(plan_date, target_minutes, estimated_total_minutes)
                    VALUES (?, ?, ?)
                    """,
                    (today, 120, 120)
                )
                plan_day_id = int(cursor.lastrowid)

                # Obtener items vencidos
                calc = SM2Calculator(conn)
                due_items = calc.get_due_items(today)

                # Agregar al plan
                for item in due_items[:10]:  # Primeros 10 vencidos
                    conn.execute(
                        """
                        INSERT INTO study_plan_items(
                            plan_day_id, scope_type, scope_id, reason, estimated_minutes
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            plan_day_id,
                            item["scope_type"],
                            item["scope_id"],
                            "vencimiento_srs",
                            5
                        )
                    )

                print(f"     Plan para {today} con {min(10, len(due_items))} items")

            print("\nPaso 4: Validacion...")
            srs_count = int(conn.execute("SELECT COUNT(*) FROM srs_state").fetchone()[0])
            plan_day_count = int(conn.execute("SELECT COUNT(*) FROM study_plan_days").fetchone()[0])
            plan_item_count = int(conn.execute("SELECT COUNT(*) FROM study_plan_items").fetchone()[0])

            print(f"  [OK] srs_state: {srs_count} articulos")
            print(f"  [OK] study_plan_days: {plan_day_count} planes")
            print(f"  [OK] study_plan_items: {plan_item_count} items")

            if srs_count > 0:
                calc = SM2Calculator(conn)
                stats = calc.get_stats()
                print(f"\n  Estado SRS:")
                print(f"    - new: {stats['new']}")
                print(f"    - learning: {stats['learning']}")
                print(f"    - review: {stats['review']}")
                print(f"    - relearning: {stats['relearning']}")
                print(f"    - due_today: {stats['due_today']}")

            if not args.dry_run:
                conn.commit()
                print("\n[OK] Migracion completada y confirmada")
            else:
                print("\n[OK] Dry-run completado (sin cambios reales)")

        return 0

    except Exception as e:
        print(f"\n[ERROR] Error fatal: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

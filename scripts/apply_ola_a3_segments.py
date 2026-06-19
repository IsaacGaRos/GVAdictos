#!/usr/bin/env python3
"""
Ola A3: Referencias en grupo (topic_source_segments + materializador).

Pasos:
1. Crear tabla topic_source_segments
2. Materializar segmentos a topic_sources
3. Validar integridad

DRY RUN: ejecutar con --dry-run para ver qué pasaría sin hacer cambios.
"""

from __future__ import annotations

import argparse
import sys

from src.core.db import connect
from src.mapping.segments_schema import apply_segments_schema, segments_table_exists
from src.mapping.materializer import materialize_all_segments


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ola A3: Referencias en grupo (topic_source_segments)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostrar que pasaria sin hacer cambios"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("OLA A3: Referencias en grupo (topic_source_segments + materializador)")
    print("=" * 70)

    if args.dry_run:
        print("\n[DRY-RUN] Modo simulacion (sin cambios reales)\n")

    try:
        with connect() as conn:
            print("\nPaso 1: Crear tabla topic_source_segments...")
            apply_segments_schema(conn)
            if segments_table_exists(conn):
                print("[OK] Tabla topic_source_segments creada/verificada")
            else:
                print("[ERROR] La tabla no se creo correctamente")
                return 1

            print("\nPaso 2: Materializar segmentos a topic_sources...")
            result = materialize_all_segments(conn, dry_run=args.dry_run)
            print(f"     Temas procesados: {result['topics_processed']}")
            print(f"     Filas creadas: {result['total_article_rows_created']}")
            print(f"     Filas actualizadas: {result['total_article_rows_updated']}")

            print("\nPaso 3: Validacion...")
            if not args.dry_run:
                seg_count = conn.execute(
                    "SELECT COUNT(*) FROM topic_source_segments"
                ).fetchone()[0]
                print(f"  [OK] topic_source_segments: {seg_count} filas")

                # Verificar que topic_sources tiene filas
                ts_count = conn.execute(
                    "SELECT COUNT(*) FROM topic_sources"
                ).fetchone()[0]
                print(f"  [OK] topic_sources: {ts_count} filas")

                # Verificar FK
                orphans = conn.execute(
                    """
                    SELECT COUNT(*) FROM topic_source_segments
                    WHERE topic_id NOT IN (SELECT id FROM topics)
                       OR law_id NOT IN (SELECT id FROM laws)
                       OR (division_id IS NOT NULL AND division_id NOT IN (SELECT id FROM law_divisions))
                       OR (from_article_id IS NOT NULL AND from_article_id NOT IN (SELECT id FROM articles))
                       OR (to_article_id IS NOT NULL AND to_article_id NOT IN (SELECT id FROM articles))
                    """
                ).fetchone()[0]
                if orphans > 0:
                    print(f"  [WARN] {orphans} referencias huerfanas")
                else:
                    print(f"  [OK] Sin referencias huerfanas")

                conn.commit()
                print("\n[OK] Migracion completada y confirmada")
            else:
                print("  [OK] Dry-run completado (sin cambios reales)")

        return 0

    except Exception as e:
        print(f"\n[ERROR] Error fatal: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Ola A2: Estructura jerárquica de leyes (law_divisions + article_division).

Pasos:
1. Crear tablas law_divisions y article_division
2. Extraer estructura de cada ley (TÍTULO, CAPÍTULO, SECCIÓN)
3. Poblar law_divisions y article_division
4. Validar integridad

DRY RUN: ejecutar con --dry-run para ver qué pasaría sin hacer cambios.
"""

from __future__ import annotations

import argparse
import sys

from src.core.db import connect
from src.laws.divisions_schema import apply_divisions_schema, divisions_tables_exist
from src.laws.divisions import extract_divisions_for_law


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extraer estructura jerárquica de leyes (Ola A2)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostrar que pasaria sin hacer cambios"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("OLA A2: Estructura jerárquica (law_divisions + article_division)")
    print("=" * 70)

    if args.dry_run:
        print("\n[DRY-RUN] Modo simulacion (sin cambios reales)\n")

    try:
        with connect() as conn:
            print("\nPaso 1: Crear tablas de divisiones...")
            apply_divisions_schema(conn)
            if divisions_tables_exist(conn):
                print("[OK] Tablas law_divisions y article_division creadas/verificadas")
            else:
                print("[ERROR] Las tablas no se crearon correctamente")
                return 1

            print("\nPaso 2: Obtener lista de leyes...")
            laws = conn.execute(
                "SELECT id, name FROM laws ORDER BY id"
            ).fetchall()
            print(f"     Total de leyes: {len(laws)}")

            print("\nPaso 3: Extraer divisiones por ley...")
            total_divisions = 0
            total_articles_linked = 0

            for law_id, law_name in laws:
                stats = extract_divisions_for_law(law_id, dry_run=args.dry_run)
                if stats["articles_linked"] > 0:
                    print(
                        f"     {law_name:30} - "
                        f"divisiones: {stats['divisions_created']:3}, "
                        f"articulos: {stats['articles_linked']:3}"
                    )
                    total_divisions += stats["divisions_created"]
                    total_articles_linked += stats["articles_linked"]

            print(f"\nResumen:")
            print(f"  Total divisiones creadas: {total_divisions}")
            print(f"  Total articulos enlazados: {total_articles_linked}")

            print("\nPaso 4: Validacion...")
            if not args.dry_run:
                div_count = conn.execute("SELECT COUNT(*) FROM law_divisions").fetchone()[0]
                article_div_count = conn.execute("SELECT COUNT(*) FROM article_division").fetchone()[0]
                print(f"  [OK] law_divisions: {div_count} filas")
                print(f"  [OK] article_division: {article_div_count} filas")

                # Verificar integridad FK
                orphans = conn.execute(
                    """
                    SELECT COUNT(*) FROM article_division
                    WHERE article_id NOT IN (SELECT id FROM articles)
                       OR division_id NOT IN (SELECT id FROM law_divisions)
                    """
                ).fetchone()[0]
                if orphans > 0:
                    print(f"  [WARN] {orphans} referencias huerfanas en article_division")
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

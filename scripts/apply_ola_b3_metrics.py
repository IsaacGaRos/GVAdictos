#!/usr/bin/env python3
"""
Ola B3: Metricas de importancia/frecuencia/dificultad.

Pasos:
1. Crear tablas de métricas
2. Materializar artículos, leyes, temas
3. Generar reportes

DRY RUN: ejecutar con --dry-run para ver qué pasaría sin hacer cambios.
"""

from __future__ import annotations

import argparse
import sys

from src.core.db import connect
from src.metrics.metrics_schema import apply_metrics_schema, metrics_tables_exist
from src.metrics.calculator import MetricsCalculator


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ola B3: Metricas de importancia"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostrar que pasaria sin hacer cambios"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("OLA B3: Metricas de importancia/frecuencia/dificultad")
    print("=" * 70)

    if args.dry_run:
        print("\n[DRY-RUN] Modo simulacion (sin cambios reales)\n")

    try:
        with connect() as conn:
            print("\nPaso 1: Crear tablas de metricas...")
            apply_metrics_schema(conn)
            if metrics_tables_exist(conn):
                print("[OK] Tablas article_metrics, law_metrics, topic_metrics creadas")
            else:
                print("[ERROR] Las tablas no se crearon correctamente")
                return 1

            print("\nPaso 2: Materializar metricas...")
            calc = MetricsCalculator(conn)

            if not args.dry_run:
                result_articles = calc.materialize_article_metrics()
                result_laws = calc.materialize_law_metrics()
                result_topics = calc.materialize_topic_metrics()

                print(f"     Articulos: {result_articles['articles_updated']} actualizados")
                print(f"     Leyes: {result_laws['laws_updated']} actualizadas")
                print(f"     Temas: {result_topics['topics_updated']} actualizados")
                print(f"     Pesos: {result_articles['weights_version']}")

            print("\nPaso 3: Validacion...")
            article_count = int(conn.execute("SELECT COUNT(*) FROM article_metrics").fetchone()[0])
            law_count = int(conn.execute("SELECT COUNT(*) FROM law_metrics").fetchone()[0])
            topic_count = int(conn.execute("SELECT COUNT(*) FROM topic_metrics").fetchone()[0])
            weights_count = int(conn.execute("SELECT COUNT(*) FROM importance_weights").fetchone()[0])

            print(f"  [OK] article_metrics: {article_count} filas")
            print(f"  [OK] law_metrics: {law_count} filas")
            print(f"  [OK] topic_metrics: {topic_count} filas")
            print(f"  [OK] importance_weights: {weights_count} versiones")

            # Top articulos por importancia
            if article_count > 0:
                print("\n  Top 5 articulos por importancia:")
                top = conn.execute(
                    """
                    SELECT a.article_ref, am.importance_score, am.exam_count, am.difficulty_index
                    FROM article_metrics am
                    INNER JOIN articles a ON a.id = am.article_id
                    ORDER BY am.importance_score DESC
                    LIMIT 5
                    """
                ).fetchall()
                for art_ref, importance, exam_cnt, difficulty in top:
                    print(f"    {art_ref}: {importance:.4f} (exams: {exam_cnt}, difficulty: {difficulty:.2f})")

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

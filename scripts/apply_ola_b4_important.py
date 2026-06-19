#!/usr/bin/env python3
"""
Ola B4: "Solo lo importante" + badges de importancia.

Demo: muestra filtrado por importancia y genera reportes.
"""

from __future__ import annotations

import argparse
import sys

from src.core.db import connect
from src.metrics.importance_filter import ImportanceFilterService


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ola B4: Solo lo importante + badges"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("OLA B4: 'Solo lo importante' + badges de importancia")
    print("=" * 70)

    try:
        with connect() as conn:
            service = ImportanceFilterService(conn)

            print("\nPaso 1: Reporte de cobertura (threshold=0.5)...")
            report = service.get_coverage_report(threshold=0.5)
            print(f"  Total articulos: {report['total_articles']}")
            print(f"  Importantes (>=0.5): {report['important_articles']}")
            print(f"  No importantes: {report['not_important_articles']}")
            print(f"  Cobertura: {report['coverage_percent']}%")

            print("\n  Top 3 leyes por importancia:")
            for law in report["by_law"][:3]:
                print(f"    {law['law_name']}: {law['important']}/{law['total']} "
                      f"({law['coverage']}%)")

            print("\n  Top 3 temas por importancia:")
            for topic in report["by_topic"][:3]:
                print(f"    Tema {topic['topic_number']} ({topic['part']}): "
                      f"{topic['important']}/{topic['total']} ({topic['coverage']}%)")

            print("\nPaso 2: Articulos importantes (top 5)...")
            important = service.get_important_articles(threshold=0.5, limit=5)
            for art in important:
                print(f"  {art['article_ref']}: {art['importance_score']:.4f} "
                      f"(exams: {art['exam_count']}, difficulty: {art['difficulty_index']:.2f})")

            print("\nPaso 3: Rankings por diferentes criterios...")
            print("  Top 3 por importancia:")
            for art in service.get_ranked_articles(order_by="importance", limit=3):
                print(f"    {art['article_ref']}: {art['importance_score']:.4f}")

            print("  Top 3 mas preguntados:")
            for art in service.get_ranked_articles(order_by="exam_count", limit=3):
                print(f"    {art['article_ref']}: {art['exam_count']} exams")

            print("  Top 3 mas dificiles:")
            for art in service.get_ranked_articles(order_by="difficulty", limit=3):
                print(f"    {art['article_ref']}: {art['difficulty_index']:.2f}")

            print("\nPaso 4: Distribucion de importancia...")
            dist = service.get_importance_distribution()
            print(f"  Total: {dist['total']}")
            for bucket in dist["buckets"]:
                print(f"    {bucket['label']} ({bucket['range']}): {bucket['count']}")

            print("\nPaso 5: Badge de ejemplo...")
            if important:
                art = important[0]
                badge = service.generate_importance_badge(art)
                print(f"  Articulo: {art['article_ref']}")
                print(f"  HTML badge: {len(badge)} caracteres")
                # Mostrar parte del HTML
                if "<span title=" in badge:
                    label_part = badge[badge.find("<span title=")+12:badge.find("</span>")+7]
                    print(f"    Badge muestra: {label_part}")

            print("\n[OK] Demo completada")
            return 0

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

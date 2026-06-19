#!/usr/bin/env python3
"""
Ola A4: Modos de estudio (por ley, por tema, "solo lo importante").

Demo: muestra acceso a estudios por ley, por tema, y filtrado por importancia.
No crea tablas nuevas, solo integra servicios existentes.
"""

from __future__ import annotations

import argparse
import sys

from src.core.db import connect
from src.study.study_mode_service import StudyModeService


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ola A4: Modos de estudio"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("OLA A4: Modos de estudio (por ley, por tema, solo importante)")
    print("=" * 70)

    try:
        with connect() as conn:
            service = StudyModeService(conn)

            print("\nPaso 1: Demo - Estudio por ley...")
            # Obtener primera ley con artículos
            law = conn.execute(
                """
                SELECT l.id, l.name
                FROM laws l
                INNER JOIN articles a ON a.law_id = l.id
                GROUP BY l.id
                ORDER BY COUNT(a.id) DESC
                LIMIT 1
                """
            ).fetchone()

            if law:
                law_id = law[0]
                law_study = service.get_law_study_structure(law_id)
                print(f"  {law_study['law_name']}")
                print(f"    - Articulos: {law_study['article_count']}")
                print(f"    - Divisiones: {len(law_study['divisions'])}")
                print(f"    - Progreso promedio: {law_study['avg_completion']}%")

            print("\nPaso 2: Demo - Estudio por tema...")
            # Obtener primer tema con artículos
            topic = conn.execute(
                """
                SELECT t.id, t.topic_number, t.part
                FROM topics t
                INNER JOIN topic_sources ts ON ts.topic_id = t.id
                GROUP BY t.id
                ORDER BY COUNT(ts.article_id) DESC
                LIMIT 1
                """
            ).fetchone()

            if topic:
                topic_id = topic[0]
                topic_study = service.get_topic_study_plan(topic_id)
                print(f"  Tema {topic_study['topic_number']} ({topic_study['part']})")
                print(f"    - Articulos: {len(topic_study['articles'])}")
                print(f"    - Notas: {topic_study['study_summary']['total_notes']}")
                print(f"    - Subrayados: {topic_study['study_summary']['total_highlights']}")
                print(f"    - Preguntas vinculadas: {topic_study['questions_linked']}")
                print(f"    - SRS: {topic_study['srs_stats']['new']} new, "
                      f"{topic_study['srs_stats']['review']} review")
                print(f"    - Progreso: {topic_study['study_summary']['avg_completion']}%")

            print("\nPaso 3: Demo - Solo lo importante...")
            important = service.get_important_articles(importance_threshold=0.5)
            print(f"  Articulos con importance >= 0.5: {len(important)}")
            if important:
                top = important[:3]
                for art in top:
                    print(f"    - {art['article_ref']}: {art['importance_score']:.4f} "
                          f"(exams: {art['exam_count']}, completion: {art['completion']}%)")

            print("\nPaso 4: Resumen general de progreso...")
            summary = service.get_study_progress_summary()
            print(f"  Items totales: {summary['total_items']}")
            print(f"  Completados: {summary['completed']}")
            print(f"  En progreso: {summary['in_progress']}")
            print(f"  Progreso promedio: {summary['avg_completion']}%")
            print(f"  Minutos estudiados: {summary['total_minutes']}")
            print(f"  Pomodoros: {summary['total_pomodoros']}")

            print("\n[OK] Demo completada")
            return 0

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

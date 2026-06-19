#!/usr/bin/env python3
"""
Ola C2-C4: Plan diario inteligente, Dashboard, Análisis de errores.

Demo: genera plan, muestra dashboard, propone repaso por errores.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

from src.core.db import connect
from src.study.planner_service import DailyPlannerService
from src.study.dashboard_service import DashboardService
from src.study.error_analyzer import ErrorAnalyzerService


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ola C2-C4: Plan diario, Dashboard, Análisis de errores"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("OLA C2-C4: Plan diario inteligente + Dashboard + Análisis de errores")
    print("=" * 70)

    try:
        with connect() as conn:
            print("\nC2: Generando plan diario inteligente...")
            planner = DailyPlannerService(conn)
            plan = planner.generate_daily_plan(target_minutes=120)
            print(f"  Plan para {plan['plan_date']}")
            print(f"    - Items: {plan['planned_items']}")
            print(f"    - Tiempo estimado: {plan['estimated_total_minutes']}/{plan['target_minutes']} min")
            print(f"    - Razones: ", end="")
            reasons = {}
            for item in plan["items"]:
                reasons[item["reason"]] = reasons.get(item["reason"], 0) + 1
            print(", ".join(f"{k}: {v}" for k, v in reasons.items()))

            print("\nC3: Dashboard de estudio...")
            dashboard = DashboardService(conn)
            summary = dashboard.get_dashboard_summary()

            progress = summary["progress"]
            print(f"  Progreso general:")
            print(f"    - Completados: {progress['completed']}/{progress['total_items']} ({progress['completion_percent']}%)")
            print(f"    - En progreso: {progress['in_progress']}")
            print(f"    - No iniciados: {progress['not_started']}")
            print(f"    - Minutos estudiados: {progress['total_minutes_studied']}")
            print(f"    - Pomodoros: {progress['total_pomodoros']}")

            srs = summary["srs"]
            print(f"  SRS (SM-2):")
            print(f"    - New: {srs['new']}, Learning: {srs['learning']}, Review: {srs['review']}")
            print(f"    - Vencidas hoy: {srs['due_today']}")

            approval = summary["approval_estimate"]
            print(f"  Estimación de aprobado:")
            print(f"    - Probabilidad: {approval['approval_chance']}")
            print(f"    - Score: {approval['estimated_approval_score']:.1f}")
            print(f"    - Días a examen (estimado): {approval['days_to_exam_estimate']}")

            streak = summary["streak"]
            print(f"  Racha de estudio:")
            print(f"    - Racha actual: {streak['current_streak_days']} días")
            print(f"    - Total estudiados: {streak['total_days_studied']} días")

            strengths_weaknesses = summary["strengths_weaknesses"]
            if strengths_weaknesses["strengths"]:
                print(f"  Temas fuertes (top 1):")
                s = strengths_weaknesses["strengths"][0]
                print(f"    - Tema {s['topic_number']}: {s['completion']}% completado")

            if strengths_weaknesses["weaknesses"]:
                print(f"  Temas débiles (bottom 1):")
                w = strengths_weaknesses["weaknesses"][0]
                print(f"    - Tema {w['topic_number']}: {w['completion']}% completado")

            print("\nC4: Análisis de errores y propuesta de repaso...")
            analyzer = ErrorAnalyzerService(conn)

            weak = analyzer.get_weak_articles()
            print(f"  Artículos débiles: {len(weak)}")
            if weak:
                w = weak[0]
                print(f"    - {w['article_ref']}: severity={w['severity']}, "
                      f"error_rate={w['error_rate']}, completion={w['completion']}%")

            review_plan = analyzer.propose_review_plan(days=7)
            print(f"  Plan de repaso (próximos {review_plan['review_period_days']} días):")
            print(f"    - Items a repasar: {review_plan['total_items_to_review']}")
            print(f"    - Tiempo estimado: {review_plan['estimated_total_minutes']} minutos")

            error_patterns = analyzer.get_common_error_patterns()
            print(f"  Patrón común de error:")
            print(f"    - {error_patterns['pattern']}")
            print(f"    - Artículos: {len(error_patterns['articles'])}")

            conn.commit()
            print("\n[OK] Demo completada")
            return 0

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Ola B1: Banco de exámenes oficiales (schema + tablas).

Pasos:
1. Crear tablas de exambank
2. Validar integridad

DRY RUN: ejecutar con --dry-run para ver qué pasaría sin hacer cambios.
"""

from __future__ import annotations

import argparse
import sys

from src.core.db import connect
from src.tests.exambank_schema import apply_exambank_schema, exambank_tables_exist


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ola B1: Banco de exámenes oficiales"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostrar que pasaria sin hacer cambios"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("OLA B1: Banco de examenes oficiales (schema + tablas)")
    print("=" * 70)

    if args.dry_run:
        print("\n[DRY-RUN] Modo simulacion (sin cambios reales)\n")

    try:
        with connect() as conn:
            print("\nPaso 1: Crear tablas de exambank...")
            apply_exambank_schema(conn)
            if exambank_tables_exist(conn):
                print("[OK] Tablas exam_papers, exam_questions, exam_question_options, exam_question_links creadas")
            else:
                print("[ERROR] Las tablas no se crearon correctamente")
                return 1

            print("\nPaso 2: Validacion...")
            exam_count = int(conn.execute("SELECT COUNT(*) FROM exam_papers").fetchone()[0])
            question_count = int(conn.execute("SELECT COUNT(*) FROM exam_questions").fetchone()[0])
            option_count = int(conn.execute("SELECT COUNT(*) FROM exam_question_options").fetchone()[0])
            link_count = int(conn.execute("SELECT COUNT(*) FROM exam_question_links").fetchone()[0])

            print(f"  [OK] exam_papers: {exam_count} filas")
            print(f"  [OK] exam_questions: {question_count} filas")
            print(f"  [OK] exam_question_options: {option_count} filas")
            print(f"  [OK] exam_question_links: {link_count} filas")

            # Verificar indices
            indices = [
                "idx_exam_papers_convocatoria",
                "idx_exam_questions_paper",
                "idx_exam_question_options_question",
                "idx_exam_question_links_article",
            ]
            missing = []
            for idx in indices:
                row = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?",
                    (idx,)
                ).fetchone()
                if not row:
                    missing.append(idx)

            if missing:
                print(f"  [WARN] Indices faltantes: {missing}")
            else:
                print(f"  [OK] Todos los indices creados")

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

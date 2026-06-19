#!/usr/bin/env python3
"""Migrate simulacros feature tables to the database."""

import sys
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.paths import DB_PATH
from src.simulacros.schema import ensure_simulacros_tables, missing_simulacros_tables


def main():
    apply = "--apply" in sys.argv
    db_path = DB_PATH

    print(f"Database path: {db_path}")
    print(f"Mode: {'APPLY' if apply else 'DRY-RUN'}")
    print()

    conn = sqlite3.connect(db_path)
    try:
        missing = missing_simulacros_tables(conn)

        if not missing:
            print("[OK] All simulacros tables already exist.")
            return 0

        print(f"Missing tables: {', '.join(missing)}")
        print()

        if not apply:
            print("DRY-RUN: Would create the following tables:")
            print("  - mock_exams")
            print("  - mock_exam_answers")
            print()
            print("Run with --apply flag to actually create the tables.")
            return 0

        print("Creating simulacros tables...")
        ensure_simulacros_tables(conn)
        print("[OK] Simulacros tables created successfully.")

        missing_after = missing_simulacros_tables(conn)
        if missing_after:
            print(f"[ERROR] Some tables still missing: {missing_after}")
            return 1

        print("[OK] All simulacros tables verified.")
        return 0

    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())

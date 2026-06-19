#!/usr/bin/env python3
"""Migrate AI feature tables to the database.

Usage:
    python scripts/migrate_ai_features.py [--apply]

Without --apply, performs a dry-run and shows the SQL that would be executed.
With --apply, actually creates the tables and commits the changes.
"""

import sys
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.paths import DB_PATH
from src.core.db import connect
from src.ai.schema import ensure_ai_tables, missing_ai_tables


def main():
    apply = "--apply" in sys.argv
    db_path = DB_PATH

    print(f"Database path: {db_path}")
    print(f"Mode: {'APPLY' if apply else 'DRY-RUN'}")
    print()

    conn = sqlite3.connect(db_path)
    try:
        missing = missing_ai_tables(conn)

        if not missing:
            print("[OK] All AI feature tables already exist.")
            return 0

        print(f"Missing tables: {', '.join(missing)}")
        print()

        if not apply:
            print("DRY-RUN: Would create the following tables:")
            print("  - ai_article_insights")
            print("  - ai_prompt_cache")
            print()
            print("Run with --apply flag to actually create the tables.")
            return 0

        print("Creating AI feature tables...")
        ensure_ai_tables(conn)
        print("[OK] AI feature tables created successfully.")

        # Verify
        missing_after = missing_ai_tables(conn)
        if missing_after:
            print(f"[ERROR] Some tables still missing: {missing_after}")
            return 1

        print("[OK] All AI feature tables verified.")
        return 0

    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())

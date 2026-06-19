#!/usr/bin/env python3
"""Create remaining Ola F tables (F4-F7)."""

import sys
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.paths import DB_PATH

TABLES_SQL = """
-- F4: Postgres-prep tables (already in use via ORM)
-- Tables will be created by sqlalchemy.orm.create_all()

-- F5: Subscriptions (Stripe)
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan TEXT NOT NULL DEFAULT 'free',
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    status TEXT DEFAULT 'active',
    current_period_end TEXT,
    cancel_at_period_end INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_plan
    ON subscriptions(plan, status);

-- F6: Backup history
CREATE TABLE IF NOT EXISTS backup_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    backup_type TEXT NOT NULL,
    drive_file_id TEXT,
    size_bytes INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_backup_history_user
    ON backup_history(user_id, created_at DESC);

-- F7: Multi-oposición
CREATE TABLE IF NOT EXISTS oposiciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    nombre TEXT NOT NULL,
    administracion TEXT,
    activa INTEGER DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_oposiciones_code
    ON oposiciones(code);

CREATE TABLE IF NOT EXISTS user_oposicion_enrollment (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    oposicion_id INTEGER NOT NULL REFERENCES oposiciones(id),
    enrolled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, oposicion_id)
);

CREATE INDEX IF NOT EXISTS idx_user_oposicion_enrollment_user
    ON user_oposicion_enrollment(user_id);
"""


def main():
    apply = "--apply" in sys.argv
    db_path = DB_PATH

    print(f"Database: {db_path}")
    print(f"Mode: {'APPLY' if apply else 'DRY-RUN'}")
    print()

    conn = sqlite3.connect(db_path)
    try:
        if not apply:
            print("DRY-RUN: Would create tables:")
            print("  - subscriptions (F5)")
            print("  - backup_history (F6)")
            print("  - oposiciones (F7)")
            print("  - user_oposicion_enrollment (F7)")
            print()
            print("Run with --apply to create tables")
            return 0

        print("Creating Ola F tables...")
        conn.executescript(TABLES_SQL)
        print("[OK] All Ola F tables created successfully")
        return 0

    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())

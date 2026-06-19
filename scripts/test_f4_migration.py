#!/usr/bin/env python3
"""Test F4 PostgreSQL migration setup.

Usage:
    python scripts/test_f4_migration.py
"""

import os
import sys
import time
import subprocess

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def test_dependencies():
    """Check if required packages are installed."""
    print("[Test] Checking dependencies...")
    try:
        import sqlalchemy
        import alembic
        import psycopg2
        print("[OK] All dependencies installed")
        return True
    except ImportError as e:
        print(f"[FAIL] Missing dependency: {e}")
        print("    Run: pip install -r requirements.txt")
        return False


def test_sqlite_engine():
    """Test SQLite engine (default)."""
    print("\n[Test] Testing SQLite engine...")
    try:
        from src.db.database import get_engine, get_database_url

        url = get_database_url()
        print(f"    URL: {url}")

        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(__import__('sqlalchemy').text("SELECT 1"))
            print("[OK] SQLite engine works")
        return True
    except Exception as e:
        print(f"[FAIL] SQLite engine error: {e}")
        return False


def test_postgres_available():
    """Check if PostgreSQL is available (requires docker-compose up)."""
    print("\n[Test] Checking PostgreSQL availability...")
    print("    (Make sure docker-compose is running: docker-compose up -d)")

    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost",
            database="gvadictos_db",
            user="gvadictos",
            password="dev_password",
            connect_timeout=2,
        )
        conn.close()
        print("[OK] PostgreSQL is available")
        return True
    except Exception as e:
        print(f"[SKIP] PostgreSQL not available: {e}")
        print("    Run: docker-compose up -d postgres")
        return False


def test_alembic_current():
    """Check current Alembic revision."""
    print("\n[Test] Checking Alembic current revision...")
    try:
        result = subprocess.run(
            ["alembic", "current"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            print(f"    Current: {result.stdout.strip()}")
            print("[OK] Alembic is configured")
            return True
        else:
            print(f"[FAIL] Alembic error: {result.stderr}")
            return False
    except Exception as e:
        print(f"[FAIL] Alembic check failed: {e}")
        return False


def test_models_import():
    """Test importing SQLAlchemy models."""
    print("\n[Test] Testing SQLAlchemy models import...")
    try:
        from src.db.models import (
            Base, Law, Article, Topic, User, Subscription,
            Entitlement, BackupHistory, ExamResult,
        )
        model_count = len(Base.registry.mappers)
        print(f"[OK] Imported {model_count} models")
        return True
    except Exception as e:
        print(f"[FAIL] Model import error: {e}")
        return False


def test_database_init():
    """Test database initialization."""
    print("\n[Test] Testing database initialization...")
    try:
        from src.db.database import init_db
        init_db()
        print("[OK] Database initialized")
        return True
    except Exception as e:
        print(f"[FAIL] Database init error: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("GVAdictos F4 PostgreSQL Migration Test")
    print("=" * 60)

    tests = [
        test_dependencies,
        test_models_import,
        test_sqlite_engine,
        test_alembic_current,
        test_database_init,
        test_postgres_available,
    ]

    results = [test() for test in tests]

    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)

    if passed >= 5:
        print("\n[OK] Core tests passed! Ready for migration.")
        print("\nNext steps:")
        print("  1. Start PostgreSQL: docker-compose up -d postgres")
        print("  2. Run migrations: alembic upgrade head")
        print("  3. Start API: uvicorn src.api.app:app --reload")
        return 0
    else:
        print("\n[FAIL] Some tests failed. See above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

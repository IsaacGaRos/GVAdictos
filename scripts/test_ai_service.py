#!/usr/bin/env python3
"""Quick test of AIService functionality.

Usage:
    python scripts/test_ai_service.py
"""

import sys
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.paths import DB_PATH
from src.ai.service import AIService, AIConfigError
from src.ai.schema import missing_ai_tables


def main():
    print("Testing AIService...")
    print()

    # Check DB tables
    print("[1] Checking AI tables...")
    conn = sqlite3.connect(DB_PATH)
    missing = missing_ai_tables(conn)
    if missing:
        print(f"    [ERROR] Missing tables: {missing}")
        conn.close()
        return 1
    print("    [OK] All AI tables exist")
    print()

    # Try to init AIService
    print("[2] Initializing AIService...")
    try:
        service = AIService(conn)
        print(f"    [OK] Service initialized")
        print(f"    Model: {service.model}")
        print(f"    Prompt version: {service.prompt_version}")
    except AIConfigError as e:
        print(f"    [WARNING] {e}")
        print("    (This is expected if ANTHROPIC_API_KEY is not set)")
    except Exception as e:
        print(f"    [ERROR] {e}")
        conn.close()
        return 1
    print()

    # Check a sample article
    print("[3] Checking sample article...")
    cursor = conn.execute("SELECT id, title FROM articles LIMIT 1")
    article = cursor.fetchone()
    if not article:
        print("    [WARNING] No articles in database")
    else:
        article_id, title = article
        print(f"    Article ID: {article_id}")
        print(f"    Title: {title}")
        print(f"    [OK] Sample article found")
    print()

    conn.close()

    print("[OK] AIService test completed successfully")
    print()
    print("Next steps:")
    print("  1. Set ANTHROPIC_API_KEY environment variable")
    print("  2. Integrate AIService into app.py or create dedicated features")
    print("  3. Start with D2 (AI article insights) or jump to other modules")
    return 0


if __name__ == "__main__":
    sys.exit(main())

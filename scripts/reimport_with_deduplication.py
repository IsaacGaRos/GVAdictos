#!/usr/bin/env python3
"""Re-import laws with improved duplicate filtering."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.db import connect
from src.laws.importer import import_law

def find_duplicates():
    """Find laws with duplicate article refs."""
    with connect() as conn:
        duplicates = conn.execute("""
            SELECT l.id, l.name, a.article_ref, COUNT(*) as count
            FROM articles a
            JOIN laws l ON l.id = a.law_id
            GROUP BY l.id, a.article_ref
            HAVING count > 1
            ORDER BY l.name, a.article_ref
        """).fetchall()
    return duplicates

def reimport_law(law_id: int):
    """Re-import a law by its ID."""
    with connect() as conn:
        law = conn.execute("SELECT name, source_path FROM laws WHERE id = ?", (law_id,)).fetchone()

    if not law:
        print(f"Law {law_id} not found")
        return False

    source_path = Path(law['source_path'])
    if not source_path.exists():
        print(f"Source file not found: {source_path}")
        return False

    print(f"Re-importing: {law['name']} from {source_path}")
    try:
        import_law(source_path, law['name'], original_source_path=source_path)
        print(f"✓ {law['name']} re-imported successfully")
        return True
    except Exception as e:
        print(f"✗ Error re-importing {law['name']}: {e}")
        return False

if __name__ == "__main__":
    print("Checking for duplicate articles...\n")
    duplicates = find_duplicates()

    if not duplicates:
        print("No duplicates found! Parser is working correctly.")
        sys.exit(0)

    # Group by law
    laws_with_dupes = {}
    for row in duplicates:
        law_id = row['id']
        if law_id not in laws_with_dupes:
            laws_with_dupes[law_id] = {"name": row['name'], "dupes": []}
        laws_with_dupes[law_id]["dupes"].append(row['article_ref'])

    print(f"Found {len(laws_with_dupes)} laws with duplicates:\n")
    for law_id, info in laws_with_dupes.items():
        print(f"  {info['name']}: {len(info['dupes'])} duplicate article refs")

    print(f"\nRe-importing {len(laws_with_dupes)} laws...")
    for law_id in laws_with_dupes.keys():
        reimport_law(law_id)

    print("\nVerifying...")
    remaining = find_duplicates()
    if remaining:
        print(f"WARNING: {len(remaining)} duplicates remain")
    else:
        print("✓ All duplicates removed!")

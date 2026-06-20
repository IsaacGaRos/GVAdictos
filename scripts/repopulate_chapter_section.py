"""Repopulate chapter and section fields in articles table by parsing law text structure.

Reads from data/processed/leyes_boe/ and updates articles.chapter, articles.section
by analyzing TÍTULO, CAPÍTULO, SECCIÓN patterns.

Usage:
    python scripts/repopulate_chapter_section.py [--law-id LAW_ID] [--dry-run]

Exit code 0 if successful.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "db" / "gvadicto.sqlite"
DATA_PROCESSED = ROOT / "data" / "processed" / "leyes_boe"


def parse_text_structure(text: str) -> dict[int, tuple[str, str]]:
    """Parse law text and extract article_ref -> (chapter, section) mapping.

    Returns mapping of article reference numbers to (chapter_name, section_name) tuples.
    """
    lines = text.split("\n")

    current_title = ""
    current_chapter = ""
    current_section = ""

    article_map = {}

    # Patterns to match structure headers
    title_pattern = re.compile(r"^(?:TÍTULO|TITLE)\s+(?:PRELIMINAR|[IVX]+|[0-9]+)\b", re.IGNORECASE)
    chapter_pattern = re.compile(r"^(?:CAPÍTULO|CHAPTER)\s+(?:PRIMERO|SEGUNDO|TERCERO|CUARTO|QUINTO|SEXTO|SÉPTIMO|OCTAVO|NOVENO|DÉCIMO|[IVX]+|[0-9]+)", re.IGNORECASE)
    section_pattern = re.compile(r"^(?:Sección|SECCIÓN|Section)\s+(?:\d+\.?ª|[IVX]+|[0-9]+\.?[ªª]?)", re.IGNORECASE)
    article_pattern = re.compile(r"^(?:Artículo|ARTÍCULO|Art\.|ART\.)\s+(?P<ref>\d+)", re.IGNORECASE)

    for line in lines:
        stripped = line.strip()

        # Check for title
        if title_pattern.match(stripped):
            current_title = stripped
            current_chapter = ""
            current_section = ""
            continue

        # Check for chapter
        if chapter_pattern.match(stripped):
            current_chapter = stripped
            current_section = ""
            continue

        # Check for section
        if section_pattern.match(stripped):
            current_section = stripped
            continue

        # Check for article
        m = article_pattern.match(stripped)
        if m:
            article_ref = m.group("ref")
            # Store mapping
            chapter = current_chapter or current_title or ""
            section = current_section or ""
            article_map[int(article_ref)] = (chapter.strip(), section.strip())

    return article_map


def get_law_source_info(law_id: int, conn: sqlite3.Connection) -> Optional[str]:
    """Get the source path for a law from the database."""
    c = conn.cursor()
    result = c.execute(
        "SELECT source_path FROM laws WHERE id = ?", (law_id,)
    ).fetchone()
    return result[0] if result else None


def main() -> int:
    import sys

    # Parse arguments
    law_id_filter = None
    dry_run = False

    if "--dry-run" in sys.argv:
        dry_run = True

    if "--law-id" in sys.argv:
        idx = sys.argv.index("--law-id")
        if idx + 1 < len(sys.argv):
            law_id_filter = int(sys.argv[idx + 1])

    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Get all laws with articles
    if law_id_filter:
        laws = c.execute(
            "SELECT DISTINCT id, name, source_path FROM laws WHERE id = ?",
            (law_id_filter,)
        ).fetchall()
    else:
        laws = c.execute(
            "SELECT DISTINCT id, name, source_path FROM laws WHERE id IN (SELECT DISTINCT law_id FROM articles)"
        ).fetchall()

    total_updated = 0
    total_skipped = 0

    for law in laws:
        law_id, law_name, source_path = law["id"], law["name"], law["source_path"]

        # Find text file - extract BOE ref from source_path if present
        text_file = None
        if source_path:
            # Try to extract BOE ref from path like "BOE_consolidadas/BOE-A-1978-31229_..."
            match = re.search(r"(BOE-A-\d+-\d+)", source_path)
            if match:
                boe_ref = match.group(1)
                text_file = DATA_PROCESSED / f"{boe_ref}.txt"

        if not text_file or not text_file.exists():
            # Fallback: try to find any .txt that matches part of law name
            matching = list(DATA_PROCESSED.glob("*.txt"))
            for f in matching:
                if any(part.lower() in f.stem.lower() for part in law_name.split()[:2]):
                    text_file = f
                    break

        if not text_file or not text_file.exists():
            print(f"[SKIP] Law {law_id} ({law_name}): no text file found")
            total_skipped += 1
            continue

        # Parse text
        try:
            text = text_file.read_text(encoding="utf-8", errors="replace")
            article_map = parse_text_structure(text)
        except Exception as e:
            print(f"[ERROR] Law {law_id} ({law_name}): parse error: {e}")
            total_skipped += 1
            continue

        if not article_map:
            print(f"[SKIP] Law {law_id} ({law_name}): no structure found")
            total_skipped += 1
            continue

        # Get articles for this law
        articles = c.execute(
            "SELECT id, article_ref FROM articles WHERE law_id = ?",
            (law_id,)
        ).fetchall()

        # Update articles
        updated_count = 0
        for article in articles:
            article_id = article["id"]
            article_ref_str = article["article_ref"]

            # Parse article_ref to get numeric part
            ref_match = re.search(r"(\d+)", article_ref_str or "")
            if not ref_match:
                continue

            ref_num = int(ref_match.group(1))
            if ref_num not in article_map:
                continue

            chapter, section = article_map[ref_num]

            if dry_run:
                print(f"  [DRY] Article {article_ref_str}: chapter={chapter}, section={section}")
            else:
                c.execute(
                    "UPDATE articles SET chapter = ?, section = ? WHERE id = ?",
                    (chapter, section, article_id)
                )
                updated_count += 1

        if updated_count > 0:
            print(f"[OK] Law {law_id} ({law_name}): {updated_count} articles updated")
            total_updated += updated_count
        else:
            print(f"[SKIP] Law {law_id} ({law_name}): no matching articles")
            total_skipped += 1

    if not dry_run:
        conn.commit()
        print(f"\n[OK] Database committed: {total_updated} articles updated")
    else:
        print(f"\n[DRY RUN] Would update {total_updated} articles")

    conn.close()
    return 0 if not dry_run else 0


if __name__ == "__main__":
    exit(main())

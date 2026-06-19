"""Pass 4: final residue cleanup.

  - Strip index lines using *spaced* dotted leaders ". . . . ." (the earlier
    passes only caught runs of consecutive dots).
  - Trim trailing uppercase structural headings (TÍTULO/CAPÍTULO/SECCIÓN/...)
    regardless of length when the line clearly starts a heading.
  - Drop malformed EUR-Lex rows whose article_ref contains a newline.

FK-safe and idempotent.
"""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "db" / "gvadicto.sqlite"

# dot, then 3+ more dots that may be separated by spaces: "...." or ". . . ."
DOTTED_RE = re.compile(r"\.(\s*\.){3,}")
# Unambiguous heading: keyword + roman/number/ordinal
STRUCT_HEAD_RE = re.compile(
    r"^\s*(T[ÍI]TULO|CAP[ÍI]TULO|SECCI[ÓO]N|SUBSECCI[ÓO]N|LIBRO|PARTE|ANEXO)\s+"
    r"([IVXLCDM]+|\d+|PRELIMINAR|[ÚU]NICO|PRIMERO|SEGUNDO|TERCERO)\b",
    re.IGNORECASE,
)


def clean(text: str) -> str:
    out = []
    for idx, ln in enumerate(text.split("\n")):
        if DOTTED_RE.search(ln):
            continue
        if idx > 0 and STRUCT_HEAD_RE.match(ln):
            break
        out.append(ln)
    return "\n".join(out).strip()


def main() -> None:
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    cleaned = 0
    for r in c.execute("SELECT id, text FROM articles").fetchall():
        new = clean(r["text"] or "")
        if new != (r["text"] or ""):
            conn.execute("UPDATE articles SET text=? WHERE id=?", (new, r["id"]))
            cleaned += 1

    # Drop malformed EUR-Lex rows (ref has a newline) -> FK-safe
    bad = c.execute("SELECT id FROM articles WHERE article_ref LIKE '%' || char(10) || '%'").fetchall()
    for r in bad:
        conn.execute("UPDATE topic_sources SET article_id=NULL WHERE article_id=?", (r["id"],))
        conn.execute("UPDATE study_annotations SET article_id=NULL WHERE article_id=?", (r["id"],))
        conn.execute("DELETE FROM articles WHERE id=?", (r["id"],))

    # Remove rows that became truly empty (but keep explicit derogados / sin contenido)
    empties = c.execute(
        "SELECT id, text FROM articles WHERE LENGTH(TRIM(text)) < 30"
    ).fetchall()
    removed_empty = 0
    for r in empties:
        t = (r["text"] or "").lower()
        if "derogad" in t or "sin contenido" in t:
            continue
        conn.execute("UPDATE topic_sources SET article_id=NULL WHERE article_id=?", (r["id"],))
        conn.execute("UPDATE study_annotations SET article_id=NULL WHERE article_id=?", (r["id"],))
        conn.execute("DELETE FROM articles WHERE id=?", (r["id"],))
        removed_empty += 1

    conn.commit()
    total = c.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    broken = c.execute(
        "SELECT COUNT(*) FROM topic_sources WHERE article_id IS NOT NULL "
        "AND article_id NOT IN (SELECT id FROM articles)"
    ).fetchone()[0]
    print(f"rows cleaned: {cleaned}")
    print(f"malformed EUR-Lex rows removed: {len(bad)}")
    print(f"empty rows removed (kept derogados): {removed_empty}")
    print(f"articles now: {total}, broken FKs: {broken}")
    conn.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

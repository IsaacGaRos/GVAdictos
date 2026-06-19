"""Pass 3: split rows where a second real article header was swallowed.

A handful of articles over-captured the following article (its
"Artículo N.  Title." header appears mid-body and that article exists nowhere
else). Split such rows into separate article rows so each contains only its
own consolidated text.

FK-safe: the first article keeps the original row id (so existing mappings stay
valid); the recovered article(s) are inserted as new rows.
"""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "db" / "gvadicto.sqlite"

# Line-start real header: capital Artículo, number, period, capitalized title
HEADER_RE = re.compile(r"(?m)^[ \t]*Art[íi]culo\s+(\d+(?:\s*(?:bis|ter))?)\.?\s+([A-ZÁÉÍÓÚ][^\n]*)$")


def main() -> None:
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    rows = c.execute("SELECT * FROM articles").fetchall()
    splits = 0
    new_rows = 0
    for r in rows:
        text = r["text"] or ""
        heads = list(HEADER_RE.finditer(text))
        if len(heads) < 2:
            continue
        # Only split when the second header introduces a DIFFERENT ref that
        # does not already exist for this law (a genuinely swallowed article).
        second = heads[1]
        second_ref = re.sub(r"\s+", " ", second.group(1)).strip()
        exists = c.execute(
            "SELECT COUNT(*) FROM articles WHERE law_id=? AND article_ref=? AND id!=?",
            (r["law_id"], second_ref, r["id"]),
        ).fetchone()[0]
        if exists:
            continue

        # Truncate original row at the second header
        first_text = text[: second.start()].strip()
        conn.execute("UPDATE articles SET text=? WHERE id=?", (first_text, r["id"]))
        splits += 1

        # Create rows for each subsequent segment
        for i in range(1, len(heads)):
            seg_start = heads[i].start()
            seg_end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
            seg_text = text[seg_start:seg_end].strip()
            ref = re.sub(r"\s+", " ", heads[i].group(1)).strip()
            title = heads[i].group(2).strip()
            # skip if this ref already exists (avoid dup)
            if c.execute(
                "SELECT COUNT(*) FROM articles WHERE law_id=? AND article_ref=?",
                (r["law_id"], ref),
            ).fetchone()[0]:
                continue
            conn.execute(
                "INSERT INTO articles(law_id, article_ref, title, text, source, original_hash, validation_status)"
                " VALUES (?,?,?,?,?,?,?)",
                (r["law_id"], ref, title, seg_text, r["source"], r["original_hash"], r["validation_status"]),
            )
            new_rows += 1

    conn.commit()
    total = c.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    print(f"rows split: {splits}, recovered articles inserted: {new_rows}")
    print(f"articles now: {total}")
    conn.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

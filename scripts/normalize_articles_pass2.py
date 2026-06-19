"""Pass 2 cleanup after normalize_articles_inplace.py.

Removes residual debris the first pass could not safely attribute:
  - lowercase 'artículo ...' citation rows (parser mis-split of disposiciones
    text that references other articles; never a real article),
  - inline BOE page-header phrases left mid-line,
  - trailing TÍTULO/CAPÍTULO/SECCIÓN headings still embedded,
then re-deduplicates by article_ref keeping the longest body.

Idempotent and FK-safe: any topic_sources/study_annotations pointing at a
removed row is re-pointed to the surviving article of the same reference,
or set NULL when none survives.
"""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "db" / "gvadicto.sqlite"

CITATION_START_RE = re.compile(r"^\s*art[íi]culo\s+\d")     # lowercase a
REALHEAD_START_RE = re.compile(r"^\s*(Art[íi]culo|Article)\s+\d")
PAGE_NOISE_LINE_RE = re.compile(
    r"^\s*(BOLET[IÍ]N OFICIAL DEL ESTADO|LEGISLACI[OÓ]N CONSOLIDADA|"
    r"P[áa]gina\s+\d+|cve:\s*BOE.*|ISSN:.*)\s*$",
    re.IGNORECASE,
)
PAGE_NOISE_INLINE_RE = re.compile(
    r"\s*(BOLET[IÍ]N OFICIAL DEL ESTADO|LEGISLACI[OÓ]N CONSOLIDADA|"
    r"P[áa]gina\s+\d+)\s*",
    re.IGNORECASE,
)
DOTTED_RE = re.compile(r"\.{4,}")
STRUCT_UPPER_RE = re.compile(
    r"^\s*(T[ÍI]TULO|CAP[ÍI]TULO|SECCI[ÓO]N|SUBSECCI[ÓO]N|LIBRO|PARTE|ANEXO|"
    r"AP[ÉE]NDICE|PRE[ÁA]MBULO)\b"
)
STRUCT_DISP_RE = re.compile(
    r"^\s*Disposici[óo]n(es)?\s+(adicional|transitoria|final|derogatoria)",
    re.IGNORECASE,
)


def is_struct_heading(line: str) -> bool:
    s = line.strip()
    if len(s) > 110:
        return False
    return bool(STRUCT_UPPER_RE.match(line) or STRUCT_DISP_RE.match(line))


def deep_clean(text: str) -> str:
    out = []
    for idx, ln in enumerate(text.split("\n")):
        if PAGE_NOISE_LINE_RE.match(ln):
            continue
        if DOTTED_RE.search(ln):
            continue
        if idx > 0 and is_struct_heading(ln):
            break
        # strip inline page-header phrases
        ln = PAGE_NOISE_INLINE_RE.sub(" ", ln)
        out.append(ln)
    return "\n".join(out).strip()


def main() -> None:
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # 1) Delete lowercase-citation debris rows (FK-safe)
    cit_rows = c.execute(
        "SELECT id, law_id, article_ref FROM articles WHERE text GLOB 'art*'"
        " AND text NOT GLOB 'Art*'"
    ).fetchall()
    deleted_cit = 0
    for r in cit_rows:
        text = c.execute("SELECT text FROM articles WHERE id=?", (r["id"],)).fetchone()["text"]
        if not (CITATION_START_RE.match(text) and not REALHEAD_START_RE.match(text)):
            continue
        # surviving sibling of same law+ref (capital/real), longest
        sib = c.execute(
            "SELECT id FROM articles WHERE law_id=? AND article_ref=? AND id!=?"
            " ORDER BY LENGTH(text) DESC LIMIT 1",
            (r["law_id"], r["article_ref"], r["id"]),
        ).fetchone()
        target = sib["id"] if sib else None
        if target:
            conn.execute("UPDATE topic_sources SET article_id=? WHERE article_id=?", (target, r["id"]))
            conn.execute("UPDATE study_annotations SET article_id=? WHERE article_id=?", (target, r["id"]))
        else:
            conn.execute("UPDATE topic_sources SET article_id=NULL WHERE article_id=?", (r["id"],))
            conn.execute("UPDATE study_annotations SET article_id=NULL WHERE article_id=?", (r["id"],))
        conn.execute("DELETE FROM articles WHERE id=?", (r["id"],))
        deleted_cit += 1

    # 2) Deep-clean every remaining row (inline page headers + trailing struct)
    cleaned = 0
    for r in c.execute("SELECT id, text FROM articles").fetchall():
        new = deep_clean(r["text"] or "")
        if new != (r["text"] or ""):
            conn.execute("UPDATE articles SET text=? WHERE id=?", (new, r["id"]))
            cleaned += 1

    # 3) Re-dedup law+ref keep longest (FK-safe)
    dedup = 0
    groups = c.execute(
        "SELECT law_id, article_ref FROM articles GROUP BY law_id, article_ref HAVING COUNT(*)>1"
    ).fetchall()
    for g in groups:
        rows = c.execute(
            "SELECT id, LENGTH(text) n FROM articles WHERE law_id=? AND article_ref=?"
            " ORDER BY n DESC",
            (g["law_id"], g["article_ref"]),
        ).fetchall()
        winner = rows[0]["id"]
        for loser in rows[1:]:
            conn.execute("UPDATE topic_sources SET article_id=? WHERE article_id=?", (winner, loser["id"]))
            conn.execute("UPDATE study_annotations SET article_id=? WHERE article_id=?", (winner, loser["id"]))
            conn.execute("DELETE FROM articles WHERE id=?", (loser["id"],))
            dedup += 1

    conn.commit()

    total = c.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    broken = c.execute(
        "SELECT COUNT(*) FROM topic_sources WHERE article_id IS NOT NULL"
        " AND article_id NOT IN (SELECT id FROM articles)"
    ).fetchone()[0]
    print(f"citation debris deleted: {deleted_cit}")
    print(f"rows deep-cleaned: {cleaned}")
    print(f"duplicates removed: {dedup}")
    print(f"articles now: {total}")
    print(f"broken FKs: {broken}")
    conn.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

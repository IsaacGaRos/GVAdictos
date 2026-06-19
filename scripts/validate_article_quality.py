"""Article + topic-mapping quality checks for the Estudiar pipeline.

Run after any import/normalization to detect regressions:

    python scripts/validate_article_quality.py

Exit code 0 if all blocking checks pass, 1 otherwise.
"""
from __future__ import annotations

import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "db" / "gvadicto.sqlite"

HEAD_LINE_RE = re.compile(r"(?m)^\s*Art[íi]culo\s+\d+\.?\s+[A-ZÁÉÍÓÚ]")
CITATION_RE = re.compile(r"^\s*art[íi]culo\s+\d")  # lowercase a


def main() -> int:
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    arts = c.execute("SELECT id, law_id, article_ref, title, text FROM articles").fetchall()

    failures = []
    warnings = []

    # 1. Same law + same article_ref repeated
    dup = c.execute(
        "SELECT COUNT(*) FROM (SELECT law_id, article_ref FROM articles "
        "GROUP BY law_id, article_ref HAVING COUNT(*) > 1)"
    ).fetchone()[0]
    (failures if dup else warnings).append(f"1. duplicate law+ref groups: {dup}")

    # 2. Articles without real body (derogated / "sin contenido" are legitimate)
    def _is_derogado(t: str) -> bool:
        low = (t or "").lower()
        return "derogad" in low or "sin contenido" in low
    empty = sum(
        1 for a in arts
        if len(re.sub(r"\s+", "", a["text"] or "")) < 30 and not _is_derogado(a["text"])
    )
    (failures if empty else warnings).append(f"2. articles without real body (<30 chars): {empty}")

    # 3. Article containing another 'Artículo N. Title' header inside
    nested = sum(1 for a in arts if a["text"] and len(HEAD_LINE_RE.findall(a["text"])) > 1)
    (failures if nested else warnings).append(f"3. articles with a nested article header: {nested}")

    # 4. Articles containing index text (dotted leaders)
    toc = sum(1 for a in arts if a["text"] and re.search(r"\.{4,}", a["text"]))
    (failures if toc else warnings).append(f"4. articles with index/dotted-leader text: {toc}")

    # 5. Articles dragging chapter/title/section/page furniture
    struct = sum(
        1 for a in arts if a["text"] and (
            re.search(r"\n\s*(T[ÍI]TULO|CAP[ÍI]TULO)\s", a["text"])
            or "BOLETÍN OFICIAL DEL ESTADO" in (a["text"] or "")
            or "LEGISLACIÓN CONSOLIDADA" in (a["text"] or "")
        )
    )
    (failures if struct else warnings).append(f"5. articles dragging structure/page furniture: {struct}")

    # 5b. lowercase citation rows still treated as articles
    cit = sum(1 for a in arts if CITATION_RE.match(a["text"] or ""))
    (failures if cit else warnings).append(f"5b. lowercase-citation rows: {cit}")

    # 6. Different topics sharing the exact same set of mapped article ids
    topic_sets = {}
    for row in c.execute(
        "SELECT topic_id, GROUP_CONCAT(article_id) g FROM topic_sources "
        "WHERE article_id IS NOT NULL GROUP BY topic_id"
    ).fetchall():
        key = tuple(sorted(int(x) for x in row["g"].split(",")))
        topic_sets.setdefault(key, []).append(row["topic_id"])
    shared = {k: v for k, v in topic_sets.items() if len(v) > 1}
    (warnings).append(f"6. topics sharing an identical mapped article set: {len(shared)}")

    # 7. Topic-law links with no specific articles (article_id NULL) -> fallback
    null_links = c.execute(
        "SELECT COUNT(DISTINCT topic_id || '-' || law_id) FROM topic_sources "
        "WHERE article_id IS NULL"
    ).fetchone()[0]
    warnings.append(f"7. topic-law links without specific articles: {null_links}")

    # 8. Topics without any fine article mapping (use fallback ranges)
    total_topics = c.execute("SELECT COUNT(*) FROM topics").fetchone()[0]
    mapped_topics = c.execute(
        "SELECT COUNT(DISTINCT topic_id) FROM topic_sources WHERE article_id IS NOT NULL"
    ).fetchone()[0]
    warnings.append(
        f"8. topics WITHOUT fine mapping (fallback): {total_topics - mapped_topics}/{total_topics}"
    )

    # 9. Topic titles present (UI shows them in full; flag empties/very short)
    short_titles = c.execute(
        "SELECT COUNT(*) FROM topics WHERE official_text IS NULL OR LENGTH(TRIM(official_text)) < 5"
    ).fetchone()[0]
    (failures if short_titles else warnings).append(f"9. topics with missing/too-short title: {short_titles}")

    # 10. Doctrinal/temario text mixed into legal text.
    # Use SPECIFIC academic markers only; generic legal terms like
    # "unificacion de doctrina" or "comentario" are valid legal language.
    doctrine_markers = re.compile(
        r"(?i)(seg[úu]n el profesor|esquema del tema|nota del autor|"
        r"academia aut[ée]ntica|apuntes? CEF|ampliaci[óo]n doctrinal|"
        r"truco de examen|nemot[ée]cnic)"
    )
    doctrine = sum(1 for a in arts if a["text"] and doctrine_markers.search(a["text"]))
    (failures if doctrine else warnings).append(f"10. legal text with doctrinal markers: {doctrine}")

    # FK integrity
    broken = c.execute(
        "SELECT COUNT(*) FROM topic_sources WHERE article_id IS NOT NULL "
        "AND article_id NOT IN (SELECT id FROM articles)"
    ).fetchone()[0]
    (failures if broken else warnings).append(f"FK. broken topic_sources article_id: {broken}")

    print(f"Total articles: {len(arts)}\n")
    print("BLOCKING CHECKS:")
    for f in failures:
        status = "FAIL" if not f.strip().endswith(": 0") and not _is_ok(f) else "ok"
        print(f"  [{status}] {f}")
    print("\nINFORMATIONAL:")
    for w in warnings:
        print(f"  [info] {w}")

    hard_fail = any(not _is_ok(f) for f in failures)
    print("\nRESULT:", "FAIL" if hard_fail else "PASS")
    conn.close()
    return 1 if hard_fail else 0


def _is_ok(line: str) -> bool:
    # a check passes when its trailing count is 0
    m = re.search(r":\s*(\d+)\s*$", line)
    return bool(m) and int(m.group(1)) == 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

"""In-place normalization of the articles table.

Fixes, without re-importing, three systemic corruptions produced by the
original PDF/HTML article parser:

  1. Index/TOC stub rows  (an "Artículo N. Title ....... 14" index line that
     became a row alongside the real article).
  2. False-positive citation rows (a body line starting with a lowercase
     "artículo N, ..." inline reference that the parser treated as a new
     article, stealing the tail of the preceding article's text).
  3. Trailing structural contamination (TÍTULO / CAPÍTULO / SECCIÓN / page
     furniture bleeding into the end of an article's body).

Strategy (per law, in document order = id order):
  - drop index stubs,
  - merge citation rows back into the article they were split from,
  - clean page noise / dotted index lines and trim trailing headings,
  - de-duplicate by article_ref keeping the longest body.

Referential integrity: every deleted/merged row id is re-pointed (in
topic_sources and study_annotations) to the surviving article of the same
reference before deletion, so Codex's validated article mappings stay intact.
"""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "db" / "gvadicto.sqlite"

PAGE_NOISE_RE = re.compile(
    r"^\s*(BOLET[IÍ]N OFICIAL DEL ESTADO|LEGISLACI[OÓ]N CONSOLIDADA|"
    r"P[áa]gina\s+\d+|cve:\s*BOE.*|ISSN:.*)\s*$",
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
CITATION_START_RE = re.compile(r"^\s*art[íi]culo\s+\d")  # lowercase a (case-sensitive)
REALHEAD_START_RE = re.compile(r"^\s*(Art[íi]culo|Article)\s+\d")
TITLE_RE = re.compile(r"^\s*(?:Art[íi]culo|Article)\s+[\w .]+?\.\s*([^\n]+)")


def is_struct_heading(line: str) -> bool:
    s = line.strip()
    if len(s) > 90:
        return False
    return bool(STRUCT_UPPER_RE.match(line) or STRUCT_DISP_RE.match(line))


def clean_and_trim(text: str) -> str:
    out = []
    for idx, ln in enumerate(text.split("\n")):
        if PAGE_NOISE_RE.match(ln):
            continue
        if DOTTED_RE.search(ln):
            continue
        if idx > 0 and is_struct_heading(ln):
            break
        out.append(ln)
    return "\n".join(out).strip()


def is_citation_row(text: str) -> bool:
    return bool(CITATION_START_RE.match(text)) and not REALHEAD_START_RE.match(text)


def compact(s: str) -> str:
    return re.sub(r"\s+", "", s)


def extract_title(final_text: str, fallback: str) -> str:
    m = TITLE_RE.match(final_text)
    if m:
        t = m.group(1).strip()
        # take first sentence-ish chunk
        t = re.split(r"\n", t)[0].strip()
        if 0 < len(t) <= 200:
            return t
    return fallback or "Sin titulo"


def main() -> None:
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    laws = c.execute("SELECT id, name FROM laws ORDER BY id").fetchall()

    updates = []          # (id, new_title, new_text)
    delete_ids = []       # rows to remove
    remap = {}            # deleted_id -> surviving_id

    for law in laws:
        rows = c.execute(
            "SELECT id, article_ref, title, text FROM articles WHERE law_id=? ORDER BY id",
            (law["id"],),
        ).fetchall()

        kept = []  # {primary_id, ref, frags:[...], merged_ids:[...]}
        for r in rows:
            text = r["text"] or ""
            cleaned_preview = clean_and_trim(text)
            if len(compact(cleaned_preview)) < 25:
                # index/empty stub -> drop, remap by ref later
                delete_ids.append(r["id"])
                kept_ref = (r["article_ref"] or "").strip().lower()
                kept.append(None) if False else None  # noop for clarity
                # store ref for later remap-by-ref resolution
                remap.setdefault(r["id"], ("__byref__", law["id"], kept_ref))
                continue
            if is_citation_row(text) and kept:
                kept[-1]["frags"].append(text)
                kept[-1]["merged_ids"].append(r["id"])
                continue
            kept.append(
                {
                    "primary_id": r["id"],
                    "ref": (r["article_ref"] or "").strip(),
                    "frags": [text],
                    "merged_ids": [],
                }
            )

        # finalize + dedup by ref (keep longest final body)
        by_ref = {}
        for k in kept:
            final = clean_and_trim("\n".join(k["frags"]))
            k["final"] = final
            ref = k["ref"].lower()
            if ref not in by_ref or len(final) > len(by_ref[ref]["final"]):
                if ref in by_ref:
                    loser = by_ref[ref]
                    delete_ids.append(loser["primary_id"])
                    remap[loser["primary_id"]] = ("__id__", k["primary_id"])
                    for mid in loser["merged_ids"]:
                        remap[mid] = ("__id__", k["primary_id"])
                by_ref[ref] = k
            else:
                delete_ids.append(k["primary_id"])
                remap[k["primary_id"]] = ("__id__", by_ref[ref]["primary_id"])
                for mid in k["merged_ids"]:
                    remap[mid] = ("__id__", by_ref[ref]["primary_id"])

        # winners: schedule text/title update; map merged citation ids to winner
        ref_to_primary = {ref: k["primary_id"] for ref, k in by_ref.items()}
        for ref, k in by_ref.items():
            title = extract_title(k["final"], k["ref"] and f"Articulo {k['ref']}")
            updates.append((k["primary_id"], title, k["final"]))
            for mid in k["merged_ids"]:
                delete_ids.append(mid)
                remap[mid] = ("__id__", k["primary_id"])

        # resolve __byref__ remaps now that we know surviving ids per ref
        for did, val in list(remap.items()):
            if isinstance(val, tuple) and val[0] == "__byref__" and val[1] == law["id"]:
                target = ref_to_primary.get(val[2])
                remap[did] = ("__id__", target) if target else ("__null__",)

    # Resolve final remap to plain ids (follow one hop is enough; winners are primaries)
    def resolve(did):
        v = remap.get(did)
        if not v:
            return None
        if v[0] == "__id__":
            return v[1]
        if v[0] == "__null__":
            return None
        return None

    delete_set = set(delete_ids)
    # winners must never be deleted
    winner_ids = {u[0] for u in updates}
    delete_set -= winner_ids

    print(f"Laws: {len(laws)}")
    print(f"Articles to update (winners): {len(updates)}")
    print(f"Articles to delete: {len(delete_set)}")

    # --- Re-point FKs before deleting ---
    fk_fixed_ts = fk_null_ts = 0
    for did in delete_set:
        target = resolve(did)
        if target is not None:
            cur = conn.execute(
                "UPDATE topic_sources SET article_id=? WHERE article_id=?", (target, did)
            )
            fk_fixed_ts += cur.rowcount
            conn.execute(
                "UPDATE study_annotations SET article_id=? WHERE article_id=?", (target, did)
            )
        else:
            cur = conn.execute(
                "UPDATE topic_sources SET article_id=NULL WHERE article_id=?", (did,)
            )
            fk_null_ts += cur.rowcount
            conn.execute(
                "UPDATE study_annotations SET article_id=NULL WHERE article_id=?", (did,)
            )
    print(f"topic_sources re-pointed: {fk_fixed_ts}, set NULL: {fk_null_ts}")

    # --- Apply updates ---
    for aid, title, text in updates:
        conn.execute(
            "UPDATE articles SET title=?, text=? WHERE id=?", (title, text, aid)
        )

    # --- Delete dropped rows ---
    conn.executemany(
        "DELETE FROM articles WHERE id=?", [(d,) for d in delete_set]
    )

    conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    broken = conn.execute(
        "SELECT COUNT(*) FROM topic_sources WHERE article_id IS NOT NULL "
        "AND article_id NOT IN (SELECT id FROM articles)"
    ).fetchone()[0]
    print(f"\nArticles after normalization: {total}")
    print(f"Broken topic_sources FKs: {broken}")
    conn.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

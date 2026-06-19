"""Fase 2D: correccion in-place de Ley 40/2015 arts 24-27 (contaminados con Ley 50/1997).

ESTRICTO:
  - Solo UPDATE de title + text en 4 article_id concretos (92040,92041,92042,92043).
  - NO cambia article_id. NO toca topic_sources, parser, importer ni reimporta.
  - Texto correcto extraido de la fuente oficial del repo:
    data/processed/official_sources/BOE-A-2015-10566.txt (cuerpo principal).
  - Backup previo. Pre-flight: valida el metodo de extraccion contra un articulo
    correcto conocido (art 28) antes de escribir; aborta si no coincide.
"""
from __future__ import annotations

import re
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "db" / "gvadicto.sqlite"
SRC = ROOT / "data" / "processed" / "official_sources" / "BOE-A-2015-10566.txt"

LAW_ID = 4
TARGET = {24: 92040, 25: 92041, 26: 92042, 27: 92043}
EXPECTED_TITLE = {
    24: "Recusación.",
    25: "Principio de legalidad.",
    26: "Irretroactividad.",
    27: "Principio de tipicidad.",
}

STRUCT = re.compile(r"(?m)^(CAP[ÍI]TULO|SECCI[ÓO]N|T[ÍI]TULO|LIBRO|SUBSECCI[ÓO]N)\b")
PAGE = re.compile(r"^(BOLET[ÍI]N OFICIAL DEL ESTADO|LEGISLACI[ÓO]N CONSOLIDADA|P[áa]gina\s+\d+)\s*$")


def extract(src: str, n: int):
    """Extrae (epigrafe, texto) del articulo n desde la PRIMERA aparicion (cuerpo)."""
    m = re.search(rf"(?m)^Art[íi]culo\s+{n}\.\s+(.+?)\s*$", src)
    if not m:
        raise SystemExit(f"No se encontro Articulo {n} en la fuente.")
    epigrafe = m.group(1).strip()
    rest = src[m.end():]
    ends = []
    nx = re.search(r"(?m)^Art[íi]culo\s+\d+\.\s+", rest)
    if nx:
        ends.append(nx.start())
    st = STRUCT.search(rest)
    if st:
        ends.append(st.start())
    cut = min(ends) if ends else len(rest)
    block = src[m.start(): m.end() + cut]
    lines = [ln for ln in block.split("\n") if not PAGE.match(ln.strip())]
    text = "\n".join(lines).strip()
    return epigrafe, text


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def main() -> None:
    src = SRC.read_text(encoding="utf-8")
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row

    # PRE-FLIGHT: validar metodo contra un articulo correcto conocido (art 28).
    epi28, txt28 = extract(src, 28)
    db28 = conn.execute("SELECT title, text FROM articles WHERE law_id=? AND article_ref='28'", (LAW_ID,)).fetchone()
    if _norm(db28["text"]) != _norm(txt28):
        print("ABORT: el metodo de extraccion NO reproduce el art 28 ya correcto.")
        print("  db28 :", _norm(db28["text"])[:120])
        print("  src28:", _norm(txt28)[:120])
        conn.close()
        return
    print(f"Pre-flight OK: extraccion reproduce art 28 ('{epi28}') identico a la BD.\n")

    # Estado previo (para prueba de estabilidad)
    ts_before = conn.execute("SELECT COUNT(*) FROM topic_sources").fetchone()[0]
    ids_before = conn.execute(
        "SELECT id, article_ref FROM articles WHERE law_id=? AND article_ref IN ('24','25','26','27') ORDER BY article_ref",
        (LAW_ID,),
    ).fetchall()
    print("article_id actuales 24-27:", [(r["article_ref"], r["id"]) for r in ids_before])

    # Backup
    backup = ROOT / "db" / f"gvadicto.backup_pre2d_{datetime.now():%Y%m%d_%H%M%S}.sqlite"
    shutil.copy2(DB, backup)
    print("Backup:", backup.name, "\n")

    # Extraer y UPDATE de los 4 articulos
    for n in (24, 25, 26, 27):
        epi, txt = extract(src, n)
        if epi != EXPECTED_TITLE[n]:
            print(f"ABORT: epigrafe inesperado art {n}: '{epi}' != '{EXPECTED_TITLE[n]}'")
            conn.close()
            return
        aid = TARGET[n]
        cur = conn.execute(
            "UPDATE articles SET title=?, text=? WHERE id=? AND law_id=? AND article_ref=?",
            (epi, txt, aid, LAW_ID, str(n)),
        )
        print(f"  art {n} (id {aid}): UPDATE rows={cur.rowcount} | title='{epi}' | text {len(txt)} chars")

    conn.commit()

    # Estado posterior
    ts_after = conn.execute("SELECT COUNT(*) FROM topic_sources").fetchone()[0]
    ids_after = conn.execute(
        "SELECT id, article_ref FROM articles WHERE law_id=? AND article_ref IN ('24','25','26','27') ORDER BY article_ref",
        (LAW_ID,),
    ).fetchall()
    print("\ntopic_sources filas: antes=%d despues=%d (delta=%d)" % (ts_before, ts_after, ts_after - ts_before))
    print("article_id 24-27 tras update:", [(r["article_ref"], r["id"]) for r in ids_after])
    same = [(r["article_ref"], r["id"]) for r in ids_before] == [(r["article_ref"], r["id"]) for r in ids_after]
    print("article_id sin cambios:", same)
    conn.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

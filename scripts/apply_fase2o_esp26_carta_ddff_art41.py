"""
Fase 2O: INSERT Carta DDFF art. 41 + mapeo esp-26

La Carta DDFF (law_id=82) solo tiene art. 51. Este script inserta el art. 41
(derecho a buena administracion) extraido del HTML EUR-Lex y mapea el tema
esp-26 (gobernanza / buena administracion) a ese articulo.

Uso:
    python scripts/apply_fase2o_esp26_carta_ddff_art41.py          # dry-run
    python scripts/apply_fase2o_esp26_carta_ddff_art41.py --apply  # aplica
"""

import re
import sys
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

DRY_RUN = "--apply" not in sys.argv
DB_PATH = Path("db/gvadicto.sqlite")
CARTA_HTML = Path(
    "data/sources/leyes_originales/EURLEX/"
    "EURLEX-12016P-TXT_Carta_Derechos_Fundamentales_UE.html"
)
CARTA_LAW_ID = 82
ESP26_TOPIC_ID = 41  # topic id=41, T26 especial


def extract_art41(html_path: Path) -> str:
    with open(html_path, encoding="utf-8") as f:
        html = f.read()
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;|&#160;", " ", text)
    text = re.sub(r"&[a-zA-Z]+;|&#\d+;", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    m = re.search(r"Art.culo\s+41\b", text)
    assert m, "Art. 41 no encontrado en Carta DDFF HTML"
    start = m.start()
    next_m = re.search(r"Art.culo\s+42\b", text[start + 5:])
    end = (start + 5 + next_m.start()) if next_m else (start + 2000)
    return text[start:end].strip()


def backup_db():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = DB_PATH.parent / f"gvadicto.backup_pre2o_esp26_{ts}.sqlite"
    shutil.copy2(DB_PATH, backup)
    print(f"[backup] {backup}")


def main():
    print(
        f"=== Fase 2O: Carta DDFF art. 41 + esp-26 "
        f"({'DRY-RUN' if DRY_RUN else 'APPLY'}) ===\n"
    )

    art41_text = extract_art41(CARTA_HTML)
    print(f"[html] Art 41 extraido ({len(art41_text)} chars):")
    print(art41_text[:300])
    print()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Estado actual
    c.execute("SELECT id, article_ref FROM articles WHERE law_id=? AND article_ref='41'", (CARTA_LAW_ID,))
    existing_art = c.fetchone()
    art41_id = existing_art[0] if existing_art else None
    print(f"[check] Art 41 en BD: {'id=' + str(art41_id) if art41_id else 'NO existe'}")

    c.execute(
        "SELECT id, article_id FROM topic_sources WHERE topic_id=? AND law_id=?",
        (ESP26_TOPIC_ID, CARTA_LAW_ID),
    )
    existing_ts = c.fetchall()
    print(f"[check] topic_sources esp-26->Carta DDFF: {existing_ts}")

    c.execute(
        "SELECT COUNT(*) FROM topic_sources WHERE topic_id=? AND article_id IS NOT NULL",
        (ESP26_TOPIC_ID,),
    )
    fine_before = c.fetchone()[0]
    print(f"[check] esp-26 fine-mapped antes: {fine_before}")
    print()

    print("=== Operaciones previstas ===")
    if art41_id is None:
        print("  INSERT articles: Carta DDFF art. 41")
    else:
        print(f"  UPDATE articles id={art41_id}: actualizar texto art. 41")

    if existing_ts:
        for ts_id, old_aid in existing_ts:
            print(f"  UPDATE topic_sources id={ts_id}: article_id {old_aid} -> <art41_id>")
    else:
        print(f"  INSERT topic_sources: esp-26 -> Carta DDFF art. 41")

    if DRY_RUN:
        print("\n[DRY-RUN] Sin cambios. Usa --apply para ejecutar.")
        conn.close()
        return

    # === APLICAR ===
    backup_db()
    now = datetime.now().isoformat()

    # INSERT/UPDATE art 41
    import hashlib
    art41_hash = hashlib.sha256(art41_text.encode("utf-8")).hexdigest()

    if art41_id is None:
        c.execute(
            """INSERT INTO articles
               (law_id, article_ref, title, text, source, original_hash, validation_status, imported_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                CARTA_LAW_ID,
                "41",
                "Articulo 41 Derecho a una buena administracion",
                art41_text,
                "EURLEX-12016P-TXT_Carta_Derechos_Fundamentales_UE.html",
                art41_hash,
                "pendiente_de_validacion",
                now,
            ),
        )
        art41_id = c.lastrowid
        print(f"[INSERT] articles: art 41 id={art41_id}")
    else:
        c.execute(
            "UPDATE articles SET text=?, title=?, validation_status=? WHERE id=?",
            (
                art41_text,
                "Articulo 41 Derecho a una buena administracion",
                "pendiente_de_validacion",
                art41_id,
            ),
        )
        print(f"[UPDATE] articles id={art41_id}: texto renovado")

    # INSERT/UPDATE topic_sources
    if existing_ts:
        for ts_id, old_aid in existing_ts:
            c.execute(
                """UPDATE topic_sources
                   SET article_id=?, mapping_basis=?, notes=?, updated_at=?
                   WHERE id=?""",
                (
                    art41_id,
                    "fase2o_carta_ddff_html_source",
                    "Art 41 desde HTML EUR-Lex Carta DDFF - derecho a buena administracion",
                    now,
                    ts_id,
                ),
            )
            print(f"[UPDATE] topic_sources id={ts_id}: article_id {old_aid} -> {art41_id}")
    else:
        c.execute(
            """INSERT INTO topic_sources
               (topic_id, law_id, article_id, normative_reference, coverage_status,
                mapping_basis, priority, validation_status, notes, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                ESP26_TOPIC_ID,
                CARTA_LAW_ID,
                art41_id,
                "Carta DDFF art. 41",
                "covered",
                "fase2o_carta_ddff_html_source",
                1,
                "pendiente_de_validacion",
                "Art 41 desde HTML EUR-Lex Carta DDFF - derecho a buena administracion",
                now,
                now,
            ),
        )
        print(f"[INSERT] topic_sources esp-26 -> Carta DDFF art 41 (id={art41_id})")

    conn.commit()
    conn.close()
    print("\n[OK] Fase 2O aplicada. Ejecuta: python scripts/validate_article_quality.py")


if __name__ == "__main__":
    main()

"""
Fase 2N: Fix TUE arts 1-5 contaminados + mapeo gen-13

Los artículos TUE 1-5 en BD contienen texto de Protocolos anejos (CECA, elecciones PE,
mayoría cualificada, petróleo Antillas, Schengen). Este script los corrige extrayendo el
texto correcto del HTML fuente EUR-Lex y luego mapea el tema gen-13 a los arts 1-5 y 6.

Uso:
    python scripts/apply_fase2n_gen13_tue_fix.py          # dry-run
    python scripts/apply_fase2n_gen13_tue_fix.py --apply  # aplica cambios
"""

import re
import sys
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

DRY_RUN = "--apply" not in sys.argv
DB_PATH = Path("db/gvadicto.sqlite")
TUE_HTML = Path("data/sources/leyes_originales/EURLEX/EURLEX-02016M-TXT-20250315_TUE_consolidado_2025-03-15.html")
TUE_LAW_ID = 34
GEN13_TOPIC_ID = 13

# IDs de artículos contaminados en BD
CONTAMINATED_IDS = {
    "1": 102517,
    "2": 102508,
    "3": 102509,
    "4": 102503,
    "5": 102461,
}
# Art 6 ya está limpio
ART6_ID = 102196


def extract_tue_arts(html_path: Path) -> dict[str, str]:
    """Extrae arts 1-6 del HTML TUE antes de los Protocolos anejos."""
    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;|&#160;", " ", text)
    text = re.sub(r"&[a-zA-Z]+;|&#\d+;", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    prot_idx = text.find("PROTOCOLOS ANEJOS")
    assert prot_idx > 0, "No se encontró 'PROTOCOLOS ANEJOS' en el HTML"
    tue_body = text[:prot_idx]

    arts = {}
    for num in range(1, 7):
        m = re.search(rf"Artículo\s+{num}(\s+\(antiguo)?\b", tue_body)
        assert m, f"No se encontró Artículo {num} en cuerpo TUE"
        start = m.start()
        # Delimitador: siguiente artículo numerado
        next_m = re.search(rf"Artículo\s+{num + 1}\b", tue_body[start + 5:])
        end = (start + 5 + next_m.start()) if next_m else (start + 3000)
        art_text = tue_body[start:end].strip()
        arts[str(num)] = art_text

    return arts


def backup_db():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = DB_PATH.parent / f"gvadicto.backup_pre2n_gen13_{ts}.sqlite"
    shutil.copy2(DB_PATH, backup)
    print(f"[backup] {backup}")
    return backup


def main():
    print(f"=== Fase 2N: fix TUE arts 1-5 + gen-13 ({'DRY-RUN' if DRY_RUN else 'APPLY'}) ===\n")

    # 1. Extraer texto correcto del HTML
    arts = extract_tue_arts(TUE_HTML)
    for ref, text in arts.items():
        print(f"[html] Art {ref}: {text[:120]}...")
        print()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 2. Mostrar texto actual (contaminado) vs nuevo
    print("=== UPDATES previstos (arts 1-5) ===")
    for ref, new_text in arts.items():
        if ref == "6":
            continue
        art_id = CONTAMINATED_IDS[ref]
        c.execute("SELECT article_ref, text FROM articles WHERE id=?", (art_id,))
        row = c.fetchone()
        print(f"Art {ref} (id={art_id})")
        print(f"  ANTES: {row[1][:100]}...")
        print(f"  DESPUES: {new_text[:100]}...")
        print()

    # 3. Verificar que ningún ID contaminado está en topic_sources de otro tema
    print("=== Verificación de uso en topic_sources ===")
    safe = True
    for ref, art_id in CONTAMINATED_IDS.items():
        c.execute(
            "SELECT topic_id, mapping_basis FROM topic_sources WHERE article_id=?",
            (art_id,),
        )
        rows = c.fetchall()
        if rows:
            print(f"  ADVERTENCIA art {ref} (id={art_id}) referenciado en: {rows}")
            safe = False
        else:
            print(f"  OK art {ref} (id={art_id}): sin referencias en topic_sources")

    if not safe:
        print("\nABORTADO: hay referencias a arts contaminados en topic_sources.")
        conn.close()
        sys.exit(1)

    # 4. topic_sources previsto para gen-13
    # Arts a mapear: 1,2,3,4,5 (corregidos) + 6 (ya limpio)
    target_arts = {
        "1": CONTAMINATED_IDS["1"],
        "2": CONTAMINATED_IDS["2"],
        "3": CONTAMINATED_IDS["3"],
        "4": CONTAMINATED_IDS["4"],
        "5": CONTAMINATED_IDS["5"],
        "6": ART6_ID,
    }
    print("\n=== topic_sources a insertar para gen-13 ===")
    for ref, aid in target_arts.items():
        print(f"  topic_id={GEN13_TOPIC_ID} law_id={TUE_LAW_ID} article_id={aid} (TUE art {ref})")

    # Verificar que ya no hay fine-mapped entries para gen-13 (no duplicar)
    c.execute(
        "SELECT COUNT(*) FROM topic_sources WHERE topic_id=? AND article_id IS NOT NULL",
        (GEN13_TOPIC_ID,),
    )
    existing_fine = c.fetchone()[0]
    print(f"\n  gen-13 fine-mapped existentes: {existing_fine} (esperado 0)")

    if DRY_RUN:
        print("\n[DRY-RUN] Sin cambios. Usa --apply para ejecutar.")
        conn.close()
        return

    # === APLICAR ===
    backup_db()

    # UPDATE arts contaminados
    for ref, new_text in arts.items():
        if ref == "6":
            continue
        art_id = CONTAMINATED_IDS[ref]
        c.execute(
            "UPDATE articles SET text=?, title=? WHERE id=?",
            (new_text, f"Artículo {ref}", art_id),
        )
        print(f"[UPDATE] art id={art_id} ref={ref} ({c.rowcount} filas)")

    # INSERT topic_sources gen-13
    now = datetime.now().isoformat()
    for ref, aid in target_arts.items():
        c.execute(
            """INSERT OR IGNORE INTO topic_sources
               (topic_id, law_id, article_id, normative_reference, coverage_status,
                mapping_basis, priority, validation_status, notes, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                GEN13_TOPIC_ID,
                TUE_LAW_ID,
                aid,
                f"TUE art. {ref}",
                "covered",
                "fase2n_tue_fix_html_source",
                1,
                "pendiente_de_validacion",
                f"Art corregido desde HTML EUR-Lex TUE consolidado 2025-03-15" if ref != "6" else "Art 6 ya estaba limpio",
                now,
                now,
            ),
        )
        print(f"[INSERT] topic_sources gen-13 -> TUE art {ref} (article_id={aid})")

    conn.commit()
    conn.close()
    print("\n[OK] Fase 2N aplicada. Ejecuta: python scripts/validate_article_quality.py")


if __name__ == "__main__":
    main()

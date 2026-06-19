"""
Fase 2Q: Importar CC art. 2 + mapeo esp-5 (eficacia temporal de las normas)

Descarga el PDF consolidado del Codigo Civil desde BOE, extrae el art. 2
(vacatio legis, derogacion, irretroactividad), crea la ley CC en BD y mapea
esp-5 a ese articulo + CE art. 9 (irretroactividad constitucional).

Fuente: https://www.boe.es/buscar/pdf/1889/BOE-A-1889-4763-consolidado.pdf
BOE-A-1889-4763 Real Decreto de 24 de julio de 1889 (Codigo Civil)

Uso:
    python scripts/apply_fase2q_esp5_cc_art2.py          # dry-run
    python scripts/apply_fase2q_esp5_cc_art2.py --apply  # aplica
"""

import re
import sys
import sqlite3
import shutil
import hashlib
import io
import urllib.request
from datetime import datetime
from pathlib import Path

DRY_RUN = "--apply" not in sys.argv
DB_PATH = Path("db/gvadicto.sqlite")
PDF_URL = "https://www.boe.es/buscar/pdf/1889/BOE-A-1889-4763-consolidado.pdf"
CC_BOE_ID = "BOE-A-1889-4763"
ESP5_TOPIC_ID = 20   # topic id=20, T5 especial
CE_LAW_ID = 2
CE_ART9_ID = 91426   # CE art. 9 ya verificado

PAGE_NOISE = re.compile(
    r"\s*Página\s+\d+\s*\n?BOLETÍN OFICIAL DEL ESTADO\s*\nLEGISLACIÓN CONSOLIDADA\s*\n?"
)


def download_pdf(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "GVAdicto/0.1"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


def extract_art2_from_pdf(pdf_bytes: bytes) -> str:
    import pdfplumber

    full_text = ""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages[:25]:
            full_text += (page.extract_text() or "") + "\n"
            if "Artículo 2." in full_text or "Artículo 3." in full_text:
                if "Artículo 3." in full_text:
                    break

    idx = full_text.find("Artículo 2.")
    assert idx >= 0, "Artículo 2. no encontrado en las primeras 25 páginas del CC"
    # Delimitar: hasta Artículo 3 o CAPÍTULO
    idx3 = full_text.find("Artículo 3.", idx + 5)
    idx_cap = full_text.find("CAPÍTULO", idx + 5)
    end = min(x for x in [idx3, idx_cap, idx + 2000] if x > idx)
    raw = full_text[idx:end].strip()

    # Limpiar ruido de página BOE
    raw = PAGE_NOISE.sub(" ", raw)
    raw = re.sub(r"\s{2,}", " ", raw).strip()
    return raw


def backup_db():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = DB_PATH.parent / f"gvadicto.backup_pre2q_esp5_{ts}.sqlite"
    shutil.copy2(DB_PATH, backup)
    print(f"[backup] {backup}")


def main():
    print(
        f"=== Fase 2Q: CC art. 2 + esp-5 "
        f"({'DRY-RUN' if DRY_RUN else 'APPLY'}) ===\n"
    )

    print("[download] Descargando CC PDF desde BOE...")
    pdf_bytes = download_pdf(PDF_URL)
    print(f"[download] OK: {len(pdf_bytes):,} bytes")

    art2_text = extract_art2_from_pdf(pdf_bytes)
    print(f"\n[extract] CC art. 2 ({len(art2_text)} chars):")
    print(art2_text)
    print()

    art2_hash = hashlib.sha256(art2_text.encode("utf-8")).hexdigest()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # ¿Ya existe la ley CC en BD?
    c.execute("SELECT id, name FROM laws WHERE name LIKE '%Codigo Civil%' OR name LIKE '%C_digo Civil%'")
    existing_law = c.fetchone()
    cc_law_id = existing_law[0] if existing_law else None
    print(f"[check] Ley CC en BD: {'id=' + str(cc_law_id) + ' ' + existing_law[1] if existing_law else 'NO existe'}")

    # ¿Ya existe art. 2 en BD?
    cc_art2_id = None
    if cc_law_id:
        c.execute("SELECT id FROM articles WHERE law_id=? AND article_ref='2'", (cc_law_id,))
        r = c.fetchone()
        cc_art2_id = r[0] if r else None
        print(f"[check] CC art. 2 en BD: {'id=' + str(cc_art2_id) if cc_art2_id else 'NO existe'}")

    # Estado actual esp-5
    c.execute(
        "SELECT id, law_id, article_id, normative_reference, mapping_basis "
        "FROM topic_sources WHERE topic_id=?",
        (ESP5_TOPIC_ID,),
    )
    current_ts = c.fetchall()
    print(f"\n[check] topic_sources esp-5 actuales ({len(current_ts)}):")
    for row in current_ts:
        print(f"  ts_id={row[0]} law_id={row[1]} article_id={row[2]} ref={row[3]}")

    c.execute(
        "SELECT COUNT(*) FROM topic_sources WHERE topic_id=? AND article_id IS NOT NULL",
        (ESP5_TOPIC_ID,),
    )
    fine_before = c.fetchone()[0]
    print(f"  fine-mapped antes: {fine_before}")

    # CE art. 9 verificación
    c.execute("SELECT id, article_ref FROM articles WHERE id=?", (CE_ART9_ID,))
    ce9 = c.fetchone()
    print(f"\n[check] CE art. 9: {'OK id=' + str(ce9[0]) if ce9 else 'NO ENCONTRADO'}")

    print("\n=== Operaciones previstas ===")
    if cc_law_id is None:
        print(f"  INSERT laws: Codigo Civil (BOE-A-1889-4763)")
    if cc_art2_id is None:
        print(f"  INSERT articles: CC art. 2")
    else:
        print(f"  (CC art. 2 ya existe, id={cc_art2_id})")

    # ¿Ya hay topic_source para CC en esp-5?
    cc_ts = next((r for r in current_ts if r[1] == cc_law_id), None) if cc_law_id else None
    ce_ts = next((r for r in current_ts if r[1] == CE_LAW_ID), None)

    if cc_ts is None:
        print(f"  INSERT topic_sources: esp-5 -> CC art. 2 (law_id=<nuevo>)")
    else:
        print(f"  UPDATE topic_sources ts_id={cc_ts[0]}: -> CC art. 2")

    if ce_ts is None:
        print(f"  INSERT topic_sources: esp-5 -> CE art. 9 (law_id={CE_LAW_ID})")
    else:
        print(f"  UPDATE topic_sources ts_id={ce_ts[0]}: -> CE art. 9 (id={CE_ART9_ID})")

    # LPAC (law_id=3) no aplica a eficacia temporal de normas
    lpac_law_id = 3
    lpac_ts = next((r for r in current_ts if r[1] == lpac_law_id), None)
    if lpac_ts:
        print(f"  DELETE topic_sources ts_id={lpac_ts[0]}: LPAC (no aplica a eficacia de normas)")

    if DRY_RUN:
        print("\n[DRY-RUN] Sin cambios. Usa --apply para ejecutar.")
        conn.close()
        return

    # === APLICAR ===
    backup_db()
    now = datetime.now().isoformat()

    # Crear ley CC si no existe
    if cc_law_id is None:
        c.execute(
            "INSERT INTO laws (name, source_path, source_hash, imported_at, validation_status) VALUES (?,?,?,?,?)",
            (
                "Real Decreto 1889/1889 Codigo Civil (BOE-A-1889-4763)",
                PDF_URL,
                hashlib.sha256(pdf_bytes[:4096]).hexdigest(),
                now,
                "pendiente_de_validacion",
            ),
        )
        cc_law_id = c.lastrowid
        print(f"[INSERT] laws: Codigo Civil id={cc_law_id}")

    # Insertar art. 2 CC
    if cc_art2_id is None:
        c.execute(
            """INSERT INTO articles
               (law_id, article_ref, title, text, source, original_hash, validation_status, imported_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                cc_law_id,
                "2",
                "Articulo 2 Codigo Civil - eficacia temporal y derogacion de las leyes",
                art2_text,
                PDF_URL,
                art2_hash,
                "pendiente_de_validacion",
                now,
            ),
        )
        cc_art2_id = c.lastrowid
        print(f"[INSERT] articles: CC art. 2 id={cc_art2_id}")
    else:
        c.execute(
            "UPDATE articles SET text=?, original_hash=?, updated_at=? WHERE id=?",
            (art2_text, art2_hash, now, cc_art2_id),
        )
        print(f"[UPDATE] articles: CC art. 2 id={cc_art2_id}")

    # topic_sources: eliminar LPAC (no aplica) y actualizar/insertar CC + CE
    if lpac_ts:
        c.execute("DELETE FROM topic_sources WHERE id=?", (lpac_ts[0],))
        print(f"[DELETE] topic_sources ts_id={lpac_ts[0]} LPAC (reemplazado)")

    # CC art. 2
    cc_ts_fresh = next((r for r in current_ts if r[1] == cc_law_id), None)
    if cc_ts_fresh is None:
        c.execute(
            """INSERT INTO topic_sources
               (topic_id, law_id, article_id, normative_reference, coverage_status,
                mapping_basis, priority, validation_status, notes, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                ESP5_TOPIC_ID, cc_law_id, cc_art2_id,
                "CC art. 2",
                "covered",
                "fase2q_cc_art2_boe_pdf",
                1,
                "pendiente_de_validacion",
                "Vacatio legis 20 dias, derogacion expresa/tacita, irretroactividad",
                now, now,
            ),
        )
        print(f"[INSERT] topic_sources esp-5 -> CC art. 2 (article_id={cc_art2_id})")
    else:
        c.execute(
            """UPDATE topic_sources
               SET article_id=?, normative_reference=?, mapping_basis=?, notes=?, updated_at=?
               WHERE id=?""",
            (cc_art2_id, "CC art. 2", "fase2q_cc_art2_boe_pdf",
             "Vacatio legis 20 dias, derogacion expresa/tacita, irretroactividad",
             now, cc_ts_fresh[0]),
        )
        print(f"[UPDATE] topic_sources ts_id={cc_ts_fresh[0]} -> CC art. 2")

    # CE art. 9 - verificar si ya hay topic_source para CE en esp-5
    c.execute(
        "SELECT id FROM topic_sources WHERE topic_id=? AND law_id=?",
        (ESP5_TOPIC_ID, CE_LAW_ID),
    )
    ce_ts_row = c.fetchone()
    if ce_ts_row is None:
        c.execute(
            """INSERT INTO topic_sources
               (topic_id, law_id, article_id, normative_reference, coverage_status,
                mapping_basis, priority, validation_status, notes, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                ESP5_TOPIC_ID, CE_LAW_ID, CE_ART9_ID,
                "CE art. 9",
                "covered",
                "fase2q_ce_art9_irretroactividad",
                2,
                "pendiente_de_validacion",
                "Art. 9.3 CE: irretroactividad constitucional disposiciones sancionadoras/restrictivas",
                now, now,
            ),
        )
        print(f"[INSERT] topic_sources esp-5 -> CE art. 9 (id={CE_ART9_ID})")
    else:
        c.execute(
            """UPDATE topic_sources
               SET article_id=?, mapping_basis=?, notes=?, updated_at=?
               WHERE id=?""",
            (CE_ART9_ID, "fase2q_ce_art9_irretroactividad",
             "Art. 9.3 CE: irretroactividad constitucional",
             now, ce_ts_row[0]),
        )
        print(f"[UPDATE] topic_sources ts_id={ce_ts_row[0]} -> CE art. 9")

    conn.commit()
    conn.close()
    print("\n[OK] Fase 2Q aplicada. Ejecuta: python scripts/validate_article_quality.py")


if __name__ == "__main__":
    main()

"""Extrae texto de Competencias-51..60.pdf (CEF Drive) y lo guarda en
topic_study_resources como campo `content_text`.

Uso:
    python scripts/import_cef_competencias_text.py [--reset]
"""
from __future__ import annotations

import sys
import sqlite3
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "db" / "gvadicto.sqlite"
CEF_DIR = Path(r"F:\Mi unidad\Opo\EraCEF\TemarioAulaVirtualCompleto\Especial\6- Competencias")

ADD_COLUMN_SQL = """
ALTER TABLE topic_study_resources ADD COLUMN content_text TEXT;
"""

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS topic_study_resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    source_document_id INTEGER REFERENCES source_documents(id),
    resource_kind TEXT NOT NULL DEFAULT 'temario_academia_cef',
    validation_status TEXT NOT NULL DEFAULT 'pendiente_de_validacion',
    content_text TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def extract_text_pdfplumber(path: Path) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(str(path)) as pdf:
            parts = []
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    parts.append(t)
            return "\n\n".join(parts)
    except Exception as e:
        print(f"  [pdfplumber] Error: {e}")
        return ""


def extract_text_pypdf(path: Path) -> str:
    try:
        import pypdf
        reader = pypdf.PdfReader(str(path))
        return "\n".join(p.extract_text() or "" for p in reader.pages)
    except Exception as e:
        print(f"  [pypdf] Error: {e}")
        return ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # Asegurar tabla existe
    conn.executescript(CREATE_TABLE_SQL)

    # Añadir columna content_text si no existe
    cols = {r[1] for r in conn.execute("PRAGMA table_info(topic_study_resources)")}
    if "content_text" not in cols:
        try:
            conn.execute(ADD_COLUMN_SQL)
            conn.commit()
            print("Columna content_text añadida.")
        except Exception as e:
            print(f"[WARN] {e}")

    if args.reset:
        conn.execute(
            "UPDATE topic_study_resources SET content_text=NULL "
            "WHERE resource_kind='temario_academia_cef'"
        )
        conn.commit()
        print("content_text vaciado.")

    # Obtener los 10 topic_study_resources de tipo CEF competencias
    rows = conn.execute(
        """
        SELECT tsr.id, tsr.topic_id, tsr.content_text, t.topic_number, t.official_text,
               sd.path, sd.title
        FROM topic_study_resources tsr
        JOIN topics t ON t.id = tsr.topic_id
        LEFT JOIN source_documents sd ON sd.id = tsr.source_document_id
        WHERE tsr.resource_kind = 'temario_academia_cef'
        ORDER BY t.topic_number
        """
    ).fetchall()

    if not rows:
        print("No hay filas de tipo 'temario_academia_cef'. Ejecuta link_cef_competencias_resources.py primero.")
        conn.close()
        return

    print(f"Recursos CEF a procesar: {len(rows)}")

    for row in rows:
        row = dict(row)
        tid = row["id"]
        tnum = row["topic_number"]
        # sd.path puede ser ruta completa o solo nombre de fichero
        _sd_path = row.get("path") or row.get("title") or ""
        fname = Path(_sd_path).name if _sd_path else f"Competencias-{tnum}.pdf"

        if row.get("content_text") and not args.reset:
            print(f"  Tema {tnum}: ya tiene texto ({len(row['content_text'])} chars). Skip.")
            continue

        # Buscar el PDF
        pdf_path = CEF_DIR / fname
        if not pdf_path.exists():
            # Intenta con número exacto del tema
            candidates = list(CEF_DIR.glob(f"*{tnum}*.pdf"))
            if candidates:
                pdf_path = candidates[0]
            else:
                print(f"  Tema {tnum}: PDF no encontrado ({fname}). Skip.")
                continue

        print(f"  Procesando: {pdf_path.name}", end="", flush=True)
        text = extract_text_pdfplumber(pdf_path)
        if not text.strip():
            text = extract_text_pypdf(pdf_path)
        if not text.strip():
            print(" [EMPTY]")
            continue

        text = text.strip()
        conn.execute(
            "UPDATE topic_study_resources SET content_text=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (text, tid)
        )
        conn.commit()
        print(f" OK ({len(text)} chars)")

    # Resumen
    done = conn.execute(
        "SELECT COUNT(*) FROM topic_study_resources WHERE resource_kind='temario_academia_cef' AND content_text IS NOT NULL"
    ).fetchone()[0]
    total = conn.execute(
        "SELECT COUNT(*) FROM topic_study_resources WHERE resource_kind='temario_academia_cef'"
    ).fetchone()[0]
    print(f"\nTexto cargado: {done}/{total} recursos CEF.")
    conn.close()


if __name__ == "__main__":
    main()

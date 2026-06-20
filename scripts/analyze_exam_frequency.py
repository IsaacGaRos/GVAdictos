"""Analiza tests/simulacros locales y extrae frecuencia de artículos preguntados.

Busca patrones "artículo X de la Ley Y" en PDFs de tests y los mapea
a artículos de la BD. Guarda resultados en article_exam_frequency.

Uso:
    python scripts/analyze_exam_frequency.py [--reset]
"""
from __future__ import annotations

import re
import sys
import json
import argparse
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "db" / "gvadicto.sqlite"

# Directorios a escanear
SCAN_DIRS = [
    ROOT / "Archivo Oposición TAG-GVA" / "Auténtica",
    ROOT / "Archivo Oposición TAG-GVA" / "EraCEF" / "Simulacro Sep 24",
    ROOT / "Archivo Oposición TAG-GVA" / "EraCEF" / "Temario" / "Test-A1-GVA",
    ROOT / "data" / "examenes_oficiales",  # exámenes oficiales descargados
]

# PDFs para ignorar (temario, no test)
IGNORE_PATTERNS = ["justificante", "factura", "calendario", "PAG", "FOR1",
                   "Decreto 42-2019 Permisos", "Decreto 49-2021 Teletrabajo",
                   "Decreto 3-2017 Carrera", "Ley 31-1995", "Ley 53-84",
                   "RD 33-1986", "flashcard", "Esquema", "Excedencia",
                   "Situaciones", "ModifLey", "Guion", "Comparativa",
                   "Caso práctico", "calend", "Pdf_1535",
                   "instrucciones_test"]  # solo instrucciones, sin preguntas

# Patrones para detectar referencias a artículos en el texto
ART_PATTERNS = [
    # "artículo 12 de la Ley 9/2003"
    re.compile(r'art[íi]culo\s+(\d+[\s\d\.º]*)\s+de(?:\s+la|\s+el|\s+los)?\s+(?:Ley|Real\s+Decreto|Orden|Reglamento|Decreto|LO|Ley\s+Org[aá]nica)\s*([\d/\-]+)', re.IGNORECASE),
    # "art. 25 del Estatuto"
    re.compile(r'\bart\.?\s+(\d+[\.\d]*)\s+del?\s+(Estatuto|Reglamento)', re.IGNORECASE),
    # "artículo 28 de la Ley 5/1983"
    re.compile(r'art[íi]culo\s+(\d+)\s+de', re.IGNORECASE),
]

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS article_exam_frequency (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER REFERENCES articles(id) ON DELETE SET NULL,
    article_ref TEXT NOT NULL,
    law_id INTEGER REFERENCES laws(id) ON DELETE SET NULL,
    law_name TEXT,
    total_count INTEGER NOT NULL DEFAULT 0,
    exam_sources TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_exam_freq_article
    ON article_exam_frequency(article_id);

CREATE INDEX IF NOT EXISTS idx_exam_freq_law
    ON article_exam_frequency(law_id, article_ref);
"""


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.executescript(CREATE_TABLE_SQL)


def extract_text_pypdf(path: Path) -> str:
    try:
        import pypdf
        reader = pypdf.PdfReader(str(path))
        return "\n".join(p.extract_text() or "" for p in reader.pages)
    except Exception as e:
        print(f"  [WARN] pypdf error on {path.name}: {e}")
        return ""


def collect_pdfs() -> list[Path]:
    pdfs = []
    for d in SCAN_DIRS:
        if not d.exists():
            continue
        for p in d.rglob("*.pdf"):
            name = p.name
            if any(ig.lower() in name.lower() for ig in IGNORE_PATTERNS):
                continue
            pdfs.append(p)
    return sorted(pdfs)


def extract_article_refs(text: str) -> list[tuple[str, str]]:
    """Extrae (art_ref, context) del texto."""
    results = []
    for pat in ART_PATTERNS:
        for m in pat.finditer(text):
            art_ref = m.group(1).strip().rstrip(".")
            # Obtener contexto alrededor del match
            start = max(0, m.start() - 50)
            end = min(len(text), m.end() + 100)
            ctx = text[start:end].replace("\n", " ").strip()
            results.append((art_ref, ctx))
    return results


def find_law_in_db(conn: sqlite3.Connection, context: str) -> tuple[int | None, str | None]:
    """Intenta identificar la ley del contexto buscando fragmentos del nombre en la BD."""
    # Patrones de ley en el contexto: "Ley 9/2003", "Ley 5/1983", etc.
    law_pat = re.compile(r'(?:Ley|Real\s+Decreto(?:\s+Legislativo)?|Orden|Decreto(?:\s+Ley)?|LO|RD(?:L)?)\s*(\d+[\-/]\d+)', re.IGNORECASE)
    for m in law_pat.finditer(context):
        ref = m.group(1).replace("/", "-")
        rows = conn.execute(
            "SELECT id, name FROM laws WHERE REPLACE(name, '/', '-') LIKE ? OR name LIKE ? LIMIT 1",
            (f"%{ref}%", f"%{ref}%")
        ).fetchall()
        if rows:
            r = rows[0]
            return (int(r[0]) if not isinstance(r, dict) else r["id"],
                    r[1] if not isinstance(r, dict) else r["name"])
    return None, None


def find_article_in_db(conn: sqlite3.Connection, law_id: int, art_ref: str) -> int | None:
    rows = conn.execute(
        "SELECT id FROM articles WHERE law_id=? AND TRIM(article_ref)=TRIM(?)",
        (law_id, art_ref)
    ).fetchall()
    if rows:
        return int(rows[0][0]) if not isinstance(rows[0], dict) else rows[0]["id"]
    # Try prefix match (e.g. "12" matches "12.1", "12.2")
    rows = conn.execute(
        "SELECT id FROM articles WHERE law_id=? AND article_ref LIKE ? LIMIT 1",
        (law_id, art_ref + "%")
    ).fetchall()
    if rows:
        return int(rows[0][0]) if not isinstance(rows[0], dict) else rows[0]["id"]
    return None


def upsert_frequency(conn: sqlite3.Connection, article_id: int | None, art_ref: str,
                     law_id: int | None, law_name: str | None, source: str) -> None:
    """Incrementa contador o crea registro."""
    row = conn.execute(
        "SELECT id, total_count, exam_sources FROM article_exam_frequency "
        "WHERE (article_id=? OR (article_id IS NULL AND law_id=? AND article_ref=?))",
        (article_id, law_id, art_ref)
    ).fetchone()

    if row:
        rid, count, sources_json = (
            (row["id"], row["total_count"], row["exam_sources"])
            if isinstance(row, dict) else (row[0], row[1], row[2])
        )
        sources = json.loads(sources_json or "[]")
        if source not in sources:
            sources.append(source)
        conn.execute(
            "UPDATE article_exam_frequency SET total_count=?, exam_sources=?, "
            "updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (count + 1, json.dumps(sources, ensure_ascii=False), rid)
        )
    else:
        conn.execute(
            "INSERT INTO article_exam_frequency "
            "(article_id, article_ref, law_id, law_name, total_count, exam_sources) "
            "VALUES (?,?,?,?,1,?)",
            (article_id, art_ref, law_id, law_name,
             json.dumps([source], ensure_ascii=False))
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Analiza frecuencia de artículos en tests")
    parser.add_argument("--reset", action="store_true", help="Borrar datos previos antes de procesar")
    args = parser.parse_args()

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    ensure_table(conn)

    if args.reset:
        conn.execute("DELETE FROM article_exam_frequency")
        conn.commit()
        print("Tabla vaciada.")

    pdfs = collect_pdfs()
    print(f"PDFs a procesar: {len(pdfs)}")

    total_refs = 0
    matched_refs = 0

    for pdf in pdfs:
        print(f"\nProcesando: {pdf.name}")
        text = extract_text_pypdf(pdf)
        if not text.strip():
            print("  [SKIP] Sin texto extraíble.")
            continue

        refs = extract_article_refs(text)
        print(f"  Referencias encontradas: {len(refs)}")

        for art_ref, ctx in refs:
            total_refs += 1
            law_id, law_name = find_law_in_db(conn, ctx)
            article_id = None
            if law_id:
                article_id = find_article_in_db(conn, law_id, art_ref)
                if article_id:
                    matched_refs += 1

            upsert_frequency(conn, article_id, art_ref, law_id, law_name, pdf.name)

        conn.commit()

    # Mostrar top resultados
    print(f"\n{'='*60}")
    print(f"Total referencias encontradas: {total_refs}")
    print(f"Mapeadas a artículos DB: {matched_refs}")
    print(f"\nTop 20 artículos más preguntados:")

    rows = conn.execute("""
        SELECT aef.article_ref, aef.law_name, aef.total_count, aef.exam_sources,
               a.title, l.name as law_full
        FROM article_exam_frequency aef
        LEFT JOIN articles a ON a.id = aef.article_id
        LEFT JOIN laws l ON l.id = aef.law_id
        ORDER BY aef.total_count DESC
        LIMIT 20
    """).fetchall()

    for r in rows:
        r = dict(r)
        law = r.get("law_full") or r.get("law_name") or "Ley desconocida"
        title = r.get("title") or ""
        sources = json.loads(r.get("exam_sources") or "[]")
        print(f"  Art. {r['article_ref']} | {law[:40]} | {r['total_count']}x | {', '.join(sources[:2])}")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()

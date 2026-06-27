"""Importa el articulado de la Ley de Expropiacion Forzosa de 1954 (LEF).

La LEF de 1954 numera sus articulos con ordinales/cardinales en palabra
("Articulo primero", "Articulo segundo", ... "Articulo ciento veintiocho"),
por lo que el importador generico (que solo reconoce digitos) no la parsea.

Este script:
  1. Extrae el texto del PDF oficial (BOE consolidado BOE-A-1954-15431).
  2. Localiza cada cabecera "Articulo <palabras>." en el cuerpo (desde DISPONGO:
     hasta la primera Disposicion), mapeando la palabra a su numero exacto.
  3. Captura el texto integro de cada articulo hasta la cabecera siguiente.
  4. Inserta en `articles` con law_id de la LEF, fuente = PDF BOE, marcado
     pendiente_de_validacion (regla del proyecto: todo importado requiere
     revision humana).

Rigor: NO se inventa texto. Se transcribe literalmente lo que figura en el PDF
oficial. Las cabeceras que no mapean a un numero (p. ej. la remision interna
"Articulo siguiente") se descartan y se listan para inspeccion.

Uso:
    python scripts/import_lef_1954.py --dry-run     # valida sin escribir
    python scripts/import_lef_1954.py --commit      # escribe en la BD
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import unicodedata
from pathlib import Path

from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.db import connect  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = ROOT / "data" / "sources" / "leyes_originales" / "BOE_consolidadas" / \
    "BOE-A-1954-15431_Ley_Expropiacion_Forzosa.pdf"
LAW_NAME = "Ley de Expropiacion Forzosa 1954"


def strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


def norm(s: str) -> str:
    """Normaliza una frase numerica: sin acentos, minusculas, sin 'y', 1 espacio."""
    s = strip_accents(s).lower().replace("-", " ")
    toks = [t for t in s.split() if t and t != "y"]
    return " ".join(toks)


_UNITS = {
    1: "uno", 2: "dos", 3: "tres", 4: "cuatro", 5: "cinco",
    6: "seis", 7: "siete", 8: "ocho", 9: "nueve",
}
_TEENS = {
    10: "diez", 11: "once", 12: "doce", 13: "trece", 14: "catorce", 15: "quince",
    16: "dieciseis", 17: "diecisiete", 18: "dieciocho", 19: "diecinueve",
    20: "veinte", 21: "veintiuno", 22: "veintidos", 23: "veintitres",
    24: "veinticuatro", 25: "veinticinco", 26: "veintiseis", 27: "veintisiete",
    28: "veintiocho", 29: "veintinueve",
}
_TENS = {30: "treinta", 40: "cuarenta", 50: "cincuenta", 60: "sesenta",
         70: "setenta", 80: "ochenta", 90: "noventa"}
_ORDINALS = {
    1: "primero", 2: "segundo", 3: "tercero", 4: "cuarto", 5: "quinto",
    6: "sexto", 7: "septimo", 8: "octavo", 9: "noveno",
}


def cardinal(n: int) -> str:
    if n in _UNITS:
        return _UNITS[n]
    if n in _TEENS:
        return _TEENS[n]
    if n in _TENS:
        return _TENS[n]
    if 31 <= n <= 99:
        return f"{_TENS[(n // 10) * 10]} y {_UNITS[n % 10]}"
    if n == 100:
        return "cien"
    if 101 <= n <= 199:
        return f"ciento {cardinal(n - 100)}"
    raise ValueError(n)


def build_word_map(max_n: int = 140) -> dict[str, int]:
    """Mapa frase-normalizada -> numero, para cardinales y ordinales 1..max_n."""
    m: dict[str, int] = {}
    for n in range(1, max_n + 1):
        m[norm(cardinal(n))] = n
    for n, w in _ORDINALS.items():
        m[norm(w)] = n
    # variante "cien" / "ciento" para 100
    m[norm("ciento")] = 100
    return m


import re  # noqa: E402

HEADER_RE = re.compile(r"(?im)^Art[ií]culo\s+([^\.\n]{1,40})\.")

# Paginacion del BOE consolidado que se cuela entre/dentro de articulos.
# Acentos perdidos en la extraccion -> usamos clases tolerantes.
FURNITURE_RE = re.compile(
    r"(?im)^\s*(?:"
    r"BOLET.?N OFICIAL DEL ESTADO|"
    r"LEGISLACI.?N CONSOLIDADA|"
    r"P.?gina\s+\d+"
    r")\s*$"
)


# Encabezados de estructura (TITULO/CAPITULO/SECCION) que el parseo absorbe al
# final de un articulo: pertenecen al SIGUIENTE articulo, no a este. Solo cuentan
# como cabecera de estructura las lineas en mayuscula CAP/TITULO + romano, o
# "SECCION ..."/"Seccion N". NO matchea referencias en minuscula dentro del texto
# (p. ej. "con arreglo al titulo quinto de esta Ley").
STRUCT_HEADING_RE = re.compile(
    r"^(CAP[IÍ]TULO\s+[IVXLC]+|T[IÍ]TULO\s+[IVXLC]+|SECCI[OÓ]N\s+|Secci[oó]n\s+[0-9])"
)


def strip_trailing_structural_headings(text: str) -> str:
    """Corta el sufijo a partir del primer marcador estructural.

    En el PDF las cabeceras de estructura van entre el fin de un articulo y la
    cabecera 'Articulo X' siguiente, por lo que aparecen siempre como sufijo del
    bloque. Cortamos desde la primera y devolvemos solo el cuerpo del articulo.
    """
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if STRUCT_HEADING_RE.match(ln.strip()):
            return "\n".join(lines[:i]).rstrip()
    return text


def clean_block(block: str) -> str:
    """Elimina la paginacion del BOE y normaliza espacios en blanco."""
    lines = [ln for ln in block.split("\n") if not FURNITURE_RE.match(ln)]
    out = "\n".join(lines)
    # colapsar 3+ saltos en 2
    out = re.sub(r"\n{3,}", "\n\n", out)
    out = strip_trailing_structural_headings(out)
    return out.strip()


def extract_body(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    text = "\n".join((p.extract_text() or "") for p in reader.pages)
    start = text.find("DISPONGO:")
    if start == -1:
        raise RuntimeError("No se encontro 'DISPONGO:' en el PDF")
    body = text[start:]
    # Cortar en la primera Disposicion (adicional/transitoria/final) tras el articulado
    mdisp = re.search(r"(?im)^Disposici[oó]n\s+", body)
    if mdisp:
        body = body[: mdisp.start()]
    return body


def parse(body: str, wmap: dict[str, int]):
    matches = list(HEADER_RE.finditer(body))
    arts = []
    skipped = []
    for i, mt in enumerate(matches):
        word = mt.group(1).strip()
        key = norm(word)
        if key not in wmap:
            skipped.append(word)
            continue
        num = wmap[key]
        start = mt.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        block = clean_block(body[start:end])
        arts.append((num, word, block))
    return arts, skipped


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--commit", action="store_true")
    args = ap.parse_args()

    wmap = build_word_map()
    body = extract_body(PDF_PATH)
    arts, skipped = parse(body, wmap)

    nums = [a[0] for a in arts]
    print(f"PDF: {PDF_PATH.name}")
    print(f"Cabeceras mapeadas: {len(arts)} | descartadas: {len(skipped)} -> {skipped}")
    if nums:
        print(f"Rango: art. {min(nums)} .. {max(nums)}")
    # huecos y duplicados
    seen = set()
    dups = sorted({n for n in nums if (n in seen) or seen.add(n)})
    gaps = [n for n in range(min(nums), max(nums) + 1) if n not in set(nums)] if nums else []
    print(f"Duplicados: {dups or 'ninguno'}")
    print(f"Huecos: {gaps or 'ninguno'}")
    # longitudes sospechosas
    short = [(n, len(b)) for n, _, b in arts if len(b) < 60]
    print(f"Articulos con <60 chars (revisar): {short or 'ninguno'}")
    print("\nMuestra art. 1, 9, 52 y ultimo:")
    by = {n: b for n, _, b in arts}
    for n in (1, 9, 52, max(nums) if nums else 1):
        b = by.get(n, "")
        print(f"--- art. {n} ({len(b)} chars) ---")
        print(b[:240].replace("\n", " "))

    if args.dry_run:
        print("\n[DRY-RUN] No se ha escrito nada.")
        return

    # COMMIT
    with connect() as conn:
        row = conn.execute("SELECT id FROM laws WHERE name=?", (LAW_NAME,)).fetchone()
        if not row:
            raise RuntimeError(f"No existe la ley '{LAW_NAME}' en la tabla laws")
        law_id = int(row["id"])
        n_prev = conn.execute(
            "SELECT COUNT(*) FROM articles WHERE law_id=?", (law_id,)
        ).fetchone()[0]
        src_hash = hashlib.sha256(PDF_PATH.read_bytes()).hexdigest()
        conn.execute("DELETE FROM articles WHERE law_id=?", (law_id,))
        for num, word, block in arts:
            title = f"Articulo {num}"
            conn.execute(
                """
                INSERT INTO articles(law_id, article_ref, title, text, source,
                                     original_hash, validation_status)
                VALUES (?,?,?,?,?,?, 'pendiente_de_validacion')
                """,
                (law_id, str(num), title, block, str(PDF_PATH), src_hash),
            )
        conn.commit()
        print(f"\n[COMMIT] law_id={law_id}: borrados {n_prev}, insertados {len(arts)} articulos.")


if __name__ == "__main__":
    main()

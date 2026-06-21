"""OCR de exámenes escaneados -> texto ordenado (cache .txt).

Renderiza cada página con PyMuPDF a 300 dpi, OCR con RapidOCR, reconstruye
orden de lectura asumiendo 1 o 2 columnas y vuelca a un .txt para parseo offline.
"""
import sys, io, time, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import fitz
from rapidocr_onnxruntime import RapidOCR


def order_page(result, width):
    """Ordena segmentos OCR en orden de lectura (2 columnas)."""
    if not result:
        return ""
    items = []
    for box, text, score in result:
        xs = [p[0] for p in box]; ys = [p[1] for p in box]
        items.append((min(xs), min(ys), max(xs), text))
    # ¿2 columnas? Heurística: hay texto a ambos lados del centro con poco solape
    mid = width / 2.0
    left = [it for it in items if (it[0] + it[2]) / 2 < mid]
    right = [it for it in items if (it[0] + it[2]) / 2 >= mid]
    # Si una columna está casi vacía, tratar como 1 columna
    if len(left) < 3 or len(right) < 3:
        ordered = sorted(items, key=lambda t: (round(t[1] / 8), t[0]))
    else:
        left = sorted(left, key=lambda t: (t[1], t[0]))
        right = sorted(right, key=lambda t: (t[1], t[0]))
        ordered = left + right
    return "\n".join(t[3] for t in ordered)


def ocr_pdf(path, out_txt, dpi=300):
    ocr = RapidOCR()
    doc = fitz.open(path)
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    parts = []
    t0 = time.time()
    for i, pg in enumerate(doc):
        pix = pg.get_pixmap(matrix=mat)
        result, _ = ocr(pix.tobytes("png"))
        parts.append("\n===== PAGINA %d =====\n" % (i + 1))
        parts.append(order_page(result, pix.width))
        print("  pag %d/%d (%.0fs)" % (i + 1, len(doc), time.time() - t0))
    with io.open(out_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    print("OK -> %s (%.0fs)" % (out_txt, time.time() - t0))


if __name__ == "__main__":
    pdf = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else pdf.rsplit(".", 1)[0] + "_ocr.txt"
    ocr_pdf(pdf, out)

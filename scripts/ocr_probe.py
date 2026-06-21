import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import fitz
from rapidocr_onnxruntime import RapidOCR

path = sys.argv[1]
page_idx = int(sys.argv[2]) if len(sys.argv) > 2 else 2

ocr = RapidOCR()
doc = fitz.open(path)
pg = doc[page_idx]
# render a 300 dpi
mat = fitz.Matrix(300/72, 300/72)
pix = pg.get_pixmap(matrix=mat)
img_bytes = pix.tobytes("png")

t0 = time.time()
result, _ = ocr(img_bytes)
dt = time.time() - t0
print("Página %d, %d segmentos OCR en %.1fs\n" % (page_idx+1, len(result or []), dt))

# result: list of [box, text, score]; box = 4 puntos [x,y]
# Reconstruir orden de lectura: 2 columnas. Detectar mitad por x.
if result:
    W = pix.width
    items = []
    for box, text, score in result:
        xs = [p[0] for p in box]; ys = [p[1] for p in box]
        items.append((min(xs), min(ys), text))
    mid = W/2
    left = sorted([it for it in items if it[0] < mid], key=lambda t:(t[1], t[0]))
    right = sorted([it for it in items if it[0] >= mid], key=lambda t:(t[1], t[0]))
    ordered = left + right
    txt = "\n".join(t[2] for t in ordered)
    print(txt[:1800])

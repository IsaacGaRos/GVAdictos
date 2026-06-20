import pdfplumber
import sys, io

path = sys.argv[1]
out = sys.argv[2]

with pdfplumber.open(path) as pdf:
    parts = []
    for i, page in enumerate(pdf.pages):
        parts.append("\n===== PAGINA %d =====\n" % (i + 1))
        parts.append(page.extract_text() or "")
    full = "\n".join(parts)

with io.open(out, "w", encoding="utf-8") as f:
    f.write(full)

print("Escrito %d chars a %s" % (len(full), out))
print("Paginas: %d" % len(pdf.pages))

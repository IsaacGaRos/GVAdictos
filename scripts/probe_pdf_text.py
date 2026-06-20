import pdfplumber
import sys

path = sys.argv[1]
with pdfplumber.open(path) as pdf:
    print("Paginas: %d" % len(pdf.pages))
    full = ""
    for p in pdf.pages[:3]:
        t = p.extract_text() or ""
        full += t + "\n"
    print("Chars extraidos (3 pags): %d" % len(full.strip()))
    print("\n--- PRIMEROS 1500 CHARS ---\n")
    print(full[:1500])

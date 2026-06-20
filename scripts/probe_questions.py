import pdfplumber
import sys

path = sys.argv[1]
start = int(sys.argv[2]) if len(sys.argv) > 2 else 3
end = int(sys.argv[3]) if len(sys.argv) > 3 else 5

with pdfplumber.open(path) as pdf:
    for i in range(start, min(end, len(pdf.pages))):
        print("\n========== PAGINA %d ==========" % (i+1))
        t = pdf.pages[i].extract_text() or ""
        # mostrar repr para ver si hay chars raros
        print(t[:2000])

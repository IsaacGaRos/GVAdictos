import sys

path = sys.argv[1]

# Prueba 1: pdfplumber
import pdfplumber
with pdfplumber.open(path) as pdf:
    t_plumber = pdf.pages[3].extract_text() or ""
repl = t_plumber.count("�")
print("[pdfplumber] chars=%d, U+FFFD(irrecuperables)=%d" % (len(t_plumber), repl))

# Prueba 2: PyMuPDF (fitz) si esta disponible
try:
    import fitz
    doc = fitz.open(path)
    t_fitz = doc[3].get_text()
    repl_f = t_fitz.count("�")
    print("[PyMuPDF]   chars=%d, U+FFFD=%d" % (len(t_fitz), repl_f))
    print("\n--- PyMuPDF muestra ---")
    # Buscar primera linea con pregunta
    for line in t_fitz.split("\n"):
        if line.strip() and line.strip()[0].isdigit():
            print(repr(line[:120]))
            break
    print(t_fitz[:600])
except ImportError:
    print("[PyMuPDF] NO instalado")

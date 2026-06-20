"""Parser de plantillas oficiales GVA (cuestionario + plantilla de respuestas).

Formato detectado (A1-01 1/25 primera parte):
  - Pagina 1: plantilla de respuestas, pares "num letra" en 5 columnas.
  - Bloque castellano: preguntas "N. enunciado" + opciones "A) ... D) ...".
  - El castellano precede al valencia (mismo contenido duplicado), por lo que
    parseamos secuencialmente 1..N_max y paramos cuando reaparece el numero 1.

Devuelve dict: {answer_key, questions:[{numero,enunciado,opciones,respuesta}]}.
"""
import re
import pdfplumber

OPT_RE = re.compile(r"^([A-D])\)\s+(.*)")
# Acepta "1. ", "1.-Texto", "3.- Texto" (formatos 2023-2025)
Q_RE = re.compile(r"^(\d{1,3})\s*\.\s*-?\s*(.+)")
FOOTER_RE = re.compile(r"^\d+\s*/\s*\d+$")
PAIR_RE = re.compile(r"(\d{1,3})\s+([A-D])\b")


def parse_answer_key(page_text):
    """Extrae {num:letra} de la pagina de plantilla."""
    key = {}
    for num, letra in PAIR_RE.findall(page_text):
        n = int(num)
        if 1 <= n <= 300:
            key[n] = letra
    return key


def parse_exam(path, max_questions=None):
    with pdfplumber.open(path) as pdf:
        pages = [p.extract_text() or "" for p in pdf.pages]

    answer_key = parse_answer_key(pages[0]) if pages else {}

    questions = []
    expected = 1
    cur = None
    cur_opt = None

    def flush():
        nonlocal cur, cur_opt
        if cur is not None:
            questions.append(cur)
        cur = None
        cur_opt = None

    for page_text in pages[1:]:
        for raw in page_text.split("\n"):
            line = raw.strip()
            if not line or FOOTER_RE.match(line):
                continue

            qm = Q_RE.match(line)
            # Nueva pregunta SOLO si el numero es el esperado (secuencial),
            # asi ignoramos numeros sueltos y el reinicio del valencia.
            if qm and int(qm.group(1)) == expected:
                flush()
                cur = {
                    "numero": expected,
                    "enunciado": qm.group(2).strip(),
                    "opciones": {},
                    "respuesta": answer_key.get(expected),
                }
                cur_opt = None
                expected += 1
                if max_questions and expected > max_questions:
                    # seguimos por si faltan opciones de la ultima
                    pass
                continue

            if cur is None:
                continue

            om = OPT_RE.match(line)
            if om:
                cur_opt = om.group(1)
                cur["opciones"][cur_opt] = om.group(2).strip()
                continue

            # Continuacion de texto (enunciado u opcion con wrap)
            if cur_opt:
                cur["opciones"][cur_opt] += " " + line
            else:
                cur["enunciado"] += " " + line

    flush()

    # Si el max esperado se alcanzo, recortamos por seguridad
    if max_questions:
        questions = [q for q in questions if q["numero"] <= max_questions]

    return {"answer_key": answer_key, "questions": questions}


if __name__ == "__main__":
    import sys
    res = parse_exam(sys.argv[1])
    qs = res["questions"]
    print("Answer key entries: %d" % len(res["answer_key"]))
    print("Preguntas parseadas: %d" % len(qs))
    # Validacion: cuantas tienen 4 opciones y respuesta
    full = [q for q in qs if len(q["opciones"]) == 4 and q["respuesta"]]
    print("Con 4 opciones + respuesta: %d" % len(full))
    incompletas = [q["numero"] for q in qs if len(q["opciones"]) != 4]
    if incompletas:
        print("Preguntas con != 4 opciones: %s" % incompletas[:20])
    # Muestra
    for q in qs[:3]:
        print("\n--- Q%d (resp=%s) ---" % (q["numero"], q["respuesta"]))
        print("ENUN:", q["enunciado"][:160])
        for L in "ABCD":
            print("  %s) %s" % (L, q["opciones"].get(L, "<FALTA>")[:90]))

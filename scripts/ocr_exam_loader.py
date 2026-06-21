"""Carga exámenes OCR (escaneados) en la BD, APENDICE tras rebuild_official_exams.

- Respuestas correctas: de la plantilla en TEXTO (fiable).
- Enunciado/contexto: del .txt OCR, segmentado por nº de pregunta.
- Vinculación ley/artículo: vía exam_linker (ley por cita en enunciado;
  artículo explícito si aparece). La inferencia posterior (bolsa de palabras)
  es robusta al desorden del OCR.
- Marca fuente_tipo='oficial_gva' y notes='ocr' (menor confianza).
"""
import os, sys, re, sqlite3
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exam_linker import build_law_index, link_question

DB = r"C:\Users\isaac\Desktop\GVAdictos\db\gvadicto.sqlite"
EXROOT = r"C:\Users\isaac\Desktop\GVAdictos\data\examenes_oficiales"

# (cuerpo, conv, anio, parte, plantilla_pdf, plantilla_pages, ocr_txt, n_preg)
# plantilla_pages = None (todo el PDF) o (inicio, fin) 1-based inclusive.
OCR_EXAMS = [
    ("A1-01", "31/16", 2016, "1er ejercicio (test, OCR)",
     r"A1-01\2016\31-16_plantilla.pdf", None, r"A1-01\2016\31-16_ocr.txt", 120),
    ("A1-01", "32/16", 2016, "1er ejercicio (test, OCR)",
     r"A1-01\2016\32-16_plantilla.pdf", None, r"A1-01\2016\32-16_ocr.txt", 120),
    ("A1-01", "63/18", 2018, "1er ejercicio (test, OCR)",
     r"A1-01\2018\63-18_plantilla.txt", None,
     r"A1-01\2018\63-18_TL_ocr.txt", 120),
]

PLANT_PAREN = re.compile(r"(\d{1,3})\)\s*(ANULADA|[A-D])")
PLANT_GRID = re.compile(r"(\d{1,3})\s+(ANULADA|[A-D])\b")
# nº seguido de uno o más de . ) - (cubre "2.", "2.-", "2)") y luego texto
QLINE = re.compile(r"^\s*(\d{1,3})\s*[\.\)\-]+\s*([A-Za-zÁÉÍÓÚÑáéíóúñ¿¡].*)")


def parse_text_plantilla(path, pages=None):
    if path.lower().endswith(".txt"):
        with open(path, encoding="utf-8") as f:
            txt = f.read()
    else:
        import pdfplumber
        txt = ""
        with pdfplumber.open(path) as pdf:
            sel = pdf.pages
            if pages:
                sel = pdf.pages[pages[0] - 1:pages[1]]
            for p in sel:
                txt += (p.extract_text() or "") + "\n"
    key = {}
    pairs = PLANT_PAREN.findall(txt)
    if len(pairs) < 20:
        pairs = PLANT_GRID.findall(txt)
    for num, val in pairs:
        n = int(num)
        if 1 <= n <= 300:
            key[n] = val
    return key


def segment_ocr(txt_path, max_q):
    """Segmenta por nº de pregunta SIN exigir orden (el OCR a 2 columnas
    desordena). Captura todas las líneas que abren pregunta, y para cada
    número se queda con la PRIMERA ocurrencia (castellano antes que valencià)."""
    with open(txt_path, encoding="utf-8") as f:
        lines = [ln for ln in f.read().split("\n") if not ln.startswith("=====")]
    # posiciones de inicio de pregunta
    starts = []  # (idx_linea, numero, primer_texto)
    for i, ln in enumerate(lines):
        m = QLINE.match(ln)
        if m:
            n = int(m.group(1))
            if 1 <= n <= max_q:
                starts.append((i, n, m.group(2)))
    blocks = {}
    for k, (idx, n, first) in enumerate(starts):
        end = starts[k + 1][0] if k + 1 < len(starts) else len(lines)
        body = [first] + [lines[j].strip() for j in range(idx + 1, end)]
        text = " ".join(body).strip()
        # quedarse con el bloque MÁS LARGO por número: descarta items de lista
        # cortos (p.ej. "19. Decretos del President") frente al enunciado real.
        if n not in blocks or len(text) > len(blocks[n]):
            blocks[n] = text
    return blocks


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    laws = [dict(r) for r in conn.execute("SELECT id, name FROM laws")]
    index = build_law_index(laws)
    now = datetime.now().isoformat()

    tot_q = tot_law = 0
    for cuerpo, conv, anio, parte, plant_rel, plant_pages, ocr_rel, npreg in OCR_EXAMS:
        plant_path = os.path.join(EXROOT, plant_rel)
        ocr_path = os.path.join(EXROOT, ocr_rel)
        if not (os.path.exists(plant_path) and os.path.exists(ocr_path)):
            print("FALTA %s / %s" % (plant_rel, ocr_rel))
            continue
        key = parse_text_plantilla(plant_path, plant_pages)
        blocks = segment_ocr(ocr_path, npreg)

        # upsert paper
        row = conn.execute(
            "SELECT id FROM exam_papers WHERE bloque=? AND convocatoria=? AND anio=? AND parte=?",
            (cuerpo, conv, anio, parte)).fetchone()
        if row:
            pid = row["id"]
            conn.execute("DELETE FROM exam_questions WHERE exam_paper_id=?", (pid,))
            conn.execute(
                "UPDATE exam_papers SET fuente_path=?, fuente_tipo='oficial_gva', "
                "fase=?, estado='importado_ocr', notes='ocr', updated_at=? WHERE id=?",
                (ocr_rel, parte, now, pid))
        else:
            cur = conn.execute(
                "INSERT INTO exam_papers (convocatoria, anio, bloque, parte, fase, "
                "fuente_path, fuente_tipo, estado, validation_status, notes, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?, 'oficial_gva', 'importado_ocr', 'oficial', 'ocr', ?, ?)",
                (conv, anio, cuerpo, parte, parte, ocr_rel, now, now))
            pid = cur.lastrowid

        ins = lk = 0
        for n in range(1, npreg + 1):
            ans = key.get(n)
            block = blocks.get(n, "")
            if ans == "ANULADA" or not block:
                continue
            enun = block[:600]
            cur = conn.execute(
                "INSERT INTO exam_questions (exam_paper_id, numero, enunciado, "
                "respuesta_oficial, anulada, validation_status, created_at) "
                "VALUES (?,?,?,?,0,?,?)",
                (pid, n, enun, ans if ans in "ABCD" else None,
                 "pendiente_revision_ocr", now))
            qid = cur.lastrowid
            ins += 1
            # opcion sintetica con el bloque completo (para inferencia bolsa-de-palabras)
            conn.execute(
                "INSERT INTO exam_question_options (exam_question_id, letra, texto, es_correcta, created_at) "
                "VALUES (?,?,?,1,?)",
                (qid, ans if ans in "ABCD" else "A", block, now))
            link = link_question(enun, {"A": block}, index)
            if link["law_id"]:
                lk += 1
                arts = link["articles"]
                if arts:
                    placed = False
                    for ref in arts:
                        a = conn.execute("SELECT id FROM articles WHERE law_id=? AND article_ref=?",
                                         (link["law_id"], ref)).fetchone()
                        if a:
                            conn.execute(
                                "INSERT INTO exam_question_links (exam_question_id, law_id, article_id, "
                                "tipo_relacion, mapping_basis, confianza, validation_status, created_at) "
                                "VALUES (?,?,?,?,?,?,?,?)",
                                (qid, link["law_id"], a["id"], "articulo_explicito",
                                 "ocr|" + link["basis"], min(link["confianza"], 0.7),
                                 "requiere_revision_humana", now))
                            placed = True
                    if not placed:
                        conn.execute(
                            "INSERT INTO exam_question_links (exam_question_id, law_id, article_id, "
                            "tipo_relacion, mapping_basis, confianza, validation_status, created_at) "
                            "VALUES (?,?,NULL,?,?,?,?,?)",
                            (qid, link["law_id"], "ley_explicita", "ocr|" + link["basis"],
                             min(link["confianza"], 0.7), "requiere_revision_humana", now))
                else:
                    conn.execute(
                        "INSERT INTO exam_question_links (exam_question_id, law_id, article_id, "
                        "tipo_relacion, mapping_basis, confianza, validation_status, created_at) "
                        "VALUES (?,?,NULL,?,?,?,?,?)",
                        (qid, link["law_id"], "ley_explicita", "ocr|" + link["basis"],
                         min(link["confianza"], 0.7), "requiere_revision_humana", now))
        conn.commit()
        tot_q += ins; tot_law += lk
        print("[%s %s] preguntas=%d  con_ley=%d  (plantilla=%d, bloques=%d)" %
              (cuerpo, conv, ins, lk, len(key), len(blocks)))

    print("\nTotal OCR: preguntas=%d  con_ley=%d" % (tot_q, tot_law))
    conn.close()


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    main()

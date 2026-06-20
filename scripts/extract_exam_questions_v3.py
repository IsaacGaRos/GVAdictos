import pdfplumber
import re
import sqlite3
from datetime import datetime
import os

db_path = r"C:\Users\isaac\Desktop\GVAdictos\db\gvadicto.sqlite"
exams_dir = r"C:\Users\isaac\Desktop\GVAdictos\data\examenes_oficiales"

def extract_text_from_pdf(pdf_path):
    """Extrae texto usando pdfplumber"""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print("    [WARN] Error extrayendo texto: %s" % str(e)[:50])

    return text

def extract_questions_from_text(text):
    """Extrae preguntas numeradas"""
    questions = []
    lines = text.split("\n")

    for line in lines:
        line_clean = line.strip()

        # Buscar linea con numero seguido de texto
        match = re.match(r"^(\d+)[.\)]\s+(.+)", line_clean)
        if match:
            try:
                num = int(match.group(1))
                text_content = match.group(2).strip()

                # Validar: numero entre 1-200, texto con minimo 5 caracteres
                if 0 < num <= 200 and len(text_content) > 5:
                    questions.append({
                        "numero": num,
                        "enunciado": text_content[:500]
                    })
            except:
                pass

    # Eliminar duplicados de numero
    seen = {}
    unique = []
    for q in questions:
        if q["numero"] not in seen:
            seen[q["numero"]] = True
            unique.append(q)

    return unique

def process_exams(conn):
    """Procesa todos los PDFs"""
    cursor = conn.cursor()

    total_processed = 0
    total_questions = 0
    total_skipped = 0

    print("Buscando PDFs en: %s\n" % exams_dir)

    for root, dirs, files in os.walk(exams_dir):
        for file in sorted(files):
            if not file.endswith(".pdf"):
                continue

            pdf_path = os.path.join(root, file)
            rel_path = os.path.relpath(pdf_path, exams_dir)

            print("[%s]" % rel_path)

            try:
                # Obtener exam_paper_id
                cursor.execute("SELECT id, bloque, anio FROM exam_papers WHERE fuente_path LIKE ?", ("%" + file,))
                result = cursor.fetchone()

                if not result:
                    print("  > Saltado: no en exam_papers")
                    total_skipped += 1
                    continue

                exam_id, bloque, ano = result

                # Extraer texto del PDF
                text = extract_text_from_pdf(pdf_path)
                text_len = len(text.strip())

                if text_len < 50:
                    print("  > Saltado: texto insuficiente (%d chars)" % text_len)
                    total_skipped += 1
                    continue

                # Extraer preguntas
                questions = extract_questions_from_text(text)

                if len(questions) == 0:
                    print("  > Procesado: 0 preguntas encontradas")
                    total_processed += 1
                    continue

                # Insertar preguntas en BD
                inserted = 0
                for q in questions:
                    cursor.execute("""
                    INSERT OR IGNORE INTO exam_questions
                    (exam_paper_id, numero, enunciado, validation_status, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """, (
                        exam_id,
                        q["numero"],
                        q["enunciado"],
                        "pendiente_validacion",
                        datetime.now().isoformat()
                    ))
                    inserted += 1
                    total_questions += 1

                conn.commit()
                print("  > OK: %d preguntas importadas" % inserted)
                total_processed += 1

            except Exception as e:
                print("  > ERROR: %s" % str(e)[:80])

    return total_processed, total_questions, total_skipped

if __name__ == "__main__":
    conn = sqlite3.connect(db_path)
    print("=== FASE 1: Extraccion de preguntas (v3 pdfplumber) ===\n")

    processed, questions, skipped = process_exams(conn)

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM exam_questions")
    total_bd = cursor.fetchone()[0]

    print("\n=== Resumen ===")
    print("Examenes procesados: %d" % processed)
    print("Examenes saltados: %d" % skipped)
    print("Preguntas importadas: %d" % questions)
    print("Total en BD: %d" % total_bd)

    if questions > 0:
        print("\n✓ FASE 1 COMPLETADA - Preguntas extraidas exitosamente")
    else:
        print("\n⚠ FASE 1: Sin preguntas extraidas (PDFs pueden ser imagenes)")
        print("  Para OCR, instalar: Tesseract-OCR from github.com/UB-Mannheim/tesseract")

    conn.close()

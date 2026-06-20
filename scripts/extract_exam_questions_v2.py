import pdfplumber
import pytesseract
from pdf2image import convert_from_path
import re
import sqlite3
from datetime import datetime
import os

db_path = r"C:\Users\isaac\Desktop\GVAdictos\db\gvadicto.sqlite"
exams_dir = r"C:\Users\isaac\Desktop\GVAdictos\data\examenes_oficiales"

def extract_text_from_pdf(pdf_path):
    """Extrae texto usando pdfplumber y OCR si es necesario"""
    text = ""

    # Intentar pdfplumber primero
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except:
        pass

    # Si no hay suficiente texto, usar OCR
    if len(text.strip()) < 100:
        try:
            print("    [OCR] Detectada imagen, aplicando Tesseract...")
            # Convertir primeras 5 paginas a imagen para OCR
            images = convert_from_path(pdf_path, first_page=1, last_page=min(5, 999))
            for img in images:
                ocr_text = pytesseract.image_to_string(img, lang='spa')
                text += ocr_text + "\n"
        except Exception as e:
            print("    [WARN] OCR fallido: %s" % str(e)[:50])

    return text

def extract_questions(text):
    """Extrae preguntas numeradas del texto"""
    questions = []
    lines = text.split("\n")
    q_num = 0

    for i, line in enumerate(lines):
        line_clean = line.strip()

        # Buscar lineas que empiezan con numero
        match = re.match(r"^(\d+)[.\)]\s+(.+)", line_clean)
        if match:
            try:
                num = int(match.group(1))
                text_content = match.group(2).strip()

                # Si el numero es razonable (1-200) y el texto tiene contenido
                if 0 < num <= 200 and len(text_content) > 5:
                    questions.append({
                        "numero": num,
                        "enunciado": text_content[:500]  # Limitar a 500 caracteres
                    })
            except:
                pass

    # Eliminar duplicados, mantener el primero de cada numero
    seen = {}
    unique = []
    for q in questions:
        if q["numero"] not in seen:
            seen[q["numero"]] = True
            unique.append(q)

    return unique

def process_exams(conn):
    """Procesa todos los examenes"""
    cursor = conn.cursor()

    total_processed = 0
    total_questions = 0

    for root, dirs, files in os.walk(exams_dir):
        for file in files:
            if not file.endswith(".pdf"):
                continue

            pdf_path = os.path.join(root, file)
            print("\n[PROCESANDO] %s" % file)

            try:
                # Obtener exam_paper_id
                cursor.execute("SELECT id FROM exam_papers WHERE fuente_path LIKE ?", ("%" + file,))
                result = cursor.fetchone()

                if not result:
                    print("  SKIP: No en tabla exam_papers")
                    continue

                exam_id = result[0]
                print("  Paper ID: %d" % exam_id)

                # Extraer texto
                text = extract_text_from_pdf(pdf_path)

                if len(text.strip()) < 50:
                    print("  SKIP: Texto insuficiente (< 50 caracteres)")
                    continue

                print("  Text length: %d chars" % len(text.strip()))

                # Extraer preguntas
                questions = extract_questions(text)
                print("  Preguntas extraidas: %d" % len(questions))

                # Insertar en BD
                for q in questions:
                    try:
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
                        total_questions += 1
                    except Exception as e:
                        print("  [DB ERROR] %s" % str(e)[:80])

                total_processed += 1
                conn.commit()

            except Exception as e:
                print("  ERROR: %s" % str(e)[:80])

    return total_processed, total_questions

if __name__ == "__main__":
    conn = sqlite3.connect(db_path)
    print("=== FASE 1: Extraccion de preguntas (v2) ===\n")

    processed, questions = process_exams(conn)

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM exam_questions")
    total = cursor.fetchone()[0]

    print("\n=== Resumen ===")
    print("Examenes procesados: %d" % processed)
    print("Preguntas nuevas: %d" % questions)
    print("Total en BD: %d" % total)

    conn.close()
    print("\nFASE 1 COMPLETADA")

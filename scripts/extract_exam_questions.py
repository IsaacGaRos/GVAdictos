import pdfplumber
import re
import sqlite3
from pathlib import Path
from datetime import datetime
import os

db_path = r"C:\Users\isaac\Desktop\GVAdictos\db\gvadicto.sqlite"
exams_dir = r"C:\Users\isaac\Desktop\GVAdictos\data\examenes_oficiales"

def extract_text_from_pdf(pdf_path):
    """Extrae texto de PDF"""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except:
        pass
    return text

def extract_questions(text):
    """Extrae preguntas del texto"""
    questions = []
    lines = text.split("\n")
    q_num = 0

    for line in lines:
        line = line.strip()
        if re.match(r"^\d+[\.\)]\s", line):
            q_num += 1
            q_text = re.sub(r"^\d+[\.\)]\s*", "", line)
            questions.append({
                "number": q_num,
                "text": q_text[:200]
            })

    return questions

def create_tables(conn):
    """Crea tablas"""
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exam_questions (
        id INTEGER PRIMARY KEY,
        exam_paper_id INTEGER,
        question_number INTEGER,
        question_text TEXT,
        extracted_by TEXT DEFAULT 'ocr',
        created_at TEXT,
        FOREIGN KEY(exam_paper_id) REFERENCES exam_papers(id)
    )
    """)
    conn.commit()

def process_exams(conn):
    """Procesa examenes"""
    cursor = conn.cursor()
    create_tables(conn)

    total = 0
    total_q = 0

    for root, dirs, files in os.walk(exams_dir):
        for file in files:
            if file.endswith(".pdf"):
                pdf_path = os.path.join(root, file)
                print("[PROCESANDO] %s" % file)

                try:
                    cursor.execute("SELECT id FROM exam_papers WHERE fuente_path LIKE ?", ("%" + file,))
                    result = cursor.fetchone()

                    if not result:
                        print("  SKIP: No en exam_papers")
                        continue

                    exam_id = result[0]
                    text = extract_text_from_pdf(pdf_path)

                    if len(text.strip()) < 50:
                        print("  SKIP: Texto insuficiente")
                        continue

                    questions = extract_questions(text)
                    print("  OK: %d preguntas extraidas" % len(questions))

                    for q in questions:
                        cursor.execute("""
                        INSERT OR IGNORE INTO exam_questions
                        (exam_paper_id, question_number, question_text, created_at)
                        VALUES (?, ?, ?, ?)
                        """, (exam_id, q["number"], q["text"], datetime.now().isoformat()))
                        total_q += 1

                    total += 1
                    conn.commit()

                except Exception as e:
                    print("  ERROR: %s" % str(e)[:50])

    return total, total_q

if __name__ == "__main__":
    conn = sqlite3.connect(db_path)
    print("=== FASE 1: Extraccion de preguntas ===\n")

    processed, questions = process_exams(conn)

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM exam_questions")
    total = cursor.fetchone()[0]

    print("\nExamenes procesados: %d" % processed)
    print("Preguntas extraidas: %d" % questions)
    print("Total en BD: %d" % total)

    conn.close()

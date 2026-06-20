import sqlite3
import re
from datetime import datetime

db_path = r"C:\Users\isaac\Desktop\GVAdictos\db\gvadicto.sqlite"

def create_linking_table(conn):
    """Crea tabla de vinculacion si no existe"""
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exam_question_article_links (
        id INTEGER PRIMARY KEY,
        question_id INTEGER,
        article_id INTEGER,
        law_id INTEGER,
        match_score REAL,
        match_type TEXT,
        created_at TEXT,
        FOREIGN KEY(question_id) REFERENCES exam_questions(id),
        FOREIGN KEY(article_id) REFERENCES articles(id),
        FOREIGN KEY(law_id) REFERENCES laws(id),
        UNIQUE(question_id, article_id)
    )
    """)
    conn.commit()

def extract_keywords(text):
    """Extrae palabras clave del texto"""
    # Remover palabras comunes
    stopwords = {
        'el', 'la', 'de', 'del', 'en', 'a', 'al', 'y', 'o', 'por', 'para',
        'con', 'sin', 'un', 'una', 'unos', 'unas', 'se', 'son', 'es', 'fue',
        'ha', 'han', 'como', 'más', 'pero', 'que', 'este', 'esta', 'este',
        'ley', 'articulo', 'los', 'las', 'está', 'están'
    }

    # Convertir a minusculas y extraer palabras
    text_clean = re.sub(r'[^\w\s]', ' ', text.lower())
    words = text_clean.split()

    # Filtrar stopwords y palabras muy cortas
    keywords = [w for w in words if len(w) > 3 and w not in stopwords]

    return list(set(keywords))  # Unicas

def link_question_to_articles(conn, question_id, question_text, exam_paper_id):
    """Vincula una pregunta a articulos relevantes"""
    cursor = conn.cursor()

    # Obtener info del examen
    cursor.execute("SELECT bloque, anio FROM exam_papers WHERE id = ?", (exam_paper_id,))
    exam_info = cursor.fetchone()
    if not exam_info:
        return 0

    bloque, ano = exam_info

    # Extraer palabras clave
    keywords = extract_keywords(question_text)
    if not keywords:
        return 0

    # Buscar articulos con palabras clave en su contenido o titulo
    linked_count = 0

    for keyword in keywords[:5]:  # Limitar a 5 keywords principales
        # Buscar en articulos
        cursor.execute("""
        SELECT DISTINCT a.id, a.law_id, a.text
        FROM articles a
        WHERE LOWER(a.text) LIKE ?
        LIMIT 5
        """, ("%" + keyword + "%",))

        for article_id, law_id, article_text in cursor.fetchall():
            # Calcular score simple (entre 0 y 1)
            # Basado en cuantos keywords coinciden
            match_score = 0.5 + (len(keyword) / 100)  # Base 0.5 + bonus por longitud

            try:
                cursor.execute("""
                INSERT OR IGNORE INTO exam_question_article_links
                (question_id, article_id, law_id, match_score, match_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    question_id,
                    article_id,
                    law_id,
                    match_score,
                    "keyword_match",
                    datetime.now().isoformat()
                ))
                linked_count += 1
            except:
                pass

    return linked_count

def process_all_questions(conn):
    """Procesa todas las preguntas"""
    cursor = conn.cursor()
    create_linking_table(conn)

    # Obtener todas las preguntas sin vincular
    cursor.execute("""
    SELECT eq.id, eq.enunciado, eq.exam_paper_id
    FROM exam_questions eq
    WHERE eq.id NOT IN (
        SELECT DISTINCT question_id FROM exam_question_article_links
    )
    """)

    questions = cursor.fetchall()
    total_linked = 0

    print("Vinculando %d preguntas a articulos...\n" % len(questions))

    for question_id, enunciado, exam_id in questions:
        links = link_question_to_articles(conn, question_id, enunciado, exam_id)
        if links > 0:
            print("  P#%d: %d articulos vinculados" % (question_id, links))
            total_linked += links

    conn.commit()
    return len(questions), total_linked

if __name__ == "__main__":
    conn = sqlite3.connect(db_path)
    print("=== FASE 2: Vincular preguntas a articulos ===\n")

    total_q, total_links = process_all_questions(conn)

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM exam_question_article_links")
    links_bd = cursor.fetchone()[0]

    print("\n=== Resumen ===")
    print("Preguntas procesadas: %d" % total_q)
    print("Links creados: %d" % total_links)
    print("Total en BD: %d" % links_bd)

    conn.close()
    print("\n✓ FASE 2 COMPLETADA")

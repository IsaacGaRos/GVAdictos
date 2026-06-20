import sqlite3
from datetime import datetime

db_path = r"C:\Users\isaac\Desktop\GVAdictos\db\gvadicto.sqlite"

def create_frequency_table(conn):
    """Crea tabla de frecuencia si no existe"""
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS article_exam_frequency (
        id INTEGER PRIMARY KEY,
        article_id INTEGER UNIQUE,
        exam_count INTEGER DEFAULT 0,
        exam_question_count INTEGER DEFAULT 0,
        body_source TEXT,
        last_seen_in_exam TEXT,
        frequency_rank INTEGER,
        updated_at TEXT,
        FOREIGN KEY(article_id) REFERENCES articles(id)
    )
    """)
    conn.commit()

def calculate_frequency_ranking(conn):
    """Calcula ranking de frecuencia de articulos"""
    cursor = conn.cursor()
    create_frequency_table(conn)

    print("Calculando frecuencia de articulos...\n")

    # Obtener articulos que aparecen en preguntas
    cursor.execute("""
    SELECT DISTINCT a.id, a.law_id, l.name, COUNT(DISTINCT eqal.question_id) as q_count
    FROM articles a
    JOIN exam_question_article_links eqal ON a.id = eqal.article_id
    JOIN laws l ON a.law_id = l.id
    GROUP BY a.id
    ORDER BY q_count DESC
    """)

    articles = cursor.fetchall()
    print("Articulos con vinculos a preguntas: %d\n" % len(articles))

    # Obtener info de cada examen por cuerpo
    cursor.execute("""
    SELECT bloque, COUNT(*) as exam_count
    FROM exam_papers
    WHERE fuente_path IS NOT NULL
    GROUP BY bloque
    """)
    exam_counts = {row[0]: row[1] for row in cursor.fetchall()}

    # Insertar/actualizar frecuencias
    rank = 1
    inserted = 0

    for article_id, law_id, law_name, q_count in articles:
        # Obtener ley padre para determinar cuerpo
        cursor.execute("""
        SELECT DISTINCT ep.bloque
        FROM exam_papers ep
        JOIN exam_questions eq ON ep.id = eq.exam_paper_id
        JOIN exam_question_article_links eqal ON eq.id = eqal.question_id
        WHERE eqal.article_id = ?
        LIMIT 1
        """, (article_id,))

        body_result = cursor.fetchone()
        body_source = body_result[0] if body_result else "UNKNOWN"

        # Obtener examen mas reciente donde aparece
        cursor.execute("""
        SELECT ep.convocatoria, ep.anio
        FROM exam_papers ep
        JOIN exam_questions eq ON ep.id = eq.exam_paper_id
        JOIN exam_question_article_links eqal ON eq.id = eqal.question_id
        WHERE eqal.article_id = ?
        ORDER BY ep.anio DESC
        LIMIT 1
        """, (article_id,))

        exam_result = cursor.fetchone()
        last_exam = "%s/%d" % (exam_result[0], exam_result[1]) if exam_result else "N/A"

        try:
            cursor.execute("""
            INSERT OR REPLACE INTO article_exam_frequency
            (article_id, exam_count, exam_question_count, body_source, last_seen_in_exam, frequency_rank, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                article_id,
                1,  # Simplificado: 1 si aparece en examenes
                q_count,
                body_source,
                last_exam,
                rank,
                datetime.now().isoformat()
            ))
            rank += 1
            inserted += 1

            if inserted <= 10 or inserted % 10 == 0:
                print("  Art#%d (Ley: %s...): %d preguntas, Cuerpo: %s" % (
                    article_id, law_name[:30], q_count, body_source))

        except Exception as e:
            print("  ERROR art#%d: %s" % (article_id, str(e)[:50]))

    conn.commit()
    return inserted

def generate_ranking_report(conn):
    """Genera reporte de ranking"""
    cursor = conn.cursor()

    print("\n=== Top 20 Articulos mas preguntados ===\n")

    cursor.execute("""
    SELECT aef.frequency_rank, a.id, a.article_num, l.name, aef.exam_question_count, aef.body_source
    FROM article_exam_frequency aef
    JOIN articles a ON aef.article_id = a.id
    JOIN laws l ON a.law_id = l.id
    ORDER BY aef.frequency_rank ASC
    LIMIT 20
    """)

    for rank, a_id, a_num, law_name, q_count, body in cursor.fetchall():
        print("%2d. Art. %s de %s (Cuerpo: %s, %d preguntas)" % (
            rank, a_num, law_name[:45], body, q_count))

    # Estadisticas por cuerpo
    print("\n=== Articulos por cuerpo de examen ===\n")
    cursor.execute("""
    SELECT body_source, COUNT(*) as count, SUM(exam_question_count) as total_questions
    FROM article_exam_frequency
    GROUP BY body_source
    ORDER BY total_questions DESC
    """)

    for body, count, total_q in cursor.fetchall():
        print("%s: %d articulos, %d preguntas totales" % (body, count, total_q))

    # Estadisticas por ley
    print("\n=== Top 10 Leyes por articulos preguntados ===\n")
    cursor.execute("""
    SELECT l.name, COUNT(*) as art_count, SUM(aef.exam_question_count) as total_q
    FROM article_exam_frequency aef
    JOIN articles a ON aef.article_id = a.id
    JOIN laws l ON a.law_id = l.id
    GROUP BY l.id
    ORDER BY total_q DESC
    LIMIT 10
    """)

    for law, art_count, total_q in cursor.fetchall():
        print("  %s: %d articulos, %d preguntas" % (law[:55], art_count, total_q))

if __name__ == "__main__":
    conn = sqlite3.connect(db_path)
    print("=== FASE 3: Crear ranking de articulos ===\n")

    inserted = calculate_frequency_ranking(conn)

    print("\n=== Resumen ===")
    print("Articulos en ranking: %d" % inserted)

    generate_ranking_report(conn)

    conn.close()
    print("\n✓ FASE 3 COMPLETADA")

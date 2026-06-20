import sqlite3
from datetime import datetime

db_path = r"C:\Users\isaac\Desktop\GVAdictos\db\gvadicto.sqlite"

def update_frequency_ranking(conn):
    """Actualiza ranking basado en examenes"""
    cursor = conn.cursor()

    print("Actualizando frecuencia de articulos...\n")

    # Obtener articulos que aparecen en preguntas de examen
    cursor.execute("""
    SELECT DISTINCT a.id, a.article_ref, a.law_id, l.name, COUNT(DISTINCT eqal.question_id) as q_count
    FROM articles a
    JOIN exam_question_article_links eqal ON a.id = eqal.article_id
    JOIN laws l ON a.law_id = l.id
    GROUP BY a.id
    ORDER BY q_count DESC
    """)

    articles = cursor.fetchall()
    print("Articulos con preguntas de examen: %d\n" % len(articles))

    updated = 0
    rank = 1

    for article_id, article_ref, law_id, law_name, q_count in articles:
        # Obtener cuerpos donde aparece
        cursor.execute("""
        SELECT DISTINCT ep.bloque
        FROM exam_papers ep
        JOIN exam_questions eq ON ep.id = eq.exam_paper_id
        JOIN exam_question_article_links eqal ON eq.id = eqal.question_id
        WHERE eqal.article_id = ?
        """, (article_id,))

        bodies = [row[0] for row in cursor.fetchall()]
        exam_sources = ','.join(bodies) if bodies else 'UNKNOWN'

        try:
            cursor.execute("""
            UPDATE article_exam_frequency
            SET total_count = ?, exam_sources = ?, updated_at = ?
            WHERE article_id = ?
            """, (q_count, exam_sources, datetime.now().isoformat(), article_id))

            if cursor.rowcount == 0:
                # Insertar si no existe
                cursor.execute("""
                INSERT INTO article_exam_frequency
                (article_id, article_ref, law_id, law_name, total_count, exam_sources, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    article_id, article_ref, law_id, law_name,
                    q_count, exam_sources,
                    datetime.now().isoformat(), datetime.now().isoformat()
                ))

            updated += 1
            rank += 1

            if updated <= 15 or updated % 20 == 0:
                print("  Art. %s (%s): %d preguntas, en: %s" % (
                    article_ref, law_name[:30], q_count, exam_sources))

        except Exception as e:
            print("  ERROR: %s" % str(e)[:80])

    conn.commit()
    return updated

def generate_report(conn):
    """Genera reporte de ranking"""
    cursor = conn.cursor()

    print("\n=== Top 20 Articulos mas preguntados ===\n")

    cursor.execute("""
    SELECT article_ref, law_name, total_count, exam_sources
    FROM article_exam_frequency
    WHERE total_count > 0
    ORDER BY total_count DESC
    LIMIT 20
    """)

    for i, (article_ref, law_name, count, sources) in enumerate(cursor.fetchall(), 1):
        print("%2d. Art. %s - %s (%d preguntas, en: %s)" % (
            i, article_ref, law_name[:40], count, sources))

    # Estadisticas por cuerpo
    print("\n=== Preguntas por cuerpo de examen ===\n")

    cursor.execute("""
    SELECT
        CASE
            WHEN exam_sources LIKE '%A1-01%' THEN 'A1-01'
            WHEN exam_sources LIKE '%A2-01%' THEN 'A2-01'
            WHEN exam_sources LIKE '%C1-01%' THEN 'C1-01'
            ELSE 'OTROS'
        END as cuerpo,
        SUM(total_count) as total
    FROM article_exam_frequency
    GROUP BY cuerpo
    ORDER BY total DESC
    """)

    for body, total in cursor.fetchall():
        print("  %s: %d preguntas" % (body, total))

    # Top leyes
    print("\n=== Top 10 Leyes por articulos preguntados ===\n")

    cursor.execute("""
    SELECT law_name, COUNT(*) as art_count, SUM(total_count) as total_q
    FROM article_exam_frequency
    WHERE total_count > 0
    GROUP BY law_id
    ORDER BY total_q DESC
    LIMIT 10
    """)

    for law, art_count, total_q in cursor.fetchall():
        print("  %s: %d articulos (%d preguntas)" % (law[:50], art_count, total_q))

if __name__ == "__main__":
    conn = sqlite3.connect(db_path)
    print("=== FASE 3: Actualizar ranking de articulos ===\n")

    updated = update_frequency_ranking(conn)

    print("\n=== Resumen ===")
    print("Articulos actualizados: %d" % updated)

    generate_report(conn)

    conn.close()
    print("\n✓ FASE 3 COMPLETADA - Ranking listo")

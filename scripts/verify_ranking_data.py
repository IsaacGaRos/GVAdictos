import sqlite3

db = sqlite3.connect(r"C:\Users\isaac\Desktop\GVAdictos\db\gvadicto.sqlite")
c = db.cursor()

print("=== Verificacion de datos ===\n")

print("1. Datos en exam_papers:")
c.execute("SELECT COUNT(*) FROM exam_papers WHERE fuente_path IS NOT NULL")
print("   Registros: %d" % c.fetchone()[0])

print("\n2. Datos en exam_questions:")
c.execute("SELECT COUNT(*) FROM exam_questions")
print("   Registros: %d" % c.fetchone()[0])

print("\n3. Datos en exam_question_article_links:")
c.execute("SELECT COUNT(*) FROM exam_question_article_links")
print("   Registros: %d" % c.fetchone()[0])

print("\n4. Datos en article_exam_frequency:")
c.execute("SELECT COUNT(*) FROM article_exam_frequency")
count = c.fetchone()[0]
print("   Registros totales: %d" % count)

c.execute("SELECT COUNT(*) FROM article_exam_frequency WHERE total_count > 0")
print("   Registros con total_count > 0: %d" % c.fetchone()[0])

print("\n5. Top 5 articulos (si existen):")
c.execute("""
SELECT article_ref, law_name, total_count
FROM article_exam_frequency
WHERE total_count > 0
ORDER BY total_count DESC
LIMIT 5
""")
results = c.fetchall()
if results:
    for art, law, cnt in results:
        print("   %s - %s : %d" % (art, law[:40] if law else "?", cnt))
else:
    print("   Sin datos")

print("\n6. Intentando consulta de get_top_exam_articles():")
try:
    rows = c.execute("""
    SELECT aef.article_ref, aef.total_count, aef.exam_sources,
           aef.law_name, l.name AS law_full, a.title
    FROM article_exam_frequency aef
    LEFT JOIN articles a ON a.id = aef.article_id
    LEFT JOIN laws l ON l.id = aef.law_id
    WHERE aef.article_id IS NOT NULL
    ORDER BY aef.total_count DESC
    LIMIT 5
    """).fetchall()
    print("   Resultados: %d" % len(rows))
    if rows:
        for r in rows:
            print("   %s - %s" % (r[0], r[3][:40] if r[3] else "?"))
except Exception as e:
    print("   ERROR: %s" % str(e))

db.close()

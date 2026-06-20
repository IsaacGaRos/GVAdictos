import sqlite3
db = sqlite3.connect(r"C:\Users\isaac\Desktop\GVAdictos\db\gvadicto.sqlite")
c = db.cursor()

for tbl in ["exam_papers", "exam_questions", "exam_question_options",
            "exam_question_links", "exam_question_article_links",
            "article_exam_frequency", "articles", "laws"]:
    print("\n=== %s ===" % tbl)
    try:
        c.execute("PRAGMA table_info(%s)" % tbl)
        for col in c.fetchall():
            print("  %s (%s)" % (col[1], col[2]))
        c.execute("SELECT COUNT(*) FROM %s" % tbl)
        print("  -> filas: %d" % c.fetchone()[0])
    except Exception as e:
        print("  ERROR: %s" % e)

# Muestra de articles para ver como referencian ley+articulo
print("\n=== muestra articles ===")
c.execute("SELECT id, law_id, article_ref, title FROM articles LIMIT 3")
for r in c.fetchall():
    print(" ", r)

db.close()

import sqlite3, io, sys, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
db = sqlite3.connect(r"C:\Users\isaac\Desktop\GVAdictos\db\gvadicto.sqlite")
db.row_factory = sqlite3.Row

print("=== Conteos ===")
for t in ["exam_papers", "exam_questions", "exam_question_options",
          "exam_question_links", "article_exam_frequency"]:
    print("  %s: %d" % (t, db.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]))

print("\n=== Top 20 articulos (article_exam_frequency) ===")
rows = db.execute("""
    SELECT aef.article_ref, aef.law_name, aef.total_count, aef.exam_sources
    FROM article_exam_frequency aef
    ORDER BY aef.total_count DESC, aef.law_name LIMIT 20
""").fetchall()
for r in rows:
    print("  %3d x  Art.%s  %s  [%s]" % (
        r["total_count"], r["article_ref"], r["law_name"][:45],
        ",".join(json.loads(r["exam_sources"]))))

print("\n=== Prueba query EXACTA de la UI get_top_exam_articles ===")
try:
    rows = db.execute("""
        SELECT aef.article_ref, aef.total_count, aef.exam_sources,
               aef.law_name, l.name AS law_full, a.title
        FROM article_exam_frequency aef
        LEFT JOIN articles a ON a.id = aef.article_id
        LEFT JOIN laws l ON l.id = aef.law_id
        WHERE aef.article_id IS NOT NULL
        ORDER BY aef.total_count DESC
        LIMIT 30
    """).fetchall()
    print("  -> filas devueltas: %d" % len(rows))
    if rows:
        print("  primera:", dict(rows[0]))
except Exception as e:
    print("  EXCEPTION:", e)

print("\n=== Vinculacion por ley (top) ===")
rows = db.execute("""
    SELECT l.name, COUNT(DISTINCT eql.exam_question_id) c
    FROM exam_question_links eql JOIN laws l ON l.id=eql.law_id
    GROUP BY eql.law_id ORDER BY c DESC LIMIT 12
""").fetchall()
for r in rows:
    print("  %2d preguntas -> %s" % (r["c"], r["name"][:55]))

db.close()

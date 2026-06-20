import sqlite3

db = sqlite3.connect(r"C:\Users\isaac\Desktop\GVAdictos\db\gvadicto.sqlite")
c = db.cursor()

print("Esquema article_exam_frequency:")
c.execute("PRAGMA table_info(article_exam_frequency)")
for col in c.fetchall():
    print("  %s (%s)" % (col[1], col[2]))

print("\nDatos:")
c.execute("SELECT COUNT(*) FROM article_exam_frequency")
print("Registros: %d" % c.fetchone()[0])

db.close()

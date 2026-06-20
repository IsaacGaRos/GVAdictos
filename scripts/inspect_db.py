import sqlite3

db_path = r"C:\Users\isaac\Desktop\GVAdictos\db\gvadicto.sqlite"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=== Esquema de tabla laws ===")
cursor.execute("PRAGMA table_info(laws)")
for col in cursor.fetchall():
    print("%s (%s)" % (col[1], col[2]))

print("\n=== Datos de ejemplo ===")
cursor.execute("SELECT * FROM laws LIMIT 1")
row = cursor.fetchone()
if row:
    cols = [d[0] for d in cursor.description]
    for i, col in enumerate(cols):
        print("%s: %s" % (col, str(row[i])[:80]))

cursor.execute("SELECT COUNT(*) FROM articles")
print("\nTotal articulos: %d" % cursor.fetchone()[0])

cursor.execute("SELECT COUNT(*) FROM exam_papers WHERE fuente_path IS NOT NULL")
print("Total examenes: %d" % cursor.fetchone()[0])

conn.close()

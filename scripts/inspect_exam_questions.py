import sqlite3

db_path = r"C:\Users\isaac\Desktop\GVAdictos\db\gvadicto.sqlite"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=== Esquema de exam_questions ===")
cursor.execute("PRAGMA table_info(exam_questions)")
for col in cursor.fetchall():
    print("%s (%s)" % (col[1], col[2]))

print("\nDatos existentes:")
cursor.execute("SELECT COUNT(*) FROM exam_questions")
print("Total registros: %d" % cursor.fetchone()[0])

cursor.execute("SELECT id, exam_paper_id, question_number, question_text FROM exam_questions LIMIT 2")
for row in cursor.fetchall():
    print("  ID %d: paper %d, pregunta %d, texto: %s..." % (row[0], row[1], row[2], row[3][:50]))

conn.close()

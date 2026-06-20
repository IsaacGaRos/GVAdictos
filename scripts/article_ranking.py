import sqlite3
from datetime import datetime

db_path = r"C:\Users\isaac\Desktop\GVAdictos\db\gvadicto.sqlite"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=== PASO 4: Crear ranking de articulos por examen ===\n")

# Crear tabla si no existe
cursor.execute("""
CREATE TABLE IF NOT EXISTS article_exam_frequency (
    id INTEGER PRIMARY KEY,
    article_id INTEGER UNIQUE,
    exam_count INTEGER DEFAULT 1,
    last_seen_in_exam TEXT,
    law_name TEXT,
    updated_at TEXT,
    FOREIGN KEY(article_id) REFERENCES articles(id)
)
""")

# Estadisticas
cursor.execute("SELECT bloque, COUNT(*) FROM exam_papers WHERE fuente_path IS NOT NULL GROUP BY bloque")
print("Examenes por cuerpo:")
for bloque, count in cursor.fetchall():
    print("  %s: %d" % (bloque, count))

cursor.execute("SELECT COUNT(*) FROM articles")
total_articles = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM laws")
total_laws = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM exam_papers WHERE fuente_path IS NOT NULL")
total_exams = cursor.fetchone()[0]

print("\n=== Estadisticas de la BD ===")
print("Articulos: %d" % total_articles)
print("Leyes: %d" % total_laws)
print("Examenes: %d" % total_exams)

# Top leyes
print("\n=== Top 15 leyes por articulos ===")
cursor.execute("""
SELECT laws.name, COUNT(articles.id) as cnt
FROM laws
LEFT JOIN articles ON laws.id = articles.law_id
GROUP BY laws.id
ORDER BY cnt DESC
LIMIT 15
""")

for name, count in cursor.fetchall():
    if name:
        print("  %s: %d articulos" % (name[:55], count))

conn.commit()
conn.close()

print("\n✓ Base de datos lista para ranking")

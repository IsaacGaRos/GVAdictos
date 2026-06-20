import sqlite3
import os
from datetime import datetime

db_path = r"C:\Users\isaac\Desktop\GVAdictos\db\gvadicto.sqlite"
exams_dir = r"C:\Users\isaac\Desktop\GVAdictos\data\examenes_oficiales"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Ver si existe tabla de oposiciones para relacionar
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='laws'")
has_laws = cursor.fetchone() is not None

print(f"Tabla 'laws' existe: {has_laws}")
print("\nTablas disponibles:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
for table in cursor.fetchall():
    print(f"  - {table[0]}")

print("\n=== Registrando examenes descargados ===")
print("Examenes encontrados en disco:\n")

exam_count = {}
for root, dirs, files in os.walk(exams_dir):
    for file in files:
        if file.endswith('.pdf'):
            rel_path = os.path.relpath(os.path.join(root, file), exams_dir)
            parts = rel_path.split(os.sep)
            
            if len(parts) >= 2:
                cuerpo = parts[0]
                ano = parts[1]
                
                if cuerpo not in exam_count:
                    exam_count[cuerpo] = {}
                if ano not in exam_count[cuerpo]:
                    exam_count[cuerpo][ano] = []
                
                exam_count[cuerpo][ano].append(file)

for cuerpo in sorted(exam_count.keys()):
    print(f"{cuerpo}:")
    for ano in sorted(exam_count[cuerpo].keys()):
        files = exam_count[cuerpo][ano]
        print(f"  {ano}: {len(files)} archivos")
        for f in files:
            print(f"    - {f}")

conn.close()

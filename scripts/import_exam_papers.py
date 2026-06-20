import sqlite3
import os
from datetime import datetime

db_path = r"C:\Users\isaac\Desktop\GVAdictos\db\gvadicto.sqlite"
exams_dir = r"C:\Users\isaac\Desktop\GVAdictos\data\examenes_oficiales"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=== Importando examenes ===\n")

# Mapping convocatorias
convocatoria_map = {
    "primer_ejercicio_respuestas": "1/24",
    "convocatoria_15_22": "15/22",
    "conv_3_4_22": "3/22",
    "conv_73_74_18": "73/18",
    "conv_154_155_18": "154/18",
    "conv_69_70": "69/18",
    "covid_convocatoria_71_18": "71/18",
    "examen_A2_respuestas": "24/24"
}

imported = 0
for root, dirs, files in os.walk(exams_dir):
    for file in files:
        if file.endswith('.pdf'):
            rel_path = os.path.relpath(os.path.join(root, file), exams_dir)
            parts = rel_path.split(os.sep)
            
            if len(parts) >= 2:
                cuerpo = parts[0]
                ano = int(parts[1])
                base_name = os.path.splitext(file)[0]
                convocatoria = convocatoria_map.get(base_name, "Unknown")
                
                if 'respuesta' in file.lower() or 'plantilla' in file.lower():
                    fase = 'answer_key'
                elif 'examen' in file.lower():
                    fase = 'exam_paper'
                else:
                    fase = 'unknown'
                
                try:
                    cursor.execute("""
                    INSERT OR IGNORE INTO exam_papers
                    (convocatoria, anio, bloque, fase, fuente_path, estado, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (convocatoria, ano, cuerpo, fase, rel_path, 'imported', datetime.now().isoformat()))
                    imported += 1
                    print("[OK] %s/%s/%s" % (cuerpo, ano, file))
                except Exception as e:
                    print("[ERR] %s: %s" % (file, str(e)))

conn.commit()

cursor.execute("SELECT bloque, COUNT(*) FROM exam_papers WHERE fuente_path IS NOT NULL GROUP BY bloque")
print("\n=== Resumen ===")
for bloque, count in cursor.fetchall():
    print("%s: %d examenes" % (bloque, count))

cursor.execute("SELECT COUNT(*) FROM exam_papers WHERE fuente_path IS NOT NULL")
total = cursor.fetchone()[0]
print("Total: %d examenes en BD" % total)

conn.close()

import sqlite3
import json

db = sqlite3.connect(r"C:\Users\isaac\Desktop\GVAdictos\db\gvadicto.sqlite")
c = db.cursor()

print("=== Verificacion de exam_sources ===\n")

c.execute("SELECT article_ref, total_count, exam_sources FROM article_exam_frequency ORDER BY total_count DESC LIMIT 5")
for ref, cnt, sources in c.fetchall():
    print("Art. %s: %d apariciones" % (ref, cnt))
    print("  exam_sources type: %s" % type(sources))
    print("  exam_sources value: %s" % str(sources)[:80])

    # Intentar parse
    try:
        if sources:
            parsed = json.loads(sources)
            print("  parsed OK: %s" % str(parsed)[:60])
        else:
            print("  exam_sources es None/NULL")
    except Exception as e:
        print("  ERROR parsing: %s" % str(e))
    print()

db.close()

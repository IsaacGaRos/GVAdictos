import sqlite3, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
db = sqlite3.connect(r"C:\Users\isaac\Desktop\GVAdictos\db\gvadicto.sqlite")
db.row_factory = sqlite3.Row
for r in db.execute("SELECT id, name FROM laws ORDER BY id"):
    n = db.execute("SELECT COUNT(*) FROM articles WHERE law_id=?", (r["id"],)).fetchone()[0]
    print("%3d | %3d arts | %s" % (r["id"], n, r["name"]))
db.close()

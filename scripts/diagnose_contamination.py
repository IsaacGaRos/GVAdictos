import sqlite3

db = sqlite3.connect(r"C:\Users\isaac\Desktop\GVAdictos\db\gvadicto.sqlite")
db.row_factory = sqlite3.Row
c = db.cursor()

print("=== TODOS los exam_papers en BD ===\n")
rows = c.execute("""
    SELECT id, oposicion_id, convocatoria, anio, bloque, fase, fuente_path
    FROM exam_papers ORDER BY id
""").fetchall()
for r in rows:
    print("ID %d | conv=%s | anio=%s | bloque=%s | fase=%s" % (
        r["id"], r["convocatoria"], r["anio"], r["bloque"], r["fase"]))
    print("       path: %s" % (r["fuente_path"] or "—"))

print("\n=== De donde vienen las exam_questions (origen real) ===\n")
rows = c.execute("""
    SELECT ep.id, ep.convocatoria, ep.bloque, ep.fuente_path, COUNT(eq.id) as nq
    FROM exam_papers ep
    JOIN exam_questions eq ON eq.exam_paper_id = ep.id
    GROUP BY ep.id
    ORDER BY nq DESC
""").fetchall()
for r in rows:
    print("paper %d (%s/%s): %d preguntas | %s" % (
        r["id"], r["convocatoria"], r["bloque"], r["nq"], r["fuente_path"] or "—"))

print("\n=== Clasificacion OFICIAL vs SIMULACRO ACADEMIA ===\n")
rows = c.execute("SELECT fuente_path, COUNT(*) FROM exam_questions eq JOIN exam_papers ep ON ep.id=eq.exam_paper_id GROUP BY ep.fuente_path").fetchall()
oficial = 0
simulacro = 0
for r in rows:
    path = (r[0] or "").lower()
    n = r[1]
    if "simulacro" in path or "tsgv" in path or "eracef" in path or "cef" in path:
        simulacro += n
        tag = "SIMULACRO ACADEMIA"
    else:
        oficial += n
        tag = "oficial?"
    print("  [%s] %s -> %d preguntas" % (tag, r[0], n))

print("\nTotal preguntas de SIMULACRO academia: %d" % simulacro)
print("Total preguntas potencialmente oficiales: %d" % oficial)

db.close()

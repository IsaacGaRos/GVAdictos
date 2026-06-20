"""Prueba de inferencia articulo: para preguntas con ley pero sin articulo
explicito, puntua el texto de la respuesta correcta (+enunciado) contra los
articulos de esa ley y elige el mejor. Imprime para juzgar calidad."""
import sqlite3, io, sys, re, unicodedata, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

DB = r"C:\Users\isaac\Desktop\GVAdictos\db\gvadicto.sqlite"

STOP = set("de la el en y a los las del un una que se por para con su sus al lo "
           "como o e segun sera son ser haya este esta estas estos no si mas "
           "cuando donde cual cuales sobre entre desde hasta ante tras".split())


def norm(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z0-9ñ ]", " ", s)


def toks(s):
    return [t for t in norm(s).split() if len(t) > 3 and t not in STOP]


db = sqlite3.connect(DB)
db.row_factory = sqlite3.Row

# articulos por ley con idf
def build_law_articles(law_id):
    arts = db.execute("SELECT id, article_ref, title, text FROM articles WHERE law_id=?",
                      (law_id,)).fetchall()
    docs = []
    df = {}
    for a in arts:
        tk = set(toks((a["title"] or "") + " " + (a["text"] or "")))
        docs.append((a, tk))
        for t in tk:
            df[t] = df.get(t, 0) + 1
    N = len(docs) or 1
    idf = {t: math.log(1 + N / c) for t, c in df.items()}
    return docs, idf


def score(qtokens, atokens, idf):
    if not atokens:
        return 0.0
    s = sum(idf.get(t, 0) for t in qtokens if t in atokens)
    return s / math.sqrt(len(atokens))


# preguntas con ley pero SIN articulo (link a nivel ley)
rows = db.execute("""
    SELECT eq.id qid, eq.enunciado, eq.respuesta_oficial, eql.law_id, l.name law_name
    FROM exam_question_links eql
    JOIN exam_questions eq ON eq.id=eql.exam_question_id
    JOIN laws l ON l.id=eql.law_id
    WHERE eql.article_id IS NULL
    ORDER BY eql.law_id
""").fetchall()

print("Preguntas con ley sin articulo: %d\n" % len(rows))

cache = {}
shown = 0
for r in rows:
    lid = r["law_id"]
    if lid not in cache:
        cache[lid] = build_law_articles(lid)
    docs, idf = cache[lid]
    if not docs:
        continue
    # texto de la respuesta correcta
    opt = db.execute("SELECT texto FROM exam_question_options WHERE exam_question_id=? AND letra=?",
                     (r["qid"], r["respuesta_oficial"])).fetchone()
    qtext = (r["enunciado"] or "") + " " + (opt["texto"] if opt else "")
    qtok = set(toks(qtext))
    best = None; best_s = 0
    for a, atok in docs:
        sc = score(qtok, atok, idf)
        if sc > best_s:
            best_s = sc; best = a
    if shown < 18 and best:
        print("Q%d [%s] resp=%s  ->  Art.%s (score %.2f)" % (
            r["qid"], r["law_name"][:32], r["respuesta_oficial"],
            best["article_ref"], best_s))
        print("   ENUN: %s" % (r["enunciado"][:110]))
        print("   ART : %s | %s" % (best["article_ref"], (best["title"] or "")[:70]))
        shown += 1

db.close()

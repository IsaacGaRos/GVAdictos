"""Paso de inferencia: para preguntas con ley vinculada pero SIN articulo
explicito, infiere el articulo mas probable comparando el texto de la
respuesta correcta (+enunciado) con los articulos de esa ley.

Inserta links tipo 'articulo_inferido' (confianza baja, requiere revision).
Luego reconstruye article_exam_frequency con explicit_count e inferred_count.
"""
import sqlite3, re, unicodedata, math, json, sys, io
from datetime import datetime

DB = r"C:\Users\isaac\Desktop\GVAdictos\db\gvadicto.sqlite"
THRESHOLD = 1.5

STOP = set("de la el en y a los las del un una que se por para con su sus al lo "
           "como o e segun sera son ser haya este esta estas estos no si mas "
           "cuando donde cual cuales sobre entre desde hasta ante tras "
           "afirmacion opcion correcta incorrecta senale indique siguientes".split())


def norm(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z0-9ñ ]", " ", s)


def toks(s):
    return [t for t in norm(s).split() if len(t) > 3 and t not in STOP]


def build_law_articles(db, law_id):
    arts = db.execute(
        "SELECT id, article_ref, title, text FROM articles WHERE law_id=?",
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


def ensure_freq_columns(db):
    cols = [r["name"] for r in db.execute("PRAGMA table_info(article_exam_frequency)")]
    if "explicit_count" not in cols:
        db.execute("ALTER TABLE article_exam_frequency ADD COLUMN explicit_count INTEGER DEFAULT 0")
    if "inferred_count" not in cols:
        db.execute("ALTER TABLE article_exam_frequency ADD COLUMN inferred_count INTEGER DEFAULT 0")
    db.commit()


def run_inference(db):
    now = datetime.now().isoformat()
    # links a nivel ley (sin articulo) de examenes oficiales
    rows = db.execute("""
        SELECT eql.id link_id, eql.exam_question_id qid, eql.law_id,
               eq.enunciado, eq.respuesta_oficial
        FROM exam_question_links eql
        JOIN exam_questions eq ON eq.id=eql.exam_question_id
        JOIN exam_papers ep ON ep.id=eq.exam_paper_id
        WHERE eql.article_id IS NULL AND ep.fuente_tipo='oficial_gva'
    """).fetchall()

    cache = {}
    inferred = 0
    for r in rows:
        lid = r["law_id"]
        if lid not in cache:
            cache[lid] = build_law_articles(db, lid)
        docs, idf = cache[lid]
        if not docs:
            continue
        opt = db.execute(
            "SELECT texto FROM exam_question_options WHERE exam_question_id=? AND letra=?",
            (r["qid"], r["respuesta_oficial"])).fetchone()
        qtext = (r["enunciado"] or "") + " " + (opt["texto"] if opt else "")
        qtok = set(toks(qtext))
        best = None; best_s = 0.0
        for a, atok in docs:
            sc = score(qtok, atok, idf)
            if sc > best_s:
                best_s = sc; best = a
        if best and best_s >= THRESHOLD:
            # confianza normalizada en banda baja 0.30-0.60
            conf = round(min(0.60, 0.30 + best_s / 40.0), 2)
            db.execute("""
                INSERT INTO exam_question_links (exam_question_id, law_id, article_id,
                    tipo_relacion, mapping_basis, confianza, validation_status, created_at)
                VALUES (?,?,?,?,?,?,?,?)
            """, (r["qid"], lid, best["id"], "articulo_inferido",
                  "inferencia_texto_respuesta:score=%.2f" % best_s, conf,
                  "requiere_revision_humana", now))
            inferred += 1
    db.commit()
    return inferred


def rebuild_frequency(db):
    now = datetime.now().isoformat()
    db.execute("DELETE FROM article_exam_frequency")
    rows = db.execute("""
        SELECT eql.article_id,
               SUM(CASE WHEN eql.tipo_relacion='articulo_explicito' THEN 1 ELSE 0 END) expl,
               SUM(CASE WHEN eql.tipo_relacion='articulo_inferido'  THEN 1 ELSE 0 END) infe,
               COUNT(DISTINCT eql.exam_question_id) cnt
        FROM exam_question_links eql
        JOIN exam_questions eq ON eq.id=eql.exam_question_id
        JOIN exam_papers ep ON ep.id=eq.exam_paper_id
        WHERE eql.article_id IS NOT NULL AND ep.fuente_tipo='oficial_gva'
        GROUP BY eql.article_id
    """).fetchall()
    n = 0
    for r in rows:
        aid = r["article_id"]
        arow = db.execute(
            "SELECT a.article_ref, a.law_id, l.name FROM articles a "
            "JOIN laws l ON l.id=a.law_id WHERE a.id=?", (aid,)).fetchone()
        if not arow:
            continue
        srcs = db.execute("""
            SELECT DISTINCT ep.bloque || ' ' || ep.convocatoria
            FROM exam_question_links eql
            JOIN exam_questions eq ON eq.id=eql.exam_question_id
            JOIN exam_papers ep ON ep.id=eq.exam_paper_id
            WHERE eql.article_id=? AND ep.fuente_tipo='oficial_gva'
        """, (aid,)).fetchall()
        src_list = [s[0] for s in srcs]
        db.execute("""
            INSERT INTO article_exam_frequency (article_id, article_ref, law_id,
                law_name, total_count, explicit_count, inferred_count,
                exam_sources, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (aid, arow["article_ref"], arow["law_id"], arow["name"],
              r["cnt"], r["expl"], r["infe"],
              json.dumps(src_list, ensure_ascii=False), now, now))
        n += 1
    db.commit()
    return n


def main():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    ensure_freq_columns(db)
    inf = run_inference(db)
    n = rebuild_frequency(db)
    print("Articulos inferidos (links nuevos): %d" % inf)
    print("Articulos en ranking: %d" % n)
    expl = db.execute("SELECT COUNT(*) FROM article_exam_frequency WHERE explicit_count>0").fetchone()[0]
    print("  con al menos 1 explicito: %d" % expl)
    db.close()


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    main()

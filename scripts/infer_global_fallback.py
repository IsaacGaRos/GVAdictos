"""Segunda barrida: garantiza que TODA pregunta oficial tenga >=1 artículo.

Para cada pregunta sin ningún link a artículo, infiere el artículo más probable
contra TODO el articulado de la BD (índice invertido + idf). Inserta link
tipo='articulo_inferido_global' (confianza muy baja, requiere_revision_humana).

Luego reconstruye article_exam_frequency contando explícitos + inferidos.
Verifica el invariante: 0 preguntas oficiales sin artículo.
"""
import sqlite3, re, unicodedata, math, json, sys, io
from datetime import datetime

DB = r"C:\Users\isaac\Desktop\GVAdictos\db\gvadicto.sqlite"

STOP = set("de la el en y a los las del un una que se por para con su sus al lo "
           "como o e segun sera son ser haya este esta estas estos no si mas "
           "cuando donde cual cuales sobre entre desde hasta ante tras articulo "
           "afirmacion opcion correcta incorrecta senale indique siguientes "
           "acuerdo conformidad dispuesto previsto respecto relacion siguiente".split())


def norm(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z0-9ñ ]", " ", s)


def toks(s):
    return [t for t in norm(s).split() if len(t) > 3 and t not in STOP]


def build_global_index(db):
    arts = db.execute(
        "SELECT a.id, a.article_ref, a.law_id, l.name AS law_name, a.title, a.text "
        "FROM articles a JOIN laws l ON l.id=a.law_id").fetchall()
    docs = []                     # idx -> dict
    inv = {}                      # token -> list idx
    df = {}
    for idx, a in enumerate(arts):
        tk = set(toks((a["title"] or "") + " " + (a["text"] or "")))
        docs.append({"id": a["id"], "ref": a["article_ref"], "law_id": a["law_id"],
                     "law_name": a["law_name"], "tk": tk, "ntok": max(1, len(tk))})
        for t in tk:
            df[t] = df.get(t, 0) + 1
            inv.setdefault(t, []).append(idx)
    N = len(docs) or 1
    idf = {t: math.log(1 + N / c) for t, c in df.items()}
    return docs, inv, idf


def infer_one(qtokens, docs, inv, idf):
    # candidatos: artículos que comparten tokens (priorizando tokens raros)
    cand = {}
    rare = sorted(set(qtokens), key=lambda t: idf.get(t, 0), reverse=True)[:25]
    for t in rare:
        for idx in inv.get(t, []):
            cand[idx] = None
    best = None; best_s = 0.0
    qset = set(qtokens)
    for idx in cand:
        d = docs[idx]
        s = sum(idf.get(t, 0) for t in qset if t in d["tk"]) / math.sqrt(d["ntok"])
        if s > best_s:
            best_s = s; best = d
    return best, best_s


def rebuild_frequency(db):
    now = datetime.now().isoformat()
    db.execute("DELETE FROM article_exam_frequency")
    rows = db.execute("""
        SELECT eql.article_id,
            SUM(CASE WHEN eql.tipo_relacion='articulo_explicito' THEN 1 ELSE 0 END) expl,
            SUM(CASE WHEN eql.tipo_relacion LIKE 'articulo_inferido%' THEN 1 ELSE 0 END) infe,
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
        arow = db.execute("SELECT a.article_ref, a.law_id, l.name FROM articles a "
                          "JOIN laws l ON l.id=a.law_id WHERE a.id=?", (aid,)).fetchone()
        if not arow:
            continue
        srcs = db.execute("""
            SELECT DISTINCT ep.bloque || ' ' || ep.convocatoria
            FROM exam_question_links eql
            JOIN exam_questions eq ON eq.id=eql.exam_question_id
            JOIN exam_papers ep ON ep.id=eq.exam_paper_id
            WHERE eql.article_id=? AND ep.fuente_tipo='oficial_gva'""", (aid,)).fetchall()
        db.execute("""INSERT INTO article_exam_frequency (article_id, article_ref, law_id,
            law_name, total_count, explicit_count, inferred_count, exam_sources, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (aid, arow["article_ref"], arow["law_id"], arow["name"], r["cnt"], r["expl"],
             r["infe"], json.dumps([s[0] for s in srcs], ensure_ascii=False), now, now))
        n += 1
    db.commit()
    return n


def main():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    now = datetime.now().isoformat()

    pend = db.execute("""
        SELECT eq.id qid, eq.enunciado, eq.respuesta_oficial
        FROM exam_questions eq
        JOIN exam_papers ep ON ep.id=eq.exam_paper_id
        WHERE ep.fuente_tipo='oficial_gva'
          AND eq.id NOT IN (SELECT exam_question_id FROM exam_question_links
                            WHERE article_id IS NOT NULL)
    """).fetchall()
    print("Preguntas sin artículo (a resolver): %d" % len(pend))

    docs, inv, idf = build_global_index(db)
    print("Índice global: %d artículos" % len(docs))

    done = 0
    for r in pend:
        opt = db.execute("SELECT texto FROM exam_question_options WHERE exam_question_id=? AND letra=?",
                         (r["qid"], r["respuesta_oficial"])).fetchone()
        qtext = (r["enunciado"] or "") + " " + (opt["texto"] if opt else "")
        qtok = toks(qtext)
        if not qtok:
            continue
        best, s = infer_one(qtok, docs, inv, idf)
        if best:
            conf = round(min(0.25, 0.10 + s / 80.0), 2)
            db.execute("""INSERT INTO exam_question_links (exam_question_id, law_id, article_id,
                tipo_relacion, mapping_basis, confianza, validation_status, created_at)
                VALUES (?,?,?,?,?,?,?,?)""",
                (r["qid"], best["law_id"], best["id"], "articulo_inferido_global",
                 "global_fallback:score=%.2f" % s, conf, "requiere_revision_humana", now))
            done += 1
    db.commit()
    print("Inferidos globalmente: %d" % done)

    nfreq = rebuild_frequency(db)
    print("Artículos en ranking: %d" % nfreq)

    # invariante
    left = db.execute("""
        SELECT COUNT(*) FROM exam_questions eq
        JOIN exam_papers ep ON ep.id=eq.exam_paper_id
        WHERE ep.fuente_tipo='oficial_gva' AND eq.anulada=0
          AND eq.id NOT IN (SELECT exam_question_id FROM exam_question_links WHERE article_id IS NOT NULL)
    """).fetchone()[0]
    tot = db.execute("""SELECT COUNT(*) FROM exam_questions eq JOIN exam_papers ep ON ep.id=eq.exam_paper_id
                        WHERE ep.fuente_tipo='oficial_gva'""").fetchone()[0]
    print("\nINVARIANTE: preguntas oficiales=%d, sin artículo=%d" % (tot, left))
    db.close()


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    main()

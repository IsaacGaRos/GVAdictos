import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, os.path.abspath("."))

from app import (get_exam_cuerpos, get_top_exam_articles,
                 get_top_exam_laws, get_article_study_payload)

print("Cuerpos:", get_exam_cuerpos())

print("\n-- Top leyes (Todos) --")
for l in get_top_exam_laws(limit=8):
    print("  %2d  %s" % (l["n_preguntas"], l["law_full"][:55]))

print("\n-- Top articulos (A1-01) --")
arts = get_top_exam_articles(limit=10, cuerpo="A1-01")
for a in arts:
    print("  expl=%d inf=%d tot=%d  Art.%s %s" % (
        a["explicit_count"], a["inferred_count"], a["total_count"],
        a["article_ref"], (a["law_full"] or "")[:40]))

print("\n-- Estudiar 1 articulo --")
if arts:
    p = get_article_study_payload(arts[0]["article_id"])
    if p:
        print("  Articulo:", p["article"]["law_full"], "Art.", p["article"]["article_ref"])
        print("  Texto (80):", (p["article"]["text"] or "")[:80])
        print("  Preguntas vinculadas:", len(p["questions"]))

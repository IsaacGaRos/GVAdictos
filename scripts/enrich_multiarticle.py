"""Barrida multi-artículo: una pregunta puede preguntar por VARIOS artículos.

Para cada pregunta oficial, escanea enunciado + TODAS las opciones y extrae
todas las referencias explícitas a artículos (sueltos y rangos). Si la pregunta
cita UNA sola ley (de la BD), mapea cada nº de artículo a esa ley y añade los
links 'articulo_explicito' que falten. Alta precisión (solo ley única).

Se ejecuta ANTES de la inferencia (que solo rellena preguntas con 0 artículos).
"""
import os, sys, re, sqlite3
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exam_linker import (build_law_index, NUM_YEAR_RE, _strip, _find_special,
                         ART_RANGE_RE, ART_SINGLE_RE)

DB = r"C:\Users\isaac\Desktop\GVAdictos\db\gvadicto.sqlite"


def all_article_refs(text):
    """Todos los nº de artículo citados (rangos expandidos + sueltos), únicos."""
    refs = []
    for a, b in ART_RANGE_RE.findall(text):
        ai, bi = int(a), int(b)
        if 0 < ai <= bi <= ai + 60:
            refs.extend(str(x) for x in range(ai, bi + 1))
    for m in ART_SINGLE_RE.findall(text):
        refs.append(str(int(m)))
    return list(dict.fromkeys(refs))


def laws_in_text(text, index):
    """Conjunto de law_ids citados explícitamente (núm/año + nombres especiales)."""
    ids = set()
    for num, year in NUM_YEAR_RE.findall(text):
        c = index["by_numyear"].get((num, year))
        if c:
            for law, _ in c:
                ids.add(law["id"])
    sp = _find_special(_strip(text), index)
    if sp:
        ids.add(sp[0]["id"])
    return ids


def main():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    laws = [dict(r) for r in db.execute("SELECT id, name FROM laws")]
    index = build_law_index(laws)
    now = datetime.now().isoformat()

    qs = db.execute("""
        SELECT eq.id qid, eq.enunciado
        FROM exam_questions eq JOIN exam_papers ep ON ep.id=eq.exam_paper_id
        WHERE ep.fuente_tipo='oficial_gva' AND eq.anulada=0
    """).fetchall()

    added = 0
    q_multi = 0
    for r in qs:
        opts = db.execute("SELECT texto FROM exam_question_options WHERE exam_question_id=?",
                          (r["qid"],)).fetchall()
        full = (r["enunciado"] or "") + " " + " ".join(o["texto"] or "" for o in opts)
        cited_laws = laws_in_text(full, index)
        if len(cited_laws) != 1:
            continue  # ambiguo o sin ley -> lo dejamos a inferencia
        law_id = next(iter(cited_laws))
        refs = all_article_refs(full)
        if len(refs) < 1:
            continue
        # links ya existentes para esta pregunta
        existing = set(x[0] for x in db.execute(
            "SELECT article_id FROM exam_question_links WHERE exam_question_id=? AND article_id IS NOT NULL",
            (r["qid"],)).fetchall())
        new_for_q = 0
        for ref in refs:
            a = db.execute("SELECT id FROM articles WHERE law_id=? AND article_ref=?",
                           (law_id, ref)).fetchone()
            if not a or a["id"] in existing:
                continue
            db.execute("""INSERT INTO exam_question_links (exam_question_id, law_id, article_id,
                tipo_relacion, mapping_basis, confianza, validation_status, created_at)
                VALUES (?,?,?,?,?,?,?,?)""",
                (r["qid"], law_id, a["id"], "articulo_explicito",
                 "multiart_enriquecido", 0.85, "pendiente_revision_humana", now))
            existing.add(a["id"])
            added += 1
            new_for_q += 1
        if new_for_q and (len(existing) > 1):
            q_multi += 1
    db.commit()
    print("Links explícitos añadidos (multi-artículo): %d" % added)
    print("Preguntas que ahora referencian >1 artículo: %d" % q_multi)
    db.close()


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    main()

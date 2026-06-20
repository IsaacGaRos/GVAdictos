"""Reconstruye los datos de examenes OFICIALES desde cero, eliminando la
contaminacion previa (simulacros de academia / matching por keywords).

Pasos:
 1. Limpia tablas derivadas (questions, options, links, frequency, tabla basura).
 2. Asegura columna exam_papers.fuente_tipo y registra los papers oficiales.
 3. Parsea cada plantilla oficial -> preguntas + opciones + respuesta_oficial.
 4. Vincula pregunta -> ley (cita explicita) -> articulo (explicito) en
    exam_question_links, con confianza y validation_status.
 5. Reconstruye article_exam_frequency (solo articulos explicitos, oficial).
"""
import os
import sys
import json
import sqlite3
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_official_exam import parse_exam
from exam_linker import build_law_index, link_question

DB = r"C:\Users\isaac\Desktop\GVAdictos\db\gvadicto.sqlite"
EXROOT = r"C:\Users\isaac\Desktop\GVAdictos\data\examenes_oficiales"

# Catalogo de plantillas oficiales a importar.
# (cuerpo, convocatoria, anio, parte_label, ruta_relativa, num_preguntas_esperado)
OFFICIAL = [
    ("A1-01", "1/25", 2025, "1er ejercicio - 1a parte (teorico)",
     r"A1-01\2025\1-25_primera_parte_cuestionario_plantilla.pdf", 160),
    ("A1-01", "1/25", 2025, "1er ejercicio - 2a parte (teorico-practico)",
     r"A1-01\2025\1-25_segunda_parte_cuestionario_plantilla.pdf", 40),
    ("C1-01", "64/25", 2025, "1er ejercicio (test teorico)",
     r"C1-01\2025\64-25_TL_cuestionario_plantilla.pdf", 110),
]


def ensure_schema(conn):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(exam_papers)")]
    if "fuente_tipo" not in cols:
        conn.execute("ALTER TABLE exam_papers ADD COLUMN fuente_tipo TEXT")
    if "parte" not in cols:
        conn.execute("ALTER TABLE exam_papers ADD COLUMN parte TEXT")
    # tabla basura de la sesion anterior
    conn.execute("DROP TABLE IF EXISTS exam_question_article_links")
    conn.commit()


def clean_derived(conn):
    conn.execute("DELETE FROM exam_question_links")
    conn.execute("DELETE FROM exam_question_options")
    conn.execute("DELETE FROM exam_questions")
    conn.execute("DELETE FROM article_exam_frequency")
    # eliminar fila corrupta (path no valido / convocatoria '2025/2026')
    conn.execute("DELETE FROM exam_papers WHERE fuente_path IS NULL OR fuente_path=''")
    conn.execute("DELETE FROM exam_papers WHERE convocatoria='2025/2026'")
    conn.commit()


def upsert_paper(conn, cuerpo, conv, anio, parte, rel_path):
    now = datetime.now().isoformat()
    row = conn.execute(
        "SELECT id FROM exam_papers WHERE bloque=? AND convocatoria=? AND anio=? AND parte=?",
        (cuerpo, conv, anio, parte),
    ).fetchone()
    if row:
        pid = row[0]
        conn.execute(
            "UPDATE exam_papers SET fuente_path=?, fuente_tipo='oficial_gva', "
            "fase=?, estado='importado', updated_at=? WHERE id=?",
            (rel_path, parte, now, pid),
        )
    else:
        cur = conn.execute(
            "INSERT INTO exam_papers (convocatoria, anio, bloque, parte, fase, "
            "fuente_path, fuente_tipo, estado, validation_status, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?, 'oficial_gva', 'importado', 'oficial', ?, ?)",
            (conv, anio, cuerpo, parte, parte, rel_path, now, now),
        )
        pid = cur.lastrowid
    return pid


def import_paper(conn, index, pid, cuerpo, conv, anio, parte, abs_path, expected):
    res = parse_exam(abs_path, max_questions=expected)
    qs = res["questions"]
    now = datetime.now().isoformat()
    inserted = 0
    linked_law = 0
    linked_art = 0
    for q in qs:
        cur = conn.execute(
            "INSERT INTO exam_questions (exam_paper_id, numero, enunciado, "
            "respuesta_oficial, anulada, validation_status, created_at) "
            "VALUES (?,?,?,?,0,?,?)",
            (pid, q["numero"], q["enunciado"], q.get("respuesta"),
             "pendiente_revision", now),
        )
        qid = cur.lastrowid
        inserted += 1
        for L in "ABCD":
            txt = q["opciones"].get(L)
            if txt is None:
                continue
            es_corr = 1 if q.get("respuesta") == L else 0
            conn.execute(
                "INSERT INTO exam_question_options (exam_question_id, letra, texto, "
                "es_correcta, created_at) VALUES (?,?,?,?,?)",
                (qid, L, txt, es_corr, now),
            )
        # Vinculacion
        link = link_question(q["enunciado"], q["opciones"], index)
        if link["law_id"]:
            linked_law += 1
            law_id = link["law_id"]
            arts = link["articles"]
            if arts:
                # localizar article_id por (law_id, article_ref)
                any_art = False
                for ref in arts:
                    arow = conn.execute(
                        "SELECT id FROM articles WHERE law_id=? AND article_ref=?",
                        (law_id, ref),
                    ).fetchone()
                    if arow:
                        conn.execute(
                            "INSERT INTO exam_question_links (exam_question_id, law_id, "
                            "article_id, tipo_relacion, mapping_basis, confianza, "
                            "validation_status, created_at) VALUES (?,?,?,?,?,?,?,?)",
                            (qid, law_id, arow[0], "articulo_explicito",
                             link["basis"], link["confianza"],
                             "pendiente_revision_humana", now),
                        )
                        any_art = True
                if any_art:
                    linked_art += 1
                else:
                    # ley sí, articulo citado pero no esta en BD -> link a nivel ley
                    conn.execute(
                        "INSERT INTO exam_question_links (exam_question_id, law_id, "
                        "article_id, tipo_relacion, mapping_basis, confianza, "
                        "validation_status, created_at) VALUES (?,?,NULL,?,?,?,?,?)",
                        (qid, law_id, "ley_explicita",
                         link["basis"] + "|art_no_en_bd:" + ",".join(arts),
                         link["confianza"], "pendiente_revision_humana", now),
                    )
            else:
                conn.execute(
                    "INSERT INTO exam_question_links (exam_question_id, law_id, "
                    "article_id, tipo_relacion, mapping_basis, confianza, "
                    "validation_status, created_at) VALUES (?,?,NULL,?,?,?,?,?)",
                    (qid, law_id, "ley_explicita", link["basis"],
                     link["confianza"], "pendiente_revision_humana", now),
                )
    conn.commit()
    return inserted, linked_law, linked_art


def rebuild_frequency(conn):
    """article_exam_frequency: solo articulos explicitos de examenes oficiales."""
    now = datetime.now().isoformat()
    rows = conn.execute(
        """
        SELECT eql.article_id,
               COUNT(DISTINCT eql.exam_question_id) AS cnt
        FROM exam_question_links eql
        JOIN exam_questions eq ON eq.id = eql.exam_question_id
        JOIN exam_papers ep ON ep.id = eq.exam_paper_id
        WHERE eql.article_id IS NOT NULL
          AND ep.fuente_tipo = 'oficial_gva'
        GROUP BY eql.article_id
        """
    ).fetchall()
    for article_id, cnt in rows:
        arow = conn.execute(
            "SELECT a.article_ref, a.law_id, l.name FROM articles a "
            "JOIN laws l ON l.id=a.law_id WHERE a.id=?",
            (article_id,),
        ).fetchone()
        if not arow:
            continue
        article_ref, law_id, law_name = arow
        # fuentes (cuerpo conv/anio) de los examenes donde aparece
        srcs = conn.execute(
            """
            SELECT DISTINCT ep.bloque || ' ' || ep.convocatoria
            FROM exam_question_links eql
            JOIN exam_questions eq ON eq.id=eql.exam_question_id
            JOIN exam_papers ep ON ep.id=eq.exam_paper_id
            WHERE eql.article_id=? AND ep.fuente_tipo='oficial_gva'
            """,
            (article_id,),
        ).fetchall()
        src_list = [s[0] for s in srcs]
        conn.execute(
            "INSERT INTO article_exam_frequency (article_id, article_ref, law_id, "
            "law_name, total_count, exam_sources, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (article_id, article_ref, law_id, law_name, cnt,
             json.dumps(src_list, ensure_ascii=False), now, now),
        )
    conn.commit()
    return len(rows)


def main():
    conn = sqlite3.connect(DB)
    laws = [dict(zip(["id", "name"], r))
            for r in conn.execute("SELECT id, name FROM laws")]
    index = build_law_index(laws)

    ensure_schema(conn)
    clean_derived(conn)

    tot_q = tot_law = tot_art = 0
    for cuerpo, conv, anio, parte, rel, expected in OFFICIAL:
        abs_path = os.path.join(EXROOT, rel)
        if not os.path.exists(abs_path):
            print("FALTA: %s" % rel)
            continue
        pid = upsert_paper(conn, cuerpo, conv, anio, parte, rel)
        ins, ll, la = import_paper(conn, index, pid, cuerpo, conv, anio,
                                   parte, abs_path, expected)
        tot_q += ins; tot_law += ll; tot_art += la
        print("[%s %s %s] preguntas=%d  con_ley=%d  con_art=%d" %
              (cuerpo, conv, parte[:20], ins, ll, la))

    nfreq = rebuild_frequency(conn)

    print("\n=== TOTALES ===")
    print("Preguntas importadas: %d" % tot_q)
    print("Con ley vinculada:    %d" % tot_law)
    print("Con articulo explicito (preguntas): %d" % tot_art)
    print("Articulos en ranking (article_exam_frequency): %d" % nfreq)

    conn.close()


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    main()

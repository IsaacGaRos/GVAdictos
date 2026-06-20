"""Vincula preguntas de examen oficial -> ley -> articulo.

- Detecta la ley citada en el enunciado mediante numero/anio (p.ej. "Ley 39/2015",
  "Ley Organica 2/1987", "Real Decreto Legislativo 5/2015", "Reglamento (UE) 2016/679")
  y mediante nombres especiales (Codigo Civil, Constitucion, TFUE, TUE, TREBEP,
  Estatuto de Autonomia, Ley Organica del Poder Judicial, Reglamento de Les Corts).
- Detecta el/los articulo(s) citados explicitamente ("articulo 6", "articulos 288 a 292").
- Devuelve (law_id, article_ref_list, confianza, basis).
"""
import re
import unicodedata


def _strip(s):
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower()


# Numero/anio de una norma a partir de texto: captura "N/AAAA"
NUM_YEAR_RE = re.compile(r"\b(\d{1,4})/(\d{4})\b")

# Articulos explicitos
ART_SINGLE_RE = re.compile(r"\bart[ií]culos?\.?\s+(\d{1,3})(?:\s*\.\s*\d+)?\b", re.IGNORECASE)
ART_RANGE_RE = re.compile(r"\bart[ií]culos?\.?\s+(\d{1,3})\s+a\s+(\d{1,3})\b", re.IGNORECASE)

# Nombres especiales -> patron de keywords (en forma normalizada sin acentos)
SPECIAL = [
    ("codigo civil", ["codigo civil"]),
    ("constitucion", ["constitucion espanola", "la constitucion", "constitucion de 1978"]),
    ("tfue", ["tratado de funcionamiento", "tfue"]),
    ("tue", ["tratado de la union europea", "(tue)"]),
    ("trebep", ["estatuto basico del empleado", "trebep", "ebep"]),
    ("estatut", ["estatuto de autonomia"]),
    ("lopj", ["ley organica del poder judicial"]),
    ("les corts", ["reglamento de les corts", "reglament de les corts"]),
    ("carta dfue", ["carta de los derechos fundamentales de la union"]),
]

# Mapa de keyword especial -> nombre de ley en BD (substring a buscar, normalizado)
SPECIAL_LAWDB = {
    "codigo civil": "codigo civil",
    "constitucion": "constitucion espanola",
    "tfue": "tratado de funcionamiento",
    "tue": "tratado de la union europea",
    "trebep": "trebep",
    "estatut": "estatuto autonomia",
    "lopj": "poder judicial",
    "les corts": "reglamento de les corts boe",  # preferimos el vigente BOE 2026
    "carta dfue": "carta de derechos fundamentales",
}


def build_law_index(laws):
    """laws: lista de dicts {id, name}. Devuelve estructuras de indice."""
    by_numyear = {}   # (num,year) -> [law dicts]
    norm = []         # [(law, normalized_name)]
    for law in laws:
        nm = _strip(law["name"])
        norm.append((law, nm))
        for num, year in NUM_YEAR_RE.findall(law["name"]):
            by_numyear.setdefault((num, year), []).append((law, nm))
    return {"by_numyear": by_numyear, "norm": norm}


def _find_special(text_norm, index):
    for key, kws in SPECIAL:
        for kw in kws:
            if kw in text_norm:
                target = SPECIAL_LAWDB[key]
                for law, nm in index["norm"]:
                    if target in nm:
                        return law, 0.9, "nombre_especial:%s" % key
    return None


def match_law(enunciado, index):
    """Devuelve (law, confianza, basis) o None."""
    tn = _strip(enunciado)

    # 1) Numero/anio explicito
    for num, year in NUM_YEAR_RE.findall(enunciado):
        cands = index["by_numyear"].get((num, year))
        if not cands:
            continue
        if len(cands) == 1:
            return cands[0][0], 0.95, "num_anio:%s/%s" % (num, year)
        # Desambiguar por solapamiento de palabras del nombre con el enunciado
        best = None
        best_score = -1
        for law, nm in cands:
            words = [w for w in nm.split() if len(w) > 4]
            score = sum(1 for w in words if w in tn)
            if score > best_score:
                best_score = score
                best = law
        return best, 0.8, "num_anio_desambig:%s/%s" % (num, year)

    # 2) Nombre especial
    sp = _find_special(tn, index)
    if sp:
        return sp[0], sp[1], sp[2]

    return None


def match_articles(enunciado):
    """Lista de refs de articulo citados explicitamente (como strings)."""
    refs = []
    for a, b in ART_RANGE_RE.findall(enunciado):
        ai, bi = int(a), int(b)
        if 0 < ai <= bi <= ai + 60:
            refs.extend(str(x) for x in range(ai, bi + 1))
    # singulares (excluyendo los ya cubiertos por rango)
    if not refs:
        for m in ART_SINGLE_RE.findall(enunciado):
            refs.append(str(int(m)))
    return list(dict.fromkeys(refs))  # unicas, en orden


def link_question(enunciado, opciones, index):
    """Devuelve dict con law_id, articles, confianza, basis."""
    law_match = match_law(enunciado, index)
    # Buscar articulos en enunciado y, si no hay, en opciones
    arts = match_articles(enunciado)
    if not arts:
        for L in "ABCD":
            arts = match_articles(opciones.get(L, ""))
            if arts:
                break
    if not law_match:
        return {"law_id": None, "law": None, "articles": arts,
                "confianza": 0.0, "basis": "sin_ley"}
    law, conf, basis = law_match
    return {"law_id": law["id"], "law": law["name"], "articles": arts,
            "confianza": conf, "basis": basis}


if __name__ == "__main__":
    import sqlite3, io, sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    from parse_official_exam import parse_exam

    db = sqlite3.connect(r"C:\Users\isaac\Desktop\GVAdictos\db\gvadicto.sqlite")
    db.row_factory = sqlite3.Row
    laws = [dict(r) for r in db.execute("SELECT id, name FROM laws")]
    index = build_law_index(laws)

    pdfs = [
        ("1a parte", r"data\examenes_oficiales\A1-01\2025\1-25_primera_parte_cuestionario_plantilla.pdf"),
        ("2a parte", r"data\examenes_oficiales\A1-01\2025\1-25_segunda_parte_cuestionario_plantilla.pdf"),
    ]
    total = 0
    con_ley = 0
    con_art = 0
    sin_ley_list = []
    for tag, p in pdfs:
        res = parse_exam(p)
        for q in res["questions"]:
            total += 1
            link = link_question(q["enunciado"], q["opciones"], index)
            if link["law_id"]:
                con_ley += 1
                if link["articles"]:
                    con_art += 1
            else:
                sin_ley_list.append((tag, q["numero"], q["enunciado"][:70]))

    print("Total preguntas: %d" % total)
    print("Con ley identificada: %d (%.0f%%)" % (con_ley, 100*con_ley/total))
    print("Con articulo explicito: %d (%.0f%%)" % (con_art, 100*con_art/total))
    print("\nSin ley (primeras 25):")
    for tag, n, e in sin_ley_list[:25]:
        print("  [%s Q%d] %s" % (tag, n, e))
    db.close()

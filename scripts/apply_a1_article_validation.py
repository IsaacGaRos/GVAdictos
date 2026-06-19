from __future__ import annotations

import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.import_official_sources import html_to_text
from src.core.db import connect, init_db
from src.core.source_catalog import upsert_source_document
from src.laws.importer import file_sha256, import_law


REG_CORTS_URL = "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-5880"
REG_CORTS_SOURCE = ROOT / "data" / "sources" / "leyes_originales" / "BOE" / "BOE-A-2026-5880_Reglamento_Les_Corts_2026.html"
REG_CORTS_TEXT = ROOT / "data" / "processed" / "official_sources" / "BOE-A-2026-5880.txt"
REG_CORTS_TITLE = "Reglamento de Les Corts BOE 2026"

MAPPING_BASIS = "validacion_articulos_codex_2026_06_18"
VALIDATION_STATUS = "validado_fuente_oficial_pendiente_revision_humana"
VALIDATION_NOTE = (
    "Delimitacion documentada en .claude/VALIDACION_ARTICULOS_POR_TEMA.md "
    "contra fuente oficial BOE/DOGV; pendiente revision humana."
)

LAW_NAMES = {
    "ley5": "Ley 5/1983 Gobierno Valenciano Consell",
    "ley1": "Ley 1/1987 Electoral Valenciana",
    "ley14": "Ley 14/2003 Patrimonio Generalitat Valenciana",
    "ley33": "Ley 33/2003 Patrimonio Administraciones Publicas",
    "ley40": "Ley 40/2015 Regimen Juridico Sector Publico",
    "ley39": "Ley 39/2015 Procedimiento Administrativo Comun",
    "lcsp": "Ley 9/2017 Contratos Sector Publico",
    "lgss": "Real Decreto Legislativo 8/2015 Ley General Seguridad Social",
    "estatut": "Ley Organica 5/1982 Estatuto Autonomia Comunitat Valenciana",
}

TOPIC_MARKERS = {
    "pg8": ("general", 8, "Les Corts"),
    "pe17": ("especial", 17, "patrimonio"),
    "pe18": ("especial", 18, "formas de actividad"),
    "pe21": ("especial", 21, "contratos"),
    "pe32": ("especial", 32, "Seguridad Social"),
    "pe52": ("especial", 52, "Justicia"),
    "pe54": ("especial", 54, "sanidad"),
    "pe55": ("especial", 55, "fomento del empleo"),
}

LEY33_BASIC_REFS = [
    "1", "2", "3", "4", "5.1", "5.2", "5.4", "6", "7.1", "8.1",
    "15", "17", "18", "20.2", "20.3", "20.6", "20 bis.8", "22", "23",
    "24.1-24.3", "27", "28", "29.2", "30.1-30.2", "32.1", "32.4",
    "36.1", "37.1-37.3", "38.1-38.2", "39", "40", "41", "42", "43",
    "44", "45", "49", "50", "53", "55", "58", "61", "62", "83.1", "84",
    "91.4", "92.1", "92.2", "92.4", "93.1-93.4", "94", "97", "98",
    "99.1", "100", "101.1", "101.3", "101.4", "102.2", "102.3", "103.1",
    "103.3", "106.1", "107.1", "109.3", "110.3", "121.4", "183", "184",
    "189", "190", "190 bis", "191",
]


class ApplySummary:
    def __init__(self) -> None:
        self.inserted = 0
        self.missing: list[str] = []

    def add_inserted(self, count: int) -> None:
        self.inserted += count

    def add_missing(self, label: str) -> None:
        self.missing.append(label)


def fetch_url(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "GVAdicto/0.1"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def ensure_reglamento_les_corts() -> int:
    REG_CORTS_SOURCE.parent.mkdir(parents=True, exist_ok=True)
    try:
        REG_CORTS_SOURCE.write_bytes(fetch_url(REG_CORTS_URL))
    except Exception:
        if not REG_CORTS_SOURCE.exists():
            raise

    upsert_source_document(
        {
            "source_kind": "boe_html",
            "external_id": "BOE-A-2026-5880",
            "title": REG_CORTS_TITLE,
            "path": str(REG_CORTS_SOURCE.relative_to(ROOT)).replace("\\", "/"),
            "mime_type": "text/html",
            "url": REG_CORTS_URL,
            "priority": "alta",
            "status": "descargado",
            "legal_status": VALIDATION_STATUS,
            "notes": (
                "Fuente oficial BOE vigente 2026 para Tema PG-08. "
                "Sustituye como referencia principal al consolidado DOGV 2024."
            ),
        }
    )

    source_hash = file_sha256(REG_CORTS_SOURCE)
    with connect() as conn:
        existing = conn.execute(
            """
            SELECT id
            FROM laws
            WHERE name = ? AND source_path = ? AND source_hash = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (REG_CORTS_TITLE, str(REG_CORTS_SOURCE), source_hash),
        ).fetchone()
        if existing:
            law_id = int(existing["id"])
            article_count = conn.execute(
                "SELECT COUNT(*) AS total FROM articles WHERE law_id = ?",
                (law_id,),
            ).fetchone()["total"]
            if article_count:
                conn.execute(
                    "UPDATE laws SET validation_status = ? WHERE id = ?",
                    (VALIDATION_STATUS, law_id),
                )
                return law_id

    REG_CORTS_TEXT.parent.mkdir(parents=True, exist_ok=True)
    REG_CORTS_TEXT.write_text(html_to_text(REG_CORTS_SOURCE), encoding="utf-8")
    law_id = import_law(REG_CORTS_TEXT, REG_CORTS_TITLE, original_source_path=REG_CORTS_SOURCE)
    with connect() as conn:
        conn.execute(
            "UPDATE laws SET validation_status = ? WHERE id = ?",
            (VALIDATION_STATUS, law_id),
        )
    return law_id


def resolve_topic(conn, key: str) -> int:
    part, topic_number, marker = TOPIC_MARKERS[key]
    row = conn.execute(
        """
        SELECT id
        FROM topics
        WHERE part = ? AND topic_number = ? AND lower(official_text) LIKE ?
        """,
        (part, topic_number, f"%{marker.lower()}%"),
    ).fetchone()
    if not row:
        raise RuntimeError(f"No se encontro el tema {key}: {part} {topic_number} {marker}")
    return int(row["id"])


def resolve_law(conn, name: str) -> int:
    row = conn.execute("SELECT id FROM laws WHERE name = ? ORDER BY id DESC LIMIT 1", (name,)).fetchone()
    if not row:
        raise RuntimeError(f"No se encontro la norma importada: {name}")
    return int(row["id"])


def is_probable_article(row) -> bool:
    ref = (row["article_ref"] or "").strip().lower()
    title = (row["title"] or "").strip().lower()
    if re.fullmatch(r"\d+", ref):
        return True
    match = re.fullmatch(r"(\d+)\s+([a-z])", ref)
    if not match:
        return False
    suffix = match.group(2)
    if suffix == "b":
        return title.startswith("is.")
    if suffix == "t":
        return title.startswith("er.")
    if suffix == "q":
        return title.startswith(("uater.", "uáter.", "uinquies."))
    if suffix == "s":
        return title.startswith("exies.")
    return False


def article_base(ref: str) -> int | None:
    match = re.match(r"\s*(\d+)", ref or "")
    return int(match.group(1)) if match else None


def parent_article_ref(reference: str) -> str:
    ref = reference.strip().lower()
    match = re.match(r"(\d+)\s*(bis|ter|quater|cuater|quáter|quinquies|sexies)?", ref)
    if not match:
        return reference
    number, suffix = match.groups()
    if not suffix:
        return number
    if suffix in {"quater", "cuater", "quáter"}:
        suffix = "quater"
    return f"{number} {suffix}"


def ref_aliases(reference: str) -> set[str]:
    ref = parent_article_ref(reference)
    lower = ref.lower().strip()
    aliases = {lower}
    replacements = {
        " bis": " b",
        " ter": " t",
        " quater": " q",
        " quinquies": " q",
        " sexies": " s",
    }
    for source, target in replacements.items():
        if lower.endswith(source):
            aliases.add(lower[: -len(source)] + target)
    return aliases


def canonical_ref(row) -> str:
    ref = (row["article_ref"] or "").strip()
    title = (row["title"] or "").strip().lower()
    match = re.fullmatch(r"(\d+)\s+([a-z])", ref.lower())
    if not match:
        return ref
    number, suffix = match.groups()
    if suffix == "b" and title.startswith("is."):
        return f"{number} bis"
    if suffix == "t" and title.startswith("er."):
        return f"{number} ter"
    if suffix == "q" and title.startswith(("uater.", "uáter.")):
        return f"{number} quater"
    if suffix == "q" and title.startswith("uinquies."):
        return f"{number} quinquies"
    if suffix == "s" and title.startswith("exies."):
        return f"{number} sexies"
    return ref


def best_article(conn, law_id: int, reference: str):
    aliases = ref_aliases(reference)
    placeholders = ",".join("?" for _ in aliases)
    rows = conn.execute(
        f"""
        SELECT *
        FROM articles
        WHERE law_id = ? AND lower(trim(article_ref)) IN ({placeholders})
        """,
        (law_id, *sorted(aliases)),
    ).fetchall()
    candidates = [row for row in rows if is_probable_article(row)]
    if not candidates:
        return None
    return max(candidates, key=lambda row: len(row["text"] or ""))


def best_articles_in_range(conn, law_id: int, start: int, end: int) -> list:
    best_by_ref = {}
    rows = conn.execute("SELECT * FROM articles WHERE law_id = ?", (law_id,)).fetchall()
    for row in rows:
        if not is_probable_article(row):
            continue
        base = article_base(row["article_ref"])
        if base is None or base < start or base > end:
            continue
        key = canonical_ref(row).lower()
        current = best_by_ref.get(key)
        if current is None or len(row["text"] or "") > len(current["text"] or ""):
            best_by_ref[key] = row
    return sorted(
        best_by_ref.values(),
        key=lambda row: (article_base(row["article_ref"]) or 0, canonical_ref(row)),
    )


def insert_topic_source(
    conn,
    summary: ApplySummary,
    topic_id: int,
    law_id: int,
    article_id: int | None,
    normative_reference: str,
    coverage_status: str,
    priority: str,
    notes: str,
) -> None:
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO topic_sources(
            topic_id, law_id, article_id, normative_reference,
            coverage_status, mapping_basis, priority, validation_status, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            topic_id,
            law_id,
            article_id,
            normative_reference,
            coverage_status,
            MAPPING_BASIS,
            priority,
            VALIDATION_STATUS,
            notes,
        ),
    )
    summary.add_inserted(cursor.rowcount)


def add_article_ref(
    conn,
    summary: ApplySummary,
    topic_id: int,
    law_id: int,
    law_label: str,
    reference: str,
    coverage_status: str = "articulo_delimitado",
    priority: str = "alta",
    notes: str = VALIDATION_NOTE,
) -> None:
    article = best_article(conn, law_id, reference)
    if not article:
        summary.add_missing(f"{law_label} art. {reference}")
        return
    insert_topic_source(
        conn,
        summary,
        topic_id,
        law_id,
        int(article["id"]),
        f"{law_label} art. {reference}",
        coverage_status,
        priority,
        notes,
    )


def add_article_range(
    conn,
    summary: ApplySummary,
    topic_id: int,
    law_id: int,
    law_label: str,
    start: int,
    end: int,
    coverage_status: str = "articulo_delimitado",
    priority: str = "alta",
    notes: str = VALIDATION_NOTE,
) -> None:
    for article in best_articles_in_range(conn, law_id, start, end):
        insert_topic_source(
            conn,
            summary,
            topic_id,
            law_id,
            int(article["id"]),
            f"{law_label} art. {canonical_ref(article)}",
            coverage_status,
            priority,
            notes,
        )


def add_reference_without_article(
    conn,
    summary: ApplySummary,
    topic_id: int,
    law_id: int,
    normative_reference: str,
    notes: str,
    priority: str = "media",
) -> None:
    insert_topic_source(
        conn,
        summary,
        topic_id,
        law_id,
        None,
        normative_reference,
        "referencia_no_parseada",
        priority,
        notes,
    )


def append_topic_note_once(conn, topic_id: int, note: str) -> None:
    row = conn.execute("SELECT notes FROM topics WHERE id = ?", (topic_id,)).fetchone()
    existing = row["notes"] or ""
    if MAPPING_BASIS in existing:
        return
    new_notes = f"{existing}\n{note}".strip() if existing else note
    conn.execute(
        """
        UPDATE topics
        SET validation_status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        ("articulos_delimitados_pendiente_revision_humana", new_notes, topic_id),
    )


def close_delimitation_findings(conn, topic_ids: set[int]) -> None:
    placeholders = ",".join("?" for _ in topic_ids)
    conn.execute(
        f"""
        UPDATE topic_validation_findings
        SET status = 'resuelto', updated_at = CURRENT_TIMESTAMP
        WHERE topic_id IN ({placeholders})
          AND finding_type = 'delimitacion_articulos_pendiente'
        """,
        tuple(sorted(topic_ids)),
    )


def apply_mappings(conn, law_ids: dict[str, int]) -> ApplySummary:
    summary = ApplySummary()
    topic_ids = {key: resolve_topic(conn, key) for key in TOPIC_MARKERS}

    placeholders = ",".join("?" for _ in topic_ids)
    conn.execute(
        f"DELETE FROM topic_sources WHERE mapping_basis = ? AND topic_id IN ({placeholders})",
        (MAPPING_BASIS, *sorted(topic_ids.values())),
    )

    # Tema 8 general: Les Corts y sistema electoral valenciano.
    add_article_range(conn, summary, topic_ids["pg8"], law_ids["reg_corts"], "Reglamento Les Corts BOE 2026", 112, 139)
    for ref in ["18", "42", "53", "54", "55", "56", "57", "58", "59"]:
        add_article_ref(conn, summary, topic_ids["pg8"], law_ids["ley5"], "Ley 5/1983", ref)
    add_article_range(conn, summary, topic_ids["pg8"], law_ids["ley1"], "Ley 1/1987", 1, 14)

    # Tema 17 especial: patrimonio publico.
    add_article_range(conn, summary, topic_ids["pe17"], law_ids["ley14"], "Ley 14/2003", 1, 107)
    for ref in LEY33_BASIC_REFS:
        add_article_ref(conn, summary, topic_ids["pe17"], law_ids["ley33"], "Ley 33/2003", ref)
    for ref in ["DA 3", "DT 1.1", "DT 5"]:
        add_reference_without_article(
            conn,
            summary,
            topic_ids["pe17"],
            law_ids["ley33"],
            f"Ley 33/2003 {ref}",
            "Referencia basica de disposicion no extraida como articulo por el importador actual. " + VALIDATION_NOTE,
        )

    # Tema 18 especial: formas de actividad administrativa y ejecucion.
    for ref in ["3", "4"]:
        add_article_ref(conn, summary, topic_ids["pe18"], law_ids["ley40"], "Ley 40/2015", ref)
    add_article_range(
        conn, summary, topic_ids["pe18"], law_ids["ley40"], "Ley 40/2015", 47, 53,
        coverage_status="complementario", priority="media",
    )
    for ref in ["69", "97", "98", "99", "100", "101", "102", "103", "104", "105"]:
        add_article_ref(conn, summary, topic_ids["pe18"], law_ids["ley39"], "Ley 39/2015", ref)
    for start, end in [(34, 39), (66, 68), (75, 83), (88, 96)]:
        add_article_range(
            conn, summary, topic_ids["pe18"], law_ids["ley39"], "Ley 39/2015", start, end,
            coverage_status="complementario", priority="media",
        )
    for ref in ["53", "70"]:
        add_article_ref(
            conn, summary, topic_ids["pe18"], law_ids["ley39"], "Ley 39/2015", ref,
            coverage_status="complementario", priority="media",
        )

    # Tema 21 especial: contratos del sector publico.
    add_article_range(conn, summary, topic_ids["pe21"], law_ids["lcsp"], "Ley 9/2017 LCSP", 1, 114)

    # Tema 32 especial: Seguridad Social.
    for start, end in [(1, 65), (136, 160), (305, 322)]:
        add_article_range(conn, summary, topic_ids["pe32"], law_ids["lgss"], "RDL 8/2015 LGSS", start, end)

    # Temas 52, 54 y 55: articulos estatutarios por bloque competencial.
    for ref in ["7.3", "33", "34", "35", "36", "49.1.3", "49.1.36", "49.3.14", "50.1", "55"]:
        add_article_ref(conn, summary, topic_ids["pe52"], law_ids["estatut"], "Estatuto CV", ref)
    for ref in ["49.1.11", "49.1.19", "49.3.4", "49.3.5", "54"]:
        add_article_ref(conn, summary, topic_ids["pe54"], law_ids["estatut"], "Estatuto CV", ref)
    for ref in ["19.1", "49.1.21", "49.3.8", "49.3.9", "51.1.1", "53.2", "79.1", "80.1", "80.4", "80.5"]:
        add_article_ref(conn, summary, topic_ids["pe55"], law_ids["estatut"], "Estatuto CV", ref)
    for ref in ["52.1.1", "52.1.4"]:
        add_article_ref(
            conn, summary, topic_ids["pe55"], law_ids["estatut"], "Estatuto CV", ref,
            coverage_status="contexto_competencial", priority="media",
        )

    note = f"{MAPPING_BASIS}: articulos prioritarios delimitados contra fuente oficial."
    for topic_id in topic_ids.values():
        append_topic_note_once(conn, topic_id, note)

    close_delimitation_findings(conn, {topic_ids["pg8"], topic_ids["pe17"]})
    return summary


def print_counts(conn) -> None:
    rows = conn.execute(
        """
        SELECT t.part, t.topic_number, substr(t.official_text, 1, 55) AS tema,
               COUNT(ts.id) AS filas_mapeo,
               COUNT(DISTINCT ts.article_id) AS articulos_mapeados,
               SUM(CASE WHEN ts.article_id IS NULL THEN 1 ELSE 0 END) AS referencias_sin_articulo
        FROM topics t
        LEFT JOIN topic_sources ts
               ON ts.topic_id = t.id AND ts.mapping_basis = ?
        WHERE t.id IN (
            SELECT topic_id FROM topic_sources WHERE mapping_basis = ?
        )
        GROUP BY t.id
        ORDER BY t.part, t.topic_number
        """,
        (MAPPING_BASIS, MAPPING_BASIS),
    ).fetchall()
    for row in rows:
        print(
            f"{row['part']} {row['topic_number']:02d}: "
            f"{row['articulos_mapeados']} articulos unicos, "
            f"{row['filas_mapeo']} filas de mapeo, "
            f"{row['referencias_sin_articulo'] or 0} refs sin articulo - {row['tema']}"
        )


def main() -> None:
    init_db()
    reg_corts_law_id = ensure_reglamento_les_corts()
    with connect() as conn:
        law_ids = {key: resolve_law(conn, name) for key, name in LAW_NAMES.items()}
        law_ids["reg_corts"] = reg_corts_law_id
        summary = apply_mappings(conn, law_ids)
        print_counts(conn)
    print(f"Mapeos insertados: {summary.inserted}")
    if summary.missing:
        print("Referencias no encontradas:")
        for item in summary.missing:
            print(f"- {item}")


if __name__ == "__main__":
    main()

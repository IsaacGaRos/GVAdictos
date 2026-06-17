from __future__ import annotations

import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.db import connect, init_db


TAG = "generado_controlado_a1_v1"
MAX_QUESTIONS = 20

PILOT_ARTICLES: dict[int, tuple[str, list[str]]] = {
    24: ("Ley 39/2015 Procedimiento Administrativo Comun", ["1", "2", "3", "4", "5", "9", "12", "13", "14", "16", "27", "30", "31"]),
    25: ("Ley 39/2015 Procedimiento Administrativo Comun", ["34", "35", "36", "37", "38", "39", "40", "41", "47", "48"]),
    26: ("Ley 39/2015 Procedimiento Administrativo Comun", ["53", "54", "55", "56", "66", "70", "75", "82", "88", "96", "97", "98"]),
    27: ("Ley 39/2015 Procedimiento Administrativo Comun", ["106", "107", "109", "112", "114", "115", "121", "123", "124", "125"]),
}


def answer_slot(article_id: int) -> int:
    return article_id % 4


def topic_label(part: str, topic_number: int) -> str:
    prefix = "PG" if part == "general" else "PE"
    return f"{prefix}-{topic_number:02d}"


def clean_option(value: str) -> str:
    text = " ".join((value or "").split())
    text = re.sub(r"\.{3,}\s*\d+\s*$", "", text).strip()
    text = re.sub(r"\s+\d+\s*$", "", text).strip()
    text = re.sub(r"(?i)^art[ií]culo\s+[\w.\-]+\s*[.:]\s*", "", text).strip()
    return text[:240]


def main() -> None:
    init_db()
    inserted = 0
    skipped = 0
    with connect() as conn:
        for drive_topic_number, (law_name, article_refs) in PILOT_ARTICLES.items():
            topic = conn.execute(
                "SELECT * FROM topics WHERE drive_topic_number = ?",
                (drive_topic_number,),
            ).fetchone()
            law = conn.execute(
                "SELECT * FROM laws WHERE name = ? ORDER BY id DESC LIMIT 1",
                (law_name,),
            ).fetchone()
            if not topic or not law:
                skipped += len(article_refs)
                continue

            distractor_rows = conn.execute(
                """
                SELECT id, article_ref, title
                FROM articles
                WHERE law_id = ?
                  AND title IS NOT NULL
                  AND trim(title) != ''
                  AND article_ref != 'sin_articulo_detectado'
                  AND article_ref NOT LIKE '%.%'
                  AND instr(title, '....') = 0
                ORDER BY CAST(article_ref AS INTEGER), article_ref, length(text) DESC
                """,
                (law["id"],),
            ).fetchall()
            distractor_titles = []
            seen_titles = set()
            for row in distractor_rows:
                title = clean_option(row["title"])
                title_key = title.casefold()
                if title and title_key not in seen_titles:
                    distractor_titles.append(title)
                    seen_titles.add(title_key)
            if len(distractor_titles) < 4:
                skipped += len(article_refs)
                continue

            for article_ref in article_refs:
                if inserted >= MAX_QUESTIONS:
                    break
                article = conn.execute(
                    """
                    SELECT *
                    FROM articles
                    WHERE law_id = ? AND article_ref = ?
                    ORDER BY
                        CASE WHEN instr(title, '....') = 0 THEN 0 ELSE 1 END,
                        length(text) DESC,
                        id
                    LIMIT 1
                    """,
                    (law["id"], article_ref),
                ).fetchone()
                if not article:
                    skipped += 1
                    continue

                correct = clean_option(article["title"])
                if not correct or correct.lower().startswith("articulo "):
                    skipped += 1
                    continue
                distractors = [title for title in distractor_titles if title.casefold() != correct.casefold()]
                if len(distractors) < 3:
                    skipped += 1
                    continue

                slot = answer_slot(int(article["id"]))
                options = distractors[:3]
                options.insert(slot, correct)
                answer = "ABCD"[slot]
                enunciado = (
                    f"Segun {law['name']}, que rubrica corresponde al articulo {article['article_ref']}?"
                )
                fuente = f"{article['source']} | law_id={law['id']} | article_id={article['id']}"

                duplicate = conn.execute(
                    "SELECT id FROM questions WHERE enunciado = ? AND fuente = ? LIMIT 1",
                    (enunciado, fuente),
                ).fetchone()
                if duplicate:
                    skipped += 1
                    continue

                conn.execute(
                    """
                    INSERT INTO questions(
                        law_id, article_id, norma, articulo, tema, enunciado,
                        opcion_a, opcion_b, opcion_c, opcion_d, respuesta_correcta,
                        explicacion, fuente, dificultad, etiquetas, requiere_revision
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'basica', ?, 1)
                    """,
                    (
                        law["id"],
                        article["id"],
                        law["name"],
                        article["article_ref"],
                        topic_label(topic["part"], int(topic["topic_number"])),
                        enunciado,
                        options[0],
                        options[1],
                        options[2],
                        options[3],
                        answer,
                        (
                            f"Fuente: {law['name']}, articulo {article['article_ref']}. "
                            f"La rubrica importada del articulo es: {correct}. "
                            "Pregunta generada de forma controlada y pendiente de revision juridica."
                        ),
                        fuente,
                        f"a1_01_2025;{TAG};requiere_validacion_juridica",
                    ),
                )
                inserted += 1
    print({"inserted": inserted, "skipped": skipped, "tag": TAG})


if __name__ == "__main__":
    main()

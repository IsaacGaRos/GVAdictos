from __future__ import annotations

from typing import Any

from src.core.db import connect


def create_question(data: dict[str, Any]) -> int:
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO questions(
                law_id, article_id, norma, articulo, tema, enunciado,
                opcion_a, opcion_b, opcion_c, opcion_d, respuesta_correcta,
                explicacion, fuente, dificultad, etiquetas, requiere_revision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("law_id"),
                data.get("article_id"),
                data["norma"],
                data["articulo"],
                data.get("tema"),
                data["enunciado"],
                data["opcion_a"],
                data["opcion_b"],
                data["opcion_c"],
                data["opcion_d"],
                data["respuesta_correcta"],
                data["explicacion"],
                data["fuente"],
                data.get("dificultad", "media"),
                data.get("etiquetas"),
                1 if data.get("requiere_revision") else 0,
            ),
        )
        return int(cursor.lastrowid)


def update_question(question_id: int, data: dict[str, Any]) -> None:
    with connect() as conn:
        conn.execute(
            """
            UPDATE questions
            SET norma = ?, articulo = ?, tema = ?, enunciado = ?,
                opcion_a = ?, opcion_b = ?, opcion_c = ?, opcion_d = ?,
                respuesta_correcta = ?, explicacion = ?, fuente = ?,
                dificultad = ?, etiquetas = ?, requiere_revision = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                data["norma"],
                data["articulo"],
                data.get("tema"),
                data["enunciado"],
                data["opcion_a"],
                data["opcion_b"],
                data["opcion_c"],
                data["opcion_d"],
                data["respuesta_correcta"],
                data["explicacion"],
                data["fuente"],
                data.get("dificultad", "media"),
                data.get("etiquetas"),
                1 if data.get("requiere_revision") else 0,
                question_id,
            ),
        )


def delete_question(question_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM questions WHERE id = ?", (question_id,))


def list_questions() -> list:
    with connect() as conn:
        return conn.execute("SELECT * FROM questions ORDER BY id DESC").fetchall()


def get_question(question_id: int):
    with connect() as conn:
        return conn.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()

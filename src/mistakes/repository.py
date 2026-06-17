from __future__ import annotations

from src.core.db import connect


ERROR_CAUSES = [
    "no sabia el articulo",
    "confusion de plazo",
    "confusion de organo",
    "confusion entre normas",
    "lei mal",
    "trampa de literalidad",
    "dude entre dos",
    "prisa",
    "otra",
]


def record_attempt(
    question_id: int,
    respuesta_usuario: str,
    respuesta_correcta: str,
    tiempo_respuesta: float | None = None,
    causa_error: str | None = None,
    comentario: str | None = None,
) -> None:
    acierto = respuesta_usuario == respuesta_correcta
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO attempts(
                question_id, respuesta_usuario, respuesta_correcta,
                acierto, tiempo_respuesta, causa_error, comentario
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                question_id,
                respuesta_usuario,
                respuesta_correcta,
                1 if acierto else 0,
                tiempo_respuesta,
                causa_error,
                comentario,
            ),
        )


def mistake_summary() -> list:
    with connect() as conn:
        return conn.execute(
            """
            SELECT
                q.id AS pregunta_id,
                q.norma,
                q.articulo,
                q.tema,
                q.enunciado,
                COUNT(a.id) AS intentos,
                SUM(CASE WHEN a.acierto = 0 THEN 1 ELSE 0 END) AS fallos,
                ROUND(100.0 * AVG(a.acierto), 1) AS porcentaje_acierto
            FROM questions q
            JOIN attempts a ON a.question_id = q.id
            GROUP BY q.id
            ORDER BY fallos DESC, intentos DESC
            """
        ).fetchall()


def weekly_summary() -> list:
    with connect() as conn:
        return conn.execute(
            """
            SELECT
                date(attempted_at, 'weekday 1', '-7 days') AS semana,
                COUNT(*) AS intentos,
                SUM(acierto) AS aciertos,
                COUNT(*) - SUM(acierto) AS fallos,
                ROUND(100.0 * AVG(acierto), 1) AS porcentaje_acierto
            FROM attempts
            GROUP BY semana
            ORDER BY semana DESC
            """
        ).fetchall()

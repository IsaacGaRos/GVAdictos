"""
Servicio para banco de exámenes: crear, actualizar, validar preguntas.
"""

from __future__ import annotations

import sqlite3
from typing import Any


class ExamBankService:
    """Gestión de banco de exámenes."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create_exam_paper(
        self,
        convocatoria: str,
        anio: int,
        fuente_oficial_url: str | None = None,
        fuente_path: str | None = None,
        bloque: str | None = None,
        fase: str | None = None,
        answer_key_version: str | None = None,
        notes: str | None = None,
    ) -> int:
        """Crear un examen (convocatoria)."""
        cursor = self.conn.execute(
            """
            INSERT INTO exam_papers(
                convocatoria, anio, bloque, fase, fuente_oficial_url, fuente_path,
                answer_key_version, notes, validation_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                convocatoria, anio, bloque, fase, fuente_oficial_url, fuente_path,
                answer_key_version, notes, "pendiente_de_validacion"
            )
        )
        return int(cursor.lastrowid)

    def create_exam_question(
        self,
        exam_paper_id: int,
        numero: int,
        enunciado: str,
        es_reserva: bool = False,
        respuesta_oficial: str | None = None,
        anulada: bool = False,
        motivo_anulacion: str | None = None,
    ) -> int:
        """Crear una pregunta de examen."""
        cursor = self.conn.execute(
            """
            INSERT INTO exam_questions(
                exam_paper_id, numero, enunciado, es_reserva, respuesta_oficial,
                anulada, motivo_anulacion, validation_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                exam_paper_id, numero, enunciado, 1 if es_reserva else 0,
                respuesta_oficial, 1 if anulada else 0, motivo_anulacion,
                "pendiente_de_validacion"
            )
        )
        return int(cursor.lastrowid)

    def create_exam_question_option(
        self,
        exam_question_id: int,
        letra: str,
        texto: str,
        es_correcta: bool = False,
    ) -> int:
        """Crear una opción de respuesta."""
        cursor = self.conn.execute(
            """
            INSERT INTO exam_question_options(
                exam_question_id, letra, texto, es_correcta
            ) VALUES (?, ?, ?, ?)
            """,
            (exam_question_id, letra, texto, 1 if es_correcta else 0)
        )
        return int(cursor.lastrowid)

    def link_question_to_article(
        self,
        exam_question_id: int,
        article_id: int,
        tipo_relacion: str = "aplicacion",
        mapping_basis: str = "curador",
        confianza: float = 1.0,
    ) -> int:
        """Vincular una pregunta a un artículo."""
        # Obtener law_id y topic_id del artículo
        art_row = self.conn.execute(
            "SELECT law_id FROM articles WHERE id = ?",
            (article_id,)
        ).fetchone()
        if not art_row:
            raise ValueError(f"article_id {article_id} no existe")

        law_id = art_row[0]

        # Obtener topic_id de topic_sources
        topic_row = self.conn.execute(
            """
            SELECT topic_id FROM topic_sources
            WHERE article_id = ? LIMIT 1
            """,
            (article_id,)
        ).fetchone()
        topic_id = topic_row[0] if topic_row else None

        cursor = self.conn.execute(
            """
            INSERT INTO exam_question_links(
                exam_question_id, topic_id, law_id, article_id,
                tipo_relacion, mapping_basis, confianza, validation_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                exam_question_id, topic_id, law_id, article_id,
                tipo_relacion, mapping_basis, confianza, "pendiente_de_validacion"
            )
        )
        return int(cursor.lastrowid)

    def get_exam_paper(self, exam_paper_id: int) -> dict[str, Any] | None:
        """Obtener detalles de un examen."""
        row = self.conn.execute(
            "SELECT * FROM exam_papers WHERE id = ?",
            (exam_paper_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_exam_questions(self, exam_paper_id: int) -> list[dict[str, Any]]:
        """Obtener preguntas de un examen."""
        rows = self.conn.execute(
            """
            SELECT * FROM exam_questions
            WHERE exam_paper_id = ?
            ORDER BY numero
            """,
            (exam_paper_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def get_question_summary(self, exam_question_id: int) -> dict[str, Any]:
        """Obtener resumen de pregunta + opciones + links."""
        question = self.conn.execute(
            "SELECT * FROM exam_questions WHERE id = ?",
            (exam_question_id,)
        ).fetchone()
        if not question:
            raise ValueError(f"exam_question_id {exam_question_id} no existe")

        options = self.conn.execute(
            """
            SELECT letra, texto, es_correcta FROM exam_question_options
            WHERE exam_question_id = ?
            ORDER BY letra
            """,
            (exam_question_id,)
        ).fetchall()

        links = self.conn.execute(
            """
            SELECT l.id, l.article_id, l.topic_id, a.article_ref, a.title,
                   l.tipo_relacion, l.confianza, l.validation_status
            FROM exam_question_links l
            LEFT JOIN articles a ON a.id = l.article_id
            WHERE l.exam_question_id = ?
            """,
            (exam_question_id,)
        ).fetchall()

        return {
            "id": question["id"],
            "numero": question["numero"],
            "enunciado": question["enunciado"],
            "respuesta_oficial": question["respuesta_oficial"],
            "anulada": bool(question["anulada"]),
            "options": [dict(row) for row in options],
            "links": [dict(row) for row in links],
        }

    def count_exams(self) -> int:
        """Contar exámenes en la BD."""
        return int(self.conn.execute("SELECT COUNT(*) FROM exam_papers").fetchone()[0])

    def count_questions(self) -> int:
        """Contar preguntas en la BD."""
        return int(self.conn.execute("SELECT COUNT(*) FROM exam_questions").fetchone()[0])

    def count_question_links(self) -> int:
        """Contar vinculaciones pregunta → artículo."""
        return int(self.conn.execute("SELECT COUNT(*) FROM exam_question_links").fetchone()[0])

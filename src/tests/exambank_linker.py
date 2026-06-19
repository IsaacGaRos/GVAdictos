"""
Linker de preguntas a artículos: vinculación con rigor jurídico.

Regla: No vincular sin cita inequívoca. Todo lo demás → pendiente_de_validacion.
"""

from __future__ import annotations

import sqlite3
import re
from typing import Any


class ExamQuestionLinker:
    """Vincular preguntas de examen a artículos."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def extract_article_citations(self, text: str) -> list[dict[str, Any]]:
        """
        Extraer citas de artículos del texto de una pregunta.

        Busca patrones como:
        - "art. 25"
        - "artículo 112.2"
        - "arts. 25-31"
        - "art. 5.1"
        """
        citations = []

        # Patrón: "art. 25", "artículo 112.2", "arts. 25-31"
        patterns = [
            r"art(?:\.?\s*)?(?:ículo)?\s+(\d+)(?:\.(\d+))?",  # art. 25, art. 25.1
            r"arts\.?\s+(\d+)\s*-\s*(\d+)",                    # arts. 25-31
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                if groups[0]:
                    citations.append({
                        "article_number": int(groups[0]),
                        "subsection": int(groups[1]) if groups[1] else None,
                        "match": match.group(0),
                    })

        return citations

    def find_articles_by_number(
        self,
        law_id: int,
        article_number: int,
        subsection: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Buscar artículos por número en una ley.

        Si subsection es None, devuelve todos con ese número.
        Si es un número específico, solo ese.
        """

        if subsection is not None:
            # Buscar article_ref = "25.1" o similar
            ref = f"{article_number}.{subsection}"
            rows = self.conn.execute(
                """
                SELECT id, article_ref, title, substr(text, 1, 200) as text_preview
                FROM articles
                WHERE law_id = ? AND article_ref = ?
                """,
                (law_id, ref)
            ).fetchall()
        else:
            # Buscar article_ref = "25" o que comience con "25."
            rows = self.conn.execute(
                """
                SELECT id, article_ref, title, substr(text, 1, 200) as text_preview
                FROM articles
                WHERE law_id = ? AND (article_ref = ? OR article_ref LIKE ?)
                """,
                (law_id, str(article_number), f"{article_number}.%")
            ).fetchall()

        return [dict(row) for row in rows]

    def link_question_by_citation(
        self,
        exam_question_id: int,
        law_id: int,
        citations: list[dict[str, Any]] | None = None,
        enunciado: str | None = None
    ) -> list[int]:
        """
        Vincular pregunta a artículos basándose en citas en el enunciado.

        Estrategia:
        1. Si se proporcionan citations, usarlas
        2. Si no, extraerlas del enunciado
        3. Para cada cita, buscar el artículo
        4. Si hay un único artículo → vincular con confianza 1.0
        5. Si hay múltiples → crear link para cada con confianza 0.8
        6. Si no hay → crear link pendiente con confianza 0.0
        """
        if citations is None:
            if not enunciado:
                # Obtener enunciado de la pregunta
                row = self.conn.execute(
                    "SELECT enunciado FROM exam_questions WHERE id = ?",
                    (exam_question_id,)
                ).fetchone()
                enunciado = row[0] if row else ""

            citations = self.extract_article_citations(enunciado)

        if not citations:
            # Sin citas: crear link pendiente
            return self._create_pending_link(exam_question_id, law_id, None, 0.0)

        linked_article_ids = []

        for citation in citations:
            article_number = citation["article_number"]
            subsection = citation.get("subsection")

            articles = self.find_articles_by_number(law_id, article_number, subsection)

            if len(articles) == 1:
                # Cita inequívoca
                article_id = articles[0]["id"]
                self._create_article_link(
                    exam_question_id, law_id, article_id,
                    tipo_relacion="cita_directa",
                    confianza=1.0
                )
                linked_article_ids.append(article_id)

            elif len(articles) > 1:
                # Múltiples candidatos (ej. art. 25 existe en varios lugares)
                # Vincular todos con confianza menor
                for article in articles:
                    article_id = article["id"]
                    self._create_article_link(
                        exam_question_id, law_id, article_id,
                        tipo_relacion="cita_ambigua",
                        confianza=0.7
                    )
                    linked_article_ids.append(article_id)

            else:
                # Sin artículo encontrado
                return self._create_pending_link(
                    exam_question_id, law_id, None, 0.0,
                    notes=f"Cita no resuelta: {citation['match']}"
                )

        return linked_article_ids

    def _create_article_link(
        self,
        exam_question_id: int,
        law_id: int,
        article_id: int,
        tipo_relacion: str = "aplicacion",
        confianza: float = 1.0,
        notes: str | None = None
    ) -> int:
        """Crear una vinculación pregunta → artículo."""
        # Obtener topic_id
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
            INSERT OR IGNORE INTO exam_question_links(
                exam_question_id, topic_id, law_id, article_id,
                tipo_relacion, mapping_basis, confianza, validation_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                exam_question_id, topic_id, law_id, article_id,
                tipo_relacion, "curador", confianza, "validado"
            )
        )
        return int(cursor.lastrowid)

    def _create_pending_link(
        self,
        exam_question_id: int,
        law_id: int,
        article_id: int | None,
        confianza: float,
        notes: str | None = None
    ) -> list[int]:
        """Crear un link pendiente de validación."""
        cursor = self.conn.execute(
            """
            INSERT INTO exam_question_links(
                exam_question_id, law_id, article_id,
                tipo_relacion, mapping_basis, confianza, validation_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                exam_question_id, law_id, article_id,
                "desconocida", "curador", confianza, "pendiente_de_validacion"
            )
        )
        return [int(cursor.lastrowid)]

    def get_unlinked_questions(self, exam_paper_id: int) -> list[dict[str, Any]]:
        """Obtener preguntas sin vinculación."""
        rows = self.conn.execute(
            """
            SELECT eq.id, eq.numero, eq.enunciado,
                   (SELECT COUNT(*) FROM exam_question_links WHERE exam_question_id = eq.id) as link_count
            FROM exam_questions eq
            WHERE eq.exam_paper_id = ? AND link_count = 0
            ORDER BY eq.numero
            """,
            (exam_paper_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def get_link_coverage(self, exam_paper_id: int) -> dict[str, Any]:
        """Estadísticas de cobertura de vinculaciones."""
        total_q = self.conn.execute(
            "SELECT COUNT(*) FROM exam_questions WHERE exam_paper_id = ?",
            (exam_paper_id,)
        ).fetchone()[0]

        linked_q = self.conn.execute(
            """
            SELECT COUNT(DISTINCT exam_question_id)
            FROM exam_question_links eql
            INNER JOIN exam_questions eq ON eq.id = eql.exam_question_id
            WHERE eq.exam_paper_id = ? AND eql.validation_status = 'validado'
            """,
            (exam_paper_id,)
        ).fetchone()[0]

        pending_q = self.conn.execute(
            """
            SELECT COUNT(DISTINCT exam_question_id)
            FROM exam_question_links eql
            INNER JOIN exam_questions eq ON eq.id = eql.exam_question_id
            WHERE eq.exam_paper_id = ? AND eql.validation_status = 'pendiente_de_validacion'
            """,
            (exam_paper_id,)
        ).fetchone()[0]

        return {
            "total_questions": total_q,
            "linked": linked_q,
            "pending": pending_q,
            "unlinked": total_q - linked_q - pending_q,
            "coverage_percent": round(100 * linked_q / total_q, 1) if total_q > 0 else 0,
        }

#!/usr/bin/env python3
"""
Ola B2 Demo: Examen piloto con vinculación de preguntas.

Crea un examen de prueba con preguntas que citan artículos reales.
Demuestra el linker automático.
"""

from __future__ import annotations

import argparse
import sys

from src.core.db import connect
from src.tests.exambank_service import ExamBankService
from src.tests.exambank_linker import ExamQuestionLinker


def create_pilot_exam(conn) -> int:
    """Crear un examen piloto con 5 preguntas."""
    service = ExamBankService(conn)

    # Crear examen
    exam_id = service.create_exam_paper(
        convocatoria="2025/2026",
        anio=2025,
        bloque="Bloque 1",
        fase="OPE",
        fuente_oficial_url="https://dogv.gva.es/",
        notes="Examen piloto para demostración de B2"
    )
    print(f"[OK] Examen creado: exam_papers id={exam_id}")

    # Crear preguntas (citando artículos reales)
    preguntas = [
        {
            "numero": 1,
            "enunciado": "Según el artículo 25 de la Ley 39/2015, ¿cuál es el plazo máximo para resolver?",
            "opciones": [
                ("A", "3 meses", True),
                ("B", "6 meses", False),
                ("C", "1 año", False),
                ("D", "2 años", False),
            ]
        },
        {
            "numero": 2,
            "enunciado": "El artículo 112.2 de la CE establece las funciones del Gobierno. ¿Cuál es correcto?",
            "opciones": [
                ("A", "Dirigir la política interior", True),
                ("B", "Legislar solo en materias no delegadas", False),
                ("C", "Elegir al Presidente del Congreso", False),
                ("D", "Ratificar tratados internacionales", False),
            ]
        },
        {
            "numero": 3,
            "enunciado": "Art. 5.1 LGCA: Señale cuál es el ámbito territorial de aplicación",
            "opciones": [
                ("A", "Solo España", True),
                ("B", "España y Unión Europea", False),
                ("C", "Solo la Comunidad Autónoma", False),
                ("D", "Municipios de la provincia", False),
            ]
        },
    ]

    question_ids = []
    for pregunta in preguntas:
        q_id = service.create_exam_question(
            exam_paper_id=exam_id,
            numero=pregunta["numero"],
            enunciado=pregunta["enunciado"],
            respuesta_oficial=pregunta["opciones"][0][0]  # Opción correcta
        )
        question_ids.append(q_id)

        # Crear opciones
        for letra, texto, es_correcta in pregunta["opciones"]:
            service.create_exam_question_option(
                exam_question_id=q_id,
                letra=letra,
                texto=texto,
                es_correcta=es_correcta
            )

    print(f"[OK] {len(question_ids)} preguntas creadas")
    return exam_id, question_ids


def link_questions(conn, exam_id: int, question_ids: list[int]) -> None:
    """Vincular preguntas a artículos mediante extracción automática."""
    linker = ExamQuestionLinker(conn)

    # Asumimos que las leyes 1 (CE) y 2 (Ley 39/2015) existen
    # En un caso real, buscaríamos la ley por nombre o teniendo el contexto

    # Obtener leyes más comunes
    laws = conn.execute(
        "SELECT id, name FROM laws ORDER BY imported_at DESC LIMIT 10"
    ).fetchall()

    print(f"\n[OK] Buscando leyes para vincular...")
    for question_id in question_ids:
        row = conn.execute(
            "SELECT enunciado FROM exam_questions WHERE id = ?",
            (question_id,)
        ).fetchone()
        enunciado = row[0] if row else ""

        # Extraer citas
        citations = linker.extract_article_citations(enunciado)

        if citations:
            print(f"\n  Pregunta {question_id}: {len(citations)} citas detectadas")
            for citation in citations:
                print(f"    - {citation['match']}")

            # Intentar vincular a todas las leyes conocidas
            for law_id, law_name in laws:
                linked = linker.link_question_by_citation(
                    question_id, law_id, citations=citations, enunciado=enunciado
                )
                if linked:
                    print(f"    [OK] Vinculado a {law_name}")
                    break
        else:
            print(f"\n  Pregunta {question_id}: sin citas detectadas (pendiente)")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Demo Ola B2: Examen piloto con linker automático"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("OLA B2 DEMO: Examen piloto con vinculacion automatica")
    print("=" * 70)

    try:
        with connect() as conn:
            print("\nPaso 1: Crear examen piloto...")
            exam_id, question_ids = create_pilot_exam(conn)

            print("\nPaso 2: Vincular preguntas a artículos...")
            link_questions(conn, exam_id, question_ids)

            print("\nPaso 3: Estadísticas...")
            service = ExamBankService(conn)
            stats = service.count_exams()
            print(f"  Exámenes en BD: {stats}")
            print(f"  Preguntas en BD: {service.count_questions()}")
            print(f"  Links pregunta-articulo: {service.count_question_links()}")

            conn.commit()
            print("\n[OK] Demo completada")

        return 0

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

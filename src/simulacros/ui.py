"""UI integration for mock exams (Streamlit).

Provides exam creation, execution, scoring, and statistics visualization.
"""

from __future__ import annotations

import sqlite3
import streamlit as st
from datetime import datetime

from src.simulacros.service import ExamService, ExamServiceError
from src.core.db import connect


def get_exam_service() -> ExamService | None:
    """Get a fresh ExamService (no caching: avoids cross-thread sqlite errors)."""
    try:
        return ExamService(connect())
    except Exception as e:
        st.warning(f"Error initializing exam service: {e}")
        return None


def render_exam_creator() -> None:
    """Render interface to create and start a new mock exam (Ola E1)."""
    service = get_exam_service()
    if not service:
        st.error("Servicio de simulacros no disponible")
        return

    st.subheader("Crear nuevo simulacro")

    col1, col2 = st.columns(2)
    with col1:
        title = st.text_input(
            "Nombre del simulacro",
            value="Simulacro test",
        )
        num_questions = st.slider(
            "Número de preguntas",
            min_value=5,
            max_value=100,
            value=30,
            step=5,
        )

    with col2:
        time_limit = st.selectbox(
            "Límite de tiempo",
            [None, 30, 45, 60, 90, 120],
            format_func=lambda x: "Sin límite" if x is None else f"{x} min",
        )
        source = st.selectbox(
            "Fuente de preguntas",
            ["oficial", "ia", "mixto"],
            format_func=lambda x: {
                "oficial": "Banco oficial",
                "ia": "Generadas por IA",
                "mixto": "Mezcla oficial + IA",
            }.get(x, x),
        )

    if st.button("Crear y comenzar simulacro"):
        try:
            with st.spinner("Preparando simulacro..."):
                exam_id = service.create_exam(
                    title=title,
                    num_questions=num_questions,
                    time_limit_minutes=time_limit,
                    source_kind=source,
                )

                questions = service.select_exam_questions(
                    exam_id,
                    num_questions=num_questions,
                    source_kind=source,
                )

                if not questions:
                    st.error(f"No hay preguntas disponibles de tipo '{source}'")
                    return

                st.session_state.exam_id = exam_id
                st.session_state.exam_questions = questions
                st.session_state.exam_current = 0
                st.session_state.exam_answers = []
                st.success(f"Simulacro creado. {len(questions)} preguntas.")
                st.rerun()

        except ExamServiceError as e:
            st.error(f"Error creando simulacro: {e}")
        except Exception as e:
            st.error(f"Error inesperado: {e}")


def render_exam_execution() -> None:
    """Render interface to execute a mock exam (Ola E1)."""
    service = get_exam_service()
    if not service or "exam_id" not in st.session_state:
        return

    exam_id = st.session_state.exam_id
    questions = st.session_state.exam_questions
    current_idx = st.session_state.exam_current
    answers = st.session_state.exam_answers

    st.subheader("Simulacro en progreso")

    # Progress bar
    progress = (current_idx + 1) / len(questions)
    st.progress(progress)
    st.caption(f"Pregunta {current_idx + 1} de {len(questions)}")

    if current_idx < len(questions):
        question = questions[current_idx]

        # Display question
        with st.container(border=True):
            st.markdown(f"**{question['enunciado']}**")
            st.divider()

            # Options
            selected = st.radio(
                "Selecciona una respuesta:",
                [f"{o['letra']}) {o['texto']}" for o in question["opciones"]],
                key=f"q_{current_idx}",
                label_visibility="collapsed",
            )

            # Navigation
            col1, col2, col3 = st.columns(3)
            with col1:
                if current_idx > 0 and st.button("< Anterior"):
                    st.session_state.exam_current -= 1
                    st.rerun()

            with col2:
                if selected:
                    answer_letter = selected.split(")")[0].strip()
                    if st.button("Siguiente >"):
                        answers.append({
                            "question_idx": current_idx,
                            "user_answer": answer_letter,
                            "correct_answer": question["respuesta_correcta"],
                        })
                        st.session_state.exam_answers = answers

                        if current_idx < len(questions) - 1:
                            st.session_state.exam_current += 1
                            st.rerun()
                        else:
                            st.session_state.exam_finished = True
                            st.rerun()

            with col3:
                if st.button("Terminar ahora"):
                    st.session_state.exam_finished = True
                    st.rerun()

    if st.session_state.get("exam_finished", False):
        render_exam_results(service, exam_id, questions, answers)


def render_exam_results(
    service: ExamService,
    exam_id: int,
    questions: list,
    answers: list,
) -> None:
    """Render exam results and statistics (Ola E1)."""
    try:
        # Calculate final score
        correct_count = 0
        for answer in answers:
            if answer["user_answer"] == answer["correct_answer"]:
                correct_count += 1

        total = len(questions)
        score = (correct_count / total * 100) if total > 0 else 0

        # Finish exam
        result = service.finish_exam(exam_id)

        st.divider()
        st.subheader("Resultados del simulacro")

        # Score display
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Puntuación", f"{score:.1f}%")
        with col2:
            st.metric("Respuestas correctas", f"{correct_count}/{total}")
        with col3:
            status = "APROBADO" if score >= 60 else "SUSPENSO"
            st.metric("Estado", status)

        st.divider()

        # Detailed review
        st.markdown("### Revisión detallada")
        for i, answer in enumerate(answers):
            is_correct = answer["user_answer"] == answer["correct_answer"]
            icon = "✓" if is_correct else "✗"
            status_color = "green" if is_correct else "red"

            with st.expander(
                f"{icon} Pregunta {i+1}: {answer['user_answer']} {'correcta' if is_correct else 'incorrecta'}",
                expanded=False,
            ):
                question = questions[i]
                st.markdown(f"**Enunciado:** {question['enunciado']}")
                st.markdown(f"**Tu respuesta:** {answer['user_answer']}")
                st.markdown(
                    f"**Respuesta correcta:** {answer['correct_answer']}"
                    if not is_correct
                    else ""
                )

        # Clear session state
        if st.button("Hacer otro simulacro"):
            st.session_state.exam_id = None
            st.session_state.exam_questions = None
            st.session_state.exam_current = 0
            st.session_state.exam_answers = None
            st.session_state.exam_finished = False
            st.rerun()

    except ExamServiceError as e:
        st.error(f"Error finalizando simulacro: {e}")
    except Exception as e:
        st.error(f"Error inesperado: {e}")


def render_exam_history() -> None:
    """Render history of completed exams and statistics (Ola E1)."""
    service = get_exam_service()
    if not service:
        return

    st.subheader("Historial y estadísticas")

    # Performance summary
    stats = service.get_performance_summary()
    if stats["total_exams"] == 0:
        st.info("Sin simulacros completados aún.")
        return

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total simulacros", stats["total_exams"])
    with col2:
        st.metric("Puntuación promedio", f"{stats['avg_score']:.1f}%")
    with col3:
        st.metric("% aprobados", f"{stats['pass_rate']:.0f}%")
    with col4:
        st.metric("Mejor puntuación", f"{stats['best_score']:.1f}%")

    st.divider()

    # Recent exams
    history = service.get_exam_history()
    if history:
        st.markdown("### Últimos simulacros")
        for exam in history[:10]:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.caption(exam["title"])
            with col2:
                st.caption(f"Puntuación: {exam['score']:.1f}%")
            with col3:
                status = "✓ Aprobado" if exam["passed"] else "✗ Suspenso"
                st.caption(status)
            with col4:
                st.caption(exam["created_at"][:10])

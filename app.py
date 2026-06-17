from __future__ import annotations

import random
import time
from pathlib import Path

import pandas as pd
import streamlit as st

from src.core.db import connect, init_db
from src.core.export import export_anki_basic, export_table
from src.core.paths import LAW_SOURCES_DIR, ensure_runtime_dirs
from src.core.source_catalog import list_source_documents
from src.laws.importer import import_law
from src.mistakes.repository import ERROR_CAUSES, mistake_summary, record_attempt, weekly_summary
from src.reports.basic import dashboard_counts
from src.tests.repository import create_question, delete_question, get_question, list_questions, update_question


st.set_page_config(page_title="GVAdicto", layout="wide")
init_db()
ensure_runtime_dirs()


def rows_to_df(rows) -> pd.DataFrame:
    return pd.DataFrame([dict(row) for row in rows])


def load_laws():
    with connect() as conn:
        return conn.execute("SELECT * FROM laws ORDER BY imported_at DESC").fetchall()


def load_articles(search: str = "", law_id: int | None = None):
    query = """
        SELECT a.*, l.name AS norma
        FROM articles a
        JOIN laws l ON l.id = a.law_id
        WHERE 1 = 1
    """
    params: list = []
    if law_id:
        query += " AND a.law_id = ?"
        params.append(law_id)
    if search:
        query += " AND (a.article_ref LIKE ? OR a.text LIKE ? OR l.name LIKE ? OR COALESCE(a.topic, '') LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term, term])
    query += " ORDER BY l.name, a.article_ref LIMIT 500"
    with connect() as conn:
        return conn.execute(query, params).fetchall()


def question_payload(prefix: str = "", existing=None, article=None) -> dict:
    law_value = existing["norma"] if existing else (article["norma"] if article else "")
    article_value = existing["articulo"] if existing else (article["article_ref"] if article else "")
    source_value = existing["fuente"] if existing else (article["source"] if article else "")
    return {
        "norma": st.text_input("Norma", value=law_value, key=f"{prefix}norma"),
        "articulo": st.text_input("Articulo", value=article_value, key=f"{prefix}articulo"),
        "tema": st.text_input("Tema", value=existing["tema"] if existing else "", key=f"{prefix}tema"),
        "enunciado": st.text_area("Enunciado", value=existing["enunciado"] if existing else "", key=f"{prefix}enunciado"),
        "opcion_a": st.text_input("Opcion A", value=existing["opcion_a"] if existing else "", key=f"{prefix}a"),
        "opcion_b": st.text_input("Opcion B", value=existing["opcion_b"] if existing else "", key=f"{prefix}b"),
        "opcion_c": st.text_input("Opcion C", value=existing["opcion_c"] if existing else "", key=f"{prefix}c"),
        "opcion_d": st.text_input("Opcion D", value=existing["opcion_d"] if existing else "", key=f"{prefix}d"),
        "respuesta_correcta": st.selectbox(
            "Respuesta correcta",
            ["A", "B", "C", "D"],
            index=["A", "B", "C", "D"].index(existing["respuesta_correcta"]) if existing else 0,
            key=f"{prefix}correcta",
        ),
        "explicacion": st.text_area("Explicacion con fuente", value=existing["explicacion"] if existing else "", key=f"{prefix}exp"),
        "fuente": st.text_input("Fuente", value=source_value, key=f"{prefix}fuente"),
        "dificultad": st.selectbox(
            "Dificultad",
            ["baja", "media", "alta"],
            index=["baja", "media", "alta"].index(existing["dificultad"]) if existing else 1,
            key=f"{prefix}dif",
        ),
        "etiquetas": st.text_input("Etiquetas", value=existing["etiquetas"] if existing else "", key=f"{prefix}tags"),
        "requiere_revision": st.checkbox(
            "Requiere revision",
            value=bool(existing["requiere_revision"]) if existing else False,
            key=f"{prefix}rev",
        ),
    }


def validate_question(data: dict) -> list[str]:
    required = [
        "norma",
        "articulo",
        "enunciado",
        "opcion_a",
        "opcion_b",
        "opcion_c",
        "opcion_d",
        "respuesta_correcta",
        "explicacion",
        "fuente",
    ]
    return [field for field in required if not str(data.get(field, "")).strip()]


st.title("GVAdicto")
st.caption("MVP local-first para oposiciones GVA. Contenido juridico siempre vinculado a fuente.")

tabs = st.tabs(["Inicio", "Fuentes", "Importar leyes", "Articulos", "Preguntas", "Modo test", "Fallos", "Informes y CSV"])

with tabs[0]:
    counts = dashboard_counts()
    cols = st.columns(len(counts))
    for col, (label, value) in zip(cols, counts.items()):
        col.metric(label.capitalize(), value)

with tabs[1]:
    st.subheader("Catalogo de fuentes")
    sources = list_source_documents()
    if sources:
        st.dataframe(rows_to_df(sources), use_container_width=True, hide_index=True)
    else:
        st.info("No hay fuentes catalogadas. Carga un manifiesto con scripts/import_source_manifest.py.")

with tabs[2]:
    st.subheader("Importar TXT/MD")
    uploaded = st.file_uploader("Archivo de ley", type=["txt", "md"])
    law_name = st.text_input("Nombre de la norma")
    if st.button("Importar ley", disabled=uploaded is None):
        source_path = LAW_SOURCES_DIR / uploaded.name
        source_path.write_bytes(uploaded.getbuffer())
        law_id = import_law(source_path, law_name or Path(uploaded.name).stem)
        st.success(f"Ley importada con id {law_id}. Los articulos quedan pendientes de validacion.")

    laws = load_laws()
    if laws:
        st.dataframe(rows_to_df(laws), use_container_width=True, hide_index=True)

with tabs[3]:
    st.subheader("Articulos importados")
    laws = load_laws()
    law_options = {"Todas": None} | {row["name"]: row["id"] for row in laws}
    selected_law = st.selectbox("Norma", list(law_options.keys()))
    search = st.text_input("Buscar por norma, articulo, tema o texto")
    articles = load_articles(search, law_options[selected_law])
    st.dataframe(rows_to_df(articles), use_container_width=True, hide_index=True)

    if articles:
        article_map = {f'{row["norma"]} - art. {row["article_ref"]}': row for row in articles}
        selected_article = st.selectbox("Crear pregunta desde articulo", list(article_map.keys()))
        with st.expander("Ver texto y crear pregunta"):
            article = article_map[selected_article]
            st.text_area("Texto fuente", value=article["text"], height=220, disabled=True)
            data = question_payload("from_article_", article=article)
            data["law_id"] = article["law_id"]
            data["article_id"] = article["id"]
            if st.button("Guardar pregunta desde articulo"):
                missing = validate_question(data)
                if missing:
                    st.error("Campos obligatorios pendientes: " + ", ".join(missing))
                else:
                    create_question(data)
                    st.success("Pregunta guardada.")

with tabs[4]:
    st.subheader("CRUD basico de preguntas")
    with st.expander("Crear pregunta manual", expanded=True):
        data = question_payload("new_")
        if st.button("Guardar pregunta manual"):
            missing = validate_question(data)
            if missing:
                st.error("Campos obligatorios pendientes: " + ", ".join(missing))
            else:
                create_question(data)
                st.success("Pregunta guardada.")

    questions = list_questions()
    if questions:
        st.dataframe(rows_to_df(questions), use_container_width=True, hide_index=True)
        question_ids = [int(row["id"]) for row in questions]
        selected_id = st.selectbox("Editar/eliminar pregunta", question_ids)
        existing = get_question(selected_id)
        with st.expander("Editar pregunta seleccionada"):
            edited = question_payload("edit_", existing=existing)
            col1, col2 = st.columns(2)
            if col1.button("Actualizar pregunta"):
                missing = validate_question(edited)
                if missing:
                    st.error("Campos obligatorios pendientes: " + ", ".join(missing))
                else:
                    update_question(selected_id, edited)
                    st.success("Pregunta actualizada.")
            if col2.button("Eliminar pregunta"):
                delete_question(selected_id)
                st.warning("Pregunta eliminada.")

with tabs[5]:
    st.subheader("Modo test")
    questions = list_questions()
    if not questions:
        st.info("Crea preguntas para iniciar un test.")
    else:
        if "test_question_id" not in st.session_state or st.button("Nueva pregunta aleatoria"):
            st.session_state.test_question_id = int(random.choice(questions)["id"])
            st.session_state.test_started_at = time.time()
            st.session_state.test_checked = False

        question = get_question(st.session_state.test_question_id)
        st.markdown(f"**{question['norma']} - articulo {question['articulo']}**")
        st.write(question["enunciado"])
        answer = st.radio(
            "Respuesta",
            ["A", "B", "C", "D"],
            format_func=lambda key: f"{key}. {question[f'opcion_{key.lower()}']}",
        )
        cause = st.selectbox("Causa del error si fallas", [""] + ERROR_CAUSES)
        comment = st.text_input("Comentario")
        if st.button("Corregir y guardar intento"):
            elapsed = round(time.time() - st.session_state.get("test_started_at", time.time()), 1)
            record_attempt(
                int(question["id"]),
                answer,
                question["respuesta_correcta"],
                elapsed,
                cause or None,
                comment or None,
            )
            if answer == question["respuesta_correcta"]:
                st.success("Correcta.")
            else:
                st.error(f"Incorrecta. Correcta: {question['respuesta_correcta']}")
            st.info(question["explicacion"])
            st.caption(f"Fuente: {question['fuente']}")

with tabs[6]:
    st.subheader("Base de fallos")
    summary = mistake_summary()
    if summary:
        st.dataframe(rows_to_df(summary), use_container_width=True, hide_index=True)
    else:
        st.info("Todavia no hay intentos registrados.")

with tabs[7]:
    st.subheader("Informes y exportaciones")
    counts = dashboard_counts()
    st.json(counts)

    weekly = weekly_summary()
    if weekly:
        st.write("Evolucion semanal")
        st.dataframe(rows_to_df(weekly), use_container_width=True, hide_index=True)

    col1, col2, col3 = st.columns(3)
    if col1.button("Exportar preguntas CSV"):
        path = export_table("questions")
        st.success(f"Exportado: {path}")
    if col2.button("Exportar intentos CSV"):
        path = export_table("attempts")
        st.success(f"Exportado: {path}")
    if col3.button("Exportar Anki CSV"):
        path = export_anki_basic()
        st.success(f"Exportado: {path}")

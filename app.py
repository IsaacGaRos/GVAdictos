from __future__ import annotations

import random
import re
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
from src.studies.annotations import (
    ANNOTATION_COLORS,
    ANNOTATION_TYPES,
    create_annotation,
    delete_annotation,
    get_annotations_for_topic,
    update_annotation,
)
from src.tests.repository import create_question, delete_question, get_question, list_questions, update_question


st.set_page_config(page_title="GVAdictos", layout="wide")
init_db()
ensure_runtime_dirs()

DEFAULT_ARTICLES_PAGE_SIZE = 30


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


def load_topics_by_part(part: str):
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM topics WHERE part = ? ORDER BY topic_number",
            (part,)
        ).fetchall()


_BOE_HEADER_RE = re.compile(
    r'^\s*(BOLET[IÍ]N OFICIAL DEL ESTADO|LEGISLACI[OÓ]N CONSOLIDADA|P[aá]gina\s+\d+)\s*$',
    re.IGNORECASE,
)
_TOC_LINE_RE = re.compile(r'\.{4,}\s*\d+\s*$')


def clean_article_text(text: str) -> str:
    """Strip BOE page headers and index lines from article text."""
    if not text:
        return text
    lines = text.split('\n')
    cleaned = [line for line in lines if not _BOE_HEADER_RE.match(line)]
    return '\n'.join(cleaned).strip()


def is_toc_stub(text: str) -> bool:
    """Return True if text is only a TOC/index line (not useful for studying)."""
    return bool(text and len(text) < 200 and _TOC_LINE_RE.search(text))


def topic_has_fine_mapping(topic_id: int) -> bool:
    with connect() as conn:
        n = conn.execute(
            "SELECT COUNT(*) FROM topic_sources WHERE topic_id=? AND article_id IS NOT NULL",
            (topic_id,)
        ).fetchone()[0]
        return n > 0


def load_topic_normativa(topic_id: int):
    with connect() as conn:
        return conn.execute(
            """
            SELECT
                l.id,
                l.name,
                COUNT(DISTINCT ts.article_id) AS mapped_articles,
                COUNT(ts.id) AS mapping_rows,
                GROUP_CONCAT(DISTINCT ts.normative_reference) AS normative_reference
            FROM topic_sources ts
            JOIN laws l ON l.id = ts.law_id
            WHERE ts.topic_id = ? AND ts.law_id IS NOT NULL
            GROUP BY l.id, l.name
            ORDER BY l.name
            """,
            (topic_id,)
        ).fetchall()


def load_topic_mapped_articles(topic_id: int, law_id: int):
    """Articles explicitly delimited for this topic+law (topic_sources.article_id)."""
    with connect() as conn:
        return conn.execute(
            """
            SELECT DISTINCT a.*, l.name AS norma
            FROM topic_sources ts
            JOIN articles a ON a.id = ts.article_id
            JOIN laws l ON l.id = a.law_id
            WHERE ts.topic_id = ? AND a.law_id = ?
            ORDER BY CAST(a.article_ref AS INTEGER), a.article_ref
            """,
            (topic_id, law_id),
        ).fetchall()


def load_law_all_articles(law_id: int):
    """Every article of a law (used only behind an explicit 'whole norm' expander)."""
    with connect() as conn:
        return conn.execute(
            """
            SELECT a.*, l.name AS norma
            FROM articles a
            JOIN laws l ON l.id = a.law_id
            WHERE a.law_id = ?
            ORDER BY CAST(a.article_ref AS INTEGER), a.article_ref
            """,
            (law_id,),
        ).fetchall()


def law_has_fine_mapping(topic_id: int, law_id: int) -> bool:
    with connect() as conn:
        n = conn.execute(
            "SELECT COUNT(*) FROM topic_sources WHERE topic_id=? AND law_id=? AND article_id IS NOT NULL",
            (topic_id, law_id),
        ).fetchone()[0]
        return n > 0


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


def annotation_label(annotation_type: str) -> str:
    labels = {
        "note": "Nota",
        "highlight": "Subrayado",
        "doubt": "Duda",
        "bookmark": "Marcador",
    }
    return labels.get(annotation_type, annotation_type)


def color_label(color: str) -> str:
    labels = {
        "": "Sin color",
        "yellow": "Amarillo",
        "green": "Verde",
        "blue": "Azul",
        "pink": "Rosa",
    }
    return labels.get(color, color)


def article_option_label(article) -> str:
    title = article["title"] or "Sin titulo"
    short_title = title[:55] + ("..." if len(title) > 55 else "")
    return f"{article['norma']} - art. {article['article_ref']} - {short_title}"


def annotation_target_options(articles: list) -> dict[str, int | None]:
    options: dict[str, int | None] = {"Tema completo": None}
    for article in articles:
        options[article_option_label(article)] = int(article["id"])
    return options


def render_article_card(article, topic_id: int) -> None:
    """Render one article: clean legal text as primary, ampliaciones in an expander."""
    display_text = clean_article_text(article['text'] or '')
    if is_toc_stub(display_text):
        return
    with st.container(border=True):
        col_ref, col_title = st.columns([1, 4])
        with col_ref:
            st.markdown(f"**Art. {article['article_ref']}**")
        with col_title:
            st.markdown(f"**{article['title'] or 'Sin titulo'}**")
        if display_text:
            lines = display_text.count('\n') + 1
            height = max(120, min(lines * 22 + 40, 500))
            st.text_area(
                f"Texto art. {article['article_ref']}",
                value=display_text,
                height=height,
                disabled=True,
                key=f"art_{topic_id}_{article['id']}",
                label_visibility="collapsed",
            )
        # Ampliaciones / notes channel: real annotations only, never invented doctrine
        ampliaciones = [
            a for a in get_annotations_for_topic(topic_id)
            if a['article_id'] == article['id']
        ]
        with st.expander(
            f"Ampliacion y notas ({len(ampliaciones)})", expanded=False
        ):
            if ampliaciones:
                for a in ampliaciones:
                    label = annotation_label(a['annotation_type'])
                    body = a['note_text'] or a['selected_text'] or a['manual_reference'] or ''
                    st.markdown(f"- **{label}:** {body}")
            else:
                st.caption(
                    "Sin ampliacion doctrinal ni notas para este articulo. "
                    "Las ampliaciones (doctrina, temario, Autentica) se anaden como "
                    "anotaciones y aparecen aqui, nunca mezcladas con el texto legal."
                )


def render_paginated_articles(articles: list, topic_id: int, key_prefix: str) -> None:
    """Render every article in a stable order with lightweight pagination."""
    total = len(articles)
    if total == 0:
        st.info("No hay articulos importados para esta norma.")
        return

    page_size_options = [20, 30, 50, 100]
    page_size_key = f"{key_prefix}_page_size"
    page_key = f"{key_prefix}_page"

    controls = st.columns([1, 1, 3])
    with controls[0]:
        page_size = st.selectbox(
            "Articulos por pagina",
            page_size_options,
            index=page_size_options.index(DEFAULT_ARTICLES_PAGE_SIZE),
            key=page_size_key,
        )

    total_pages = max(1, (total + page_size - 1) // page_size)
    with controls[1]:
        page = st.number_input(
            "Pagina",
            min_value=1,
            max_value=total_pages,
            value=1,
            step=1,
            key=page_key,
        )

    page = int(page)
    start = (page - 1) * page_size
    end = min(start + page_size, total)
    st.caption(
        f"Mostrando articulos {start + 1}-{end} de {total}. "
        f"Orden: numero de articulo ascendente."
    )
    for article in articles[start:end]:
        render_article_card(article, topic_id)


def render_study_annotations(topic, articles: list) -> None:
    st.divider()
    st.markdown("#### Anotaciones")

    target_options = annotation_target_options(articles)
    with st.expander("Nueva anotacion", expanded=False):
        col_type, col_target, col_color = st.columns([1, 3, 1])
        with col_type:
            new_type = st.selectbox(
                "Tipo",
                ANNOTATION_TYPES,
                format_func=annotation_label,
                key=f"ann_new_type_{topic['id']}",
            )
        with col_target:
            new_target = st.selectbox(
                "Vincular a",
                list(target_options.keys()),
                key=f"ann_new_target_{topic['id']}",
            )
        with col_color:
            new_color = st.selectbox(
                "Color",
                ANNOTATION_COLORS,
                format_func=color_label,
                key=f"ann_new_color_{topic['id']}",
            )

        new_selected_text = st.text_area(
            "Texto seleccionado o fragmento",
            key=f"ann_new_selected_{topic['id']}",
            height=90,
        )
        new_manual_reference = st.text_input(
            "Referencia manual",
            placeholder="Ejemplo: art. 112.2, parrafo tercero",
            key=f"ann_new_reference_{topic['id']}",
        )
        new_note_text = st.text_area(
            "Nota",
            key=f"ann_new_note_{topic['id']}",
            height=110,
        )

        if st.button("Guardar anotacion", key=f"ann_new_save_{topic['id']}"):
            has_content = any(
                value.strip()
                for value in [new_selected_text, new_manual_reference, new_note_text]
            )
            if new_type != "bookmark" and not has_content:
                st.error("Anade texto, referencia o nota antes de guardar.")
            else:
                create_annotation(
                    int(topic["id"]),
                    target_options[new_target],
                    new_type,
                    new_selected_text.strip() or None,
                    new_manual_reference.strip() or None,
                    new_note_text.strip() or None,
                    new_color or None,
                )
                st.success("Anotacion guardada.")

    annotations = get_annotations_for_topic(int(topic["id"]))
    if not annotations:
        st.info("Este tema aun no tiene anotaciones.")
        return

    st.caption(f"{len(annotations)} anotaciones guardadas")
    for annotation in annotations:
        target = "Tema completo"
        if annotation["article_id"]:
            article_title = annotation["article_title"] or "Sin titulo"
            target = f"{annotation['law_name']} - art. {annotation['article_ref']} - {article_title}"

        with st.container(border=True):
            col_info, col_date = st.columns([3, 1])
            with col_info:
                st.markdown(f"**{annotation_label(annotation['annotation_type'])}**")
                st.caption(target)
            with col_date:
                st.caption(f"Actualizada: {annotation['updated_at']}")

            if annotation["selected_text"]:
                st.text_area(
                    "Texto guardado",
                    value=annotation["selected_text"],
                    height=80,
                    disabled=True,
                    key=f"ann_selected_read_{annotation['id']}",
                )
            if annotation["manual_reference"]:
                st.caption(f"Referencia: {annotation['manual_reference']}")
            if annotation["note_text"]:
                st.write(annotation["note_text"])
            if annotation["color"]:
                st.caption(f"Color: {color_label(annotation['color'])}")

            with st.expander("Editar anotacion"):
                edit_target_options = dict(target_options)
                edit_type = st.selectbox(
                    "Tipo",
                    ANNOTATION_TYPES,
                    index=ANNOTATION_TYPES.index(annotation["annotation_type"]),
                    format_func=annotation_label,
                    key=f"ann_edit_type_{annotation['id']}",
                )
                current_target_label = "Tema completo"
                for label, article_id in target_options.items():
                    if article_id == annotation["article_id"]:
                        current_target_label = label
                        break
                if annotation["article_id"] and current_target_label == "Tema completo":
                    current_target_label = target
                    edit_target_options[current_target_label] = int(annotation["article_id"])
                edit_target = st.selectbox(
                    "Vincular a",
                    list(edit_target_options.keys()),
                    index=list(edit_target_options.keys()).index(current_target_label),
                    key=f"ann_edit_target_{annotation['id']}",
                )
                current_color = annotation["color"] if annotation["color"] in ANNOTATION_COLORS else ""
                edit_color = st.selectbox(
                    "Color",
                    ANNOTATION_COLORS,
                    index=ANNOTATION_COLORS.index(current_color),
                    format_func=color_label,
                    key=f"ann_edit_color_{annotation['id']}",
                )
                edit_selected_text = st.text_area(
                    "Texto seleccionado o fragmento",
                    value=annotation["selected_text"] or "",
                    height=90,
                    key=f"ann_edit_selected_{annotation['id']}",
                )
                edit_manual_reference = st.text_input(
                    "Referencia manual",
                    value=annotation["manual_reference"] or "",
                    key=f"ann_edit_reference_{annotation['id']}",
                )
                edit_note_text = st.text_area(
                    "Nota",
                    value=annotation["note_text"] or "",
                    height=110,
                    key=f"ann_edit_note_{annotation['id']}",
                )
                col_update, col_delete = st.columns(2)
                if col_update.button("Actualizar", key=f"ann_update_{annotation['id']}"):
                    update_annotation(
                        int(annotation["id"]),
                        edit_target_options[edit_target],
                        edit_type,
                        edit_selected_text.strip() or None,
                        edit_manual_reference.strip() or None,
                        edit_note_text.strip() or None,
                        edit_color or None,
                    )
                    st.success("Anotacion actualizada.")
                if col_delete.button("Eliminar", key=f"ann_delete_{annotation['id']}"):
                    delete_annotation(int(annotation["id"]))
                    st.warning("Anotacion eliminada.")


st.title("GVAdictos")
st.caption("MVP local-first para oposiciones GVA. Contenido juridico siempre vinculado a fuente.")

tabs = st.tabs(["Inicio", "Fuentes", "Importar leyes", "Articulos", "Preguntas", "Estudiar", "Modo test", "Fallos", "Informes y CSV"])

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
    st.subheader("Estudiar por tema")

    part_label = st.radio(
        "Parte del temario",
        ["general", "especial"],
        format_func=lambda p: "Parte general" if p == "general" else "Parte especifica",
        horizontal=True,
    )

    topics = load_topics_by_part(part_label)
    if not topics:
        st.info(f"No hay temas en la parte {part_label}.")
    else:
        # Full topic titles, never truncated
        topic_options = {
            f"Tema {row['topic_number']:02d} - {row['official_text']}": row
            for row in topics
        }
        selected_topic_text = st.selectbox(
            "Selecciona tema", list(topic_options.keys())
        )
        selected_topic = topic_options[selected_topic_text]

        st.divider()
        part_name = "Parte general" if part_label == "general" else "Parte especifica"
        st.markdown(f"### Tema {selected_topic['topic_number']} ({part_name})")
        st.write(selected_topic['official_text'])
        if selected_topic['section']:
            st.caption(f"Seccion: {selected_topic['section']}")

        st.divider()

        articles_for_annotations: list = []
        normativa = load_topic_normativa(selected_topic['id'])
        if not normativa:
            st.warning(
                "Este tema aun no tiene normativa vinculada en la validacion. "
                "Pendiente de delimitacion."
            )
        else:
            st.markdown("#### Normas de este tema")
            st.caption(
                f"{len(normativa)} norma(s) vinculada(s) especificamente a este tema."
            )
            for norma in normativa:
                law_id = norma['id']
                mapped = load_topic_mapped_articles(selected_topic['id'], law_id)
                has_fine = law_has_fine_mapping(selected_topic['id'], law_id)
                articles_for_annotations.extend(mapped)

                with st.container(border=True):
                    st.markdown(f"##### {norma['name']}")
                    if has_fine and mapped:
                        st.caption(
                            f"{len(mapped)} articulo(s) delimitado(s) para este tema "
                            "(validado contra fuente oficial, pendiente revision humana)."
                        )
                        search_art = st.text_input(
                            "Filtrar por numero o titulo",
                            key=f"search_{selected_topic['id']}_{law_id}",
                        )
                        shown = [
                            a for a in mapped
                            if not search_art
                            or search_art.lower() in str(a['article_ref']).lower()
                            or search_art.lower() in (a['title'] or '').lower()
                        ]
                        for article in shown:
                            render_article_card(article, selected_topic['id'])
                        if not shown:
                            st.info(f"Ningun articulo coincide con '{search_art}'.")
                    else:
                        # No fine delimitation: be explicit, do NOT present the whole
                        # law as if it were this topic's articles.
                        st.warning(
                            "Sin delimitacion fina de articulos para este tema. "
                            "Aun no esta validado que subconjunto de esta norma entra "
                            "en el tema, asi que no se muestran articulos como si fueran "
                            "los del tema. Prioridad: delimitar con temario de Autentica."
                        )
                        all_articles = load_law_all_articles(law_id)
                        with st.expander(
                            f"Ver toda la norma sin delimitar ({len(all_articles)} articulos)",
                            expanded=False,
                        ):
                            st.caption(
                                "Referencia completa de la norma. NO equivale a los "
                                "articulos concretos del tema."
                            )
                            render_paginated_articles(
                                all_articles,
                                selected_topic['id'],
                                f"all_articles_{selected_topic['id']}_{law_id}",
                            )

        render_study_annotations(selected_topic, articles_for_annotations)

with tabs[6]:
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

with tabs[7]:
    st.subheader("Base de fallos")
    summary = mistake_summary()
    if summary:
        st.dataframe(rows_to_df(summary), use_container_width=True, hide_index=True)
    else:
        st.info("Todavia no hay intentos registrados.")

with tabs[8]:
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

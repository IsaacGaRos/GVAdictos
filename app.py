from __future__ import annotations

import random
import re
import time
from datetime import datetime
from pathlib import Path

# Carga variables de entorno desde .env (ANTHROPIC_API_KEY, STRIPE_API_KEY, etc.)
# antes de importar servicios que las leen en su inicializacion.
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

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
import json as _json
from src.ai.ui import render_ai_insights, render_ai_question_generator
from src.audio.global_player import (
    tts_button, render_global_player, render_article_tts, render_tts_button_iframe,
)
from src.search.ui import render_related_articles
from src.simulacros.ui import render_exam_creator, render_exam_execution, render_exam_history
from src.accounts.schema import ensure_accounts_tables
from src.accounts.service import AuthService, AuthError
from src.study.repository import StudyRepository
from src.study.service import StudyService, StudyTarget, HIGHLIGHT_COLORS
from src.study.rendering import render_text_with_highlights
from src.study.doubts import (
    ensure_doubts_table,
    save_doubt,
    get_doubt,
    delete_doubt,
    list_doubts,
    resolve_doubt,
)


st.set_page_config(page_title="GVAdictos", layout="wide")

# ─── INICIALIZACIÓN ──────────────────────────────────────────────────────────

def _migrate_highlights_color_constraint(conn) -> None:
    """Elimina el CHECK constraint de color en study_highlights si todavía existe.

    SQLite no soporta DROP CONSTRAINT, así que hay que recrear la tabla.
    Se detecta comprobando si el CREATE TABLE en sqlite_master contiene la cláusula CHECK de color.
    """
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='study_highlights'"
    ).fetchone()
    if not row:
        return  # tabla aún no existe
    ddl = row[0] or ""
    if "CHECK(color IN" not in ddl and "CHECK (color IN" not in ddl:
        return  # ya migrada
    conn.executescript("""
        PRAGMA foreign_keys = OFF;

        ALTER TABLE study_highlights RENAME TO _study_highlights_old;

        CREATE TABLE study_highlights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER REFERENCES articles(id) ON DELETE SET NULL,
            law_id_snapshot INTEGER,
            article_ref_snapshot TEXT,
            anchor_key TEXT,
            selected_text TEXT NOT NULL,
            start_offset INTEGER,
            end_offset INTEGER,
            color TEXT NOT NULL DEFAULT 'yellow',
            note_text TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            archived_at TEXT,
            CHECK(start_offset IS NULL OR end_offset IS NULL OR start_offset <= end_offset)
        );

        INSERT INTO study_highlights SELECT * FROM _study_highlights_old;

        DROP TABLE _study_highlights_old;

        PRAGMA foreign_keys = ON;
    """)


def _ensure_extra_tables() -> None:
    """Crea tablas de usuarios, oposiciones y suscripciones si no existen."""
    with connect() as conn:
        _migrate_highlights_color_constraint(conn)
        ensure_accounts_tables(conn)
        ensure_doubts_table(conn)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS oposiciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                nombre TEXT NOT NULL,
                administracion TEXT NOT NULL DEFAULT 'GVA',
                activa INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS user_oposicion_enrollment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                oposicion_id INTEGER NOT NULL REFERENCES oposiciones(id) ON DELETE CASCADE,
                enrolled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, oposicion_id)
            );

            CREATE TABLE IF NOT EXISTS subscriptions_local (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                plan TEXT NOT NULL DEFAULT 'free',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_color_presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                hex_color TEXT NOT NULL,
                label TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        # Insertar oposiciones de muestra si no hay ninguna
        n = conn.execute("SELECT COUNT(*) FROM oposiciones").fetchone()[0]
        if n == 0:
            conn.executemany(
                "INSERT OR IGNORE INTO oposiciones(code, nombre, administracion) VALUES (?,?,?)",
                [
                    ("A1-01-GVA-2025", "Oposición A1-01 GVA 2025 (Escala Superior)", "GVA"),
                    ("C1-01-GVA-2025", "Oposición C1-01 GVA 2025 (Gestión)", "GVA"),
                    ("A2-01-GVA-2025", "Oposición A2-01 GVA 2025 (Administración General)", "GVA"),
                ],
            )
            conn.commit()


init_db()
ensure_runtime_dirs()
_ensure_extra_tables()

DEFAULT_ARTICLES_PAGE_SIZE = 30

# ─── AUTH HELPERS ─────────────────────────────────────────────────────────────

def _get_auth_service():
    return AuthService(connect())


def current_user() -> dict | None:
    """Devuelve el usuario actual desde session_state o None si no hay sesión."""
    token = st.session_state.get("auth_token")
    if not token:
        return None
    try:
        user = _get_auth_service().get_current_user(token)
        return user
    except Exception:
        return None


def current_user_id() -> int:
    """Devuelve el user_id actual. 1 si no hay sesión (modo local sin cuenta)."""
    user = current_user()
    return user["id"] if user else 1


def get_user_plan(user_id: int) -> str:
    """Devuelve el plan del usuario: free / pro / premium."""
    with connect() as conn:
        row = conn.execute(
            "SELECT plan FROM subscriptions_local WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row["plan"] if row else "free"


def get_study_service() -> StudyService | None:
    """Devuelve un StudyService fresco (conexion nueva por llamada).

    Sin cache: una conexion sqlite cacheada quedaria atada a un hilo y los
    reruns de Streamlit pueden ejecutarse en otro hilo.
    """
    try:
        return StudyService(StudyRepository(connect()))
    except Exception:
        return None


def study_mutate(action):
    """Ejecuta una escritura de estudio y hace commit.

    El StudyRepository no hace commit por si mismo; aqui garantizamos el commit
    y el cierre de la conexion. `action` recibe el StudyService y devuelve un valor.
    """
    conn = connect()
    try:
        svc = StudyService(StudyRepository(conn))
        result = action(svc)
        conn.commit()
        return result
    finally:
        conn.close()


def icon_toggle(icon: str, label: str, key: str, help_text: str = "") -> bool:
    """Render an icon button that toggles section visibility.

    Returns True if the section should be visible.
    """
    # Initialize state if not present
    if key not in st.session_state:
        st.session_state[key] = False

    def toggle_state():
        st.session_state[key] = not st.session_state[key]

    col1, col2 = st.columns([0.08, 0.92])
    with col1:
        st.button(icon, key=f"{key}_btn", help=help_text, use_container_width=True, on_click=toggle_state)

    with col2:
        st.caption(label)

    return st.session_state.get(key, False)


HIGHLIGHT_COLOR_LABELS = {
    "yellow": "🟡 Amarillo",
    "green": "🟢 Verde",
    "blue": "🔵 Azul",
    "pink": "🩷 Rosa",
    "purple": "🟣 Morado",
    "red": "🔴 Rojo",
}

# Colores predefinidos con sus valores CSS/hex
PRESET_COLORS = [
    ("yellow", "#FFEB3B", "🟡 Amarillo"),
    ("green",  "#4CAF50", "🟢 Verde"),
    ("blue",   "#2196F3", "🔵 Azul"),
    ("pink",   "#FF69B4", "🩷 Rosa"),
    ("purple", "#9C27B0", "🟣 Morado"),
    ("red",    "#F44336", "🔴 Rojo"),
    ("#FF9800", "#FF9800", "🟠 Naranja"),
    ("#00BCD4", "#00BCD4", "🔵 Cyan"),
]


def load_color_presets(user_id: int = 1) -> list:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM user_color_presets WHERE user_id=? ORDER BY id", (user_id,)
        ).fetchall()
        return [dict(r) if not isinstance(r, dict) else r for r in rows]


def save_color_preset(hex_color: str, label: str, user_id: int = 1) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO user_color_presets(user_id, hex_color, label) VALUES(?,?,?)",
            (user_id, hex_color, label),
        )
        conn.commit()


def delete_color_preset(preset_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM user_color_presets WHERE id=?", (preset_id,))
        conn.commit()


def render_color_selector(key_prefix: str) -> str:
    """Render a color picker with presets, custom, and saved colors.

    Returns the selected color value (named or hex string).
    """
    mode = st.radio(
        "Tipo de color",
        ["Predefinido", "Personalizado", "Mis colores"],
        horizontal=True,
        key=f"{key_prefix}_color_mode",
        label_visibility="collapsed",
    )

    if mode == "Predefinido":
        options = {label: key for key, _css, label in PRESET_COLORS}
        selected_label = st.radio(
            "Color",
            list(options.keys()),
            horizontal=True,
            key=f"{key_prefix}_preset_pick",
            label_visibility="collapsed",
        )
        return options[selected_label]

    if mode == "Personalizado":
        col_pick, col_lbl, col_save = st.columns([1, 2, 1])
        with col_pick:
            hex_color = st.color_picker("Color", "#FFAA00", key=f"{key_prefix}_custom_hex")
        with col_lbl:
            lbl = st.text_input(
                "Etiqueta (opcional)", key=f"{key_prefix}_custom_lbl",
                placeholder="p.ej. Definición clave",
            )
        with col_save:
            st.write("")
            if st.button("💾 Guardar", key=f"{key_prefix}_save_color", help="Guardar en Mis colores"):
                if lbl.strip():
                    save_color_preset(hex_color, lbl.strip(), current_user_id())
                    st.success("Color guardado")
                else:
                    st.warning("Escribe una etiqueta antes de guardar")
        return hex_color

    # mode == "Mis colores"
    presets = load_color_presets(current_user_id())
    if not presets:
        st.info("No tienes colores guardados. Créalos en 'Personalizado'.")
        return "yellow"
    label_map = {f"{p['label']}  ({p['hex_color']})": p for p in presets}
    chosen_lbl = st.selectbox(
        "Mis colores", list(label_map.keys()), key=f"{key_prefix}_my_color",
        label_visibility="collapsed",
    )
    chosen = label_map[chosen_lbl]
    if st.button("🗑 Eliminar este color", key=f"{key_prefix}_del_color"):
        delete_color_preset(chosen["id"])
        st.rerun()
    return chosen["hex_color"]


# ─── FUNCIONES DE DATOS ──────────────────────────────────────────────────────

def rows_to_df(rows) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows if isinstance(rows[0], dict) else [dict(r) for r in rows])


def load_laws():
    with connect() as conn:
        rows = conn.execute("SELECT * FROM laws ORDER BY imported_at DESC").fetchall()
        return [dict(r) if not isinstance(r, dict) else r for r in rows]


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
        rows = conn.execute(query, params).fetchall()
        return [dict(r) if not isinstance(r, dict) else r for r in rows]


def load_topics_by_part(part: str):
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM topics WHERE part = ? ORDER BY topic_number",
            (part,)
        ).fetchall()
        return [dict(r) if not isinstance(r, dict) else r for r in rows]


def load_oposiciones(activa_only: bool = True):
    query = "SELECT * FROM oposiciones"
    if activa_only:
        query += " WHERE activa = 1"
    query += " ORDER BY administracion, nombre"
    with connect() as conn:
        rows = conn.execute(query).fetchall()
        return [dict(r) if not isinstance(r, dict) else r for r in rows]


def get_user_oposiciones(user_id: int):
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT o.* FROM oposiciones o
            JOIN user_oposicion_enrollment uoe ON o.id = uoe.oposicion_id
            WHERE uoe.user_id = ?
            ORDER BY o.nombre
            """,
            (user_id,),
        ).fetchall()
        return [dict(r) if not isinstance(r, dict) else r for r in rows]


def enroll_user_oposicion(user_id: int, opo_id: int) -> bool:
    try:
        with connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO user_oposicion_enrollment(user_id, oposicion_id) VALUES (?,?)",
                (user_id, opo_id),
            )
            conn.commit()
        return True
    except Exception:
        return False


def unenroll_user_oposicion(user_id: int, opo_id: int) -> bool:
    try:
        with connect() as conn:
            conn.execute(
                "DELETE FROM user_oposicion_enrollment WHERE user_id=? AND oposicion_id=?",
                (user_id, opo_id),
            )
            conn.commit()
        return True
    except Exception:
        return False


# ─── HELPERS DE TEXTO ────────────────────────────────────────────────────────

_BOE_HEADER_RE = re.compile(
    r'^\s*(BOLET[IÍ]N OFICIAL DEL ESTADO|LEGISLACI[OÓ]N CONSOLIDADA|P[aá]gina\s+\d+)\s*$',
    re.IGNORECASE,
)
_TOC_LINE_RE = re.compile(r'\.{4,}\s*\d+\s*$')


def clean_article_text(text: str) -> str:
    if not text:
        return text
    lines = text.split('\n')
    # Eliminar cabeceras BOE
    cleaned = [line for line in lines if not _BOE_HEADER_RE.match(line)]
    # Unir líneas que son continuación de párrafo (línea previa no termina en
    # punto/dos puntos/punto y coma y la siguiente empieza en minúscula)
    merged: list[str] = []
    for line in cleaned:
        stripped = line.strip()
        if not stripped:
            merged.append("")
            continue
        if (merged and merged[-1]
                and not merged[-1].rstrip().endswith((".", ";", ":", "–", "—"))
                and stripped and stripped[0].islower()):
            merged[-1] = merged[-1].rstrip() + " " + stripped
        else:
            merged.append(line)
    return '\n'.join(merged).strip()


def is_toc_stub(text: str) -> bool:
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
        rows = conn.execute(
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
        return [dict(r) if not isinstance(r, dict) else r for r in rows]


def load_topic_mapped_articles(topic_id: int, law_id: int):
    with connect() as conn:
        rows = conn.execute(
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
        return [dict(r) if not isinstance(r, dict) else r for r in rows]


def load_study_plan_today(date_str: str) -> list[dict]:
    try:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT sp.id, sp.topic_id, sp.goal_min, sp.done_min, sp.sessions_done,
                       t.topic_number, t.official_text, t.part
                FROM study_plan sp
                JOIN topics t ON t.id = sp.topic_id
                WHERE sp.date=?
                ORDER BY t.topic_number
                """,
                (date_str,),
            ).fetchall()
            return [dict(r) if not isinstance(r, dict) else r for r in rows]
    except Exception:
        return []


def upsert_study_plan(date_str: str, topic_id: int, goal_min: int) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO study_plan(date,topic_id,goal_min)
            VALUES(?,?,?)
            ON CONFLICT(date,topic_id) DO UPDATE SET goal_min=excluded.goal_min,
                updated_at=CURRENT_TIMESTAMP
            """,
            (date_str, topic_id, goal_min),
        )
        conn.commit()


def log_pomodoro_session(date_str: str, topic_id: int, work_min: int) -> None:
    """Incrementa done_min y sessions_done para el plan del día."""
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO study_plan(date,topic_id,goal_min,done_min,sessions_done)
            VALUES(?,?,25,?,1)
            ON CONFLICT(date,topic_id) DO UPDATE SET
                done_min=done_min+?,
                sessions_done=sessions_done+1,
                updated_at=CURRENT_TIMESTAMP
            """,
            (date_str, topic_id, work_min, work_min),
        )
        conn.commit()


def delete_study_plan_entry(plan_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM study_plan WHERE id=?", (plan_id,))
        conn.commit()


def get_article_exam_freq(article_id: int) -> dict | None:
    """Devuelve {total_count, exam_sources} de article_exam_frequency o None."""
    try:
        with connect() as conn:
            row = conn.execute(
                "SELECT total_count, exam_sources FROM article_exam_frequency WHERE article_id=?",
                (article_id,),
            ).fetchone()
            if row:
                r = dict(row) if not isinstance(row, dict) else row
                import json as _json
                return {
                    "count": r["total_count"],
                    "sources": _json.loads(r.get("exam_sources") or "[]"),
                }
    except Exception:
        pass
    return None


def get_exam_cuerpos() -> list[str]:
    """Lista de cuerpos (oposiciones) con exámenes oficiales cargados."""
    try:
        with connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT bloque FROM exam_papers "
                "WHERE fuente_tipo='oficial_gva' AND bloque IS NOT NULL "
                "ORDER BY bloque"
            ).fetchall()
            return [r["bloque"] for r in rows]
    except Exception:
        return []


def get_top_exam_articles(limit: int = 40, cuerpo: str | None = None) -> list[dict]:
    """Top artículos por frecuencia en exámenes OFICIALES.

    Diferencia conteo explícito (la pregunta cita el artículo) de inferido
    (deducido del texto de la respuesta correcta, requiere revisión).
    Permite cribar por cuerpo/oposición.
    """
    import json as _json
    try:
        with connect() as conn:
            if cuerpo and cuerpo != "Todos":
                # Recalcular por cuerpo desde los links (article_exam_frequency es global)
                rows = conn.execute(
                    """
                    SELECT eql.article_id,
                           a.article_ref, a.title, a.law_id, l.name AS law_full,
                           SUM(CASE WHEN eql.tipo_relacion='articulo_explicito' THEN 1 ELSE 0 END) AS explicit_count,
                           SUM(CASE WHEN eql.tipo_relacion='articulo_inferido'  THEN 1 ELSE 0 END) AS inferred_count,
                           COUNT(DISTINCT eql.exam_question_id) AS total_count
                    FROM exam_question_links eql
                    JOIN exam_questions eq ON eq.id = eql.exam_question_id
                    JOIN exam_papers ep ON ep.id = eq.exam_paper_id
                    JOIN articles a ON a.id = eql.article_id
                    JOIN laws l ON l.id = a.law_id
                    WHERE eql.article_id IS NOT NULL
                      AND ep.fuente_tipo='oficial_gva' AND ep.bloque = ?
                    GROUP BY eql.article_id
                    ORDER BY explicit_count DESC, total_count DESC
                    LIMIT ?
                    """,
                    (cuerpo, limit),
                ).fetchall()
                return [
                    {
                        "article_id": r["article_id"], "article_ref": r["article_ref"],
                        "title": r["title"], "law_id": r["law_id"], "law_full": r["law_full"],
                        "law_name": r["law_full"], "explicit_count": r["explicit_count"],
                        "inferred_count": r["inferred_count"], "total_count": r["total_count"],
                        "sources": [cuerpo],
                    }
                    for r in rows
                ]
            rows = conn.execute(
                """
                SELECT aef.article_id, aef.article_ref, aef.total_count, aef.exam_sources,
                       COALESCE(aef.explicit_count, 0) AS explicit_count,
                       COALESCE(aef.inferred_count, 0) AS inferred_count,
                       aef.law_name, l.name AS law_full, a.title
                FROM article_exam_frequency aef
                LEFT JOIN articles a ON a.id = aef.article_id
                LEFT JOIN laws l ON l.id = aef.law_id
                WHERE aef.article_id IS NOT NULL
                ORDER BY aef.explicit_count DESC, aef.total_count DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            result = []
            for r in rows:
                row_dict = dict(r)
                try:
                    sources = _json.loads(r["exam_sources"] or "[]")
                    if isinstance(sources, str):
                        sources = [sources]
                except Exception:
                    sources = []
                row_dict["sources"] = sources
                result.append(row_dict)
            return result
    except Exception:
        return []


def get_top_exam_laws(limit: int = 25, cuerpo: str | None = None) -> list[dict]:
    """Top LEYES por nº de preguntas en exámenes oficiales (cobertura alta y fiable)."""
    try:
        with connect() as conn:
            q = """
                SELECT l.id AS law_id, l.name AS law_full,
                       COUNT(DISTINCT eql.exam_question_id) AS n_preguntas
                FROM exam_question_links eql
                JOIN exam_questions eq ON eq.id = eql.exam_question_id
                JOIN exam_papers ep ON ep.id = eq.exam_paper_id
                JOIN laws l ON l.id = eql.law_id
                WHERE ep.fuente_tipo='oficial_gva'
            """
            params: list = []
            if cuerpo and cuerpo != "Todos":
                q += " AND ep.bloque = ?"
                params.append(cuerpo)
            q += " GROUP BY l.id ORDER BY n_preguntas DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(q, params).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def get_article_study_payload(article_id: int) -> dict | None:
    """Texto del artículo + preguntas oficiales que lo referencian (para estudiar)."""
    try:
        with connect() as conn:
            a = conn.execute(
                "SELECT a.id, a.article_ref, a.title, a.text, l.name AS law_full, l.id AS law_id "
                "FROM articles a JOIN laws l ON l.id=a.law_id WHERE a.id=?",
                (article_id,),
            ).fetchone()
            if not a:
                return None
            qs = conn.execute(
                """
                SELECT eq.enunciado, eq.respuesta_oficial, eql.tipo_relacion, eql.confianza,
                       ep.bloque, ep.convocatoria, ep.parte
                FROM exam_question_links eql
                JOIN exam_questions eq ON eq.id = eql.exam_question_id
                JOIN exam_papers ep ON ep.id = eq.exam_paper_id
                WHERE eql.article_id = ? AND ep.fuente_tipo='oficial_gva'
                ORDER BY eql.tipo_relacion
                """,
                (article_id,),
            ).fetchall()
            return {"article": dict(a), "questions": [dict(r) for r in qs]}
    except Exception:
        return None


def load_topic_cef_resource(topic_id: int) -> dict | None:
    """Devuelve el recurso CEF de estudio para este tema (con content_text) si existe."""
    try:
        with connect() as conn:
            row = conn.execute(
                """
                SELECT tsr.id, tsr.content_text, tsr.validation_status, tsr.notes,
                       sd.title, sd.path
                FROM topic_study_resources tsr
                LEFT JOIN source_documents sd ON sd.id = tsr.source_document_id
                WHERE tsr.topic_id=? AND tsr.resource_kind='temario_academia_cef'
                  AND tsr.content_text IS NOT NULL
                LIMIT 1
                """,
                (topic_id,),
            ).fetchone()
            if row:
                return dict(row) if not isinstance(row, dict) else row
    except Exception:
        pass
    return None


def load_law_all_articles(law_id: int):
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT a.*, l.name AS norma
            FROM articles a
            JOIN laws l ON l.id = a.law_id
            WHERE a.law_id = ?
            ORDER BY CAST(a.article_ref AS INTEGER), a.article_ref
            """,
            (law_id,),
        ).fetchall()
        return [dict(r) if not isinstance(r, dict) else r for r in rows]


def law_has_fine_mapping(topic_id: int, law_id: int) -> bool:
    with connect() as conn:
        n = conn.execute(
            "SELECT COUNT(*) FROM topic_sources WHERE topic_id=? AND law_id=? AND article_id IS NOT NULL",
            (topic_id, law_id),
        ).fetchone()[0]
        return n > 0


# ─── COMPONENTES UI ──────────────────────────────────────────────────────────

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
        "norma", "articulo", "enunciado",
        "opcion_a", "opcion_b", "opcion_c", "opcion_d",
        "respuesta_correcta", "explicacion", "fuente",
    ]
    return [field for field in required if not str(data.get(field, "")).strip()]


def annotation_label(annotation_type: str) -> str:
    return {"note": "Nota", "highlight": "Subrayado", "doubt": "Duda", "bookmark": "Marcador"}.get(annotation_type, annotation_type)


def color_label(color: str) -> str:
    return {"": "Sin color", "yellow": "Amarillo", "green": "Verde", "blue": "Azul", "pink": "Rosa"}.get(color, color)


def article_option_label(article) -> str:
    title = article["title"] or "Sin titulo"
    short_title = title[:55] + ("..." if len(title) > 55 else "")
    return f"{article['norma']} - art. {article['article_ref']} - {short_title}"


def annotation_target_options(articles: list) -> dict[str, int | None]:
    options: dict[str, int | None] = {"Tema completo": None}
    for article in articles:
        options[article_option_label(article)] = int(article["id"])
    return options


def _article_location(article) -> str:
    """Construye una etiqueta legible de capitulo/seccion del articulo."""
    parts = []
    chapter = (article.get("chapter") or "").strip()
    section = (article.get("section") or "").strip()
    if chapter:
        parts.append(chapter)
    if section and section != chapter:
        parts.append(section)
    return " · ".join(parts)


def render_study_panel(article_id: int) -> None:
    """Panel de estudio por articulo: marcas (importante/duda), subrayado y notas.

    Usa el backend src/study (StudyService). Todo es contenido del usuario,
    nunca contenido juridico inventado.
    """
    svc = get_study_service()
    if not svc:
        return
    try:
        state = svc.get_article_state(article_id)
    except Exception:
        # Tablas de estudio no migradas: aviso discreto, no romper la card.
        st.caption("Funciones de estudio no disponibles (tablas pendientes de migrar).")
        return

    highlights = state.get("highlights", [])
    notes = state.get("notes", [])
    marks = state.get("marks", [])
    active_marks = {m["mark_type"] for m in marks if not m.get("resolved")}

    # ── Marcas rapidas: Importante / Duda ──
    col_imp, col_dud, _ = st.columns([1, 1, 3])
    is_important = "important" in active_marks
    is_doubt = "doubt" in active_marks
    with col_imp:
        if st.button(
            "★ Importante" if is_important else "☆ Importante",
            key=f"mark_imp_{article_id}",
            help="Marca este articulo como importante",
        ):
            study_mutate(lambda s: s.mark(
                StudyTarget(article_id=article_id),
                mark_type="important",
                resolved=is_important,  # si ya estaba activo, lo desactiva
            ))
            st.rerun()
    with col_dud:
        if st.button(
            "❓ Duda (activa)" if is_doubt else "❓ Marcar duda",
            key=f"mark_dud_{article_id}",
            help="Marca una duda sobre este articulo",
        ):
            study_mutate(lambda s: s.mark(
                StudyTarget(article_id=article_id),
                mark_type="doubt",
                resolved=is_doubt,
            ))
            st.rerun()

    # ── Guardar texto de duda ──
    if is_doubt:
        with st.container(border=True):
            st.caption("📝 Escribe tu duda")
            conn = connect()
            current_doubt = get_doubt(conn, article_id, current_user_id())
            doubt_text = st.text_area(
                "Duda",
                value=current_doubt.get("doubt_text", "") if current_doubt else "",
                height=80,
                placeholder="¿Qué no entiendes de este artículo? Escribe tu pregunta aquí...",
                key=f"doubt_text_{article_id}",
                label_visibility="collapsed",
            )
            col_save, col_del = st.columns([1, 1])
            with col_save:
                if st.button("Guardar duda", key=f"save_doubt_{article_id}", use_container_width=True):
                    if doubt_text.strip():
                        save_doubt(conn, article_id, doubt_text, user_id=current_user_id())
                        st.success("Duda guardada")
                    else:
                        st.warning("Escribe tu duda primero")
            with col_del:
                if st.button("Eliminar duda", key=f"del_doubt_{article_id}", use_container_width=True):
                    delete_doubt(conn, article_id, user_id=current_user_id())
                    st.info("Duda eliminada")
            conn.close()

    # ── Subrayado y notas ──
    if icon_toggle(
        "📝",
        f"Subrayado y notas ({len(highlights)} subrayados · {len(notes)} notas)",
        key=f"toggle_highlights_{article_id}",
    ):
        # Subrayados existentes
        if highlights:
            st.markdown("**Subrayados**")
            for h in highlights:
                color_lbl = HIGHLIGHT_COLOR_LABELS.get(h.get("color", ""), h.get("color", ""))
                col_txt, col_del = st.columns([5, 1])
                with col_txt:
                    st.markdown(f"{color_lbl} _{h.get('selected_text', '')}_")
                    if h.get("note_text"):
                        st.caption(f"Nota: {h['note_text']}")
                with col_del:
                    if st.button("🗑", key=f"del_hl_{h['id']}", help="Eliminar subrayado"):
                        study_mutate(lambda s, hid=int(h["id"]): s.delete_highlight(hid))
                        st.rerun()
            st.divider()

        # Nuevo subrayado
        st.markdown("**Nuevo subrayado**")
        hl_text = st.text_area(
            "Fragmento a subrayar",
            key=f"new_hl_text_{article_id}",
            height=70,
            placeholder="Pega aqui el fragmento exacto del articulo",
        )
        tab_preset, tab_custom = st.tabs(["Color preestablecido", "Color personalizado"])

        with tab_preset:
            hl_color = st.selectbox(
                "Color",
                list(HIGHLIGHT_COLOR_LABELS.keys()),
                format_func=lambda c: HIGHLIGHT_COLOR_LABELS[c],
                key=f"new_hl_color_{article_id}",
            )
            use_custom = False
        with tab_custom:
            hl_color_custom = st.color_picker(
                "Elige un color",
                value="#FFFF00",
                key=f"new_hl_custom_{article_id}",
            )
            hl_style = st.radio(
                "Estilo",
                ["Fondo", "Línea inferior"],
                key=f"new_hl_style_{article_id}",
            )
            hl_color = hl_color_custom
            use_custom = True

        hl_note = st.text_input("Nota (opcional)", key=f"new_hl_note_{article_id}")
        if st.button("Guardar subrayado", key=f"save_hl_{article_id}"):
            if not hl_text.strip():
                st.error("Escribe el fragmento a subrayar.")
            else:
                study_mutate(lambda s: s.add_highlight(
                    article_id=article_id,
                    selected_text=hl_text.strip(),
                    color=hl_color,
                    note_text=hl_note.strip() or None,
                ))
                st.success("Subrayado guardado.")
                st.rerun()

        st.divider()

        # Notas existentes
        if notes:
            st.markdown("**Notas**")
            for n in notes:
                col_txt, col_del = st.columns([5, 1])
                with col_txt:
                    st.markdown(n.get("note_text", ""))
                    if n.get("selected_text"):
                        st.caption(f"Sobre: {n['selected_text']}")
                with col_del:
                    if st.button("🗑", key=f"del_note_{n['id']}", help="Eliminar nota"):
                        study_mutate(lambda s, nid=int(n["id"]): s.delete_article_note(nid))
                        st.rerun()
            st.divider()

        # Nueva nota
        st.markdown("**Nueva nota**")
        note_text = st.text_area(
            "Tu nota",
            key=f"new_note_text_{article_id}",
            height=80,
            placeholder="Apunte personal, duda, conexion con otro articulo...",
        )
        if st.button("Guardar nota", key=f"save_note_{article_id}"):
            if not note_text.strip():
                st.error("Escribe el texto de la nota.")
            else:
                study_mutate(lambda s: s.add_article_note(
                    article_id=article_id,
                    note_text=note_text.strip(),
                ))
                st.success("Nota guardada.")
                st.rerun()


def _make_toggle(key: str):
    """Return an on_click callback that flips a boolean session_state key."""
    def _toggle(k=key):
        st.session_state[k] = not st.session_state.get(k, False)
    return _toggle


def _set_active_panel(panel_key: str, panel_name: str):
    """Callback: abre `panel_name` y cierra todos los demás (acordeón)."""
    def _cb(pk=panel_key, pn=panel_name):
        current = st.session_state.get(pk)
        st.session_state[pk] = None if current == pn else pn
    return _cb


def render_study_panel_compact(
    article_id: int,
    article_title: str = "",
    article_text: str = "",
) -> None:
    """Fila de acciones compacta con 6 botones en acordeón.

    ☆/★ Imp. | ❓/❗ Duda | 🖊 Subrayado | 📝 Notas | 🧠 IA | 🔗 Rel.
    Solo un panel puede estar abierto a la vez.
    """
    svc = get_study_service()
    if not svc:
        return
    try:
        state = svc.get_article_state(article_id)
    except Exception:
        return

    highlights = state.get("highlights", [])
    notes = state.get("notes", [])
    marks = state.get("marks", [])
    active_marks = {m["mark_type"] for m in marks if not m.get("resolved")}
    is_important = "important" in active_marks
    is_doubt = "doubt" in active_marks
    n_hl = len(highlights)
    n_notes = len(notes)

    # Un único key de acordeón por artículo — valor = nombre del panel activo o None
    accordion_key = f"panel_{article_id}"
    if accordion_key not in st.session_state:
        st.session_state[accordion_key] = None
    active_panel = st.session_state[accordion_key]

    st.markdown('<div style="height:2px"></div>', unsafe_allow_html=True)

    # ── Fila de 5 botones (imp. se mueve a cabecera del artículo) ────────────
    col_dud, col_hl, col_notes, col_ai, col_rel = st.columns(5)

    with col_dud:
        dud_lbl = "❗ Duda" if is_doubt else "❓ Duda"
        if st.button(dud_lbl, key=f"mark_dud_{article_id}",
                     help="Marcar duda", use_container_width=True):
            study_mutate(lambda s: s.mark(
                StudyTarget(article_id=article_id), mark_type="doubt", resolved=is_doubt,
            ))
            st.rerun()

    with col_hl:
        hl_lbl = f"🖊 ({n_hl})" if n_hl else "🖊 Subray."
        clicked_hl = st.button(hl_lbl, key=f"btn_hl_{article_id}",
                               help="Subrayados", use_container_width=True)

    with col_notes:
        notes_lbl = f"📝 ({n_notes})" if n_notes else "📝 Notas"
        clicked_notes = st.button(notes_lbl, key=f"btn_notes_{article_id}",
                                  help="Notas personales", use_container_width=True)

    with col_ai:
        clicked_ai = st.button("🧠 IA", key=f"btn_ai_{article_id}",
                               help="Insights de IA", use_container_width=True)

    with col_rel:
        clicked_rel = st.button("🔗 Rel.", key=f"btn_rel_{article_id}",
                                help="Artículos relacionados", use_container_width=True)

    # Procesar clics del acordeón después de renderizar todos los botones
    _toggled = None
    if clicked_hl:
        _toggled = "highlight"
    elif clicked_notes:
        _toggled = "notes"
    elif clicked_ai:
        _toggled = "ai"
    elif clicked_rel:
        _toggled = "related"
    if _toggled is not None:
        st.session_state[accordion_key] = None if active_panel == _toggled else _toggled
        active_panel = st.session_state[accordion_key]

    # ── Panel: Duda (se muestra cuando la marca está activa, sin ocupar slot acordeón) ──
    if is_doubt:
        conn = connect()
        current_doubt = get_doubt(conn, article_id, current_user_id())
        conn.close()
        with st.container(border=True):
            st.caption("✏️ Texto de tu duda")
            doubt_text = st.text_area(
                "duda",
                value=current_doubt.get("doubt_text", "") if current_doubt else "",
                height=70,
                placeholder="¿Qué no entiendes? Escríbelo aquí...",
                key=f"doubt_text_{article_id}",
                label_visibility="collapsed",
            )
            col_s, col_d = st.columns(2)
            with col_s:
                if st.button("Guardar duda", key=f"save_doubt_{article_id}", use_container_width=True):
                    if doubt_text.strip():
                        conn2 = connect()
                        save_doubt(conn2, article_id, doubt_text, user_id=current_user_id())
                        conn2.close()
                        st.success("Duda guardada")
                    else:
                        st.warning("Escribe tu duda primero")
            with col_d:
                if st.button("Eliminar duda", key=f"del_doubt_{article_id}", use_container_width=True):
                    conn2 = connect()
                    delete_doubt(conn2, article_id, user_id=current_user_id())
                    conn2.close()
                    st.info("Duda eliminada")
                    st.rerun()

    # ── Panel acordeón ────────────────────────────────────────────────────────
    if active_panel == "highlight":
        with st.container(border=True):
            st.markdown("##### 🖊 Subrayados")
            if highlights:
                for h in highlights:
                    col_h, col_hd = st.columns([6, 1])
                    with col_h:
                        clr = h.get("color", "#FFFF00")
                        css_color = HIGHLIGHT_COLORS_CSS_MAP.get(clr, clr)
                        st.markdown(
                            f'<mark style="background:{css_color};padding:1px 4px;border-radius:2px;">'
                            f'{h.get("selected_text","")}</mark>',
                            unsafe_allow_html=True,
                        )
                        if h.get("note_text"):
                            st.caption(f"Nota: {h['note_text']}")
                    with col_hd:
                        if st.button("🗑", key=f"del_hl_{h['id']}", help="Eliminar"):
                            study_mutate(lambda s, hid=int(h["id"]): s.delete_highlight(hid))
                            st.rerun()
                st.divider()
            # Botón JS para capturar la selección actual del texto del artículo
            _cap_key = f"cap_sel_{article_id}"
            _cap_html = f"""
<style>body{{margin:0;background:transparent}}</style>
<button style="font-size:11px;padding:2px 8px;cursor:pointer;width:100%;
               background:#45475a;border:1px solid #6c7086;color:#cdd6f4;border-radius:4px;"
  onclick="captureSelection()">📋 Capturar texto seleccionado</button>
<script>
function captureSelection() {{
  var sel = window.parent.getSelection();
  var text = sel ? sel.toString().trim() : '';
  if (!text) {{ return; }}
  var ta = null;
  var all = window.parent.document.querySelectorAll('textarea');
  for (var i = 0; i < all.length; i++) {{
    var ph = all[i].getAttribute('placeholder') || '';
    if (ph.indexOf('Copia aquí') !== -1) {{ ta = all[i]; break; }}
  }}
  if (ta) {{
    var nativeSetter = Object.getOwnPropertyDescriptor(
      window.parent.HTMLTextAreaElement.prototype, 'value').set;
    nativeSetter.call(ta, text);
    ta.dispatchEvent(new window.parent.Event('input', {{bubbles:true}}));
  }} else {{
    window.parent.navigator.clipboard.writeText(text).then(function(){{
      alert('Copiado al portapapeles. Pega con Ctrl+V en el campo de abajo.');
    }}).catch(function() {{
      alert('Selecciona el texto y cópialo manualmente (Ctrl+C).');
    }});
  }}
}}
</script>"""
            st.components.v1.html(_cap_html, height=30)

            hl_text = st.text_area(
                "Fragmento exacto a subrayar",
                key=f"new_hl_text_{article_id}", height=60,
                placeholder="Copia aquí el texto exacto del artículo",
            )
            hl_color = render_color_selector(f"hl_{article_id}")
            hl_note = st.text_input("Nota sobre el subrayado (opcional)", key=f"new_hl_note_{article_id}")
            if st.button("Guardar subrayado", key=f"save_hl_{article_id}"):
                if not hl_text.strip():
                    st.error("Escribe el fragmento a subrayar.")
                else:
                    study_mutate(lambda s: s.add_highlight(
                        article_id=article_id,
                        selected_text=hl_text.strip(),
                        color=hl_color,
                        note_text=hl_note.strip() or None,
                    ))
                    st.success("Subrayado guardado.")
                    st.rerun()

    elif active_panel == "notes":
        with st.container(border=True):
            st.markdown("##### 📝 Notas")
            if notes:
                for n in notes:
                    col_n, col_nd = st.columns([6, 1])
                    with col_n:
                        st.markdown(n.get("note_text", ""))
                        if n.get("selected_text"):
                            st.caption(f"Sobre: {n['selected_text']}")
                    with col_nd:
                        if st.button("🗑", key=f"del_note_{n['id']}", help="Eliminar nota"):
                            study_mutate(lambda s, nid=int(n["id"]): s.delete_article_note(nid))
                            st.rerun()
                st.divider()
            note_text = st.text_area(
                "Tu nota", key=f"new_note_text_{article_id}", height=80,
                placeholder="Apunte personal, conexión con otro artículo...",
            )
            if st.button("Guardar nota", key=f"save_note_{article_id}"):
                if not note_text.strip():
                    st.error("Escribe el texto de la nota.")
                else:
                    study_mutate(lambda s: s.add_article_note(
                        article_id=article_id, note_text=note_text.strip(),
                    ))
                    st.success("Nota guardada.")
                    st.rerun()

    elif active_panel == "ai":
        with st.container(border=True):
            render_ai_insights(article_id, article_title, article_text, show_toggle_button=False)

    elif active_panel == "related":
        with st.container(border=True):
            render_related_articles(article_id, article_title, show_toggle_button=False)


# Mapa de colores named → CSS para mostrar subrayados en la lista
HIGHLIGHT_COLORS_CSS_MAP = {
    "yellow": "#FFEB3B", "green": "#4CAF50", "blue": "#2196F3",
    "pink": "#FF69B4", "purple": "#9C27B0", "red": "#F44336",
}


def _load_article_highlights(article_id: int) -> list:
    svc = get_study_service()
    if not svc:
        return []
    try:
        return svc.get_article_state(article_id).get("highlights", [])
    except Exception:
        return []


def render_article_card(article, topic_id: int) -> None:
    display_text = clean_article_text(article['text'] or '')
    if is_toc_stub(display_text):
        return
    article_id = article['id']
    article_ref = article['article_ref']
    article_title = article.get('title') or f"Art. {article_ref}"

    # Cargamos estado para la estrella de importancia en la cabecera
    _is_important = False
    _svc = get_study_service()
    if _svc:
        try:
            _state = _svc.get_article_state(article_id)
            _marks = {m["mark_type"] for m in _state.get("marks", []) if not m.get("resolved")}
            _is_important = "important" in _marks
        except Exception:
            pass

    _exam_freq = get_article_exam_freq(article_id)

    with st.container(border=True):
        # ── Cabecera: ★ | Art N | Título | 🔥 | 🔊 ⏸ ⏹ ──────────────────────
        col_star, col_ref, col_title, col_freq, col_tts = st.columns([0.35, 0.9, 5.5, 0.8, 1.6])
        with col_star:
            star_lbl = "★" if _is_important else "☆"
            if st.button(star_lbl, key=f"mark_imp_{article_id}",
                         help="Marcar como importante", use_container_width=True):
                study_mutate(lambda s: s.mark(
                    StudyTarget(article_id=article_id),
                    mark_type="important",
                    resolved=_is_important,
                ))
                st.rerun()
        with col_ref:
            st.markdown(f"**Art. {article_ref}**")
        with col_title:
            st.markdown(f"**{article_title}**")
        with col_freq:
            if _exam_freq and _exam_freq["count"] > 0:
                _cnt = _exam_freq["count"]
                _tip = f"Preguntado ~{_cnt}x en exámenes oficiales"
                st.markdown(
                    f'<span title="{_tip}" style="color:#f38ba8;font-size:12px;'
                    f'font-weight:700;cursor:help;">🔥{_cnt}</span>',
                    unsafe_allow_html=True,
                )
        with col_tts:
            render_article_tts(
                items=[{"text": display_text, "label": f"Art. {article_ref}"}],
                key=f"tts_art_{topic_id}_{article_id}",
            )

        # ── Capítulo / sección en color acento ─────────────────────────────────
        location = _article_location(article)
        if location:
            st.markdown(
                f'<div style="color:#f38ba8;font-size:11px;font-weight:600;margin:-4px 0 4px;">'
                f'{location}</div>',
                unsafe_allow_html=True,
            )

        # ── Texto legal con highlights integrados ───────────────────────────────
        if display_text:
            highlights = _load_article_highlights(article_id)
            if highlights:
                html_text = render_text_with_highlights(display_text, highlights)
                # Wrap in a styled div matching Streamlit dark theme
                st.markdown(
                    f'<div style="font-size:14px;line-height:1.7;color:#cdd6f4;'
                    f'white-space:pre-wrap;padding:8px 0;">{html_text}</div>',
                    unsafe_allow_html=True,
                )
            else:
                import html as _html_mod
                _escaped = _html_mod.escape(display_text)
                st.markdown(
                    f'<div style="font-size:14px;line-height:1.7;color:#cdd6f4;'
                    f'white-space:pre-wrap;padding:8px 0;word-break:break-word;">'
                    f'{_escaped}</div>',
                    unsafe_allow_html=True,
                )

        # ── Panel compacto: Imp | Duda | Notas | IA | Relacionados
        render_study_panel_compact(article_id, article_title, display_text)


def render_paginated_articles(articles: list, topic_id: int, key_prefix: str) -> None:
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
    st.caption(f"Mostrando articulos {start + 1}-{end} de {total}. Orden: numero de articulo ascendente.")
    for article in articles[start:end]:
        render_article_card(article, topic_id)


def render_study_annotations(topic, articles: list) -> None:
    st.divider()
    st.markdown("#### Anotaciones del tema (sistema legado)")
    st.caption(
        "Las anotaciones de aquí fueron creadas con el sistema antiguo de anotaciones "
        "a nivel de tema. Los subrayados, notas y dudas nuevos se gestionan dentro de "
        "cada artículo mediante el panel compacto ❓ 🖊 📝."
    )

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

        new_selected_text = st.text_area("Texto seleccionado o fragmento", key=f"ann_new_selected_{topic['id']}", height=90)
        new_manual_reference = st.text_input(
            "Referencia manual", placeholder="Ejemplo: art. 112.2, parrafo tercero", key=f"ann_new_reference_{topic['id']}"
        )
        new_note_text = st.text_area("Nota", key=f"ann_new_note_{topic['id']}", height=110)

        if st.button("Guardar anotacion", key=f"ann_new_save_{topic['id']}"):
            has_content = any(v.strip() for v in [new_selected_text, new_manual_reference, new_note_text])
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
            article_title = annotation.get("article_title") or "Sin titulo"
            target = f"{annotation['law_name']} - art. {annotation['article_ref']} - {article_title}"

        with st.container(border=True):
            col_info, col_date = st.columns([3, 1])
            with col_info:
                st.markdown(f"**{annotation_label(annotation['annotation_type'])}**")
                st.caption(target)
            with col_date:
                st.caption(f"Actualizada: {annotation['updated_at']}")

            if annotation["selected_text"]:
                st.text_area("Texto guardado", value=annotation["selected_text"], height=80, disabled=True, key=f"ann_selected_read_{annotation['id']}")
            if annotation["manual_reference"]:
                st.caption(f"Referencia: {annotation['manual_reference']}")
            if annotation["note_text"]:
                st.write(annotation["note_text"])
            if annotation["color"]:
                st.caption(f"Color: {color_label(annotation['color'])}")

            with st.expander("Editar anotacion"):
                edit_target_options = dict(target_options)
                edit_type = st.selectbox(
                    "Tipo", ANNOTATION_TYPES,
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
                    "Vincular a", list(edit_target_options.keys()),
                    index=list(edit_target_options.keys()).index(current_target_label),
                    key=f"ann_edit_target_{annotation['id']}",
                )
                current_color = annotation["color"] if annotation["color"] in ANNOTATION_COLORS else ""
                edit_color = st.selectbox(
                    "Color", ANNOTATION_COLORS,
                    index=ANNOTATION_COLORS.index(current_color),
                    format_func=color_label,
                    key=f"ann_edit_color_{annotation['id']}",
                )
                edit_selected_text = st.text_area("Texto seleccionado o fragmento", value=annotation["selected_text"] or "", height=90, key=f"ann_edit_selected_{annotation['id']}")
                edit_manual_reference = st.text_input("Referencia manual", value=annotation["manual_reference"] or "", key=f"ann_edit_reference_{annotation['id']}")
                edit_note_text = st.text_area("Nota", value=annotation["note_text"] or "", height=110, key=f"ann_edit_note_{annotation['id']}")
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


# ─── RENDERIZADO DE TABS NUEVAS ──────────────────────────────────────────────

def render_cuenta_tab() -> None:
    """Tab Cuenta: login/registro o perfil si ya esta autenticado."""
    user = current_user()

    if user:
        # ── Perfil autenticado ──
        plan = get_user_plan(user["id"])
        plan_labels = {"free": "Gratuito", "pro": "Pro ($9.99/mes)", "premium": "Premium ($19.99/mes)"}
        plan_badge = plan_labels.get(plan, plan)

        col_info, col_logout = st.columns([3, 1])
        with col_info:
            st.markdown(f"### {user.get('full_name') or user['email']}")
            st.caption(user["email"])
        with col_logout:
            if st.button("Cerrar sesion", type="secondary"):
                try:
                    _get_auth_service().logout(st.session_state.get("auth_token", ""))
                except Exception:
                    pass
                st.session_state.pop("auth_token", None)
                st.rerun()

        st.divider()
        col_plan, col_uid = st.columns(2)
        col_plan.metric("Plan actual", plan_badge)
        col_uid.metric("ID de usuario", user["id"])

        # Oposiciones del usuario
        st.divider()
        st.markdown("#### Mis oposiciones")
        mis_opos = get_user_oposiciones(user["id"])
        if mis_opos:
            for o in mis_opos:
                st.markdown(f"- **{o['nombre']}** ({o['administracion']})")
        else:
            st.info("No estas inscrito en ninguna oposicion. Ve a la pestana **Oposiciones** para inscribirte.")

        # Planes
        st.divider()
        st.markdown("#### Planes disponibles")
        col_f, col_p, col_pr = st.columns(3)
        with col_f:
            st.markdown("**Gratuito**")
            st.caption("Estudio basico, SRS")
            st.markdown("**0 €/mes**")
        with col_p:
            st.markdown("**Pro**")
            st.caption("IA, TTS, Examenes")
            st.markdown("**9,99 €/mes**")
            if plan == "free":
                st.info("Configura STRIPE_API_KEY para activar pagos")
        with col_pr:
            st.markdown("**Premium**")
            st.caption("Todo + Drive backup")
            st.markdown("**19,99 €/mes**")
            if plan in ("free", "pro"):
                st.info("Configura STRIPE_API_KEY para activar pagos")

        # Cambiar contrasena
        st.divider()
        with st.expander("Cambiar contrasena"):
            old_pw = st.text_input("Contrasena actual", type="password", key="pw_old")
            new_pw = st.text_input("Nueva contrasena (min. 8 caracteres)", type="password", key="pw_new")
            new_pw2 = st.text_input("Repetir nueva contrasena", type="password", key="pw_new2")
            if st.button("Guardar nueva contrasena"):
                if new_pw != new_pw2:
                    st.error("Las contrasenas no coinciden.")
                elif len(new_pw) < 8:
                    st.error("La contrasena debe tener al menos 8 caracteres.")
                else:
                    try:
                        _get_auth_service().change_password(user["id"], old_pw, new_pw)
                        st.success("Contrasena actualizada correctamente.")
                    except AuthError as e:
                        st.error(str(e))

    else:
        # ── Login / Registro ──
        st.markdown("### Accede a tu cuenta")
        st.caption("La cuenta es opcional. Sin cuenta puedes usar la app en modo local (usuario=1).")

        modo = st.radio(
            "Modo de acceso",
            ["Iniciar sesion", "Crear cuenta nueva"],
            horizontal=True,
            label_visibility="collapsed",
        )

        if modo == "Iniciar sesion":
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Contrasena", type="password", key="login_pw")
            if st.button("Entrar", type="primary"):
                if not email or not password:
                    st.error("Introduce email y contrasena.")
                else:
                    try:
                        token = _get_auth_service().login(email, password)
                        st.session_state["auth_token"] = token
                        st.success("Sesion iniciada correctamente.")
                        st.rerun()
                    except AuthError as e:
                        st.error(str(e))
                    except Exception as e:
                        st.error(f"Error inesperado: {e}")

        else:  # Registro
            full_name = st.text_input("Nombre completo (opcional)", key="reg_name")
            email = st.text_input("Email", key="reg_email")
            password = st.text_input("Contrasena (min. 8 caracteres)", type="password", key="reg_pw")
            password2 = st.text_input("Repetir contrasena", type="password", key="reg_pw2")
            if st.button("Crear cuenta", type="primary"):
                if not email or not password:
                    st.error("Email y contrasena son obligatorios.")
                elif password != password2:
                    st.error("Las contrasenas no coinciden.")
                elif len(password) < 8:
                    st.error("La contrasena debe tener al menos 8 caracteres.")
                else:
                    try:
                        svc = _get_auth_service()
                        svc.register(email, password, full_name or None)
                        token = svc.login(email, password)
                        st.session_state["auth_token"] = token
                        st.success("Cuenta creada y sesion iniciada.")
                        st.rerun()
                    except AuthError as e:
                        st.error(str(e))
                    except Exception as e:
                        st.error(f"Error inesperado: {e}")


def render_oposiciones_tab() -> None:
    """Tab Oposiciones: ver y gestionar inscripciones."""
    user_id = current_user_id()
    user = current_user()

    st.markdown("### Oposiciones disponibles")
    st.caption("Inscribete en las oposiciones que preparas para personalizar tu estudio.")

    if not user:
        st.info("Inicia sesion en la pestana **Cuenta** para guardar tus inscripciones. En modo anonimo se usa usuario=1.")

    opos = load_oposiciones()
    if not opos:
        st.warning("No hay oposiciones cargadas.")
        return

    mis_opos_ids = {o["id"] for o in get_user_oposiciones(user_id)}

    for opo in opos:
        with st.container(border=True):
            col_info, col_btn = st.columns([4, 1])
            with col_info:
                st.markdown(f"**{opo['nombre']}**")
                st.caption(f"{opo['administracion']} · {opo['code']}")
            with col_btn:
                enrolled = opo["id"] in mis_opos_ids
                if enrolled:
                    if st.button("Desinscribirse", key=f"unenroll_{opo['id']}", type="secondary"):
                        unenroll_user_oposicion(user_id, opo["id"])
                        st.rerun()
                else:
                    if st.button("Inscribirse", key=f"enroll_{opo['id']}", type="primary"):
                        enroll_user_oposicion(user_id, opo["id"])
                        st.rerun()

    st.divider()
    st.markdown("#### Mis inscripciones")
    mis_opos = get_user_oposiciones(user_id)
    if mis_opos:
        for o in mis_opos:
            st.markdown(f"- {o['nombre']}")
    else:
        st.info("Aun no estas inscrito en ninguna oposicion.")

    # Añadir oposicion personalizada
    st.divider()
    with st.expander("Anadir oposicion personalizada"):
        col_code, col_nombre, col_adm = st.columns([1, 2, 1])
        new_code = col_code.text_input("Codigo (unico)", placeholder="B2-01-GVA-2025", key="new_opo_code")
        new_nombre = col_nombre.text_input("Nombre", placeholder="Oposicion B2-01", key="new_opo_nombre")
        new_adm = col_adm.text_input("Administracion", value="GVA", key="new_opo_adm")
        if st.button("Crear oposicion", key="create_opo"):
            if not new_code or not new_nombre:
                st.error("Codigo y nombre son obligatorios.")
            else:
                try:
                    with connect() as conn:
                        conn.execute(
                            "INSERT INTO oposiciones(code, nombre, administracion) VALUES (?,?,?)",
                            (new_code, new_nombre, new_adm or "GVA"),
                        )
                        conn.commit()
                    st.success(f"Oposicion '{new_nombre}' creada.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")


# ─── CABECERA ────────────────────────────────────────────────────────────────

st.title("GVAdictos")
st.caption("MVP local-first para oposiciones GVA. Contenido juridico siempre vinculado a fuente.")

# Banner de usuario activo
user = current_user()
if user:
    plan = get_user_plan(user["id"])
    plan_str = {"free": "Gratuito", "pro": "Pro", "premium": "Premium"}.get(plan, plan)
    st.sidebar.success(f"Sesion: {user.get('full_name') or user['email']}\nPlan: {plan_str}")
else:
    st.sidebar.info("Modo local (sin cuenta)\nVe a Cuenta para iniciar sesion.")

# ─── TABS ────────────────────────────────────────────────────────────────────

TABS = [
    "Inicio", "Cuenta", "Oposiciones",
    "Fuentes", "Importar leyes", "Articulos", "Preguntas",
    "Estudiar", "Modo test", "Modo examen",
    "Fallos", "Informes y CSV"
]
tabs = st.tabs(TABS)

# ── Inicio ──────────────────────────────────────────────────────────────────
with tabs[0]:
    counts = dashboard_counts()
    cols = st.columns(len(counts))
    for col, (label, value) in zip(cols, counts.items()):
        col.metric(label.capitalize(), value)

    # Estado del usuario en la pantalla principal
    st.divider()
    col_u, col_o = st.columns(2)
    with col_u:
        if user:
            st.success(f"Conectado como **{user.get('full_name') or user['email']}**")
        else:
            st.info("Usando modo local (sin cuenta). Ve a **Cuenta** para crear una sesion.")
    with col_o:
        mis_opos = get_user_oposiciones(current_user_id())
        if mis_opos:
            nombres = ", ".join(o["nombre"] for o in mis_opos[:2])
            if len(mis_opos) > 2:
                nombres += f" (+{len(mis_opos)-2} mas)"
            st.info(f"Oposiciones: {nombres}")
        else:
            st.info("Sin oposiciones seleccionadas. Ve a **Oposiciones** para inscribirte.")

# ── Cuenta ──────────────────────────────────────────────────────────────────
with tabs[1]:
    render_cuenta_tab()

# ── Oposiciones ─────────────────────────────────────────────────────────────
with tabs[2]:
    render_oposiciones_tab()

# ── Fuentes ─────────────────────────────────────────────────────────────────
with tabs[3]:
    st.subheader("Catalogo de fuentes")
    sources = list_source_documents()
    if sources:
        st.dataframe(rows_to_df(sources), use_container_width=True, hide_index=True)
    else:
        st.info("No hay fuentes catalogadas. Carga un manifiesto con scripts/import_source_manifest.py.")

# ── Importar leyes ───────────────────────────────────────────────────────────
with tabs[4]:
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

# ── Articulos ────────────────────────────────────────────────────────────────
with tabs[5]:
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

# ── Preguntas ────────────────────────────────────────────────────────────────
with tabs[6]:
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

# ── Estudiar ─────────────────────────────────────────────────────────────────
with tabs[7]:
    st.subheader("Estudiar por tema")

    # ── Reproductor TTS + Pomodoro ───────────────────────────────────────────
    _col_tts_global, _col_pomo = st.columns([3, 2])
    with _col_tts_global:
        render_global_player()
    with _col_pomo:
        st.components.v1.html("""
<style>
body{margin:0;background:transparent;font-family:system-ui,sans-serif}
#pm{display:flex;align-items:center;gap:6px;padding:4px 8px;
    background:#1e1e2e;border:1px solid #313244;border-radius:6px;flex-wrap:wrap}
#pmtimer{font-size:22px;font-weight:700;color:#cba6f7;min-width:52px;text-align:center}
#pmlbl{font-size:10px;color:#6c7086;white-space:nowrap}
#pmcfg{font-size:10px;color:#585b70;display:flex;align-items:center;gap:4px;flex-wrap:wrap}
#pmcfg label{color:#6c7086}
.pb{background:#313244;border:1px solid #45475a;color:#cdd6f4;
    padding:2px 7px;border-radius:4px;cursor:pointer;font-size:12px}
.pb:hover{background:#45475a}
.work{color:#a6e3a1!important}
.rest{color:#89b4fa!important}
#pmprog{width:100%;height:4px;background:#313244;border-radius:2px;margin-top:3px}
#pmprogbar{height:100%;width:0%;border-radius:2px;transition:width 1s linear}
#pmsession{font-size:10px;color:#585b70;white-space:nowrap}
</style>
<div id="pm">
  <span id="pmtimer">25:00</span>
  <span id="pmsession">🍅×0</span>
  <span id="pmlbl" class="work">Trabajo</span>
  <button class="pb" id="pmbtn" onclick="pmToggle()">▶</button>
  <button class="pb" onclick="pmReset()" title="Reiniciar">↺</button>
  <div id="pmcfg">
    <label>⏱<input type="number" id="pmw" min="1" max="90" value="25"
      style="width:36px;background:#181825;color:#cdd6f4;border:1px solid #45475a;border-radius:3px;padding:1px 3px;font-size:11px"
      onchange="pmUpdW()" title="Minutos de trabajo">m</label>
    <label>☕<input type="number" id="pmr" min="1" max="30" value="5"
      style="width:28px;background:#181825;color:#cdd6f4;border:1px solid #45475a;border-radius:3px;padding:1px 3px;font-size:11px"
      onchange="pmUpdR()" title="Minutos de descanso">m</label>
    <label><input type="checkbox" id="pmauto" checked style="accent-color:#cba6f7"> auto</label>
  </div>
</div>
<div id="pmprog"><div id="pmprogbar" style="background:#cba6f7"></div></div>
<script>
(function(){
  var workMin=25, restMin=5, totalSec=1500, remSec=1500;
  var isRunning=false, isWork=true, interval=null, sessCount=0;
  var tmr=document.getElementById('pmtimer');
  var lbl=document.getElementById('pmlbl');
  var btn=document.getElementById('pmbtn');
  var bar=document.getElementById('pmprogbar');
  var sess=document.getElementById('pmsession');

  function fmt(s){var m=Math.floor(s/60),ss=s%60;return ('0'+m).slice(-2)+':'+('0'+ss).slice(-2);}
  function render(){
    tmr.textContent=fmt(remSec);
    var pct=Math.min(100,((totalSec-remSec)/totalSec)*100);
    bar.style.width=pct+'%';
    bar.style.background=isWork?'#cba6f7':'#89b4fa';
    tmr.style.color=isWork?'#cba6f7':'#89b4fa';
  }

  function notify(msg){
    if(Notification.permission==='granted') new Notification(msg,{icon:'data:,'});
  }

  function startPhase(work){
    isWork=work;
    workMin=parseInt(document.getElementById('pmw').value)||25;
    restMin=parseInt(document.getElementById('pmr').value)||5;
    totalSec=(work?workMin:restMin)*60;
    remSec=totalSec;
    lbl.textContent=work?'Trabajo':'Descanso';
    lbl.className=work?'work':'rest';
    render();
    if(work){
      notify('☕ ¡Descanso terminado! A estudiar 🍅');
    } else {
      sessCount++;
      sess.textContent='🍅×'+sessCount;
      notify('🍅 Pomodoro completado. ¡Descansa '+restMin+' min!');
    }
  }

  function tick(){
    if(remSec>0){ remSec--; render(); }
    else {
      clearInterval(interval); interval=null;
      isRunning=false; btn.textContent='▶';
      var wasWork=isWork;
      startPhase(!isWork);
      // Auto-start si checkbox marcado
      if(document.getElementById('pmauto').checked){
        interval=setInterval(tick,1000);
        isRunning=true; btn.textContent='⏸';
      }
    }
  }

  window.pmToggle=function(){
    if(isRunning){
      clearInterval(interval); interval=null;
      isRunning=false; btn.textContent='▶';
    } else {
      if(Notification.permission==='default') Notification.requestPermission();
      interval=setInterval(tick,1000);
      isRunning=true; btn.textContent='⏸';
    }
  };
  window.pmReset=function(){
    clearInterval(interval); interval=null;
    isRunning=false; btn.textContent='▶';
    isWork=true; sessCount=0; sess.textContent='🍅×0';
    startPhase(true);
  };
  window.pmUpdW=function(){if(!isRunning&&isWork){totalSec=(parseInt(document.getElementById('pmw').value)||25)*60;remSec=totalSec;render();}};
  window.pmUpdR=function(){if(!isRunning&&!isWork){totalSec=(parseInt(document.getElementById('pmr').value)||5)*60;remSec=totalSec;render();}};
  render();
})();
</script>
""", height=90)
    st.divider()

    # ── Plan del día (scheduler) ─────────────────────────────────────────────
    import datetime as _dt
    _today = _dt.date.today().isoformat()
    _plan_key = f"study_plan_open_{_today}"

    with st.expander("📅 Plan de estudio de hoy", expanded=st.session_state.get(_plan_key, False)):
        st.session_state[_plan_key] = True
        _plan = load_study_plan_today(_today)

        # ── Añadir tema al plan ──
        with st.form("add_plan_form", clear_on_submit=True):
            _all_topics_for_plan = load_topics_by_part("general") + load_topics_by_part("especial")
            _topic_opts = {
                f"Tema {r['topic_number']:02d} - {r['official_text'][:50]}": r['id']
                for r in _all_topics_for_plan
            }
            _existing_ids = {p['topic_id'] for p in _plan}
            _available_opts = {k: v for k, v in _topic_opts.items() if v not in _existing_ids}
            _fcols = st.columns([4, 1, 1])
            with _fcols[0]:
                _sel_topic_text = st.selectbox("Añadir tema", list(_available_opts.keys()) or ["—"], label_visibility="collapsed")
            with _fcols[1]:
                _goal = st.number_input("Min", min_value=5, max_value=480, value=50, step=25, label_visibility="collapsed")
            with _fcols[2]:
                _submitted = st.form_submit_button("➕ Añadir")
            if _submitted and _available_opts:
                upsert_study_plan(_today, _available_opts[_sel_topic_text], int(_goal))
                st.rerun()

        if not _plan:
            st.info("No hay temas planificados para hoy. Añade uno arriba.")
        else:
            _total_goal = sum(p['goal_min'] for p in _plan)
            _total_done = sum(p['done_min'] for p in _plan)
            _pct_global = min(100, int(_total_done / _total_goal * 100)) if _total_goal else 0
            st.progress(_pct_global / 100, text=f"Progreso global: {_total_done}/{_total_goal} min ({_pct_global}%)")

            for _pe in _plan:
                _pcols = st.columns([5, 1, 1, 1])
                _pct = min(100, int(_pe['done_min'] / _pe['goal_min'] * 100)) if _pe['goal_min'] else 0
                with _pcols[0]:
                    st.markdown(
                        f"**T{_pe['topic_number']:02d}** {_pe['official_text'][:55]}  \n"
                        f"<small style='color:#6c7086'>{_pe['done_min']}/{_pe['goal_min']} min · "
                        f"🍅×{_pe['sessions_done']} · {_pct}%</small>",
                        unsafe_allow_html=True,
                    )
                    st.progress(_pct / 100)
                with _pcols[1]:
                    _wmin_key = f"wmin_{_pe['id']}"
                    _wmin = st.number_input("min", 5, 90, 25, 5, key=_wmin_key, label_visibility="collapsed")
                with _pcols[2]:
                    if st.button("🍅", key=f"log_pm_{_pe['id']}", help="Registrar pomodoro completado"):
                        log_pomodoro_session(_today, _pe['topic_id'], int(_wmin))
                        st.rerun()
                with _pcols[3]:
                    if st.button("🗑", key=f"del_plan_{_pe['id']}", help="Eliminar del plan"):
                        delete_study_plan_entry(_pe['id'])
                        st.rerun()
    st.divider()

    # ── Ranking de exámenes oficiales (leyes y artículos más preguntados) ────
    with st.expander("🔥 Lo más preguntado en exámenes oficiales GVA", expanded=False):
        import pandas as _pd
        _cuerpos = get_exam_cuerpos()
        if not _cuerpos:
            st.info(
                "Sin exámenes oficiales cargados. Ejecuta:\n"
                "`python scripts/rebuild_official_exams.py` y "
                "`python scripts/infer_and_link.py`"
            )
        else:
            st.caption(
                "Fuente: cuestionarios + plantillas oficiales de la GVA "
                "(NO simulacros de academia). El conteo **explícito** = la pregunta "
                "cita el artículo; **≈ inferido** = deducido del texto de la respuesta "
                "correcta (requiere revisión)."
            )
            _cf1, _cf2 = st.columns([2, 3])
            with _cf1:
                _cuerpo_sel = st.selectbox(
                    "Oposición / cuerpo",
                    ["Todos"] + _cuerpos,
                    key="exam_rank_cuerpo",
                )
            with _cf2:
                _top_n = st.slider(
                    "Mostrar top N", min_value=10, max_value=100, value=100, step=10,
                    key="exam_rank_topn",
                )
            _crit = None if _cuerpo_sel == "Todos" else _cuerpo_sel

            _tab_art, _tab_ley = st.tabs(["📑 Artículos", "⚖️ Leyes"])

            # ── Artículos más preguntados ──
            with _tab_art:
                _top_arts = get_top_exam_articles(limit=_top_n, cuerpo=_crit)
                if not _top_arts:
                    st.info("Sin artículos vinculados para este filtro.")
                else:
                    _rows_ui = []
                    for _r in _top_arts:
                        _expl = _r.get("explicit_count") or 0
                        _infe = _r.get("inferred_count") or 0
                        _marca = "✓" if _expl else "≈"
                        _rows_ui.append({
                            "": _marca,
                            "Art.": _r["article_ref"],
                            "Ley": (_r.get("law_full") or _r.get("law_name") or "—")[:42],
                            "Título": (_r.get("title") or "")[:46],
                            "Explíc.": _expl,
                            "≈Infer.": _infe,
                            "Total": _r["total_count"],
                        })
                    st.dataframe(
                        _pd.DataFrame(_rows_ui),
                        use_container_width=True, hide_index=True,
                        column_config={
                            "": st.column_config.TextColumn("", width="small", help="✓ explícito · ≈ inferido"),
                            "Total": st.column_config.NumberColumn("🔥 Total", width="small"),
                            "Explíc.": st.column_config.NumberColumn("✓", width="small"),
                            "≈Infer.": st.column_config.NumberColumn("≈", width="small"),
                            "Art.": st.column_config.TextColumn("Art.", width="small"),
                        },
                    )
                    st.markdown("**📖 Estudiar un artículo del ranking**")
                    _opts = {
                        "Art. %s — %s" % (
                            _r["article_ref"],
                            (_r.get("law_full") or _r.get("law_name") or "")[:40],
                        ): _r.get("article_id")
                        for _r in _top_arts if _r.get("article_id")
                    }
                    _sel = st.selectbox(
                        "Selecciona", ["—"] + list(_opts.keys()),
                        key="exam_rank_art_study",
                    )
                    if _sel != "—":
                        _payload = get_article_study_payload(_opts[_sel])
                        if _payload:
                            _a = _payload["article"]
                            st.markdown(
                                "#### %s — Art. %s%s" % (
                                    _a["law_full"], _a["article_ref"],
                                    (" · " + _a["title"]) if _a.get("title") else "",
                                )
                            )
                            st.text_area(
                                "Texto del artículo",
                                value=clean_article_text(_a["text"] or ""),
                                height=240, disabled=True,
                                key="exam_rank_art_text",
                            )
                            _expl_qs = [q for q in _payload["questions"]
                                        if q["tipo_relacion"] == "articulo_explicito"]
                            _infe_qs = [q for q in _payload["questions"]
                                        if q["tipo_relacion"] == "articulo_inferido"]
                            st.caption(
                                "Aparece en %d pregunta(s) oficial(es): "
                                "%d explícita(s), %d inferida(s)." % (
                                    len(_payload["questions"]), len(_expl_qs), len(_infe_qs))
                            )
                            for _q in _payload["questions"]:
                                _badge = "✓ explícita" if _q["tipo_relacion"] == "articulo_explicito" else "≈ inferida (revisar)"
                                with st.expander(
                                    "[%s %s] %s — %s" % (
                                        _q["bloque"], _q["convocatoria"], _badge,
                                        _q["enunciado"][:80]),
                                    expanded=False,
                                ):
                                    st.write(_q["enunciado"])
                                    st.caption("Respuesta oficial: **%s**" % (_q["respuesta_oficial"] or "—"))

            # ── Leyes más preguntadas ──
            with _tab_ley:
                _top_laws = get_top_exam_laws(limit=_top_n, cuerpo=_crit)
                if not _top_laws:
                    st.info("Sin datos para este filtro.")
                else:
                    st.dataframe(
                        _pd.DataFrame([
                            {"Ley": _l["law_full"][:60], "Preguntas": _l["n_preguntas"]}
                            for _l in _top_laws
                        ]),
                        use_container_width=True, hide_index=True,
                        column_config={
                            "Preguntas": st.column_config.NumberColumn("🔥 Preguntas", width="small"),
                        },
                    )
    st.divider()

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
        topic_options = {
            f"Tema {row['topic_number']:02d} - {row['official_text']}": row
            for row in topics
        }
        selected_topic_text = st.selectbox("Selecciona tema", list(topic_options.keys()))
        selected_topic = topic_options[selected_topic_text]

        st.divider()
        part_name = "Parte general" if part_label == "general" else "Parte especifica"

        # Cargamos normativa y pre-cargamos artículos mapeados por ley
        normativa = load_topic_normativa(selected_topic['id'])

        # Pre-cargar mapped+has_fine por ley para no repetir queries
        _law_data: dict = {}  # law_id -> {'mapped': [...], 'has_fine': bool}
        for _norma in (normativa or []):
            _lid = _norma['id']
            _m = load_topic_mapped_articles(selected_topic['id'], _lid)
            _hf = law_has_fine_mapping(selected_topic['id'], _lid)
            _law_data[_lid] = {'mapped': _m, 'has_fine': _hf, 'name': _norma['name']}

        # TTS de Tema: solo artículos mapeados específicamente al tema
        _topic_tts_items: list = [
            {"text": f"Tema {selected_topic['topic_number']}. {selected_topic['official_text']}", "label": f"Tema {selected_topic['topic_number']}"}
        ]
        for _norma in (normativa or []):
            _lid = _norma['id']
            _ld = _law_data[_lid]
            if _ld['has_fine'] and _ld['mapped']:
                _topic_tts_items.append({"text": _norma['name'], "label": f"Ley: {_norma['name']}"})
                for _a in _ld['mapped']:
                    _txt = clean_article_text(_a.get('text') or '')
                    if _txt:
                        _topic_tts_items.append({"text": _txt, "label": f"Art. {_a['article_ref']}"})

        col_th, col_taudio = st.columns([5, 1])
        with col_th:
            st.markdown(f"### Tema {selected_topic['topic_number']} ({part_name})")
        with col_taudio:
            render_tts_button_iframe(
                items=_topic_tts_items,
                label="🔊 Tema",
                key=f"tts_topic_{selected_topic['id']}",
            )
        st.write(selected_topic['official_text'])
        if selected_topic['section']:
            st.caption(f"Seccion: {selected_topic['section']}")

        st.divider()

        articles_for_annotations: list = []
        if not normativa:
            st.warning(
                "Este tema aun no tiene normativa vinculada en la validacion. "
                "Pendiente de delimitacion."
            )
        else:
            st.markdown("#### Normas de este tema")
            st.caption(f"{len(normativa)} norma(s) vinculada(s) especificamente a este tema.")
            for norma in normativa:
                law_id = norma['id']
                _ld = _law_data[law_id]
                mapped = _ld['mapped']
                has_fine = _ld['has_fine']
                articles_for_annotations.extend(mapped)

                with st.expander(f"📄 {norma['name']}", expanded=False):
                    # TTS de Ley: solo artículos de esa ley mapeados a este tema
                    if has_fine and mapped:
                        _law_items = [{"text": norma['name'], "label": f"Ley: {norma['name']}"}]
                        for _la in mapped:
                            _lt = clean_article_text(_la.get('text') or '')
                            if _lt:
                                _law_items.append({"text": _lt, "label": f"Art. {_la['article_ref']}"})
                        render_tts_button_iframe(
                            items=_law_items,
                            label="🔊 Reproducir ley",
                            key=f"tts_law_{law_id}",
                        )

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
                            or search_art.lower() in (a.get('title') or '').lower()
                        ]
                        for article in shown:
                            render_article_card(article, selected_topic['id'])
                        if not shown:
                            st.info(f"Ningun articulo coincide con '{search_art}'.")
                    else:
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
                            st.caption("Referencia completa de la norma. NO equivale a los articulos concretos del tema.")
                            render_paginated_articles(
                                all_articles,
                                selected_topic['id'],
                                f"all_articles_{selected_topic['id']}_{law_id}",
                            )

        # ── Temario CEF (para PE-51..60 y cualquier tema con recurso CEF) ───────
        _cef_res = load_topic_cef_resource(selected_topic['id'])
        if _cef_res and _cef_res.get("content_text"):
            _cef_text = _cef_res["content_text"]
            _cef_title = _cef_res.get("title") or "Temario CEF"
            _cef_status = _cef_res.get("validation_status") or "pendiente_de_validacion"
            _cef_preview = _cef_text[:300].replace("\n", " ") + "…"
            with st.expander(
                f"📚 Temario CEF — {_cef_title} "
                f"({'✓ contrastado' if 'contrastado' in _cef_status else '⚠ pendiente validación'})",
                expanded=False,
            ):
                st.caption(
                    "Contenido extraído del temario CEF (academia). "
                    "Material auxiliar de estudio — NO es fuente oficial. "
                    f"Estado: `{_cef_status}`"
                )
                # Mostrar por secciones si el texto tiene cabeceras tipo "1." o "TEMA"
                import html as _html_cef
                _escaped_cef = _html_cef.escape(_cef_text)
                st.markdown(
                    f'<div style="font-size:13px;line-height:1.7;color:#cdd6f4;'
                    f'white-space:pre-wrap;padding:8px 0;word-break:break-word;'
                    f'max-height:600px;overflow-y:auto;'
                    f'border:1px solid #313244;border-radius:4px;padding:12px;">'
                    f'{_escaped_cef}</div>',
                    unsafe_allow_html=True,
                )

        with st.expander("📁 Anotaciones antiguas (sistema legado)", expanded=False):
            render_study_annotations(selected_topic, articles_for_annotations)

    # ── Mis dudas ──
    st.divider()
    st.subheader("🤔 Mis dudas")

    conn = connect()
    doubts = list_doubts(conn, user_id=current_user_id())
    conn.close()

    if not doubts:
        st.info("No tienes dudas registradas. Marca artículos con dudas para guardarlas aquí.")
    else:
        st.caption(f"{len(doubts)} duda(s) registrada(s)")

        for doubt in doubts:
            with st.container(border=True):
                col_ref, col_resolve = st.columns([4, 1])
                with col_ref:
                    st.markdown(f"**Art. {doubt['article_ref']}** · {doubt['law_name']}")
                    st.write(doubt['doubt_text'])
                    st.caption(f"Guardada: {doubt['created_at'][:10]}")

                with col_resolve:
                    if st.button(
                        "✓ Resuelto",
                        key=f"resolve_doubt_{doubt['id']}",
                        use_container_width=True,
                    ):
                        conn = connect()
                        resolve_doubt(conn, doubt['article_id'], user_id=current_user_id())
                        conn.close()
                        st.success("Duda marcada como resuelta")
                        st.rerun()

        st.divider()
        st.markdown("**Exportar mis dudas**")
        col_csv, col_copy = st.columns(2)

        with col_csv:
            # Prepare CSV
            csv_content = "Artículo,Ley,Duda,Fecha\n"
            for doubt in doubts:
                csv_content += f'"{doubt["article_ref"]}","{doubt["law_name"]}","{doubt["doubt_text"].replace(chr(34), chr(34)*2)}","{doubt["created_at"][:10]}"\n'

            st.download_button(
                label="📥 Descargar CSV",
                data=csv_content,
                file_name="mis_dudas.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with col_copy:
            # Plain text for copy
            txt_content = "MIS DUDAS - " + datetime.now().strftime("%Y-%m-%d") + "\n" + "="*50 + "\n\n"
            for doubt in doubts:
                txt_content += f"Art. {doubt['article_ref']} ({doubt['law_name']})\n"
                txt_content += f"Duda: {doubt['doubt_text']}\n"
                txt_content += f"Fecha: {doubt['created_at'][:10]}\n\n"

            st.text_area(
                "Copiar texto",
                value=txt_content,
                height=150,
                disabled=True,
                label_visibility="collapsed",
            )

# ── Modo test ────────────────────────────────────────────────────────────────
with tabs[8]:
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

# ── Modo examen ──────────────────────────────────────────────────────────────
with tabs[9]:
    st.subheader("Modo examen (Ola E1)")
    tab_ex1, tab_ex2 = st.tabs(["Crear y ejecutar", "Historial"])

    with tab_ex1:
        if "exam_finished" not in st.session_state:
            st.session_state.exam_finished = False

        if st.session_state.exam_finished or "exam_id" in st.session_state:
            render_exam_execution()
        else:
            render_exam_creator()

    with tab_ex2:
        render_exam_history()

# ── Fallos ───────────────────────────────────────────────────────────────────
with tabs[10]:
    st.subheader("Base de fallos")
    summary = mistake_summary()
    if summary:
        st.dataframe(rows_to_df(summary), use_container_width=True, hide_index=True)
    else:
        st.info("Todavia no hay intentos registrados.")

# ── Informes y CSV ───────────────────────────────────────────────────────────
with tabs[11]:
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

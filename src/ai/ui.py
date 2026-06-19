"""UI integration for AI article insights (Streamlit).

Provides functions to render and manage AI insights in the study interface.
"""

from __future__ import annotations

import sqlite3
import streamlit as st

from src.ai.service import AIService, AIConfigError, AIServiceError
from src.core.db import connect


INSIGHT_TYPE_LABELS = {
    "explicacion": "Explicación sencilla",
    "resumen": "Resumen estructurado",
    "mnemotecnia": "Mnemotecnia",
    "comparacion": "Comparación con otros",
    "errores_comunes": "Errores comunes",
    "que_se_pregunta": "Qué suele preguntarse",
}


@st.cache_resource
def get_ai_service() -> AIService | None:
    """Get or initialize AIService. Returns None if API key not configured."""
    try:
        conn = connect()
        service = AIService(conn)
        return service
    except AIConfigError:
        return None
    except Exception as e:
        st.warning(f"Error initializing AI service: {e}")
        return None


def render_ai_insights(article_id: int, article_title: str, article_text: str) -> None:
    """Render AI insights expander for an article in the study interface."""
    service = get_ai_service()
    if not service:
        with st.expander("Insights IA (no configurado)", expanded=False):
            st.info(
                "Para usar insights de IA, configura ANTHROPIC_API_KEY. "
                "[Ver instrucciones](https://console.anthropic.com/account/keys)"
            )
        return

    with st.expander("Insights IA (Ola D2)", expanded=False):
        # Show existing insights
        existing = service.get_all_insights(article_id)
        if existing:
            st.caption(f"{len(existing)} insight(s) generado(s)")
            for insight in existing:
                insight_label = INSIGHT_TYPE_LABELS.get(
                    insight["insight_type"], insight["insight_type"]
                )
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{insight_label}**")
                    with col2:
                        status_badge = (
                            "🔴 Revisión" if insight["requiere_revision"] else "✓"
                        )
                        st.caption(status_badge)
                    st.markdown(insight["content"])
            st.divider()

        # Generate new insights
        st.markdown("**Generar nuevo insight**")
        insight_type = st.selectbox(
            "Tipo de insight",
            list(INSIGHT_TYPE_LABELS.keys()),
            format_func=lambda x: INSIGHT_TYPE_LABELS[x],
            key=f"insight_type_{article_id}",
        )

        col1, col2 = st.columns([4, 1])
        with col1:
            generate_btn = col1.button(
                "Generar",
                key=f"generate_insight_{article_id}_{insight_type}",
            )
        with col2:
            show_cost = col2.checkbox("Ver coste estimado", value=False)

        if show_cost:
            st.caption(
                "Estimación: ~2 minutos, ~$0.01-0.05 por insight con Opus 4.8"
            )

        if generate_btn:
            try:
                with st.spinner(f"Generando {INSIGHT_TYPE_LABELS[insight_type].lower()}..."):
                    if insight_type == "explicacion":
                        content = service.explain_article(
                            article_id, article_title, article_text, use_cache=True
                        )
                    elif insight_type == "resumen":
                        content = service.summarize_article(
                            article_id, article_title, article_text, use_cache=True
                        )
                    elif insight_type == "mnemotecnia":
                        content = service.create_mnemonic(
                            article_id, article_title, article_text, use_cache=True
                        )
                    elif insight_type == "errores_comunes":
                        content = service.identify_common_mistakes(
                            article_id, article_title, article_text, use_cache=True
                        )
                    elif insight_type == "que_se_pregunta":
                        content = service.predict_exam_questions(
                            article_id, article_title, article_text, use_cache=True
                        )
                    else:
                        content = "(tipo no soportado)"

                st.success(f"{INSIGHT_TYPE_LABELS[insight_type]} generado.")
                with st.container(border=True):
                    st.markdown(content)
                st.info(
                    "Este contenido está marcado como pendiente de revisión. "
                    "Verifica antes de usarlo para estudiar."
                )

            except AIServiceError as e:
                st.error(f"Error generando insight: {e}")
            except Exception as e:
                st.error(f"Error inesperado: {e}")

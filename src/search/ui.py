"""UI integration for search and article relations (Streamlit)."""

from __future__ import annotations

import sqlite3
import streamlit as st

from src.search.service import SearchService, SearchServiceError
from src.core.db import connect


def get_search_service() -> SearchService | None:
    """Get a fresh SearchService (no caching: avoids cross-thread sqlite errors)."""
    try:
        return SearchService(connect())
    except Exception as e:
        st.warning(f"Error initializing search service: {e}")
        return None


def render_related_articles(article_id: int, article_title: str) -> None:
    """Render related articles section (Ola D5)."""
    service = get_search_service()
    if not service:
        return

    with st.expander("Artículos relacionados (Ola D5)", expanded=False):
        st.markdown("**Mapa de relaciones**")

        # Tabs for different relation types
        tab1, tab2, tab3 = st.tabs(["Similares", "Citados", "Que citan"])

        with tab1:
            similar = service.find_related_articles(article_id, limit=10)
            if similar:
                st.markdown("**Artículos semánticamente similares:**")
                for rel in similar:
                    with st.container(border=True):
                        st.markdown(
                            f"**{rel['law_name']} - Art. {rel['article_ref']}** "
                            f"({rel['relation_type']})"
                        )
                        if rel["title"]:
                            st.caption(rel["title"])
                        st.caption(f"Similitud: {rel['weight']:.1%}")
            else:
                st.info("Sin artículos similares relacionados aún.")

        with tab2:
            related = service.find_related_articles(
                article_id,
                relation_type="desarrolla",
                limit=10,
            )
            if related:
                st.markdown("**Artículos que desarrollan este:**")
                for rel in related:
                    with st.container(border=True):
                        st.markdown(
                            f"**{rel['law_name']} - Art. {rel['article_ref']}**"
                        )
                        if rel["title"]:
                            st.caption(rel["title"])
            else:
                st.info("Sin artículos relacionados por desarrollo.")

        with tab3:
            citing = service.find_citing_articles(article_id, limit=10)
            if citing:
                st.markdown("**Artículos que citan este:**")
                for art in citing:
                    with st.container(border=True):
                        st.markdown(
                            f"**{art['law_name']} - Art. {art['article_ref']}**"
                        )
                        if art["title"]:
                            st.caption(art["title"])
            else:
                st.info("Sin referencias cruzadas registradas aún.")

        st.divider()
        st.caption(
            "Las relaciones entre artículos se pueden agregar "
            "mediante análisis automático o curaduría manual."
        )

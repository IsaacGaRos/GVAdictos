"""
Materializador: expande topic_source_segments a filas en topic_sources.

Segmentos en grupo → artículos individuales en topic_sources.
Operación idempotente: ejecutar múltiples veces = mismo resultado.
"""

from __future__ import annotations

import sqlite3
from typing import Any


def materialize_segments_for_topic(
    conn: sqlite3.Connection,
    topic_id: int,
    dry_run: bool = False
) -> dict[str, Any]:
    """
    Expandir todos los segmentos de un tema a topic_sources.

    Pasos:
    1. Obtener segmentos del tema
    2. Para cada segmento, expandir a artículos:
       - division → todos los artículos en esa división
       - range → artículos en [from_id, to_id]
       - single → un artículo
    3. Crear/actualizar filas en topic_sources
    4. Registrar estadísticas

    Idempotencia: si ya existe (topic_id, article_id), no duplicar.
    """
    segments = conn.execute(
        """
        SELECT id, segment_type, division_id, from_article_id, to_article_id,
               priority, mapping_basis, validation_status
        FROM topic_source_segments
        WHERE topic_id = ?
        """,
        (topic_id,)
    ).fetchall()

    if not segments:
        return {
            "topic_id": topic_id,
            "segments_processed": 0,
            "article_rows_created": 0,
            "article_rows_updated": 0,
            "article_rows_skipped": 0,
        }

    article_rows_created = 0
    article_rows_updated = 0
    article_rows_skipped = 0

    for segment in segments:
        seg_id, seg_type, div_id, from_art_id, to_art_id, priority, mapping_basis, validation_status = segment

        article_ids = []

        if seg_type == "division":
            # Expandir division a todos sus artículos
            rows = conn.execute(
                """
                SELECT DISTINCT a.id
                FROM articles a
                INNER JOIN article_division ad ON ad.article_id = a.id
                WHERE ad.division_id = ?
                ORDER BY a.id
                """,
                (div_id,)
            ).fetchall()
            article_ids = [row[0] for row in rows]

        elif seg_type == "range":
            # Expandir rango [from_id, to_id]
            rows = conn.execute(
                """
                SELECT id FROM articles
                WHERE id >= ? AND id <= ?
                ORDER BY id
                """,
                (from_art_id, to_art_id)
            ).fetchall()
            article_ids = [row[0] for row in rows]

        elif seg_type == "single":
            # Un artículo
            article_ids = [from_art_id]

        # Crear/actualizar filas en topic_sources
        for article_id in article_ids:
            existing = conn.execute(
                """
                SELECT id FROM topic_sources
                WHERE topic_id = ? AND article_id = ?
                """,
                (topic_id, article_id)
            ).fetchone()

            if existing:
                # Actualizar si cambió validation_status
                if not dry_run:
                    conn.execute(
                        """
                        UPDATE topic_sources
                        SET validation_status = ?, mapping_basis = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE topic_id = ? AND article_id = ?
                        """,
                        (validation_status, mapping_basis, topic_id, article_id)
                    )
                article_rows_updated += 1
            else:
                # Crear nueva fila
                if not dry_run:
                    conn.execute(
                        """
                        INSERT INTO topic_sources(
                            topic_id, law_id, article_id, priority, mapping_basis,
                            validation_status, created_at, updated_at
                        ) SELECT ?, a.law_id, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        FROM articles a WHERE a.id = ?
                        """,
                        (topic_id, article_id, priority, mapping_basis, validation_status, article_id)
                    )
                article_rows_created += 1

    if not dry_run:
        conn.commit()

    return {
        "topic_id": topic_id,
        "segments_processed": len(segments),
        "article_rows_created": article_rows_created,
        "article_rows_updated": article_rows_updated,
        "article_rows_skipped": article_rows_skipped,
    }


def materialize_all_segments(
    conn: sqlite3.Connection,
    dry_run: bool = False
) -> dict[str, Any]:
    """
    Materializar todos los segmentos de todos los temas.
    """
    topics = conn.execute(
        "SELECT DISTINCT topic_id FROM topic_source_segments ORDER BY topic_id"
    ).fetchall()

    total_created = 0
    total_updated = 0
    topic_results = []

    for (topic_id,) in topics:
        result = materialize_segments_for_topic(conn, topic_id, dry_run=dry_run)
        total_created += result["article_rows_created"]
        total_updated += result["article_rows_updated"]
        topic_results.append(result)

    return {
        "topics_processed": len(topics),
        "total_article_rows_created": total_created,
        "total_article_rows_updated": total_updated,
        "topic_results": topic_results,
    }

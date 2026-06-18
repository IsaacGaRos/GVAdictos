from __future__ import annotations

from typing import Any

from src.core.db import connect


ANNOTATION_TYPES = ["note", "highlight", "doubt", "bookmark"]
ANNOTATION_COLORS = ["", "yellow", "green", "blue", "pink"]


def validate_annotation_type(annotation_type: str) -> None:
    if annotation_type not in ANNOTATION_TYPES:
        raise ValueError(f"Unsupported annotation_type: {annotation_type}")


def create_annotation(
    topic_id: int | None,
    article_id: int | None,
    annotation_type: str,
    selected_text: str | None = None,
    manual_reference: str | None = None,
    note_text: str | None = None,
    color: str | None = None,
) -> int:
    validate_annotation_type(annotation_type)
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO study_annotations(
                topic_id, article_id, annotation_type, selected_text,
                manual_reference, note_text, color
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                topic_id,
                article_id,
                annotation_type,
                selected_text,
                manual_reference,
                note_text,
                color,
            ),
        )
        return int(cursor.lastrowid)


def update_annotation(
    annotation_id: int,
    article_id: int | None,
    annotation_type: str,
    selected_text: str | None = None,
    manual_reference: str | None = None,
    note_text: str | None = None,
    color: str | None = None,
) -> None:
    validate_annotation_type(annotation_type)
    with connect() as conn:
        conn.execute(
            """
            UPDATE study_annotations
            SET article_id = ?,
                annotation_type = ?,
                selected_text = ?,
                manual_reference = ?,
                note_text = ?,
                color = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                article_id,
                annotation_type,
                selected_text,
                manual_reference,
                note_text,
                color,
                annotation_id,
            ),
        )


def delete_annotation(annotation_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM study_annotations WHERE id = ?", (annotation_id,))


def get_annotations_for_topic(topic_id: int) -> list:
    with connect() as conn:
        return conn.execute(
            """
            SELECT
                sa.*,
                a.article_ref,
                a.title AS article_title,
                l.name AS law_name
            FROM study_annotations sa
            LEFT JOIN articles a ON a.id = sa.article_id
            LEFT JOIN laws l ON l.id = a.law_id
            WHERE sa.topic_id = ?
            ORDER BY sa.updated_at DESC, sa.id DESC
            """,
            (topic_id,),
        ).fetchall()

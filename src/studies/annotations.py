"""
Capa de compatibilidad para anotaciones.

Después de Ola A1, este módulo delega a StudyService en lugar de usar SQL directo.
La UI (app.py) sigue llamando a estas funciones sin cambios.
"""

from __future__ import annotations

from typing import Any

from src.core.db import connect
from src.study.repository import StudyRepository
from src.study.service import StudyService, StudyTarget


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
    """
    Crear anotacion. Delega a StudyService.

    Mapeo:
    - annotation_type='note' -> add_article_note
    - annotation_type='highlight' -> add_highlight
    - annotation_type='doubt' -> mark(mark_type='doubt')
    - annotation_type='bookmark' -> mark(mark_type='bookmark')
    """
    validate_annotation_type(annotation_type)

    with connect() as conn:
        service = StudyService(StudyRepository(conn))

        try:
            if annotation_type == "note" and article_id:
                note_id = service.add_article_note(
                    article_id=article_id,
                    note_text=note_text or manual_reference or "",
                    selected_text=selected_text,
                    anchor_key=None,
                    tags=None,
                )
                conn.commit()
                return note_id

            elif annotation_type == "highlight" and article_id:
                highlight_color = color or "yellow"
                highlight_id = service.add_highlight(
                    article_id=article_id,
                    selected_text=selected_text or "",
                    color=highlight_color,
                    anchor_key=None,
                    start_offset=None,
                    end_offset=None,
                    note_text=note_text or manual_reference,
                )
                conn.commit()
                return highlight_id

            elif annotation_type == "doubt":
                target = StudyTarget(topic_id=topic_id, article_id=article_id)
                mark_id = service.mark(
                    target,
                    mark_type="doubt",
                    note_text=note_text or manual_reference,
                    resolved=False,
                )
                conn.commit()
                return mark_id

            elif annotation_type == "bookmark":
                target = StudyTarget(topic_id=topic_id, article_id=article_id)
                mark_id = service.mark(
                    target,
                    mark_type="bookmark",
                    note_text=note_text or manual_reference,
                    resolved=False,
                )
                conn.commit()
                return mark_id

            else:
                raise ValueError(f"Unsupported annotation_type: {annotation_type}")

        except Exception as e:
            raise RuntimeError(f"Error creating annotation: {e}")


def update_annotation(
    annotation_id: int,
    article_id: int | None,
    annotation_type: str,
    selected_text: str | None = None,
    manual_reference: str | None = None,
    note_text: str | None = None,
    color: str | None = None,
) -> None:
    """
    Actualizar anotacion. Delega a StudyService.

    Nota: La vieja tabla study_annotations se mantuvo para compatibilidad,
    pero si hubiera registros, habría que migrarlos. Por ahora esta funcion
    trabaja sobre las nuevas tablas.
    """
    validate_annotation_type(annotation_type)

    with connect() as conn:
        service = StudyService(StudyRepository(conn))

        try:
            if annotation_type == "note" and article_id:
                service.update_article_note(
                    note_id=annotation_id,
                    note_text=note_text or manual_reference or "",
                    selected_text=selected_text,
                    anchor_key=None,
                    tags=None,
                )

            elif annotation_type == "highlight" and article_id:
                highlight_color = color or "yellow"
                service.update_highlight(
                    highlight_id=annotation_id,
                    selected_text=selected_text or "",
                    color=highlight_color,
                    anchor_key=None,
                    start_offset=None,
                    end_offset=None,
                    note_text=note_text or manual_reference,
                )

            else:
                # Para dudas y marcadores, no hay update directo; se haria un upsert
                # Por ahora simplemente no hacer nada o lanzar error descriptivo
                raise NotImplementedError(
                    f"Update no soportado para annotation_type={annotation_type}"
                )

            conn.commit()

        except Exception as e:
            raise RuntimeError(f"Error updating annotation: {e}")


def delete_annotation(annotation_id: int) -> None:
    """
    Borrar anotacion. Para notas y subrayados, archivamos en lugar de borrar.
    Para marcas, seria un cambio de resolved o borrado directo.
    """
    with connect() as conn:
        service = StudyService(StudyRepository(conn))

        try:
            # Intentamos archivar como nota (soft delete)
            service.delete_article_note(annotation_id)
            conn.commit()
        except Exception:
            # Si falla como nota, intentamos como highlight
            try:
                service.delete_highlight(annotation_id)
                conn.commit()
            except Exception as e:
                raise RuntimeError(f"Error deleting annotation {annotation_id}: {e}")


def get_annotations_for_topic(topic_id: int) -> list:
    """
    Obtener anotaciones para un tema.

    Devuelve una lista de diccionarios compatibles con el formato antiguo
    para que app.py no tenga que cambiar.
    """
    with connect() as conn:
        service = StudyService(StudyRepository(conn))
        result = []

        try:
            # Obtener resumen del tema
            summary = service.get_topic_summary(topic_id)

            # Todos los articulos delimitados del tema (ignorando filas sin article_id)
            article_id_rows = conn.execute(
                "SELECT DISTINCT article_id FROM topic_sources "
                "WHERE topic_id = ? AND article_id IS NOT NULL",
                (topic_id,),
            ).fetchall()
            article_ids = [int(r["article_id"]) for r in article_id_rows]

            for article_id in article_ids:
                article_state = service.get_article_state(article_id)

                # Notas
                for note in article_state.get("notes", []):
                    result.append({
                        "id": note["id"],
                        "topic_id": topic_id,
                        "article_id": article_id,
                        "annotation_type": "note",
                        "selected_text": note.get("selected_text"),
                        "manual_reference": note.get("anchor_key"),
                        "note_text": note.get("note_text"),
                        "color": None,
                        "article_ref": conn.execute(
                            "SELECT article_ref FROM articles WHERE id = ?", (article_id,)
                        ).fetchone()[0],
                        "article_title": conn.execute(
                            "SELECT title FROM articles WHERE id = ?", (article_id,)
                        ).fetchone()[0],
                        "law_name": conn.execute(
                            "SELECT l.name FROM articles a JOIN laws l ON l.id = a.law_id WHERE a.id = ?",
                            (article_id,),
                        ).fetchone()[0],
                        "updated_at": note.get("updated_at"),
                    })

                # Subrayados
                for highlight in article_state.get("highlights", []):
                    result.append({
                        "id": highlight["id"],
                        "topic_id": topic_id,
                        "article_id": article_id,
                        "annotation_type": "highlight",
                        "selected_text": highlight.get("selected_text"),
                        "manual_reference": highlight.get("anchor_key"),
                        "note_text": highlight.get("note_text"),
                        "color": highlight.get("color", "yellow"),
                        "article_ref": conn.execute(
                            "SELECT article_ref FROM articles WHERE id = ?", (article_id,)
                        ).fetchone()[0],
                        "article_title": conn.execute(
                            "SELECT title FROM articles WHERE id = ?", (article_id,)
                        ).fetchone()[0],
                        "law_name": conn.execute(
                            "SELECT l.name FROM articles a JOIN laws l ON l.id = a.law_id WHERE a.id = ?",
                            (article_id,),
                        ).fetchone()[0],
                        "updated_at": highlight.get("updated_at"),
                    })

                # Dudas (marks)
                for mark in article_state.get("marks", []):
                    if mark.get("mark_type") == "doubt":
                        result.append({
                            "id": mark["id"],
                            "topic_id": topic_id,
                            "article_id": article_id,
                            "annotation_type": "doubt",
                            "selected_text": None,
                            "manual_reference": None,
                            "note_text": mark.get("note_text"),
                            "color": None,
                            "article_ref": conn.execute(
                                "SELECT article_ref FROM articles WHERE id = ?", (article_id,)
                            ).fetchone()[0],
                            "article_title": conn.execute(
                                "SELECT title FROM articles WHERE id = ?", (article_id,)
                            ).fetchone()[0],
                            "law_name": conn.execute(
                                "SELECT l.name FROM articles a JOIN laws l ON l.id = a.law_id WHERE a.id = ?",
                                (article_id,),
                            ).fetchone()[0],
                            "updated_at": mark.get("updated_at"),
                        })

        except Exception as e:
            # Si hay error, devolver lista vacía para no romper la UI
            print(f"Error getting annotations for topic {topic_id}: {e}")
            return []

    return sorted(result, key=lambda x: x.get("updated_at", ""), reverse=True)

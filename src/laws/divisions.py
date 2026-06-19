"""
Extractor de estructura jerárquica de leyes.

Lee la estructura de divisiones (TÍTULO, CAPÍTULO, SECCIÓN, etc.) de los artículos
y la registra en law_divisions + article_division.

Fuera del importer (zona sensible). Trabajo de datos, no de parsing crítico.
"""

from __future__ import annotations

import re
import sqlite3
from typing import Any

from src.core.db import connect


# Patrones de cabecera de sección
DIVISION_PATTERNS = {
    "libro": r"^LIBRO\s+([IVX]+|[0-9]+)(?:\s*[-–]\s*(.+))?",
    "titulo": r"^T[ÍI]TULO\s+(PRELIMINAR|[IVX]+|[0-9]+)(?:\s*[-–]\s*(.+))?",
    "capitulo": r"^CAP[ÍI]TULO\s+(PRELIMINAR|[IVX]+|[0-9]+)(?:\s*[-–]\s*(.+))?",
    "seccion": r"^SECCI[ÓO]N\s+([IVX]+|[0-9]+)(?:\s*[-–]\s*(.+))?",
    "subseccion": r"^SUBSECCIO?N\s+([IVX]+|[0-9]+)(?:\s*[-–]\s*(.+))?",
    "disposicion": r"^DISPOSICI[ÓO]N (ADICIONAL|TRANSITORIA|DEROGATORIA)\s+([A-Z0-9]+)?(?:\s*[-–]\s*(.+))?",
}

HIERARCHY = ["libro", "titulo", "capitulo", "seccion", "subseccion", "disposicion"]


def parse_division_line(line: str) -> tuple[str, str, str] | None:
    """
    Analizar una línea para extraer tipo de división, número y etiqueta.

    Retorna: (division_type, number, label) o None
    """
    for div_type, pattern in DIVISION_PATTERNS.items():
        match = re.match(pattern, line.strip(), re.IGNORECASE)
        if match:
            groups = match.groups()
            number = groups[0] if groups else None

            # Para disposiciones, el número es más complejo
            if div_type == "disposicion":
                number = groups[1] if len(groups) > 1 else groups[0]
                label = groups[2] if len(groups) > 2 else None
            else:
                label = groups[1] if len(groups) > 1 else None

            return (div_type, number, label)

    return None


def extract_article_divisions(text: str) -> list[tuple[str, str, str]]:
    """
    Extraer divisiones de sección del texto de un artículo.

    Los artículos generalmente empiezan con su número, pero pueden contener
    estructuras internas con subsecciones. Buscamos esas líneas.
    """
    divisions = []
    lines = text.split('\n')

    for line in lines[:20]:  # Buscar en las primeras 20 líneas
        parsed = parse_division_line(line)
        if parsed:
            divisions.append(parsed)

    return divisions


class DivisionBuilder:
    """Construir árbol de divisiones para una ley."""

    def __init__(self, law_id: int, conn: sqlite3.Connection):
        self.law_id = law_id
        self.conn = conn
        self.divisions: dict[str, int] = {}  # (parent_id, div_type, number) -> division_id

    def get_or_create_division(
        self,
        division_type: str,
        number: str,
        label: str | None = None,
        parent_id: int | None = None,
        order_index: int = 0,
    ) -> int:
        """Obtener o crear una división, devolver su ID."""

        # Buscar si ya existe
        row = self.conn.execute(
            """
            SELECT id FROM law_divisions
            WHERE law_id = ? AND parent_id IS ? AND division_type = ? AND number = ?
            """,
            (self.law_id, parent_id, division_type, number),
        ).fetchone()

        if row:
            return int(row[0])

        # Crear nueva
        full_path = self._build_full_path(parent_id, division_type, number)
        cursor = self.conn.execute(
            """
            INSERT INTO law_divisions(
                law_id, parent_id, division_type, number, label, order_index, full_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (self.law_id, parent_id, division_type, number, label, order_index, full_path),
        )
        return int(cursor.lastrowid)

    def _build_full_path(self, parent_id: int | None, division_type: str, number: str) -> str:
        """Construir full_path como "Título I > Capítulo II"."""
        parts = []

        # Recorrer hacia arriba si hay parent
        current_id = parent_id
        while current_id:
            row = self.conn.execute(
                "SELECT division_type, number, parent_id FROM law_divisions WHERE id = ?",
                (current_id,),
            ).fetchone()
            if row:
                parts.insert(0, f"{self._format_label(row[0])} {row[1]}")
                current_id = row[2]
            else:
                break

        parts.append(f"{self._format_label(division_type)} {number}")
        return " > ".join(parts)

    def _format_label(self, div_type: str) -> str:
        """Formatear tipo de división para full_path."""
        labels = {
            "libro": "Libro",
            "titulo": "Título",
            "capitulo": "Capítulo",
            "seccion": "Sección",
            "subseccion": "Subsección",
            "disposicion": "Disposición",
        }
        return labels.get(div_type, div_type.capitalize())

    def add_article_to_division(self, article_id: int, division_id: int, is_primary: bool = True) -> None:
        """Asignar un artículo a una división."""
        self.conn.execute(
            """
            INSERT OR IGNORE INTO article_division(article_id, division_id, is_primary)
            VALUES (?, ?, ?)
            """,
            (article_id, division_id, 1 if is_primary else 0),
        )


def extract_divisions_for_law(law_id: int, dry_run: bool = False) -> dict[str, Any]:
    """
    Extraer divisiones de todos los artículos de una ley.

    Retorna estadísticas: {divisions_created, articles_linked, ...}
    """
    with connect() as conn:
        # Obtener nombre de la ley
        law_row = conn.execute(
            "SELECT name FROM laws WHERE id = ?", (law_id,)
        ).fetchone()
        law_name = law_row[0] if law_row else f"Law {law_id}"

        # Obtener artículos de la ley
        articles = conn.execute(
            "SELECT id, article_ref, text FROM articles WHERE law_id = ? ORDER BY id",
            (law_id,),
        ).fetchall()

        if not articles:
            return {"law_id": law_id, "law_name": law_name, "divisions_created": 0, "articles_linked": 0}

        builder = DivisionBuilder(law_id, conn)
        divisions_created = 0
        articles_linked = 0

        for article_id, article_ref, text in articles:
            divisions_found = extract_article_divisions(text)

            if not divisions_found:
                continue

            # Construir árbol de divisiones para este artículo
            parent_id = None
            for idx, (div_type, number, label) in enumerate(divisions_found):
                # Solo crear divisiones en el orden jerárquico esperado
                if div_type not in HIERARCHY:
                    continue

                # Crear o obtener división
                div_id = builder.get_or_create_division(
                    division_type=div_type,
                    number=number,
                    label=label,
                    parent_id=parent_id,
                    order_index=idx,
                )

                if parent_id is None:
                    divisions_created += 1

                parent_id = div_id

            # Asignar artículo a la división más específica
            if parent_id:
                if not dry_run:
                    builder.add_article_to_division(article_id, parent_id, is_primary=True)
                articles_linked += 1

        if not dry_run:
            conn.commit()

        return {
            "law_id": law_id,
            "law_name": law_name,
            "articles_processed": len(articles),
            "divisions_created": divisions_created,
            "articles_linked": articles_linked,
        }

"""
Servicio de preferencias de lectura (Ola A5).

Gestiona tipografía, contraste, tema, accesibilidad.
"""

from __future__ import annotations

import sqlite3
from typing import Any


class ReadingPreferencesService:
    """Gestionar preferencias de lectura del usuario."""

    def __init__(self, conn: sqlite3.Connection, user_id: int = 1):
        self.conn = conn
        self.user_id = user_id
        self.conn.row_factory = sqlite3.Row

    def get_preferences(self) -> dict[str, Any]:
        """Obtener preferencias del usuario (o defaults)."""
        row = self.conn.execute(
            """
            SELECT font_family, font_size, line_height, max_width, theme, contrast,
                   dyslexia_mode, word_spacing, letter_spacing
            FROM user_reading_preferences
            WHERE user_id = ?
            """,
            (self.user_id,)
        ).fetchone()

        if row:
            return dict(row)

        # Return defaults
        return {
            "font_family": "Georgia",
            "font_size": 16,
            "line_height": 1.6,
            "max_width": 680,
            "theme": "light",
            "contrast": "normal",
            "dyslexia_mode": 0,
            "word_spacing": 1.0,
            "letter_spacing": 0.0,
        }

    def set_preferences(
        self,
        font_family: str | None = None,
        font_size: int | None = None,
        line_height: float | None = None,
        max_width: int | None = None,
        theme: str | None = None,
        contrast: str | None = None,
        dyslexia_mode: bool | None = None,
        word_spacing: float | None = None,
        letter_spacing: float | None = None,
    ) -> None:
        """Actualizar preferencias del usuario."""
        # Obtener actuales
        current = self.get_preferences()

        # Sobrescribir con nuevos valores
        if font_family is not None:
            current["font_family"] = font_family
        if font_size is not None:
            current["font_size"] = font_size
        if line_height is not None:
            current["line_height"] = line_height
        if max_width is not None:
            current["max_width"] = max_width
        if theme is not None:
            current["theme"] = theme
        if contrast is not None:
            current["contrast"] = contrast
        if dyslexia_mode is not None:
            current["dyslexia_mode"] = 1 if dyslexia_mode else 0
        if word_spacing is not None:
            current["word_spacing"] = word_spacing
        if letter_spacing is not None:
            current["letter_spacing"] = letter_spacing

        # Guardar
        self.conn.execute(
            """
            INSERT OR REPLACE INTO user_reading_preferences(
                user_id, font_family, font_size, line_height, max_width,
                theme, contrast, dyslexia_mode, word_spacing, letter_spacing
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self.user_id,
                current["font_family"],
                current["font_size"],
                current["line_height"],
                current["max_width"],
                current["theme"],
                current["contrast"],
                current["dyslexia_mode"],
                current["word_spacing"],
                current["letter_spacing"],
            )
        )

    def apply_preset(self, preset_name: str) -> None:
        """Aplicar un preset de lectura."""
        preset = self.conn.execute(
            """
            SELECT font_family, font_size, line_height, max_width, theme, contrast, dyslexia_mode
            FROM reading_presets
            WHERE preset_name = ?
            """,
            (preset_name,)
        ).fetchone()

        if not preset:
            raise ValueError(f"Preset '{preset_name}' no existe")

        self.set_preferences(
            font_family=preset["font_family"],
            font_size=preset["font_size"],
            line_height=preset["line_height"],
            max_width=preset["max_width"],
            theme=preset["theme"],
            contrast=preset["contrast"],
            dyslexia_mode=bool(preset["dyslexia_mode"]),
        )

    def get_color_tokens(self, theme: str | None = None) -> dict[str, str]:
        """Obtener tokens de color para un tema."""
        if theme is None:
            theme = self.get_preferences()["theme"]

        tokens = self.conn.execute(
            """
            SELECT token_name, token_value
            FROM design_tokens
            WHERE token_category = 'color' AND theme = ?
            """,
            (theme,)
        ).fetchall()

        return {row["token_name"]: row["token_value"] for row in tokens}

    def generate_css(self) -> str:
        """Generar CSS basado en preferencias actuales."""
        prefs = self.get_preferences()
        tokens = self.get_color_tokens(prefs["theme"])

        font_stack = self._get_font_stack(prefs["font_family"])
        bg_color = tokens.get("background-light", "#ffffff")
        text_color = tokens.get("text-primary-light", "#2c3e50")
        accent_color = tokens.get("accent-light", "#3498db")

        css = f"""
/* Generated CSS for reading preferences */
body {{
    font-family: {font_stack};
    font-size: {prefs['font_size']}px;
    line-height: {prefs['line_height']};
    max-width: {prefs['max_width']}px;
    word-spacing: {prefs['word_spacing']}em;
    letter-spacing: {prefs['letter_spacing']}px;
    background-color: {bg_color};
    color: {text_color};
    margin: 0 auto;
    padding: 20px;
}}

a {{
    color: {accent_color};
    text-decoration: underline;
}}

.article-text {{
    line-height: {prefs['line_height']};
    hyphens: auto;
}}

/* Contraste */
"""

        if prefs["contrast"] == "high":
            css += "body { font-weight: 600; }\n"
        elif prefs["contrast"] == "aaa":
            css += "body { font-weight: 700; }\n"

        # Dislexia
        if prefs["dyslexia_mode"]:
            css += """
/* Dyslexia-friendly */
body { letter-spacing: 0.12em; word-spacing: 0.25em; }
.article-text { font-family: Arial, sans-serif; }
"""

        return css

    def _get_font_stack(self, font_family: str) -> str:
        """Obtener font-stack CSS para una familia de fuente."""
        stacks = {
            "Georgia": "Georgia, 'Times New Roman', serif",
            "Arial": "Arial, Helvetica, sans-serif",
            "Verdana": "Verdana, Geneva, sans-serif",
            "Courier": "'Courier New', Courier, monospace",
        }
        return stacks.get(font_family, "'Georgia', serif")

    def list_presets(self) -> list[dict[str, Any]]:
        """Listar presets disponibles."""
        rows = self.conn.execute(
            """
            SELECT preset_name, description, font_family, font_size, theme, contrast, dyslexia_mode
            FROM reading_presets
            ORDER BY preset_name
            """
        ).fetchall()
        return [dict(row) for row in rows]

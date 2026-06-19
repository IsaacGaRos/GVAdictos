"""
Schema para preferencias de lectura optimizadas (Ola A5).

Tipografía, contraste, diseño basados en evidencia de legibilidad.
"""

from __future__ import annotations

import sqlite3


CREATE_READING_SQL = """
-- Preferencias de lectura del usuario
CREATE TABLE IF NOT EXISTS user_reading_preferences (
    user_id INTEGER PRIMARY KEY DEFAULT 1,
    font_family TEXT NOT NULL DEFAULT 'Georgia',  -- serif para lectura prolongada
    font_size INTEGER NOT NULL DEFAULT 16,        -- pixels
    line_height REAL NOT NULL DEFAULT 1.6,        -- proporción (1.5-1.8 óptimo)
    max_width INTEGER NOT NULL DEFAULT 680,       -- pixels (60-75 chars típico)
    theme TEXT NOT NULL DEFAULT 'light' CHECK(theme IN ('light', 'dark', 'sepia')),
    contrast TEXT NOT NULL DEFAULT 'normal' CHECK(contrast IN ('normal', 'high', 'aa', 'aaa')),
    dyslexia_mode INTEGER NOT NULL DEFAULT 0 CHECK(dyslexia_mode IN (0, 1)),
    word_spacing REAL NOT NULL DEFAULT 1.0,       -- proporción
    letter_spacing REAL NOT NULL DEFAULT 0.0,     -- pixels
    background_color TEXT,                         -- hex color (usa theme por defecto)
    text_color TEXT,                              -- hex color (usa theme por defecto)
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Tokens de diseño (colores para temas)
CREATE TABLE IF NOT EXISTS design_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_name TEXT NOT NULL UNIQUE,
    token_category TEXT NOT NULL,  -- color | typography | spacing | contrast
    token_value TEXT NOT NULL,
    theme TEXT,                    -- light | dark | sepia | NULL (global)
    description TEXT,
    wcag_level TEXT,              -- AA | AAA | NULL
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_design_tokens_category
    ON design_tokens(token_category, theme);

-- Presets de lectura (para usuarios sin preferences, o para compartir)
CREATE TABLE IF NOT EXISTS reading_presets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    preset_name TEXT NOT NULL UNIQUE,
    description TEXT,
    font_family TEXT NOT NULL,
    font_size INTEGER NOT NULL,
    line_height REAL NOT NULL,
    max_width INTEGER NOT NULL,
    theme TEXT NOT NULL,
    contrast TEXT NOT NULL,
    dyslexia_mode INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def apply_reading_schema(conn: sqlite3.Connection) -> None:
    """Crear tablas de lectura si no existen."""
    conn.executescript(CREATE_READING_SQL)

    # Insertar presets estándar
    presets = [
        (
            "standard",
            "Legibilidad estándar: Georgia, 16px, 1.6 line height",
            "Georgia", 16, 1.6, 680, "light", "normal", 0
        ),
        (
            "large_print",
            "Letra grande: 20px, 1.8 line height para problemas de visión",
            "Georgia", 20, 1.8, 600, "light", "high", 0
        ),
        (
            "dyslexia_friendly",
            "Dislexia: tipografía sans-serif, espaciado aumentado",
            "Arial", 16, 1.8, 650, "light", "aaa", 1
        ),
        (
            "dark_mode",
            "Modo oscuro: fondo oscuro, contraste alto",
            "Georgia", 16, 1.6, 680, "dark", "aaa", 0
        ),
        (
            "sepia_warm",
            "Modo sepia cálido: fondo sepia, tipografía cálida",
            "Georgia", 16, 1.6, 680, "sepia", "aa", 0
        ),
    ]

    for preset in presets:
        conn.execute(
            """
            INSERT OR IGNORE INTO reading_presets(
                preset_name, description, font_family, font_size, line_height,
                max_width, theme, contrast, dyslexia_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            preset
        )

    # Insertar tokens de diseño de colores por tema
    color_tokens = [
        # Light theme
        ("text-primary-light", "color", "#2c3e50", "light", "Texto principal", "AAA"),
        ("text-secondary-light", "color", "#7f8c8d", "light", "Texto secundario", "AA"),
        ("background-light", "color", "#ffffff", "light", "Fondo principal", None),
        ("accent-light", "color", "#3498db", "light", "Color de acento", "AAA"),
        # Dark theme
        ("text-primary-dark", "color", "#ecf0f1", "dark", "Texto principal", "AAA"),
        ("text-secondary-dark", "color", "#95a5a6", "dark", "Texto secundario", "AA"),
        ("background-dark", "color", "#1a1a1a", "dark", "Fondo principal", None),
        ("accent-dark", "color", "#3498db", "dark", "Color de acento", "AAA"),
        # Sepia theme
        ("text-primary-sepia", "color", "#3e3d32", "sepia", "Texto principal", "AAA"),
        ("text-secondary-sepia", "color", "#8b8680", "sepia", "Texto secundario", "AA"),
        ("background-sepia", "color", "#f4ecd8", "sepia", "Fondo principal", None),
        ("accent-sepia", "color", "#8b6914", "sepia", "Color de acento", "AA"),
    ]

    for token in color_tokens:
        conn.execute(
            """
            INSERT OR IGNORE INTO design_tokens(
                token_name, token_category, token_value, theme, description, wcag_level
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            token
        )


def reading_schema_exists(conn: sqlite3.Connection) -> bool:
    """Comprobar si las tablas de lectura existen."""
    tables = {"user_reading_preferences", "design_tokens", "reading_presets"}
    existing = set(
        row[0]
        for row in conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN (?, ?, ?)
            """,
            tuple(tables)
        ).fetchall()
    )
    return tables == existing

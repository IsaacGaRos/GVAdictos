from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.core.db import connect
from src.core.paths import EXPORTS_DIR, ensure_runtime_dirs


def export_table(table: str, output_path: Path | None = None) -> Path:
    allowed = {"questions", "attempts", "laws", "articles"}
    if table not in allowed:
        raise ValueError(f"Tabla no exportable: {table}")

    ensure_runtime_dirs()
    path = output_path or EXPORTS_DIR / f"{table}.csv"
    with connect() as conn:
        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def export_anki_basic(output_path: Path | None = None) -> Path:
    ensure_runtime_dirs()
    path = output_path or EXPORTS_DIR / "anki_preguntas.csv"
    with connect() as conn:
        df = pd.read_sql_query(
            """
            SELECT
                enunciado AS Front,
                respuesta_correcta || ': ' ||
                CASE respuesta_correcta
                    WHEN 'A' THEN opcion_a
                    WHEN 'B' THEN opcion_b
                    WHEN 'C' THEN opcion_c
                    ELSE opcion_d
                END || char(10) || explicacion || char(10) || 'Fuente: ' || fuente AS Back,
                replace(COALESCE(etiquetas, ''), ',', ' ') AS Tags
            FROM questions
            """,
            conn,
        )
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path

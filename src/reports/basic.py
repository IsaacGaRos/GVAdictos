from __future__ import annotations

from src.core.db import connect


def dashboard_counts() -> dict[str, int]:
    with connect() as conn:
        return {
            "normas": conn.execute("SELECT COUNT(*) FROM laws").fetchone()[0],
            "articulos": conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0],
            "preguntas": conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0],
            "intentos": conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0],
            "fallos": conn.execute("SELECT COUNT(*) FROM attempts WHERE acierto = 0").fetchone()[0],
            "fuentes": conn.execute("SELECT COUNT(*) FROM source_documents").fetchone()[0],
        }

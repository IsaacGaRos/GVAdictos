from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mapping_tools import (
    build_status_snapshot,
    connect_readonly,
    ensure_reports_dir,
    render_md_table,
)


def main() -> int:
    reports_dir = ensure_reports_dir()
    md_path = reports_dir / "mapping_status.md"
    json_path = reports_dir / "mapping_status.json"

    with connect_readonly() as conn:
        snapshot = build_status_snapshot(conn)

    json_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    top_rows = snapshot["top_urgent_topics"]
    lines = [
        "# Estado global del mapping fino",
        "",
        "Informe generado en modo read-only. No modifica la BD.",
        "",
        "## Resumen",
        "",
        f"- Total temas: {snapshot['total_topics']}",
        f"- Temas con mapping fino: {snapshot['fine_mapping_topics']}",
        f"- Temas en fallback: {snapshot['fallback_topics']}",
        f"- Temas parciales: {snapshot['partial_topics']}",
        f"- Temas mapped: {snapshot['mapped_topics']}",
        f"- Temas ambiguous: {snapshot['ambiguous_topics']}",
        f"- Normas afectadas por fallback/revision: {snapshot['affected_law_count']}",
        f"- Progreso: {snapshot['progress_percent']}%",
        "",
        "## Riesgos e inconsistencias",
        "",
        *[f"- {key}: {value}" for key, value in snapshot["risks"].items()],
        "",
        "## Top temas urgentes",
        "",
        render_md_table(
            top_rows,
            [
                ("part", "Parte"),
                ("topic_number", "Tema"),
                ("topic_status", "Estado"),
                ("unresolved_law_count", "Normas sin delimitar"),
                ("unresolved_article_total", "Articulos potenciales"),
                ("topic_title", "Titulo"),
            ],
        ),
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

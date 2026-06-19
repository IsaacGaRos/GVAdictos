from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.study.repository import StudyRepository
from src.study.schema import apply_study_schema
from src.study.service import StudyService, StudyTarget


REPORTS_DIR = ROOT / "reports"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def seed_temp_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE laws (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );

        CREATE TABLE topics (
            id INTEGER PRIMARY KEY,
            topic_number INTEGER,
            part TEXT,
            official_text TEXT
        );

        CREATE TABLE articles (
            id INTEGER PRIMARY KEY,
            law_id INTEGER,
            article_ref TEXT,
            title TEXT
        );

        CREATE TABLE topic_sources (
            id INTEGER PRIMARY KEY,
            topic_id INTEGER,
            law_id INTEGER,
            article_id INTEGER,
            normative_reference TEXT
        );

        INSERT INTO laws(id, name) VALUES (1, 'Norma demo');
        INSERT INTO topics(id, topic_number, part, official_text)
        VALUES (1, 1, 'especial', 'Tema demo');
        INSERT INTO articles(id, law_id, article_ref, title)
        VALUES
            (1, 1, '1', 'Articulo demo 1'),
            (2, 1, '2', 'Articulo demo 2');
        INSERT INTO topic_sources(id, topic_id, law_id, article_id, normative_reference)
        VALUES
            (1, 1, 1, 1, 'Articulo 1'),
            (2, 1, 1, 2, 'Articulo 2');
        """
    )
    apply_study_schema(conn)
    conn.commit()
    return conn


def write_report(payload: dict[str, object]) -> tuple[Path, Path]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_DIR / "study_features_demo.json"
    md_path = REPORTS_DIR / "study_features_demo.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Study features demo",
        "",
        f"- Generated at: {payload['generated_at']}",
        f"- Uses temp DB: {payload['uses_temp_db']}",
        f"- Temp DB path: `{payload['temp_db_path']}`",
        "",
        "## Article State",
        "",
        "```json",
        json.dumps(payload["article_state"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## Topic Summary",
        "",
        "```json",
        json.dumps(payload["topic_summary"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## Law Summary",
        "",
        "```json",
        json.dumps(payload["law_summary"], ensure_ascii=False, indent=2),
        "```",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path, json_path


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="gvadicto_study_demo_") as tmp:
        temp_db = Path(tmp) / "study_demo.sqlite"
        conn = seed_temp_db(temp_db)
        service = StudyService(StudyRepository(conn))

        note_id = service.add_article_note(article_id=1, note_text="Nota demo", selected_text="seleccion")
        service.update_article_note(note_id=note_id, note_text="Nota demo actualizada")
        highlight_id = service.add_highlight(article_id=1, selected_text="texto clave", color="yellow")
        service.update_highlight(highlight_id=highlight_id, selected_text="texto clave actualizado", color="green")
        service.mark(StudyTarget(article_id=1), mark_type="important", note_text="Alta prioridad")
        service.mark(StudyTarget(article_id=2), mark_type="doubt", note_text="Revisar despues")
        service.set_progress(StudyTarget(article_id=1), status="reviewing", completion_percent=60, minutes_delta=25)
        service.set_progress(StudyTarget(article_id=2), status="reading", completion_percent=20, minutes_delta=10)
        service.record_review(StudyTarget(article_id=1), result="good", confidence=4, next_review_at="2026-06-25")

        payload = {
            "generated_at": now_iso(),
            "uses_temp_db": True,
            "temp_db_path": str(temp_db),
            "article_state": service.get_article_state(1),
            "topic_summary": service.get_topic_summary(1),
            "law_summary": service.get_law_summary(1),
        }
        conn.close()

        md_path, json_path = write_report(payload)

    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print("Demo used a temporary SQLite DB only; real db/gvadicto.sqlite was not opened.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

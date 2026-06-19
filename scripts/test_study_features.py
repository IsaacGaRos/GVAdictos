from __future__ import annotations

import hashlib
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.paths import DB_PATH
from src.study.repository import StudyRepository, StudySchemaMissingError
from src.study.schema import STUDY_TABLES, apply_study_schema, missing_study_tables
from src.study.service import StudyService, StudyTarget


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_base_schema(conn: sqlite3.Connection) -> None:
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

        INSERT INTO laws(id, name)
        VALUES (7, 'Ley test');

        INSERT INTO topics(id, topic_number, part, official_text)
        VALUES (10, 10, 'especial', 'Tema test');

        INSERT INTO articles(id, law_id, article_ref, title)
        VALUES
            (100, 7, '3', 'Articulo test'),
            (101, 7, '4', 'Articulo test 2');

        INSERT INTO topic_sources(id, topic_id, law_id, article_id, normative_reference)
        VALUES
            (1, 10, 7, 100, 'articulo 3'),
            (2, 10, 7, 101, 'articulo 4');
        """
    )


def make_conn(*, migrated: bool = True) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    create_base_schema(conn)
    if migrated:
        apply_study_schema(conn)
    return conn


def make_temp_db(path: Path, *, with_base: bool = True) -> None:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    if with_base:
        create_base_schema(conn)
    conn.commit()
    conn.close()


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )


def expect_error(fn, expected: str, error_type: type[Exception] = ValueError) -> None:
    try:
        fn()
    except error_type as exc:
        assert expected in str(exc), str(exc)
        return
    raise AssertionError(f"Expected {error_type.__name__} containing {expected!r}")


def test_schema() -> None:
    conn = make_conn()
    missing = missing_study_tables(conn)
    assert missing == [], missing
    for table in STUDY_TABLES:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert count == 0
    conn.close()
    print("ok schema")


def test_notes() -> None:
    conn = make_conn()
    service = StudyService(StudyRepository(conn))

    note_id = service.add_article_note(
        article_id=100,
        note_text="Nota inicial",
        selected_text="fragmento",
        anchor_key="art-3-p1",
        tags="test",
    )
    notes = service.repository.list_article_notes(100)
    assert len(notes) == 1
    assert notes[0]["id"] == note_id
    assert notes[0]["law_id_snapshot"] == 7
    assert notes[0]["article_ref_snapshot"] == "3"

    service.update_article_note(note_id=note_id, note_text="Nota actualizada")
    assert service.repository.list_article_notes(100)[0]["note_text"] == "Nota actualizada"

    service.delete_article_note(note_id)
    assert service.repository.list_article_notes(100) == []
    expect_error(lambda: service.add_article_note(article_id=999, note_text="x"), "article_id does not exist")
    conn.close()
    print("ok notes")


def test_highlights() -> None:
    conn = make_conn()
    service = StudyService(StudyRepository(conn))

    highlight_id = service.add_highlight(
        article_id=100,
        selected_text="texto subrayado",
        color="green",
        start_offset=1,
        end_offset=15,
    )
    service.update_highlight(
        highlight_id=highlight_id,
        selected_text="texto actualizado",
        color="blue",
        note_text="nota highlight",
    )
    highlights = service.repository.list_highlights(100)
    assert len(highlights) == 1
    assert highlights[0]["id"] == highlight_id
    assert highlights[0]["color"] == "blue"
    assert highlights[0]["selected_text"] == "texto actualizado"

    service.delete_highlight(highlight_id)
    assert service.repository.list_highlights(100) == []
    expect_error(
        lambda: service.add_highlight(article_id=100, selected_text="x", color="orange"),
        "Unsupported highlight color",
    )
    expect_error(
        lambda: service.add_highlight(article_id=100, selected_text="x", start_offset=9, end_offset=2),
        "start_offset",
    )
    expect_error(lambda: service.add_highlight(article_id=999, selected_text="x"), "article_id does not exist")
    conn.close()
    print("ok highlights")


def test_progress_marks_reviews_and_state() -> None:
    conn = make_conn()
    service = StudyService(StudyRepository(conn))

    progress_id = service.set_progress(
        StudyTarget(topic_id=10),
        status="reading",
        completion_percent=25,
        minutes_delta=25,
        pomodoro_delta=1,
    )
    same_progress_id = service.set_progress(
        StudyTarget(topic_id=10),
        status="completed",
        completion_percent=100,
        minutes_delta=10,
    )
    assert same_progress_id == progress_id
    progress = service.repository.get_progress(topic_id=10)
    assert progress is not None
    assert progress["status"] == "completed"
    assert progress["total_minutes"] == 35

    service.set_progress(StudyTarget(article_id=100), status="reviewing", completion_percent=60)
    service.mark(StudyTarget(article_id=100), mark_type="important", note_text="Muy preguntable")
    doubt_id = service.mark(StudyTarget(article_id=100), mark_type="doubt", note_text="Duda")
    same_doubt_id = service.mark(StudyTarget(article_id=100), mark_type="doubt", resolved=True)
    assert same_doubt_id == doubt_id

    review_id = service.record_review(
        StudyTarget(article_id=100),
        result="good",
        confidence=4,
        next_review_at="2026-06-25",
    )
    same_review_id = service.record_review(StudyTarget(article_id=100), result="easy", confidence=5)
    assert same_review_id == review_id

    state = service.get_article_state(100)
    assert state["progress"]["completion_percent"] == 60
    assert len(state["marks"]) == 2
    assert state["last_review"]["review_count"] == 2

    expect_error(lambda: service.set_progress(StudyTarget(topic_id=999), status="reading", completion_percent=10), "topic_id does not exist")
    expect_error(lambda: service.set_progress(StudyTarget(article_id=999), status="reading", completion_percent=10), "article_id does not exist")
    expect_error(lambda: service.set_progress(StudyTarget(), status="reading", completion_percent=10), "requires")
    expect_error(
        lambda: service.set_progress(StudyTarget(topic_id=10), status="bad", completion_percent=10),
        "Unsupported progress status",
    )
    expect_error(lambda: service.mark(StudyTarget(article_id=100), mark_type="flag"), "Unsupported mark_type")
    expect_error(
        lambda: service.record_review(StudyTarget(article_id=100), result="perfect"),
        "Unsupported review result",
    )
    conn.close()
    print("ok progress/marks/reviews/state")


def test_topic_and_law_summary() -> None:
    conn = make_conn()
    service = StudyService(StudyRepository(conn))
    service.add_article_note(article_id=100, note_text="Nota")
    service.add_highlight(article_id=100, selected_text="Texto")
    service.set_progress(StudyTarget(article_id=100), status="reading", completion_percent=50)
    service.set_progress(StudyTarget(article_id=101), status="completed", completion_percent=100)
    service.mark(StudyTarget(article_id=100), mark_type="important")
    service.mark(StudyTarget(article_id=101), mark_type="doubt")
    service.record_review(StudyTarget(article_id=100), result="hard")

    topic_summary = service.get_topic_summary(10)
    assert topic_summary["article_count"] == 2
    assert topic_summary["notes"] == 1
    assert topic_summary["highlights"] == 1
    assert topic_summary["important_marks"] == 1
    assert topic_summary["doubt_marks"] == 1
    assert topic_summary["progress_average"] == 75.0
    assert topic_summary["latest_review"] is not None

    law_summary = service.get_law_summary(7)
    assert law_summary["article_count"] == 2
    assert law_summary["progress_average"] == 75.0
    expect_error(lambda: service.get_law_summary(999), "law_id does not exist")
    conn.close()
    print("ok topic/law summary")


def test_unmigrated_database_behavior() -> None:
    conn = make_conn(migrated=False)
    service = StudyService(StudyRepository(conn))
    expect_error(
        lambda: service.add_article_note(article_id=100, note_text="Nota"),
        "not migrated",
        StudySchemaMissingError,
    )
    conn.close()
    print("ok unmigrated database")


def test_migration_dry_run_idempotent_and_read_only() -> None:
    with tempfile.TemporaryDirectory(prefix="gvadicto_study_features_") as tmp:
        db_path = Path(tmp) / "study.sqlite"
        make_temp_db(db_path, with_base=True)
        before = file_sha256(db_path)
        for _ in range(2):
            completed = run_command(
                ["scripts/migrate_study_features.py", "--dry-run", "--db-path", str(db_path)]
            )
            combined = completed.stdout + completed.stderr
            assert completed.returncode == 0, combined
            assert "Applied: False" in combined, combined
            assert file_sha256(db_path) == before

        broken_db = Path(tmp) / "broken.sqlite"
        make_temp_db(broken_db, with_base=False)
        completed = run_command(
            ["scripts/migrate_study_features.py", "--dry-run", "--db-path", str(broken_db)]
        )
        combined = completed.stdout + completed.stderr
        assert completed.returncode == 2, combined
        assert "missing required base tables" in combined, combined
    print("ok migration dry-run")


def test_counts() -> None:
    conn = make_conn()
    service = StudyService(StudyRepository(conn))
    service.add_article_note(article_id=100, note_text="Nota")
    service.add_highlight(article_id=100, selected_text="Texto")
    service.set_progress(StudyTarget(article_id=100), status="reading", completion_percent=50)
    service.mark(StudyTarget(article_id=100), mark_type="important")
    service.record_review(StudyTarget(article_id=100), result="hard")
    counts = service.repository.counts()
    assert counts == {
        "study_article_notes": 1,
        "study_highlights": 1,
        "study_progress": 1,
        "study_marks": 1,
        "study_last_reviews": 1,
    }, counts
    conn.close()
    print("ok counts")


def main() -> int:
    real_db_hash_before = file_sha256(DB_PATH)
    test_schema()
    test_notes()
    test_highlights()
    test_progress_marks_reviews_and_state()
    test_topic_and_law_summary()
    test_unmigrated_database_behavior()
    test_migration_dry_run_idempotent_and_read_only()
    test_counts()
    real_db_hash_after = file_sha256(DB_PATH)
    assert real_db_hash_before == real_db_hash_after, (
        real_db_hash_before,
        real_db_hash_after,
    )
    print("ok real DB hash unchanged")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

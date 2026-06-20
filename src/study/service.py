from __future__ import annotations

from dataclasses import dataclass

from src.study.repository import StudyRepository


import re as _re

NOTE_MAX_CHARS = 20_000
HIGHLIGHT_COLORS = {"yellow", "green", "blue", "pink", "purple", "red"}
PROGRESS_STATUSES = {"not_started", "reading", "reviewing", "completed", "paused"}
MARK_TYPES = {"doubt", "important", "bookmark"}
REVIEW_RESULTS = {"unknown", "again", "hard", "good", "easy"}
_HEX_COLOR_RE = _re.compile(r"^#[0-9A-Fa-f]{3}([0-9A-Fa-f]{3})?$")


@dataclass(frozen=True)
class StudyTarget:
    topic_id: int | None = None
    article_id: int | None = None

    def validate(self) -> None:
        if self.topic_id is None and self.article_id is None:
            raise ValueError("Study target requires topic_id or article_id.")


class StudyService:
    def __init__(self, repository: StudyRepository) -> None:
        self.repository = repository

    def add_article_note(
        self,
        *,
        article_id: int,
        note_text: str,
        selected_text: str | None = None,
        anchor_key: str | None = None,
        tags: str | None = None,
    ) -> int:
        self.repository.ensure_storage_ready()
        self._ensure_article_exists(article_id)
        self._validate_text(note_text, "note_text")
        return self.repository.create_article_note(
            article_id=article_id,
            note_text=note_text,
            selected_text=selected_text,
            anchor_key=anchor_key,
            tags=tags,
        )

    def update_article_note(
        self,
        *,
        note_id: int,
        note_text: str,
        selected_text: str | None = None,
        anchor_key: str | None = None,
        tags: str | None = None,
    ) -> None:
        self.repository.ensure_storage_ready()
        self._validate_text(note_text, "note_text")
        self.repository.update_article_note(
            note_id=note_id,
            note_text=note_text,
            selected_text=selected_text,
            anchor_key=anchor_key,
            tags=tags,
        )

    def delete_article_note(self, note_id: int) -> None:
        self.repository.archive_article_note(note_id)

    def add_highlight(
        self,
        *,
        article_id: int,
        selected_text: str,
        color: str = "yellow",
        anchor_key: str | None = None,
        start_offset: int | None = None,
        end_offset: int | None = None,
        note_text: str | None = None,
    ) -> int:
        self.repository.ensure_storage_ready()
        self._ensure_article_exists(article_id)
        self._validate_text(selected_text, "selected_text")
        self._validate_highlight_bounds(color, start_offset, end_offset)
        return self.repository.create_highlight(
            article_id=article_id,
            selected_text=selected_text,
            color=color,
            anchor_key=anchor_key,
            start_offset=start_offset,
            end_offset=end_offset,
            note_text=note_text,
        )

    def update_highlight(
        self,
        *,
        highlight_id: int,
        selected_text: str,
        color: str = "yellow",
        anchor_key: str | None = None,
        start_offset: int | None = None,
        end_offset: int | None = None,
        note_text: str | None = None,
    ) -> None:
        self.repository.ensure_storage_ready()
        self._validate_text(selected_text, "selected_text")
        self._validate_highlight_bounds(color, start_offset, end_offset)
        self.repository.update_highlight(
            highlight_id=highlight_id,
            selected_text=selected_text,
            color=color,
            anchor_key=anchor_key,
            start_offset=start_offset,
            end_offset=end_offset,
            note_text=note_text,
        )

    def delete_highlight(self, highlight_id: int) -> None:
        self.repository.archive_highlight(highlight_id)

    def set_progress(
        self,
        target: StudyTarget,
        *,
        status: str,
        completion_percent: int,
        minutes_delta: int = 0,
        pomodoro_delta: int = 0,
    ) -> int:
        self.repository.ensure_storage_ready()
        target.validate()
        self._validate_target_entities(target)
        if status not in PROGRESS_STATUSES:
            raise ValueError(f"Unsupported progress status: {status}")
        if not 0 <= completion_percent <= 100:
            raise ValueError("completion_percent must be between 0 and 100.")
        if minutes_delta < 0 or pomodoro_delta < 0:
            raise ValueError("minutes_delta and pomodoro_delta cannot be negative.")
        return self.repository.upsert_progress(
            topic_id=target.topic_id,
            article_id=target.article_id,
            status=status,
            completion_percent=completion_percent,
            minutes_delta=minutes_delta,
            pomodoro_delta=pomodoro_delta,
        )

    def mark(
        self,
        target: StudyTarget,
        *,
        mark_type: str,
        note_text: str | None = None,
        resolved: bool = False,
    ) -> int:
        self.repository.ensure_storage_ready()
        target.validate()
        self._validate_target_entities(target)
        if mark_type not in MARK_TYPES:
            raise ValueError(f"Unsupported mark_type: {mark_type}")
        return self.repository.upsert_mark(
            topic_id=target.topic_id,
            article_id=target.article_id,
            mark_type=mark_type,
            note_text=note_text,
            resolved=resolved,
        )

    def record_review(
        self,
        target: StudyTarget,
        *,
        result: str,
        confidence: int | None = None,
        next_review_at: str | None = None,
        notes: str | None = None,
    ) -> int:
        self.repository.ensure_storage_ready()
        target.validate()
        self._validate_target_entities(target)
        if result not in REVIEW_RESULTS:
            raise ValueError(f"Unsupported review result: {result}")
        if confidence is not None and not 0 <= confidence <= 5:
            raise ValueError("confidence must be between 0 and 5.")
        return self.repository.record_last_review(
            topic_id=target.topic_id,
            article_id=target.article_id,
            result=result,
            confidence=confidence,
            next_review_at=next_review_at,
            notes=notes,
        )

    def get_article_state(self, article_id: int) -> dict:
        self.repository.ensure_storage_ready()
        self._ensure_article_exists(article_id)
        return self.repository.get_article_study_state(article_id)

    def get_topic_summary(self, topic_id: int) -> dict:
        self.repository.ensure_storage_ready()
        self._ensure_topic_exists(topic_id)
        return self.repository.get_topic_summary(topic_id)

    def get_law_summary(self, law_id: int) -> dict:
        self.repository.ensure_storage_ready()
        if not self.repository._article_ids_for_law(law_id):
            raise ValueError(f"law_id does not exist or has no articles: {law_id}")
        return self.repository.get_law_summary(law_id)

    def _validate_text(self, value: str, field_name: str) -> None:
        if not value or not value.strip():
            raise ValueError(f"{field_name} cannot be empty.")
        if len(value) > NOTE_MAX_CHARS:
            raise ValueError(f"{field_name} cannot exceed {NOTE_MAX_CHARS} chars.")

    def _validate_highlight_bounds(
        self,
        color: str,
        start_offset: int | None,
        end_offset: int | None,
    ) -> None:
        if color not in HIGHLIGHT_COLORS and not _HEX_COLOR_RE.match(color or ""):
            raise ValueError(f"Unsupported highlight color: {color}")
        if start_offset is not None and end_offset is not None and start_offset > end_offset:
            raise ValueError("start_offset cannot be greater than end_offset.")

    def _validate_target_entities(self, target: StudyTarget) -> None:
        if target.topic_id is not None:
            self._ensure_topic_exists(target.topic_id)
        if target.article_id is not None:
            self._ensure_article_exists(target.article_id)

    def _ensure_article_exists(self, article_id: int) -> None:
        if self.repository.get_article_snapshot(article_id) is None:
            raise ValueError(f"article_id does not exist: {article_id}")

    def _ensure_topic_exists(self, topic_id: int) -> None:
        if self.repository.get_topic_snapshot(topic_id) is None:
            raise ValueError(f"topic_id does not exist: {topic_id}")

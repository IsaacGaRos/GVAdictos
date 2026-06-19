from __future__ import annotations

import sqlite3
from typing import Any

from src.audio.schema import missing_audio_tables

RowDict = dict[str, Any]


class AudioStorageError(RuntimeError):
    """Base error for audio storage issues."""


class AudioSchemaMissingError(AudioStorageError):
    """Raised when audio feature tables have not been migrated yet."""


class AudioRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.conn.row_factory = sqlite3.Row

    def ensure_storage_ready(self) -> None:
        missing = missing_audio_tables(self.conn)
        if missing:
            raise AudioSchemaMissingError(
                "Audio feature tables are not migrated: " + ", ".join(missing)
            )

    def create_tts_audio(
        self,
        *,
        scope_type: str,
        scope_id: int,
        content_hash: str,
        voice: str | None = None,
        speed: float = 1.0,
        format: str = "mp3",
        storage_url: str | None = None,
        storage_path: str | None = None,
        duration_seconds: float | None = None,
    ) -> int:
        """Create a new TTS audio record."""
        self.ensure_storage_ready()
        cursor = self.conn.execute(
            """
            INSERT INTO tts_audio(
                scope_type, scope_id, voice, speed, format, content_hash,
                storage_url, storage_path, duration_seconds
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scope_type,
                scope_id,
                voice,
                speed,
                format,
                content_hash,
                storage_url,
                storage_path,
                duration_seconds,
            ),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def get_tts_audio(
        self,
        scope_type: str,
        scope_id: int,
        voice: str | None = None,
        speed: float = 1.0,
        format: str = "mp3",
    ) -> RowDict | None:
        """Get cached TTS audio for a scope."""
        row = self.conn.execute(
            """
            SELECT * FROM tts_audio
            WHERE scope_type = ? AND scope_id = ? AND voice = ? AND speed = ? AND format = ?
            """,
            (scope_type, scope_id, voice, speed, format),
        ).fetchone()
        return dict(row) if row else None

    def get_tts_audio_by_hash(self, content_hash: str) -> RowDict | None:
        """Get TTS audio by content hash."""
        row = self.conn.execute(
            "SELECT * FROM tts_audio WHERE content_hash = ? LIMIT 1",
            (content_hash,),
        ).fetchone()
        return dict(row) if row else None

    def update_tts_storage(
        self,
        audio_id: int,
        storage_url: str | None = None,
        storage_path: str | None = None,
        duration_seconds: float | None = None,
    ) -> None:
        """Update storage location of TTS audio."""
        self.conn.execute(
            """
            UPDATE tts_audio
            SET storage_url = ?, storage_path = ?, duration_seconds = ?
            WHERE id = ?
            """,
            (storage_url, storage_path, duration_seconds, audio_id),
        )
        self.conn.commit()

    def delete_tts_audio(self, audio_id: int) -> None:
        """Delete a TTS audio record."""
        self.conn.execute("DELETE FROM tts_audio WHERE id = ?", (audio_id,))
        self.conn.commit()

"""TTS (Text-to-Speech) service for article content.

MVP: Uses browser Web Speech API (free, client-side)
Future: Cloud TTS with caching (Google, Azure, ElevenLabs)
"""

from __future__ import annotations

import hashlib
import sqlite3
from typing import Any

from src.audio.repository import AudioRepository


class TTSServiceError(RuntimeError):
    """Base error for TTS service issues."""


class TTSService:
    """TTS service for generating audio from legal text."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.repo = AudioRepository(conn)
        self.provider = "browser"  # MVP: browser Web Speech
        self.voice = None  # Let browser choose
        self.speed = 1.0

    def _hash_content(self, text: str) -> str:
        """Create hash of content for caching."""
        return hashlib.sha256(text.encode()).hexdigest()

    def get_or_create_audio(
        self,
        scope_type: str,
        scope_id: int,
        text: str,
        voice: str | None = None,
        speed: float = 1.0,
    ) -> dict[str, Any]:
        """Get cached audio or prepare generation metadata.

        Returns dict with audio_id, scope_type, scope_id, and generation instructions.
        For MVP, returns metadata for browser TTS generation.
        """
        content_hash = self._hash_content(text)

        # Check if already cached
        existing = self.repo.get_tts_audio(
            scope_type,
            scope_id,
            voice=voice or self.voice,
            speed=speed,
        )
        if existing and existing["storage_url"]:
            return {
                "audio_id": existing["id"],
                "cached": True,
                "storage_url": existing["storage_url"],
                "duration_seconds": existing["duration_seconds"],
            }

        # Create new record
        audio_id = self.repo.create_tts_audio(
            scope_type=scope_type,
            scope_id=scope_id,
            content_hash=content_hash,
            voice=voice or self.voice,
            speed=speed,
            format="mp3",
        )

        return {
            "audio_id": audio_id,
            "cached": False,
            "scope_type": scope_type,
            "scope_id": scope_id,
            "text": text,
            "voice": voice or self.voice,
            "speed": speed,
            "provider": self.provider,
        }

    def get_audio_metadata(self, audio_id: int) -> dict[str, Any] | None:
        """Get TTS audio metadata."""
        row = self.conn.execute(
            "SELECT * FROM tts_audio WHERE id = ?",
            (audio_id,),
        ).fetchone()
        return dict(row) if row else None

    def set_storage_url(
        self,
        audio_id: int,
        storage_url: str,
        duration_seconds: float | None = None,
    ) -> None:
        """Update storage location for generated audio."""
        self.repo.update_tts_storage(
            audio_id,
            storage_url=storage_url,
            duration_seconds=duration_seconds,
        )

    def estimate_duration(self, text: str, speed: float = 1.0) -> float:
        """Estimate audio duration in seconds.

        Heuristic: ~150 words per minute, accounting for legal language pace.
        Adjusts for speed: 1.0 = normal, 0.5 = half speed (2x time), 2.0 = double (half time)
        """
        words = len(text.split())
        base_wpm = 130  # Slower for legal content
        minutes = words / base_wpm
        seconds = minutes * 60
        # Adjust for speed
        if speed > 0:
            seconds = seconds / speed
        return max(1.0, seconds)  # Minimum 1 second

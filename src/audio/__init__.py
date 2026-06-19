"""Audio/TTS module for generating speech from legal text.

MVP: Browser Web Speech API (free, client-side)
Future: Cloud TTS with caching

This module provides:
- TTSService: Main service for TTS generation and caching
- AudioRepository: Data access layer
"""

from src.audio.service import TTSService, TTSServiceError
from src.audio.repository import AudioRepository, AudioStorageError, AudioSchemaMissingError
from src.audio.schema import ensure_audio_tables, missing_audio_tables

__all__ = [
    "TTSService",
    "TTSServiceError",
    "AudioRepository",
    "AudioStorageError",
    "AudioSchemaMissingError",
    "ensure_audio_tables",
    "missing_audio_tables",
]

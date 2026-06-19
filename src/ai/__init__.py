"""AI service module for generating legal insights using Claude API.

This module provides:
- AIService: Main service for generating article insights (explanations, summaries, mnemonics, etc.)
- AIRepository: Data access layer for caching and storing AI-generated content
- Prompts: Versioned prompt templates for consistent, reproducible outputs
"""

from src.ai.service import AIService, AIServiceError, AIConfigError
from src.ai.repository import AIRepository, AIStorageError, AISchemaMissingError
from src.ai.schema import ensure_ai_tables, missing_ai_tables

__all__ = [
    "AIService",
    "AIServiceError",
    "AIConfigError",
    "AIRepository",
    "AIStorageError",
    "AISchemaMissingError",
    "ensure_ai_tables",
    "missing_ai_tables",
]

"""Servicio de IA para generación de insights jurídicos.

Gestiona adaptación a Claude API, caché y trazabilidad de prompts.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any
import os

from anthropic import Anthropic

from src.ai.repository import AIRepository
from src.ai import prompts


class AIServiceError(RuntimeError):
    """Base error for AI service issues."""


class AIConfigError(AIServiceError):
    """Raised when API key or configuration is missing."""


class AIService:
    """Servicio de IA para generación de insights sobre artículos."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.repo = AIRepository(conn)
        self.client = self._init_client()
        self.model = "claude-opus-4-8"  # Default model, can be overridden
        self.prompt_version = prompts.PROMPT_VERSION

    def _init_client(self) -> Anthropic:
        """Initialize Anthropic client with API key from environment."""
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise AIConfigError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Set it before using AI features."
            )
        return Anthropic(api_key=api_key)

    def _hash_input(self, text: str) -> str:
        """Create a hash of input text for caching."""
        return hashlib.sha256(text.encode()).hexdigest()

    def _generate_with_claude(
        self,
        prompt: str,
        max_tokens: int = 1000,
    ) -> str:
        """Call Claude API and return the response text."""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )
        return message.content[0].text

    def explain_article(
        self,
        article_id: int,
        article_title: str,
        article_text: str,
        use_cache: bool = True,
    ) -> str:
        """Generate a simple explanation of an article."""
        input_hash = self._hash_input(f"explain:{article_text}")

        if use_cache:
            cached = self.repo.get_article_insight(
                article_id,
                "explicacion",
                input_hash,
            )
            if cached:
                return cached["content"]

        prompt = prompts.get_article_explanation_prompt(article_title, article_text)
        response = self._generate_with_claude(prompt)

        self.repo.create_article_insight(
            article_id=article_id,
            insight_type="explicacion",
            content=response,
            model=self.model,
            prompt_version=self.prompt_version,
            input_hash=input_hash,
        )

        return response

    def summarize_article(
        self,
        article_id: int,
        article_title: str,
        article_text: str,
        use_cache: bool = True,
    ) -> str:
        """Generate a structured summary of an article."""
        input_hash = self._hash_input(f"summary:{article_text}")

        if use_cache:
            cached = self.repo.get_article_insight(
                article_id,
                "resumen",
                input_hash,
            )
            if cached:
                return cached["content"]

        prompt = prompts.get_article_summary_prompt(article_title, article_text)
        response = self._generate_with_claude(prompt)

        self.repo.create_article_insight(
            article_id=article_id,
            insight_type="resumen",
            content=response,
            model=self.model,
            prompt_version=self.prompt_version,
            input_hash=input_hash,
        )

        return response

    def create_mnemonic(
        self,
        article_id: int,
        article_title: str,
        article_text: str,
        use_cache: bool = True,
    ) -> str:
        """Generate mnemonic techniques for remembering an article."""
        input_hash = self._hash_input(f"mnemonic:{article_text}")

        if use_cache:
            cached = self.repo.get_article_insight(
                article_id,
                "mnemotecnia",
                input_hash,
            )
            if cached:
                return cached["content"]

        prompt = prompts.get_article_mnemonic_prompt(article_title, article_text)
        response = self._generate_with_claude(prompt)

        self.repo.create_article_insight(
            article_id=article_id,
            insight_type="mnemotecnia",
            content=response,
            model=self.model,
            prompt_version=self.prompt_version,
            input_hash=input_hash,
        )

        return response

    def compare_articles(
        self,
        article_id: int,
        article_title: str,
        article_text: str,
        related_articles: list[tuple[str, str]],
        use_cache: bool = True,
    ) -> str:
        """Generate a comparison between an article and related ones."""
        related_titles = [t for t, _ in related_articles]
        input_hash = self._hash_input(
            f"compare:{article_text}:{json.dumps(related_titles)}"
        )

        if use_cache:
            cached = self.repo.get_article_insight(
                article_id,
                "comparacion",
                input_hash,
            )
            if cached:
                return cached["content"]

        prompt = prompts.get_article_comparison_prompt(
            article_title,
            article_text,
            related_articles,
        )
        response = self._generate_with_claude(prompt)

        self.repo.create_article_insight(
            article_id=article_id,
            insight_type="comparacion",
            content=response,
            model=self.model,
            prompt_version=self.prompt_version,
            input_hash=input_hash,
        )

        return response

    def identify_common_mistakes(
        self,
        article_id: int,
        article_title: str,
        article_text: str,
        use_cache: bool = True,
    ) -> str:
        """Identify common mistakes about an article."""
        input_hash = self._hash_input(f"mistakes:{article_text}")

        if use_cache:
            cached = self.repo.get_article_insight(
                article_id,
                "errores_comunes",
                input_hash,
            )
            if cached:
                return cached["content"]

        prompt = prompts.get_common_mistakes_prompt(article_title, article_text)
        response = self._generate_with_claude(prompt)

        self.repo.create_article_insight(
            article_id=article_id,
            insight_type="errores_comunes",
            content=response,
            model=self.model,
            prompt_version=self.prompt_version,
            input_hash=input_hash,
        )

        return response

    def predict_exam_questions(
        self,
        article_id: int,
        article_title: str,
        article_text: str,
        use_cache: bool = True,
    ) -> str:
        """Predict what aspects of an article are likely to be tested."""
        input_hash = self._hash_input(f"questions:{article_text}")

        if use_cache:
            cached = self.repo.get_article_insight(
                article_id,
                "que_se_pregunta",
                input_hash,
            )
            if cached:
                return cached["content"]

        prompt = prompts.get_what_is_asked_prompt(article_title, article_text)
        response = self._generate_with_claude(prompt)

        self.repo.create_article_insight(
            article_id=article_id,
            insight_type="que_se_pregunta",
            content=response,
            model=self.model,
            prompt_version=self.prompt_version,
            input_hash=input_hash,
        )

        return response

    def get_all_insights(
        self,
        article_id: int,
        insight_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve all insights for an article."""
        return self.repo.get_article_insights(article_id, insight_type)

    def mark_for_review(
        self,
        insight_id: int,
        requiere_revision: bool = True,
    ) -> None:
        """Mark an insight as requiring human review."""
        self.repo.update_insight_validation(
            insight_id,
            "pendiente_de_validacion",
            requiere_revision=requiere_revision,
        )

    def validate_insight(
        self,
        insight_id: int,
        is_valid: bool = True,
    ) -> None:
        """Validate or reject an insight after human review."""
        status = "validado" if is_valid else "rechazado"
        self.repo.update_insight_validation(
            insight_id,
            status,
            requiere_revision=False,
        )

    def set_model(self, model: str) -> None:
        """Override the default Claude model."""
        self.model = model

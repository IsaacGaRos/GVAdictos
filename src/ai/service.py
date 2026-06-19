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

    def generate_question(
        self,
        article_id: int,
        article_title: str,
        article_text: str,
        estilo: str = "normal",
        topic_id: int | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Generate a test question about an article.

        Returns dict with keys: question_id, pregunta, respuesta_correcta, opciones, explicacion
        """
        input_hash = self._hash_input(f"question:{estilo}:{article_text}")

        prompt = prompts.get_question_generation_prompt(
            article_title,
            article_text,
            estilo,
        )
        response = self._generate_with_claude(prompt, max_tokens=1500)

        # Parse response
        question_data = self._parse_question_response(response)
        if not question_data:
            raise AIServiceError("Failed to parse question response from Claude")

        # Store in database
        question_id = self.repo.create_ai_question(
            article_id=article_id,
            topic_id=topic_id,
            estilo=estilo,
            enunciado=question_data["pregunta"],
            respuesta_correcta=question_data["respuesta_correcta"],
            explicacion_razonada=question_data.get("explicacion"),
            options=question_data.get("opciones", []),
            model=self.model,
            prompt_version=self.prompt_version,
            input_hash=input_hash,
        )

        return {
            "question_id": question_id,
            "pregunta": question_data["pregunta"],
            "respuesta_correcta": question_data["respuesta_correcta"],
            "opciones": question_data.get("opciones", []),
            "explicacion": question_data.get("explicacion"),
        }

    def _parse_question_response(self, response: str) -> dict[str, Any] | None:
        """Parse question response from Claude."""
        lines = response.strip().split("\n")
        data = {}
        current_section = None
        opciones_raw = []

        for line in lines:
            line = line.strip()
            if line.startswith("PREGUNTA:"):
                data["pregunta"] = line.replace("PREGUNTA:", "").strip()
                current_section = None
            elif line.startswith("OPCIONES:"):
                current_section = "opciones"
            elif line.startswith("RESPUESTA CORRECTA:"):
                data["respuesta_correcta"] = line.replace("RESPUESTA CORRECTA:", "").strip()
                current_section = None
            elif line.startswith("EXPLICACIÓN:"):
                data["explicacion"] = line.replace("EXPLICACIÓN:", "").strip()
                current_section = None
            elif current_section == "opciones" and len(line) > 0:
                if line[0] in "ABCD" and len(line) > 2 and line[1] == ")":
                    opciones_raw.append(line[3:].strip())

        # Format options as tuples (letra, texto)
        if opciones_raw:
            data["opciones"] = list(zip("ABCD", opciones_raw[: 4]))

        # Validate required fields
        required = {"pregunta", "respuesta_correcta"}
        if not required.issubset(set(data.keys())):
            return None

        return data

    def get_question(self, question_id: int) -> dict[str, Any] | None:
        """Retrieve an AI question."""
        return self.repo.get_ai_question(question_id)

    def mark_question_for_review(self, question_id: int) -> None:
        """Mark a question as requiring human review."""
        self.repo.update_ai_question_validation(
            question_id,
            "pendiente_de_validacion",
            requiere_revision=True,
        )

    def validate_question(self, question_id: int, is_valid: bool = True) -> None:
        """Validate or reject a question."""
        status = "validado" if is_valid else "rechazado"
        self.repo.update_ai_question_validation(
            question_id,
            status,
            requiere_revision=False,
        )

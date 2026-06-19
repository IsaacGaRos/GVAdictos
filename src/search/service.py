"""Search service for semantic search and article relations.

MVP: Uses explicit relations between articles (no vector DB)
Future: Full semantic search with embeddings + vector DB (pgvector/sqlite-vec)
"""

from __future__ import annotations

import hashlib
import sqlite3
from typing import Any

from anthropic import Anthropic

from src.search.repository import SearchRepository


class SearchServiceError(RuntimeError):
    """Base error for search service issues."""


class SearchService:
    """Service for semantic search and article relation mapping."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.repo = SearchRepository(conn)
        self.client = None
        self.embedding_model = "text-embedding-3-small"  # MVP: no embeddings, just relations

    def find_related_articles(
        self,
        article_id: int,
        relation_type: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Find articles related to a given one.

        Returns list of related articles with their metadata.
        """
        relations = self.repo.get_relations_from(article_id, relation_type)
        result = []

        for rel in relations[:limit]:
            article_row = self.conn.execute(
                "SELECT id, article_ref, title, law_id FROM articles WHERE id = ?",
                (rel["to_article_id"],),
            ).fetchone()

            if article_row:
                law_row = self.conn.execute(
                    "SELECT name FROM laws WHERE id = ?",
                    (article_row["law_id"],),
                ).fetchone()

                result.append(
                    {
                        "article_id": article_row["id"],
                        "article_ref": article_row["article_ref"],
                        "title": article_row["title"],
                        "law_name": law_row["name"] if law_row else None,
                        "relation_type": rel["relation_type"],
                        "weight": rel["weight"],
                        "source": rel["source"],
                    }
                )

        return result

    def find_citing_articles(
        self,
        article_id: int,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Find articles that cite a given one."""
        relations = self.repo.get_relations_to(article_id, "cita")
        result = []

        for rel in relations[:limit]:
            article_row = self.conn.execute(
                "SELECT id, article_ref, title, law_id FROM articles WHERE id = ?",
                (rel["from_article_id"],),
            ).fetchone()

            if article_row:
                law_row = self.conn.execute(
                    "SELECT name FROM laws WHERE id = ?",
                    (article_row["law_id"],),
                ).fetchone()

                result.append(
                    {
                        "article_id": article_row["id"],
                        "article_ref": article_row["article_ref"],
                        "title": article_row["title"],
                        "law_name": law_row["name"] if law_row else None,
                    }
                )

        return result

    def create_relation(
        self,
        from_article_id: int,
        to_article_id: int,
        relation_type: str,
        source: str,
        weight: float = 0.5,
    ) -> int:
        """Create or update a relation between two articles.

        Relation types: cita, desarrolla, concordancia, similar_semantica
        """
        valid_types = {"cita", "desarrolla", "concordancia", "similar_semantica"}
        if relation_type not in valid_types:
            raise SearchServiceError(f"Invalid relation type: {relation_type}")

        return self.repo.create_relation(
            from_article_id=from_article_id,
            to_article_id=to_article_id,
            relation_type=relation_type,
            source=source,
            weight=weight,
        )

    def delete_relation(
        self,
        from_article_id: int,
        to_article_id: int,
        relation_type: str,
        source: str,
    ) -> None:
        """Delete a relation between articles."""
        self.repo.delete_relation(
            from_article_id,
            to_article_id,
            relation_type,
            source,
        )

    def get_relation_map(self, article_id: int) -> dict[str, Any]:
        """Get full relation map for an article (incoming and outgoing)."""
        outgoing = self.repo.get_relations_from(article_id)
        incoming = self.repo.get_relations_to(article_id)

        return {
            "article_id": article_id,
            "outgoing_relations": [dict(r) for r in outgoing],
            "incoming_relations": [dict(r) for r in incoming],
            "total_outgoing": len(outgoing),
            "total_incoming": len(incoming),
        }

    def search_similar_articles(
        self,
        article_id: int,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search for semantically similar articles.

        MVP: Returns articles with explicit 'similar_semantica' relations.
        Future: Will use vector similarity search.
        """
        return self.find_related_articles(
            article_id,
            relation_type="similar_semantica",
            limit=limit,
        )

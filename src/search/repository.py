from __future__ import annotations

import sqlite3
import struct
from typing import Any

from src.search.schema import missing_search_tables

RowDict = dict[str, Any]


class SearchStorageError(RuntimeError):
    """Base error for search storage issues."""


class SearchSchemaMissingError(SearchStorageError):
    """Raised when search feature tables have not been migrated yet."""


class SearchRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def ensure_storage_ready(self) -> None:
        missing = missing_search_tables(self.conn)
        if missing:
            raise SearchSchemaMissingError(
                "Search feature tables are not migrated: " + ", ".join(missing)
            )

    def save_embedding(
        self,
        *,
        article_id: int,
        model: str,
        embedding_vector: list[float],
        input_hash: str,
    ) -> int:
        """Save embedding vector for an article."""
        self.ensure_storage_ready()
        # Store vector as bytes (8-byte doubles)
        vector_bytes = struct.pack(f"{len(embedding_vector)}d", *embedding_vector)
        cursor = self.conn.execute(
            """
            INSERT OR REPLACE INTO article_embeddings(
                article_id, model, dimension, embedding_vector, input_hash
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                article_id,
                model,
                len(embedding_vector),
                vector_bytes,
                input_hash,
            ),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def get_embedding(self, article_id: int) -> tuple[list[float], str] | None:
        """Get embedding vector for an article."""
        row = self.conn.execute(
            "SELECT embedding_vector, dimension FROM article_embeddings WHERE article_id = ?",
            (article_id,),
        ).fetchone()
        if not row:
            return None
        dimension = row["dimension"]
        vector_bytes = row["embedding_vector"]
        vector = list(struct.unpack(f"{dimension}d", vector_bytes))
        return vector, row["dimension"]

    def create_relation(
        self,
        *,
        from_article_id: int,
        to_article_id: int,
        relation_type: str,
        source: str,
        weight: float = 0.5,
    ) -> int:
        """Create a relation between two articles."""
        self.ensure_storage_ready()
        cursor = self.conn.execute(
            """
            INSERT INTO article_relations(
                from_article_id, to_article_id, relation_type, weight, source
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (from_article_id, to_article_id, relation_type, weight, source),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def get_relations_from(
        self,
        from_article_id: int,
        relation_type: str | None = None,
    ) -> list[RowDict]:
        """Get all relations from an article."""
        if relation_type:
            rows = self.conn.execute(
                """
                SELECT * FROM article_relations
                WHERE from_article_id = ? AND relation_type = ?
                ORDER BY weight DESC
                """,
                (from_article_id, relation_type),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """
                SELECT * FROM article_relations
                WHERE from_article_id = ?
                ORDER BY weight DESC
                """,
                (from_article_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_relations_to(
        self,
        to_article_id: int,
        relation_type: str | None = None,
    ) -> list[RowDict]:
        """Get all relations pointing to an article."""
        if relation_type:
            rows = self.conn.execute(
                """
                SELECT * FROM article_relations
                WHERE to_article_id = ? AND relation_type = ?
                ORDER BY weight DESC
                """,
                (to_article_id, relation_type),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """
                SELECT * FROM article_relations
                WHERE to_article_id = ?
                ORDER BY weight DESC
                """,
                (to_article_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_relation(
        self,
        from_article_id: int,
        to_article_id: int,
        relation_type: str,
        source: str,
    ) -> None:
        """Delete a specific relation."""
        self.conn.execute(
            """
            DELETE FROM article_relations
            WHERE from_article_id = ? AND to_article_id = ? AND relation_type = ? AND source = ?
            """,
            (from_article_id, to_article_id, relation_type, source),
        )
        self.conn.commit()

    def compute_similarity(self, v1: list[float], v2: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(v1) != len(v2):
            return 0.0
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm_v1 = sum(a * a for a in v1) ** 0.5
        norm_v2 = sum(b * b for b in v2) ** 0.5
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
        return dot_product / (norm_v1 * norm_v2)

    def find_similar_articles(
        self,
        article_id: int,
        limit: int = 5,
        min_similarity: float = 0.5,
    ) -> list[RowDict]:
        """Find articles similar to a given one using embeddings."""
        # This is a simple implementation without vector DB
        # Real implementation would use pgvector or sqlite-vec
        # For MVP, return related articles by explicit relations
        relations = self.get_relations_from(article_id, "similar_semantica")
        return relations[:limit]

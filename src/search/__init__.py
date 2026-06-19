"""Search module for semantic search and article relations.

MVP: Explicit relations between articles (no vector DB)
Future: Full semantic embeddings + vector DB (pgvector/sqlite-vec)

This module provides:
- SearchService: Search and relation mapping
- SearchRepository: Data access layer
"""

from src.search.service import SearchService, SearchServiceError
from src.search.repository import SearchRepository, SearchStorageError, SearchSchemaMissingError
from src.search.schema import ensure_search_tables, missing_search_tables

__all__ = [
    "SearchService",
    "SearchServiceError",
    "SearchRepository",
    "SearchStorageError",
    "SearchSchemaMissingError",
    "ensure_search_tables",
    "missing_search_tables",
]

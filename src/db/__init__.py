"""Database abstraction layer."""

from src.db.postgres_migration import MIGRATION_STRATEGY

__all__ = ["MIGRATION_STRATEGY"]

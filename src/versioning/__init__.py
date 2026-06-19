"""Versioning module for tracking legislative changes and annotation remapping.

Provides version snapshots, diff generation, and annotation preservation across updates.
"""

from src.versioning.service import VersioningService, VersioningServiceError
from src.versioning.repository import VersioningRepository, VersioningError, VersioningSchemaMissingError
from src.versioning.schema import ensure_versioning_tables, missing_versioning_tables

__all__ = [
    "VersioningService",
    "VersioningServiceError",
    "VersioningRepository",
    "VersioningError",
    "VersioningSchemaMissingError",
    "ensure_versioning_tables",
    "missing_versioning_tables",
]

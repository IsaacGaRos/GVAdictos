"""Legislation versioning service for tracking changes and annotation remapping.

Handles law versions, diffs, and remapping highlights between versions.
"""

from __future__ import annotations

import sqlite3
from typing import Any
from difflib import unified_diff

from src.versioning.repository import VersioningRepository


class VersioningServiceError(RuntimeError):
    """Base error for versioning service issues."""


class VersioningService:
    """Service for managing legislative versions and comparing changes."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.repo = VersioningRepository(conn)

    def create_version_snapshot(
        self,
        law_id: int,
        version_label: str,
        source_document_id: int | None = None,
    ) -> int:
        """Create a snapshot of a law's current state."""
        # Get all articles for this law from the DB
        articles = self.conn.execute(
            """
            SELECT id, article_ref, text FROM articles
            WHERE law_id = ?
            ORDER BY article_ref
            """,
            (law_id,),
        ).fetchall()

        if not articles:
            raise VersioningServiceError(f"No articles found for law {law_id}")

        # Create version record
        # For MVP, use simple content hash
        version_text = "\n---\n".join([a["text"] for a in articles])
        import hashlib
        content_hash = hashlib.sha256(version_text.encode()).hexdigest()

        version_id = self.repo.create_law_version(
            law_id=law_id,
            version_label=version_label,
            content_hash=content_hash,
            source_document_id=source_document_id,
        )

        # Record each article in this version
        for article in articles:
            # Generate anchor_key from article_ref
            anchor_key = f"law_{law_id}_art_{article['article_ref']}"
            self.repo.create_article_version(
                law_version_id=version_id,
                article_ref=article["article_ref"],
                anchor_key=anchor_key,
                text=article["text"],
            )

        return version_id

    def compare_versions(
        self,
        version_id_old: int,
        version_id_new: int,
    ) -> dict[str, Any]:
        """Compare two law versions and generate diff report."""
        changes = self.repo.find_text_changes(version_id_old, version_id_new)

        added = [c for c in changes if c["change_type"] == "added"]
        removed = [c for c in changes if c["change_type"] == "removed"]
        modified = [c for c in changes if c["change_type"] == "modified"]

        return {
            "version_old": version_id_old,
            "version_new": version_id_new,
            "total_changes": len(changes),
            "added_count": len(added),
            "removed_count": len(removed),
            "modified_count": len(modified),
            "changes": changes,
        }

    def generate_article_diff(
        self,
        version_id_old: int,
        version_id_new: int,
        anchor_key: str,
    ) -> str:
        """Generate unified diff for a specific article between versions."""
        old_row = self.conn.execute(
            """
            SELECT text FROM article_versions
            WHERE law_version_id = ? AND anchor_key = ?
            """,
            (version_id_old, anchor_key),
        ).fetchone()

        new_row = self.conn.execute(
            """
            SELECT text FROM article_versions
            WHERE law_version_id = ? AND anchor_key = ?
            """,
            (version_id_new, anchor_key),
        ).fetchone()

        if not old_row or not new_row:
            return ""

        old_lines = old_row["text"].split("\n")
        new_lines = new_row["text"].split("\n")

        diff_lines = unified_diff(
            old_lines,
            new_lines,
            fromfile=f"Old ({anchor_key})",
            tofile=f"New ({anchor_key})",
            lineterm="",
        )

        return "\n".join(diff_lines)

    def remap_annotations(
        self,
        from_version_id: int,
        to_version_id: int,
    ) -> dict[str, Any]:
        """Remap annotations from old version to new version.

        Returns summary of remapping with any issues encountered.
        """
        # Find articles that changed
        changes = self.repo.find_text_changes(from_version_id, to_version_id)

        remapped = 0
        failed = 0
        warnings = []

        for change in changes:
            anchor_key = change["anchor_key"]

            if change["change_type"] == "removed":
                warnings.append(
                    f"Article {anchor_key} was removed. Annotations lost."
                )
                failed += 1
            elif change["change_type"] == "added":
                # New articles have no annotations to remap
                pass
            elif change["change_type"] == "modified":
                # Try to remap annotations
                # Get old and new article version IDs
                old_av = self.conn.execute(
                    """
                    SELECT id FROM article_versions
                    WHERE law_version_id = ? AND anchor_key = ?
                    """,
                    (from_version_id, anchor_key),
                ).fetchone()

                new_av = self.conn.execute(
                    """
                    SELECT id FROM article_versions
                    WHERE law_version_id = ? AND anchor_key = ?
                    """,
                    (to_version_id, anchor_key),
                ).fetchone()

                if old_av and new_av:
                    # Create mapping for annotation remapping
                    self.repo.create_annotation_mapping(
                        old_av["id"],
                        new_av["id"],
                        mapping_quality="fuzzy",
                    )
                    remapped += 1
                else:
                    failed += 1

        return {
            "from_version": from_version_id,
            "to_version": to_version_id,
            "remapped": remapped,
            "failed": failed,
            "warnings": warnings,
        }

    def get_article_history(self, anchor_key: str) -> list[dict[str, Any]]:
        """Get change history for a specific article."""
        versions = self.repo.get_article_versions(anchor_key)
        return [
            {
                "version_label": v["version_label"],
                "article_ref": v["article_ref"],
                "text_hash": v["text_hash"],
                "imported_at": v["imported_at"],
            }
            for v in versions
        ]

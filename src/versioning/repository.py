from __future__ import annotations

import sqlite3
import hashlib
from typing import Any

from src.versioning.schema import missing_versioning_tables

RowDict = dict[str, Any]


class VersioningError(RuntimeError):
    """Base error for versioning issues."""


class VersioningSchemaMissingError(VersioningError):
    """Raised when versioning tables are not migrated."""


class VersioningRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def ensure_storage_ready(self) -> None:
        missing = missing_versioning_tables(self.conn)
        if missing:
            raise VersioningSchemaMissingError(
                "Versioning tables are not migrated: " + ", ".join(missing)
            )

    def create_law_version(
        self,
        *,
        law_id: int,
        version_label: str,
        content_hash: str,
        source_document_id: int | None = None,
        vigencia_desde: str | None = None,
        vigencia_hasta: str | None = None,
    ) -> int:
        """Create a new version of a law."""
        self.ensure_storage_ready()
        cursor = self.conn.execute(
            """
            INSERT INTO law_versions(
                law_id, version_label, content_hash, source_document_id,
                vigencia_desde, vigencia_hasta
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                law_id,
                version_label,
                content_hash,
                source_document_id,
                vigencia_desde,
                vigencia_hasta,
            ),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def get_law_versions(self, law_id: int) -> list[RowDict]:
        """Get all versions of a law."""
        rows = self.conn.execute(
            """
            SELECT * FROM law_versions
            WHERE law_id = ?
            ORDER BY imported_at DESC
            """,
            (law_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_current_version(self, law_id: int) -> RowDict | None:
        """Get the current (latest) version of a law."""
        row = self.conn.execute(
            """
            SELECT * FROM law_versions
            WHERE law_id = ? AND is_current = 1
            ORDER BY imported_at DESC
            LIMIT 1
            """,
            (law_id,),
        ).fetchone()
        return dict(row) if row else None

    def set_current_version(self, law_version_id: int) -> None:
        """Mark a version as current."""
        law_version = self.conn.execute(
            "SELECT law_id FROM law_versions WHERE id = ?",
            (law_version_id,),
        ).fetchone()

        if law_version:
            law_id = law_version["law_id"]
            self.conn.execute(
                "UPDATE law_versions SET is_current = 0 WHERE law_id = ?",
                (law_id,),
            )
            self.conn.execute(
                "UPDATE law_versions SET is_current = 1 WHERE id = ?",
                (law_version_id,),
            )
            self.conn.commit()

    def create_article_version(
        self,
        *,
        law_version_id: int,
        article_ref: str,
        anchor_key: str,
        text: str,
        change_type: str | None = None,
        diff_summary: str | None = None,
    ) -> int:
        """Record an article in a specific law version."""
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        cursor = self.conn.execute(
            """
            INSERT INTO article_versions(
                law_version_id, article_ref, anchor_key, text, text_hash,
                change_type, diff_summary
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                law_version_id,
                article_ref,
                anchor_key,
                text,
                text_hash,
                change_type,
                diff_summary,
            ),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def get_article_versions(self, anchor_key: str) -> list[RowDict]:
        """Get all versions of an article by anchor_key."""
        rows = self.conn.execute(
            """
            SELECT av.*, lv.law_id, lv.version_label
            FROM article_versions av
            JOIN law_versions lv ON av.law_version_id = lv.id
            WHERE av.anchor_key = ?
            ORDER BY lv.imported_at DESC
            """,
            (anchor_key,),
        ).fetchall()
        return [dict(row) for row in rows]

    def find_text_changes(
        self,
        law_version_id_old: int,
        law_version_id_new: int,
    ) -> list[dict[str, Any]]:
        """Find articles that changed between two law versions."""
        old_articles = self.conn.execute(
            """
            SELECT anchor_key, text FROM article_versions
            WHERE law_version_id = ?
            """,
            (law_version_id_old,),
        ).fetchall()

        new_articles = self.conn.execute(
            """
            SELECT anchor_key, text FROM article_versions
            WHERE law_version_id = ?
            """,
            (law_version_id_new,),
        ).fetchall()

        old_dict = {row["anchor_key"]: row["text"] for row in old_articles}
        new_dict = {row["anchor_key"]: row["text"] for row in new_articles}

        changes = []

        # Added articles
        for key in new_dict:
            if key not in old_dict:
                changes.append({"anchor_key": key, "change_type": "added"})

        # Removed articles
        for key in old_dict:
            if key not in new_dict:
                changes.append({"anchor_key": key, "change_type": "removed"})

        # Modified articles
        for key in old_dict:
            if key in new_dict and old_dict[key] != new_dict[key]:
                changes.append({"anchor_key": key, "change_type": "modified"})

        return changes

    def create_annotation_mapping(
        self,
        from_article_version_id: int,
        to_article_version_id: int,
        mapping_quality: str = "automatic",
    ) -> int:
        """Create a mapping between article versions for annotation remapping."""
        cursor = self.conn.execute(
            """
            INSERT INTO annotation_mappings(
                from_article_version_id, to_article_version_id, mapping_quality
            )
            VALUES (?, ?, ?)
            """,
            (from_article_version_id, to_article_version_id, mapping_quality),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def find_annotation_target(
        self,
        from_article_version_id: int,
    ) -> int | None:
        """Find the target article version for annotation remapping."""
        row = self.conn.execute(
            """
            SELECT to_article_version_id FROM annotation_mappings
            WHERE from_article_version_id = ?
            ORDER BY mapping_quality DESC
            LIMIT 1
            """,
            (from_article_version_id,),
        ).fetchone()
        return row["to_article_version_id"] if row else None

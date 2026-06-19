"""Drive backup service for F6 implementation."""

from __future__ import annotations

import sqlite3
import shutil
from pathlib import Path
from typing import Any
from datetime import datetime

from src.core.paths import DB_PATH


class BackupService:
    """Service for managing database backups."""

    BACKUP_DIR = Path(__file__).parent.parent.parent / "backups"

    def __init__(self) -> None:
        self.BACKUP_DIR.mkdir(exist_ok=True)

    def create_local_backup(self, user_id: int | None = None) -> str:
        """Create a local backup of the database."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"gvadicto_backup_{timestamp}.sqlite"
        backup_path = self.BACKUP_DIR / backup_name

        try:
            shutil.copy2(DB_PATH, backup_path)
            return str(backup_path)
        except Exception as e:
            raise RuntimeError(f"Backup failed: {e}")

    def restore_from_backup(self, backup_path: str) -> bool:
        """Restore database from backup."""
        try:
            shutil.copy2(backup_path, DB_PATH)
            return True
        except Exception as e:
            print(f"Restore failed: {e}")
            return False

    def list_backups(self) -> list[dict[str, Any]]:
        """List available backups."""
        backups = []
        for backup_file in sorted(self.BACKUP_DIR.glob("*.sqlite"), reverse=True):
            stat = backup_file.stat()
            backups.append({
                "name": backup_file.name,
                "path": str(backup_file),
                "size_mb": stat.st_size / (1024 * 1024),
                "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        return backups

    def upload_to_drive(self, backup_path: str, user_token: str | None = None) -> bool:
        """Upload backup to Google Drive (MVP: placeholder)."""
        # Full implementation would use Google Drive API
        # For MVP: just track that backup was attempted
        print(f"[MVP] Would upload {backup_path} to Drive")
        return True

    def auto_backup_scheduled(self) -> None:
        """Scheduled auto-backup (call daily)."""
        try:
            backup_path = self.create_local_backup()
            print(f"[BACKUP] Created: {backup_path}")
            # Could upload to Drive here
        except Exception as e:
            print(f"[BACKUP ERROR] {e}")

"""Google Drive backup service for database and user data (F6).

Supports:
  - Database backup (SQLite)
  - Study data export (JSON)
  - Automatic scheduling
  - Restore from backup
"""

import os
import json
import shutil
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from sqlalchemy.orm import Session

from src.db.models import BackupHistory, User
from src.core.paths import DB_PATH


class DriveBackupService:
    """Google Drive backup service."""

    FOLDER_NAME = "GVAdictos"
    SCOPES = ["https://www.googleapis.com/auth/drive"]

    def __init__(self, user_id: int, db: Session, credentials_json: Optional[str] = None):
        """Initialize Drive service.

        Args:
            user_id: User ID in database
            db: SQLAlchemy session
            credentials_json: Google credentials JSON (env var)
        """
        self.user_id = user_id
        self.db = db
        self.service = None

        # Try to initialize Drive service
        try:
            creds = self._get_credentials(credentials_json)
            if creds:
                self.service = build("drive", "v3", credentials=creds)
        except Exception as e:
            print(f"[Drive] Init error: {e}")

    def _get_credentials(self, credentials_json: Optional[str] = None) -> Optional[Credentials]:
        """Get Google Drive credentials."""
        creds_str = credentials_json or os.getenv("GOOGLE_CREDENTIALS_JSON", "")

        if not creds_str or creds_str == "{}":
            return None

        try:
            creds_data = json.loads(creds_str)
            creds = Credentials.from_authorized_user_info(creds_data, self.SCOPES)

            if creds.expired and creds.refresh_token:
                creds.refresh(Request())

            return creds
        except Exception as e:
            print(f"[Drive] Credentials error: {e}")
            return None

    def _get_or_create_folder(self, folder_name: str) -> Optional[str]:
        """Get or create folder in Drive."""
        if not self.service:
            return None

        try:
            # Search for folder
            results = self.service.files().list(
                q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                spaces="drive",
                fields="files(id)",
                pageSize=1,
            ).execute()

            files = results.get("files", [])
            if files:
                return files[0]["id"]

            # Create folder
            file_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
            }
            folder = self.service.files().create(body=file_metadata, fields="id").execute()
            return folder.get("id")

        except Exception as e:
            print(f"[Drive] Folder error: {e}")
            return None

    def backup_database(self, backup_type: str = "auto") -> bool:
        """Backup SQLite database to Drive.

        Args:
            backup_type: 'auto' or 'manual'

        Returns:
            True if successful
        """
        if not self.service or not os.path.exists(DB_PATH):
            return False

        try:
            # Create temp copy
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"gvadictos_{timestamp}.sqlite"

            # Upload to Drive
            parent_id = self._get_or_create_folder(self.FOLDER_NAME)
            if not parent_id:
                return False

            file_metadata = {
                "name": filename,
                "parents": [parent_id],
            }
            media = MediaFileUpload(DB_PATH, mimetype="application/octet-stream")

            file = (
                self.service.files()
                .create(body=file_metadata, media_body=media, fields="id, size")
                .execute()
            )

            file_id = file.get("id")
            file_size = int(file.get("size", 0))

            # Record in database
            backup = BackupHistory(
                user_id=self.user_id,
                backup_type=backup_type,
                drive_file_id=file_id,
                drive_file_name=filename,
                backup_size_bytes=file_size,
                status="success",
            )
            self.db.add(backup)
            self.db.commit()

            return True

        except Exception as e:
            print(f"[Drive] Backup error: {e}")

            # Record failure
            backup = BackupHistory(
                user_id=self.user_id,
                backup_type=backup_type,
                status="failed",
                error_message=str(e),
            )
            self.db.add(backup)
            self.db.commit()

            return False

    def restore_database(self, backup_file_id: str) -> bool:
        """Restore database from Drive backup.

        Args:
            backup_file_id: Stripe file ID to restore

        Returns:
            True if successful
        """
        if not self.service:
            return False

        try:
            # Download from Drive
            request = self.service.files().get_media(fileId=backup_file_id)

            # Create temp file
            temp_path = DB_PATH + ".restore"
            with open(temp_path, "wb") as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()

            # Backup current and restore
            backup_path = DB_PATH + ".old"
            if os.path.exists(DB_PATH):
                shutil.move(DB_PATH, backup_path)

            shutil.move(temp_path, DB_PATH)
            return True

        except Exception as e:
            print(f"[Drive] Restore error: {e}")
            return False

    def list_backups(self) -> list[Dict[str, Any]]:
        """List all backups for user."""
        backups = (
            self.db.query(BackupHistory)
            .filter_by(user_id=self.user_id, status="success")
            .order_by(BackupHistory.created_at.desc())
            .limit(10)
            .all()
        )

        return [
            {
                "id": b.id,
                "type": b.backup_type,
                "filename": b.drive_file_name,
                "size_mb": b.backup_size_bytes / (1024 * 1024) if b.backup_size_bytes else 0,
                "created_at": b.created_at.isoformat() if b.created_at else "",
            }
            for b in backups
        ]

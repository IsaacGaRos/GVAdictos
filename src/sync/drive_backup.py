"""
Google Drive backup and sync for Ola F6.

MVP: Placeholder specification for backup integration.

Implementation uses existing Google Drive MCP connector.
"""

DRIVE_SYNC_SPEC = """
F6 — Google Drive Backup & Sync

Features:
  1. Auto-backup SQLite database to Drive (daily)
  2. Export study data (notes, highlights) as JSON
  3. Sync preferences across devices
  4. Share study resources with other users

Implementation:
  - Use existing src/ai with Google Drive MCP
  - Backup location: /GVAdictos/backups/{date}.sqlite
  - Study export: /GVAdictos/exports/{user_id}_study_{date}.json
  - Preferences: /GVAdictos/config/{user_id}_prefs.json

Workflow:
  1. User authenticates with Google (OAuth2)
  2. Grant folder access to GVAdictos
  3. Enable backup toggle in settings
  4. Daily backup runs automatically
  5. User can restore from Drive backup anytime

Database additions:
  CREATE TABLE backup_history (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    backup_type TEXT,  -- database, study, config
    drive_file_id TEXT,
    size_bytes INTEGER,
    created_at TEXT
  );
"""

def backup_database_to_drive(user_id: int) -> dict:
    """Backup SQLite database to Google Drive.

    Implementation would use MCP Google Drive connector:
        from src.ai import GoogleDriveService
        service = GoogleDriveService(user_token)
        result = service.upload_file(
            local_path='db/gvadictos.sqlite',
            remote_path='GVAdictos/backups/...'
        )
    """
    raise NotImplementedError("F6: Drive backup pending")


def sync_study_data_to_drive(user_id: int) -> dict:
    """Export and sync study data to Drive."""
    raise NotImplementedError("F6: Study data sync pending")


def restore_from_backup(user_id: int, backup_id: int) -> bool:
    """Restore database from Drive backup."""
    raise NotImplementedError("F6: Restore from backup pending")

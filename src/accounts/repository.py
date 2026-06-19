from __future__ import annotations

import sqlite3
import hashlib
import secrets
from typing import Any

from src.accounts.schema import missing_accounts_tables

RowDict = dict[str, Any]


class AccountsStorageError(RuntimeError):
    """Base error for accounts storage issues."""


class AccountsSchemaMissingError(AccountsStorageError):
    """Raised when accounts tables are not migrated."""


class AccountsRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        # Keep whatever row_factory the caller set (dict factory from src.core.db)

    def ensure_storage_ready(self) -> None:
        missing = missing_accounts_tables(self.conn)
        if missing:
            raise AccountsSchemaMissingError(
                "Accounts tables are not migrated: " + ", ".join(missing)
            )

    def hash_password(self, password: str) -> str:
        """Hash a password using SHA256."""
        return hashlib.sha256(password.encode()).hexdigest()

    def create_user(
        self,
        *,
        email: str,
        password: str,
        full_name: str | None = None,
    ) -> int:
        """Create a new user account."""
        self.ensure_storage_ready()
        password_hash = self.hash_password(password)

        cursor = self.conn.execute(
            """
            INSERT INTO users(email, password_hash, full_name)
            VALUES (?, ?, ?)
            """,
            (email, password_hash, full_name),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def get_user_by_email(self, email: str) -> RowDict | None:
        """Get user by email."""
        row = self.conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> RowDict | None:
        """Get user by ID."""
        row = self.conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None

    def verify_password(self, user_id: int, password: str) -> bool:
        """Verify user password."""
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        password_hash = self.hash_password(password)
        return user["password_hash"] == password_hash

    def create_session(self, user_id: int, expires_hours: int = 24) -> str:
        """Create a session token for a user."""
        self.ensure_storage_ready()
        token = secrets.token_urlsafe(32)

        from datetime import datetime, timedelta
        expires_at = (datetime.utcnow() + timedelta(hours=expires_hours)).isoformat()

        self.conn.execute(
            """
            INSERT INTO user_sessions(user_id, token, expires_at)
            VALUES (?, ?, ?)
            """,
            (user_id, token, expires_at),
        )
        self.conn.commit()
        return token

    def verify_session(self, token: str) -> int | None:
        """Verify a session token and return user_id if valid."""
        from datetime import datetime
        row = self.conn.execute(
            """
            SELECT user_id, expires_at FROM user_sessions
            WHERE token = ? AND is_active = 1
            """,
            (token,),
        ).fetchone()

        if not row:
            return None

        if row["expires_at"]:
            expires = datetime.fromisoformat(row["expires_at"])
            if expires < datetime.utcnow():
                return None

        return row["user_id"]

    def invalidate_session(self, token: str) -> None:
        """Invalidate a session token."""
        self.conn.execute(
            "UPDATE user_sessions SET is_active = 0 WHERE token = ?",
            (token,),
        )
        self.conn.commit()

    def get_user_sessions(self, user_id: int) -> list[RowDict]:
        """Get active sessions for a user."""
        rows = self.conn.execute(
            """
            SELECT * FROM user_sessions
            WHERE user_id = ? AND is_active = 1
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()
        return [dict(row) for row in rows]

"""Authentication and user account service.

Manages user registration, login, and session handling.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from src.accounts.repository import AccountsRepository


class AuthError(RuntimeError):
    """Base error for auth issues."""


class AuthService:
    """Service for user authentication and account management."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.repo = AccountsRepository(conn)

    def register(
        self,
        email: str,
        password: str,
        full_name: str | None = None,
    ) -> int:
        """Register a new user."""
        existing = self.repo.get_user_by_email(email)
        if existing:
            raise AuthError(f"Email {email} already registered")

        if len(password) < 8:
            raise AuthError("Password must be at least 8 characters")

        user_id = self.repo.create_user(
            email=email,
            password=password,
            full_name=full_name,
        )
        return user_id

    def login(self, email: str, password: str) -> str:
        """Authenticate user and return session token."""
        user = self.repo.get_user_by_email(email)
        if not user:
            raise AuthError("Invalid email or password")

        if not user["is_active"]:
            raise AuthError("User account is inactive")

        if not self.repo.verify_password(user["id"], password):
            raise AuthError("Invalid email or password")

        # Update last_login
        self.conn.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
            (user["id"],),
        )
        self.conn.commit()

        # Create session
        token = self.repo.create_session(user["id"])
        return token

    def logout(self, token: str) -> None:
        """Logout user (invalidate session)."""
        self.repo.invalidate_session(token)

    def get_current_user(self, token: str) -> dict[str, Any] | None:
        """Get current user from session token."""
        user_id = self.repo.verify_session(token)
        if not user_id:
            return None

        user = self.repo.get_user_by_id(user_id)
        return {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "is_admin": bool(user["is_admin"]),
        } if user else None

    def change_password(
        self,
        user_id: int,
        old_password: str,
        new_password: str,
    ) -> bool:
        """Change user password."""
        if not self.repo.verify_password(user_id, old_password):
            raise AuthError("Current password is incorrect")

        if len(new_password) < 8:
            raise AuthError("New password must be at least 8 characters")

        password_hash = self.repo.hash_password(new_password)
        self.conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (password_hash, user_id),
        )
        self.conn.commit()
        return True

"""Accounts module for user authentication and account management.

Provides registration, login, session management for multiuser support (F1-F2).
"""

from src.accounts.service import AuthService, AuthError
from src.accounts.repository import AccountsRepository, AccountsStorageError, AccountsSchemaMissingError
from src.accounts.schema import ensure_accounts_tables, missing_accounts_tables, add_user_id_column

__all__ = [
    "AuthService",
    "AuthError",
    "AccountsRepository",
    "AccountsStorageError",
    "AccountsSchemaMissingError",
    "ensure_accounts_tables",
    "missing_accounts_tables",
    "add_user_id_column",
]

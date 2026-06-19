"""FastAPI dependency providers for database sessions and authentication."""

from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from src.db.database import SessionLocal
from src.accounts.service import AuthService


def get_db() -> Session:
    """Dependency: Get SQLAlchemy database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
) -> dict:
    """Dependency: Extract and verify current user from Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )

    token = authorization.split(" ")[1]

    # TODO: Use SQLAlchemy AuthService to get user
    # For now, fallback to existing service if it exists
    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return user

"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
import sqlite3

from src.api.models import UserRegister, UserLogin, TokenResponse, UserResponse
from src.core.db import connect
from src.core.paths import DB_PATH
from src.accounts.service import AuthService, AuthError

router = APIRouter()


def get_db() -> sqlite3.Connection:
    """Get database connection."""
    return connect(DB_PATH)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: sqlite3.Connection = Depends(get_db)):
    """Register a new user."""
    try:
        auth_service = AuthService(db)
        user_id = auth_service.register(
            email=data.email,
            password=data.password,
            full_name=data.full_name,
        )
        token = auth_service.login(data.email, data.password)

        user = {
            "id": user_id,
            "email": data.email,
            "full_name": data.full_name,
            "is_admin": False,
        }

        return TokenResponse(access_token=token, user=UserResponse(**user))

    except AuthError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: sqlite3.Connection = Depends(get_db)):
    """Login user and get access token."""
    try:
        auth_service = AuthService(db)
        token = auth_service.login(data.email, data.password)
        user = auth_service.get_current_user(token)

        return TokenResponse(access_token=token, user=UserResponse(**user))

    except AuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/logout")
async def logout(
    authorization: str = None,
    db: sqlite3.Connection = Depends(get_db),
):
    """Logout user (invalidate token)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    token = authorization.split(" ")[1]
    auth_service = AuthService(db)
    auth_service.logout(token)

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    authorization: str = None,
    db: sqlite3.Connection = Depends(get_db),
):
    """Get current authenticated user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    token = authorization.split(" ")[1]
    auth_service = AuthService(db)
    user = auth_service.get_current_user(token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return UserResponse(**user)

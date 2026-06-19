"""FastAPI application for GVAdictos REST API.

Serves as the backend for web and mobile clients.
Reuses existing service layer from src/ modules.
"""

from __future__ import annotations

from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import sqlite3

from src.api.models import *
from src.api.routes import auth, articles, topics, exams, study
from src.core.db import connect
from src.core.paths import DB_PATH
from src.accounts.service import AuthService

# Lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    print("[API] Starting GVAdictos API server...")
    yield
    print("[API] Shutting down...")


# Create app
app = FastAPI(
    title="GVAdictos API",
    description="REST API para preparación de oposiciones GVA",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # MVP: allow all; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency: get DB connection
def get_db() -> sqlite3.Connection:
    """Get database connection."""
    return connect(DB_PATH)


# Dependency: get current user
def get_current_user(
    authorization: str = Header(None),
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Extract and verify current user from token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )

    token = authorization.split(" ")[1]
    auth_service = AuthService(db)
    user = auth_service.get_current_user(token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return user


# Routes
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(articles.router, prefix="/api/articles", tags=["articles"])
app.include_router(topics.router, prefix="/api/topics", tags=["topics"])
app.include_router(exams.router, prefix="/api/exams", tags=["exams"])
app.include_router(study.router, prefix="/api/study", tags=["study"])


# Health check
@app.get("/health", tags=["health"])
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "GVAdictos API",
    }


# Root
@app.get("/", tags=["root"])
async def root() -> dict:
    """API root."""
    return {
        "message": "GVAdictos API v1.0.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

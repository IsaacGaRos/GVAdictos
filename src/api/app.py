"""FastAPI application for GVAdictos REST API.

Serves as the backend for web and mobile clients.
Reuses existing service layer from src/ modules.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.api.models import *
from src.api.routes import auth, articles, topics, exams, study, billing, oposiciones
from src.db.database import init_db

# Lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    print("[API] Starting GVAdictos API server...")
    print("[API] Initializing database...")
    init_db()
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


# Routes
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(articles.router, prefix="/api/articles", tags=["articles"])
app.include_router(topics.router, prefix="/api/topics", tags=["topics"])
app.include_router(exams.router, prefix="/api/exams", tags=["exams"])
app.include_router(study.router, prefix="/api/study", tags=["study"])
app.include_router(billing.router, prefix="/api/billing", tags=["billing"])
app.include_router(oposiciones.router, prefix="/api/oposiciones", tags=["oposiciones"])


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

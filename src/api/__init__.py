"""FastAPI REST API module for GVAdictos.

Provides REST endpoints for web and mobile clients.
Reuses existing service layer from src/ modules.

To run the API:
    pip install fastapi uvicorn
    uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000

Documentation available at:
    http://localhost:8000/docs
    http://localhost:8000/redoc
"""

from src.api.app import app

__all__ = ["app"]

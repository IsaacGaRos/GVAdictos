@echo off
REM Run GVAdictos API server

echo Installing API dependencies...
pip install -q -r requirements-api.txt

echo Starting GVAdictos API...
echo Documentation: http://localhost:8000/docs
echo.

uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000

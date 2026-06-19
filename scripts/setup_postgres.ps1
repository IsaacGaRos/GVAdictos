# PowerShell script to setup PostgreSQL for development

Write-Host "[Setup] Installing dependencies..." -ForegroundColor Green
pip install -r requirements.txt

Write-Host "[Setup] Starting PostgreSQL with docker-compose..." -ForegroundColor Green
docker-compose up -d postgres

Write-Host "[Setup] Waiting for PostgreSQL to be ready..." -ForegroundColor Green
Start-Sleep -Seconds 5

Write-Host "[Setup] Running migrations..." -ForegroundColor Green
alembic upgrade head

Write-Host "[Setup] Done! Database is ready." -ForegroundColor Green
Write-Host ""
Write-Host "Start the API with:" -ForegroundColor Cyan
Write-Host "  uvicorn src.api.app:app --reload"
Write-Host ""
Write-Host "Or Streamlit with:" -ForegroundColor Cyan
Write-Host "  streamlit run app.py"

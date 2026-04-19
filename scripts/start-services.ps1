# Start Cuckoo-Echo services for development

$ErrorActionPreference = "Stop"

Write-Host "Starting API Gateway on port 8000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "uvicorn api_gateway.main:app --host 0.0.0.0 --port 8000 --reload" -WorkingDirectory $PWD -WindowStyle Normal

Write-Host "Starting Chat Service on port 8001..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "uvicorn chat_service.main:app --host 0.0.0.0 --port 8001 --reload" -WorkingDirectory $PWD -WindowStyle Normal

Write-Host "Starting Admin Service on port 8002..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python -m admin_service.main" -WorkingDirectory $PWD -WindowStyle Normal

Write-Host ""
Write-Host "Services started!" -ForegroundColor Cyan
Write-Host "- API Gateway: http://localhost:8000" -ForegroundColor Yellow
Write-Host "- Chat Service: http://localhost:8001" -ForegroundColor Yellow
Write-Host "- Admin Service: http://localhost:8002" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Ctrl+C in each window to stop." -ForegroundColor Gray
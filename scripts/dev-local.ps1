# Cuckoo-Echo Local Development Startup Script
# Starts infrastructure in Docker, services run locally

param(
    [switch]$SkipInstall,
    [switch]$SkipMigrate
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

Set-Location $ProjectDir

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "Cuckoo-Echo Local Development Setup" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

# Check dependencies
$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uv) {
    Write-Host "uv not found. Install: pip install uv" -ForegroundColor Red
    exit 1
}

$docker = Get-Command docker -ErrorAction SilentlyContinue
if (-not $docker) {
    Write-Host "docker not found." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[1/4] Starting infrastructure (Docker)..." -ForegroundColor Green

docker compose -f docker-compose.dev.yml up -d

Write-Host "Waiting for infrastructure to be healthy..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Wait for postgres
$pgReady = $false
$pgRetries = 30
while (-not $pgReady -and $pgRetries -gt 0) {
    $pgReady = docker compose -f docker-compose.dev.yml exec -T postgres pg_isready -U postgres 2>$null
    if (-not $pgReady) {
        Write-Host "  Waiting for PostgreSQL..." -ForegroundColor Yellow
        Start-Sleep -Seconds 2
        $pgRetries--
    }
}

# Wait for redis
$redisReady = $false
$redisRetries = 30
while (-not $redisReady -and $redisRetries -gt 0) {
    $redisReady = docker compose -f docker-compose.dev.yml exec -T redis redis-cli ping 2>$null
    if (-not $redisReady) {
        Write-Host "  Waiting for Redis..." -ForegroundColor Yellow
        Start-Sleep -Seconds 2
        $redisRetries--
    }
}

Write-Host "  Infrastructure ready!" -ForegroundColor Green

if (-not $SkipInstall) {
    Write-Host ""
    Write-Host "[2/4] Installing dependencies..." -ForegroundColor Green
    uv sync
}

if (-not $SkipMigrate) {
    Write-Host ""
    Write-Host "[3/4] Running migrations..." -ForegroundColor Green
    uv run alembic upgrade head
}

Write-Host ""
Write-Host "[4/4] Starting services..." -ForegroundColor Green

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "Services ready! Start each service in a separate terminal:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Terminal 1 (API Gateway):" -ForegroundColor White
Write-Host "    uvicorn api_gateway.main:app --reload --port 8000" -ForegroundColor Gray
Write-Host ""
Write-Host "  Terminal 2 (Chat Service):" -ForegroundColor White
Write-Host "    uvicorn chat_service.main:app --reload --port 8001" -ForegroundColor Gray
Write-Host ""
Write-Host "  Terminal 3 (Admin Service):" -ForegroundColor White
Write-Host "    python -m admin_service.main" -ForegroundColor Gray
Write-Host ""
Write-Host "  Terminal 4 (Frontend - optional):" -ForegroundColor White
Write-Host "    cd frontend && pnpm dev" -ForegroundColor Gray
Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "Endpoints:" -ForegroundColor Cyan
Write-Host "  API Gateway:  http://localhost:8000" -ForegroundColor White
Write-Host "  Chat Service: http://localhost:8001" -ForegroundColor White
Write-Host "  Admin Svc:     http://localhost:8002" -ForegroundColor White
Write-Host "  Frontend:      http://localhost:5173" -ForegroundColor White
Write-Host "==============================================" -ForegroundColor Cyan
# run_servers.ps1
#
# Helper script to start all 4 microservices and the Next.js frontend of the PRAVAH suite.
# Each service will start in a separate PowerShell window so you can monitor logs and stop them individually.

$projectRoot = $PSScriptRoot
if (-not $projectRoot) {
    $projectRoot = Get-Location
}

Write-Host "====================================================="
Write-Host "  PRAVAH Microservice & Frontend Orchestrator"
Write-Host "====================================================="
Write-Host "Project Root: $projectRoot"
Write-Host ""

# Set PYTHONPATH environment variable to include the project root directory
$env:PYTHONPATH = $projectRoot

# 0. Start Shared Service on Port 8000
Write-Host "Starting Shared Service (Port 8000)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot\shared'; `$env:PYTHONPATH='$projectRoot'; uvicorn main:app --port 8000"

# 1. Start Risk Agent on Port 8001
Write-Host "Starting Risk Agent (Port 8001)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot\risk-agent'; `$env:PYTHONPATH='$projectRoot'; uvicorn main:app --port 8001"

# 2. Start Scenario Engine on Port 8002
Write-Host "Starting Scenario Engine (Port 8002)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot\scenario-engine'; `$env:PYTHONPATH='$projectRoot'; uvicorn main:app --port 8002"

# 3. Start Procurement Agent on Port 8003
Write-Host "Starting Procurement Agent (Port 8003)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot\procurement-agent'; `$env:PYTHONPATH='$projectRoot'; uvicorn main:app --port 8003"

# 4. Start SPR Agent on Port 8004
Write-Host "Starting SPR Agent (Port 8004)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot\spr-agent'; `$env:PYTHONPATH='$projectRoot'; uvicorn main:app --port 8004"

# 5. Start Next.js Frontend
Write-Host "Starting Next.js Frontend (Port 3000)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot\frontend'; npm run dev"

Write-Host ""
Write-Host "====================================================="
Write-Host " All services have been launched in separate windows!"
Write-Host " - Frontend: http://localhost:3000"
Write-Host " - Shared Service: http://127.0.0.1:8000"
Write-Host " - Risk Agent: http://127.0.0.1:8001"
Write-Host " - Scenario Engine: http://127.0.0.1:8002"
Write-Host " - Procurement Agent: http://127.0.0.1:8003"
Write-Host " - SPR Agent: http://127.0.0.1:8004"
Write-Host "====================================================="

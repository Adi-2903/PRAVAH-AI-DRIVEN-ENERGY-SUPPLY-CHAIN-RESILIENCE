# run_pipeline.ps1

$env:PYTHONPATH = "."

Write-Host "====================================================="
Write-Host "  PRAVAH Stage 1-3 Pipeline Execution"
Write-Host "====================================================="
Write-Host ""

Write-Host "1. Running Data Ingestion & DB Upserts..."
python shared/clients/test_spine.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Data Ingestion completed with some failures." -ForegroundColor Yellow
} else {
    Write-Host "Data Ingestion completed successfully." -ForegroundColor Green
}
Write-Host ""

Write-Host "2. Rebuilding Knowledge Graph from DB..."
python shared/db/knowledge_graph.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Knowledge Graph build failed." -ForegroundColor Red
} else {
    Write-Host "Knowledge Graph built successfully." -ForegroundColor Green
}
Write-Host ""

Write-Host "3. Running Integration Tests..."
python -m pytest shared/clients/test_integration.py -v
if ($LASTEXITCODE -ne 0) {
    Write-Host "Integration Tests failed." -ForegroundColor Red
} else {
    Write-Host "Integration Tests passed successfully." -ForegroundColor Green
}
Write-Host ""

Write-Host "====================================================="
Write-Host "  Pipeline Execution Complete"
Write-Host "====================================================="

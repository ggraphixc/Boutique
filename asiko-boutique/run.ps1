# ASIKO Boutique - Quick Preview (PowerShell)
# Right-click > Run with PowerShell

$Host.UI.RawUI.WindowTitle = "ASIKO Boutique - Development Server"
$Host.UI.RawUI.BackgroundColor = "Black"

Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "  ASIKO Boutique - Quick Preview" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""

Set-Location $PSScriptRoot

if (-not (Test-Path ".env")) {
    Write-Host "ERROR: .env file not found!" -ForegroundColor Red
    Write-Host "Please create .env with DATABASE_URL and BREVO_API_KEY" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Starting server on " -NoNewline
Write-Host "http://localhost:8000" -ForegroundColor Green
Write-Host ""
Write-Host "  Storefront:      http://localhost:8000/" -ForegroundColor Cyan
Write-Host "  Admin Dashboard: http://localhost:8000/admin/dashboard" -ForegroundColor Cyan
Write-Host "  Virtual Atelier: http://localhost:8000/virtual-experience" -ForegroundColor Cyan
Write-Host "  Debug PDP:       http://localhost:8000/test-pdp" -ForegroundColor Cyan
Write-Host "  DPP Verify:      http://localhost:8000/verify/{token}" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""

python -m uvicorn app.main:app --reload --port 8000

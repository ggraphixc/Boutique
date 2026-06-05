@echo off
title ASIKO Boutique - Development Server
color 0A

echo ========================================
echo   ASIKO Boutique - Quick Preview
echo ========================================
echo.

cd /d "%~dp0"

echo [1/2] Checking environment...
if not exist ".env" (
    echo ERROR: .env file not found!
    echo Please create .env with DATABASE_URL and BREVO_API_KEY
    pause
    exit /b 1
)

echo [2/2] Starting server on http://localhost:8000
echo.
echo   Storefront:      http://localhost:8000/
echo   Admin Dashboard: http://localhost:8000/admin/dashboard
echo   Virtual Atelier: http://localhost:8000/virtual-experience
echo   Debug PDP:       http://localhost:8000/test-pdp
echo   DPP Verify:      http://localhost:8000/verify/{token}
echo.
echo   Press Ctrl+C to stop
echo ========================================
echo.

python -m uvicorn app.main:app --reload --port 8000

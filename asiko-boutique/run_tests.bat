@echo off
title ASIKO Boutique - Test Runner
color 0B

echo ========================================
echo   ASIKO Boutique - Integration Tests
echo ========================================
echo.

cd /d "%~dp0"

echo Running all 27 tests...
echo.

python -m pytest app/tests/ -v

echo.
echo ========================================
echo   Tests complete
echo ========================================
pause

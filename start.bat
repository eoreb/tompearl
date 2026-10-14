@echo off
chcp 65001 >nul
title Fight Tom Pearl (Undertale Edition)

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py %*
    exit /b %errorlevel%
)

python start.py %*
if %errorlevel% neq 0 (
    echo.
    echo Ошибка при запуске игры.
    pause
)

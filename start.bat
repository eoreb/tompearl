@echo off
chcp 65001 >nul
title Fight Tom Pearl (Undertale Edition)

echo ========================================================
echo   Fight Tom Pearl (Undertale Edition) - Windows Launcher
echo ========================================================

cd /d "%~dp0"

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python start.py
    goto end
)

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py start.py
    goto end
)

echo [ПРЕДУПРЕЖДЕНИЕ] Python не найден в системе.
echo Открытие index.html напрямую в браузере...
start "" "index.html"

:end

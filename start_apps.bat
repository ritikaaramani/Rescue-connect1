@echo off
:: ============================================================
::  Rescue Connect - Applications Startup Script (Windows)
::  This script starts Flutter first, then Authority Dashboard.
:: ============================================================

echo.
echo =====================================================
echo   RESCUE CONNECT - Starting Applications
echo =====================================================
echo.

:: --- Kill any zombie Dart/Flutter processes first ---
echo [0/2] Cleaning up any existing Dart/Flutter processes...
taskkill /F /IM dart.exe /T >nul 2>&1
taskkill /F /IM flutter.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul

:: --- Flutter App (--no-dds disables the Dart Development Service which was failing) ---
echo [1/2] Starting Flutter Emergency Routing App on Web (background)...
start "Flutter-App" /min cmd /k "cd /d %~dp0Traffic_Model1\emergency_routing_flutter && flutter run -d chrome --web-port 8080 --web-browser-flag \"--disable-web-security\" --no-dds"
timeout /t 8 /nobreak >nul

:: --- React Authority Dashboard ---
echo [2/2] Starting React Authority Dashboard...
start "React-Authority" cmd /k "cd /d %~dp0user_app\rescue_connect\authority && if not exist node_modules (npm install) && npm run dev"

echo.
echo =====================================================
echo   Flutter (background) and Authority launched!
echo =====================================================
echo   If Flutter does not open, run: .\kill_flutter.bat
echo   Then re-run this script.
echo =====================================================
pause

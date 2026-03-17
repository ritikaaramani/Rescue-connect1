@echo off
:: ============================================================
::  Rescue Connect - Applications Startup Script (Windows)
::  This script starts the Simulator, Authority Dashboard, and Flutter App.
:: ============================================================

echo.
echo =====================================================
echo   RESCUE CONNECT - Starting Applications
echo =====================================================
echo.

:: --- Kill any zombie Dart/Flutter processes first ---
echo [0/3] Cleaning up any existing Dart/Flutter processes...
taskkill /F /IM dart.exe /T >nul 2>&1
taskkill /F /IM flutter.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul

:: --- React Simulator App ---
echo [1/3] Starting React Simulator App...
start "React-Simulator" cmd /k "cd /d %~dp0user_app\rescue_connect\simulator && npm run dev"
timeout /t 3 /nobreak >nul

:: --- React Authority Dashboard ---
echo [2/3] Starting React Authority Dashboard...
start "React-Authority" cmd /k "cd /d %~dp0user_app\rescue_connect\authority && npm run dev"
timeout /t 3 /nobreak >nul

:: --- Flutter App (--no-dds disables the Dart Development Service which was failing) ---
echo [3/3] Starting Flutter Emergency Routing App on Web...
start "Flutter-App" cmd /k "cd /d %~dp0Traffic_Model1\emergency_routing_flutter && flutter run -d chrome --no-dds"

echo.
echo =====================================================
echo   All applications launched! 
echo =====================================================
echo   If Flutter does not open, run: .\kill_flutter.bat
echo   Then re-run this script.
echo =====================================================
pause

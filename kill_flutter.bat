@echo off
:: ============================================================
::  Rescue Connect - Flutter/Dart Cleanup Script
::  Run this if Flutter hangs or fails to start.
::  Then re-run start_apps.bat
:: ============================================================
echo.
echo Stopping all Dart and Flutter processes...
taskkill /F /IM dart.exe /T >nul 2>&1
taskkill /F /IM flutter.exe /T >nul 2>&1
echo Done. You can now re-run start_apps.bat
echo.
pause

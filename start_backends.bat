@echo off
:: ============================================================
::  Rescue Connect - Backends Startup Script (Windows)
::  Starts all services in the correct order:
::    Port 9001 - Model 1  (Traffic LSTM+GCN)
::    Port 9002 - Pipeline (Model 2 XGBoost + Model 3 DQN)
::    Port 9000 - Unified API (orchestrator + Supabase bridge)
::    Port 9003 - ML Backend (user app image analysis)
:: ============================================================

echo.
echo =====================================================
echo   RESCUE CONNECT - Starting Backend Services
echo =====================================================
echo.

:: --- Model 1: Traffic Prediction (port 9001) ---
echo [1/4] Starting Model 1 - Traffic Prediction (port 9001)...
start "Model1-TrafficPrediction" cmd /k "cd /d %~dp0Traffic_Model1\emergency-routing-model1 && python -m uvicorn inference.api:app --host 0.0.0.0 --port 9001 --reload"
timeout /t 3 /nobreak >nul

:: --- Model Pipeline: M1->M2->M3 (port 9002) ---
echo [2/4] Starting ML Pipeline - M1->M2->M3 (port 9002)...
start "MLPipeline-M1M2M3" cmd /k "cd /d %~dp0hacky-backend && python -m uvicorn route_reliability_scoring.integration.pipeline:app --host 0.0.0.0 --port 9002 --reload"
timeout /t 3 /nobreak >nul

:: --- Unified API: Main Orchestrator (port 9000) ---
echo [3/4] Starting Unified API - Main Orchestrator (port 9000)...
start "UnifiedAPI-Orchestrator" cmd /k "cd /d %~dp0dynamic-rerouting\api && python -m uvicorn unified_api:app --host 0.0.0.0 --port 9000 --reload"
timeout /t 3 /nobreak >nul

:: --- ML Backend: User App Image Analysis (port 9003) ---
echo [4/4] Starting ML Backend - Image Analysis (port 9003)...
start "MLBackend-UserApp" cmd /k "cd /d %~dp0user_app\rescue_connect\ml_backend && python -m uvicorn main:app --host 0.0.0.0 --port 9003 --reload"

echo.
echo =====================================================
echo   All backends started! Check each terminal window.
echo =====================================================
echo.
echo   Model 1  (Traffic):      http://localhost:9001/docs
echo   ML Pipeline (M1+M2+M3):  http://localhost:9002/docs
echo   Unified API (Main):      http://localhost:9000/docs
echo   ML Backend (User App):   http://localhost:9003/docs
echo.
pause

@echo off
:: ============================================================
::  Rescue Connect - Unified Startup Script (Windows)
::  Starts all services in the correct order:
::    Port 8001 - Model 1  (Traffic LSTM+GCN)
::    Port 8002 - Pipeline (Model 2 XGBoost + Model 3 DQN)
::    Port 8000 - Unified API (orchestrator + Supabase bridge)
::    Port 8003 - ML Backend (user app image analysis)
:: ============================================================

echo.
echo =====================================================
echo   RESCUE CONNECT - Starting All Services
echo =====================================================
echo.

:: --- Optional: set Supabase credentials ---
:: Uncomment and fill in your values before running
:: set SUPABASE_URL=https://your-project.supabase.co
:: set SUPABASE_SERVICE_KEY=your-service-role-key

:: --- Model 1: Traffic Prediction (port 8001) ---
echo [1/4] Starting Model 1 - Traffic Prediction (port 8001)...
start "Model1-TrafficPrediction" cmd /k "cd /d %~dp0Traffic_Model1\emergency-routing-model1 && python -m uvicorn inference.api:app --host 0.0.0.0 --port 8001 --reload"
timeout /t 3 /nobreak >nul

:: --- Model Pipeline: M1->M2->M3 (port 8002) ---
echo [2/4] Starting ML Pipeline - M1->M2->M3 (port 8002)...
start "MLPipeline-M1M2M3" cmd /k "cd /d %~dp0hacky-backend && python -m uvicorn route_reliability_scoring.integration.pipeline:app --host 0.0.0.0 --port 8002 --reload"
timeout /t 3 /nobreak >nul

:: --- Unified API: Main Orchestrator (port 8000) ---
echo [3/4] Starting Unified API - Main Orchestrator (port 8000)...
start "UnifiedAPI-Orchestrator" cmd /k "cd /d %~dp0dynamic-rerouting\api && python -m uvicorn unified_api:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 3 /nobreak >nul

:: --- ML Backend: User App Image Analysis (port 8003) ---
echo [4/4] Starting ML Backend - Image Analysis (port 8003)...
start "MLBackend-UserApp" cmd /k "cd /d %~dp0user_app\rescue_connect\ml_backend && python -m uvicorn main:app --host 0.0.0.0 --port 8003 --reload"

echo.
echo =====================================================
echo   All services started! Check each terminal window.
echo =====================================================
echo.
echo   Model 1  (Traffic):      http://localhost:8001/docs
echo   ML Pipeline (M1+M2+M3): http://localhost:8002/docs
echo   Unified API (Main):      http://localhost:8000/docs
echo   ML Backend (User App):   http://localhost:8003/docs
echo.
echo   Flutter app: run 'flutter run' in
echo   Traffic_Model1\emergency_routing_flutter\
echo.
echo   Simulator (React): cd user_app\rescue_connect\simulator && npm run dev
echo   Authority (React): cd user_app\rescue_connect\authority && npm run dev
echo.
pause

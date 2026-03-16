#!/bin/bash
# ============================================================
#  Rescue Connect - Unified Startup Script (Linux/Mac)
#  Starts all services in the correct order:
#    Port 8001 - Model 1  (Traffic LSTM+GCN)
#    Port 8002 - Pipeline (Model 2 XGBoost + Model 3 DQN)
#    Port 8000 - Unified API (orchestrator + Supabase bridge)
#    Port 8003 - ML Backend (user app image analysis)
# ============================================================

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "====================================================="
echo "  RESCUE CONNECT - Starting All Services"
echo "====================================================="
echo ""

# --- Optional: set Supabase credentials ---
# Uncomment and fill in your values before running
# export SUPABASE_URL=https://your-project.supabase.co
# export SUPABASE_SERVICE_KEY=your-service-role-key

# --- Model 1: Traffic Prediction (port 8001) ---
echo "[1/4] Starting Model 1 - Traffic Prediction (port 8001)..."
cd "$REPO_ROOT/Traffic_Model1/emergency-routing-model1"
uvicorn inference.api:app --host 0.0.0.0 --port 8001 --reload &
M1_PID=$!
sleep 2

# --- Model Pipeline: M1->M2->M3 (port 8002) ---
echo "[2/4] Starting ML Pipeline - M1->M2->M3 (port 8002)..."
cd "$REPO_ROOT/hacky-backend"
uvicorn route_reliability_scoring.integration.pipeline:app --host 0.0.0.0 --port 8002 --reload &
PIPELINE_PID=$!
sleep 2

# --- Unified API: Main Orchestrator (port 8000) ---
echo "[3/4] Starting Unified API - Main Orchestrator (port 8000)..."
cd "$REPO_ROOT/dynamic-rerouting/api"
uvicorn unified_api:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!
sleep 2

# --- ML Backend: User App Image Analysis (port 8003) ---
echo "[4/4] Starting ML Backend - Image Analysis (port 8003)..."
cd "$REPO_ROOT/user_app/rescue_connect/ml_backend"
uvicorn main:app --host 0.0.0.0 --port 8003 --reload &
MLBACKEND_PID=$!

echo ""
echo "====================================================="
echo "  All services started!"
echo "====================================================="
echo ""
echo "  Model 1  (Traffic):      http://localhost:8001/docs"
echo "  ML Pipeline (M1+M2+M3): http://localhost:8002/docs"
echo "  Unified API (Main):      http://localhost:8000/docs"
echo "  ML Backend (User App):   http://localhost:8003/docs"
echo ""
echo "  Flutter: cd Traffic_Model1/emergency_routing_flutter && flutter run"
echo "  Simulator: cd user_app/rescue_connect/simulator && npm run dev"
echo "  Authority: cd user_app/rescue_connect/authority && npm run dev"
echo ""
echo "Press Ctrl+C to stop all services."
echo ""

# Wait and clean up on exit
trap "echo 'Stopping all services...'; kill $M1_PID $PIPELINE_PID $API_PID $MLBACKEND_PID 2>/dev/null; exit 0" INT TERM
wait

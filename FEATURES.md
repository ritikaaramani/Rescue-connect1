# Emergency Routing Engine: Integrated Feature List

This document summarizes the features implemented across the Unified Emergency Routing System, integrating **Model 1 (Traffic Forecasting)**, **Model 2 (Reliability Scoring)**, and **Model 3 (Dynamic Rerouting Agent)**.

## 🧠 AI-Driven Orchestration (Unified Backend)
- **Centralized FastAPI Hub**: A single orchestrator (`unified_api.py`) that unifies spatiotemporal prediction, XGBoost reliability scoring, and RL agent decisions.
- **Model 1: Spatiotemporal Forecast**: LSTM+GCN based congestion prediction for 5, 10, 20, and 30-minute intervals across key Indian cities.
- **Model 2: Route Reliability Scaling**: XGBoost-driven reliability classifier (0.0 to 1.0) predicting the stability of emergency corridors.
- **Model 3: RL Dynamic Rerouter**: Deep Q-Network (DQN) agent that performs real-time path optimization within SUMO simulations.
- **Intelligent Fallback**: Mathematical heuristics that ensure functionality even when local model checkpoints are missing.

## 🚑 Advanced Emergency Simulation (SUMO)
- **Emergency Pre-emption**: Automatic Traffic Light green-forcing as the ambulance approaches intersections.
- **Electronic Siren Simulation**: Civilian vehicleyielding and lane-clearing logic via TraCI.
- **Dynamic Blockage Handling**: API-driven road closure injection forcing immediate AI rerouting.
- **Patient Criticality logic**: High-criticality missions bypass standard safety constraints for maximum speed.
- **Weather Sensitivity**: Real-time scaling of maximum edge velocities based on rain/storm conditions.

## 📱 Mobile Experience (Flutter)
- **Unified Navigation Layer**: Connected to the Backend API for comprehensive route analysis.
- **Reliability Dashboard**: Real-time display of Reliability Scores and ETA confidence bands.
- **India-Factor Engine**: Detection of region-specific delays including:
  - Monsoon Waterlogging
  - Festival Processions (Diwali, Holi, Ganesh Chaturthi)
  - Wedding Season blocks
  - Market Day congestion
  - IPL Match traffic
- **Interactive Map**: Flutter Map integration with OSRM routing and AI-predicted overlays.

## 🏗️ Technical Capabilities
- **Standardized I/O**: JSON-based request/response structure for cross-language integration (Python/Dart).
- **Bangalore Real-World Layout**: SUMO configuration pre-set for Bangalore topologies using OpenStreetMap.
- **Latency Optimization**: Sub-10ms backend inference for real-time corridor management.

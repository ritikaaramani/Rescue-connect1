# 🚑 RescueConnect: Unified Emergency Routing System

![Emergency Routing System Overview](https://img.shields.io/badge/Status-Active-success)
![Platform](https://img.shields.io/badge/Platform-Flutter_|_FastAPI_|_SUMO-blue)
![AI Models](https://img.shields.io/badge/AI_Models-RL_(DQN)_|_LSTM+GCN_|_XGBoost-orange)

**RescueConnect** is a comprehensive, AI-driven emergency response orchestration platform specifically designed for complex, heterogeneous traffic environments in India. It integrates multi-platform mobile applications for Dispatch, Drivers, and Citizens with a robust FastAPI backend. Our core innovation lies in the deployment of Deep Reinforcement Learning (DQN), XGBoost, and Spatiotemporal Forecasting to manage real-time traffic gridlocks, automatically routing emergency vehicles dynamically. 

By minimizing traversal delays caused by monsoons, unorganized blockages, processions, and standard congestion, RescueConnect ensures that critical patients receive life-saving interventions within the golden hour.

---

## 🚀 Key Innovations & Features

### 🧠 3-Tier AI Architecture
1. **Model 1: Spatiotemporal Forecast:** Utilizes LSTM + GCN architectures to predict upcoming congestion dynamically for 5, 10, 20, and 30-minute intervals. 
2. **Model 2: Route Reliability Scoring:** An XGBoost-driven reliability classifier evaluating corridors on a 0.0 to 1.0 confidence scale. It accounts for real-time delays, historical traffic behaviors, and localized disruptions.
3. **Model 3: RL Dynamic Rerouter (DQN Agent):** An autonomous Deep Q-Network agent navigating real-time path optimizations within the SUMO (Simulation of Urban MObility) environment. Adapts mid-route to sudden obstacles instantly.

### 🚗 Advanced SUMO Integration & Traffic Simulation
* **Emergency Pre-emption:** Automatic traffic light green-forcing as the ambulance approaches intersections.
* **Electronic Siren Simulation:** Emulation of civilian vehicle yielding and lane-clearing logic via TraCI protocols.
* **Dynamic Blockages:** Instant injection of road closures (due to simulated accidents, waterlogging, or processions), forcing our RL agent into split-second rerouting.
* **Hyper-Realistic Physics:** Real-time calculation of vehicle telemetry, taking weather scenarios into account (e.g., speed capping during storms).
* **Patient Criticality logic:** High-criticality missions bypass standard safety constraints for maximum speed.

### 📱 Triple-Interface Mobile Experience (Integrated via Flutter)
* **Citizen Mode:** Intuitive incident reporting dashboard.
* **Dispatcher Dashboard:** A command-center view over incidents, fleet deployment, and real-time tracking.
* **Ambulance / Driver HUD:** Live GPS positioning, OSRM routing, AI-predicted problem alerts, ETA confidence bands, and Reliability scores seamlessly overlaying the map.

### 🇮🇳 The "India-Factor" Engine
RescueConnect specifically models delays standard routing engines ignore:
* Monsoon Waterlogging
* Festival Processions (Diwali, Holi, Ganesh Chaturthi)
* Wedding Season street congestion
* Market day density and IPL match externalities.

---

## 📁 Repository Structure and Module Breakdown

The system breaks down into modular, independently scalable domains:

| Module Path | Description |
|---|---|
| `/dynamic-rerouting/` | The SUMO simulation and RL (DQN) engine backend. Contains the `unified_api.py` orchestrator, TraCI logic, environment rendering, and Bangalore geospatial configs (`.net.xml`, `.osm`). |
| `/user_app/` | Flutter-based end-user applications for the 3 core personas. Integrates GenAI handlers (Groq/Gemini LLMs) for incident parsing, OCR modules, and Supabase database integrations. |
| `/hacky-backend/` & `/Traffic_Model1/` | Traffic Spatiotemporal forecasting microservices. |
| `/route-reliability-scoring/` | Jupyter notebooks and model definitions for our XGBoost corridor reliability algorithms. |

---

## ⚡ Quick Start & Full Integration Demo (5 Minutes)

Launch our complete simulation locally, watch an ambulance deploy, witness a random AI-generated blockage, and observe the DQN agent instantaneously calculate and assign a new path.

### **Step 1: Start the Core Intelligence & SUMO Backend**
This launches the FastAPI Orchestrator, begins the websocket pipeline, and initializes the Traffic Simulation.
```powershell
# Open terminal 1
cd "dynamic-rerouting"
pip install -r requirements.txt
python startup.py
```
*(Runs on localhost:8000. Wait for the terminal to print backend logs.)*

### **Step 2: Start the Flutter Frontend Dashboard**
Launch the Mobile App directly in your browser.
```powershell
# Open terminal 2
cd "Traffic_Model1/emergency_routing_flutter"
flutter pub get
flutter run -d chrome
```

### **Step 3: Run the Live Scenario**
1. Once the Browser opens (`http://localhost:8080`), click into **DISPATCH CENTER**.
2. Wait for an initial incident to populate, then click **DISPATCH NOW**.
3. Watch the map focus on a moving vehicle marker pulsing at 2Hz updates. Follow its path intuitively.
4. **The Rerouting Event:** Within 2-4 minutes, our `blockage_simulator` automatically strikes a segment of the current path with an obstacle. The system identifies it within 30 seconds and autonomous route correction engages.
5. The UI updates natively (Green line = Traveled, Orange line = Planned, Cyan = Newly Rerouted).

> **Troubleshooting the Demo:** If blockages don't spawn naturally, force one manually:
> `curl -X POST "http://localhost:8000/blockages/create?lat=22.75&lon=75.89&segment_name=Main%20St&blockage_type=accident"`

---

## 📡 Live Endpoints & API Architecture

RescueConnect's Orchestrator (`unified_api.py`) runs 25+ real-time endpoints.
* **`WS /v1/ws/vehicle/{id}`**: 2 Hz geospatial telemetry stream.
* **`POST /incidents`**: Central event ingestion.
* **`GET /incidents/{incident_id}/route`**: Triggers ML route extraction and reliability checks.
* **`POST /blockages/create`**: Injects live obstacles to the simulation state.

Standardized JSON schemas ensure smooth I/O transfer between Python Data models and Dart/Flutter rendering loops.

---

## 🛠 Tech Stack

*   **Machine Learning:** PyTorch (DQN RL Agent), XGBoost, Scikit-Learn
*   **Routing & Simulation:** SUMO, TraCI Interface, OSRM.
*   **Backend Servers:** Python 3, FastAPI, Uvicorn, Websockets.
*   **Frontend Ecosystem:** Flutter, Dart, Flutter_Map SDK.
*   **Database & LLM integrations:** SQLite, Supabase, Groq/Gemini GenAI for Natural Language processing of Citizen reports.

---

## 📊 Evaluation & System Metrics

Our dual-system model successfully minimizes backend inference block-times. Sub-10ms logic resolution enables high-frequency client mapping with virtually no jitter. The mathematical fallback layers included locally guarantee functioning fallback routes in case of main network fragmentation in critical emergency scenarios.

---

**Developed for cutting-edge Emergency Medical Logistics.** 🚀
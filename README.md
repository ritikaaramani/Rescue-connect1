# 🚑 RescueConnect: Unified Emergency Routing System

RescueConnect is a comprehensive, AI-driven emergency response orchestration platform. It integrates cross-platform mobile apps for dispatch, drivers, and citizens with a powerful FastAPI backend and deep-learning traffic and routing simulations.

## 🚀 Key Features

*   **Real-Time Vehicle Tracking:** 2 Hz geospatial updates streamed via WebSockets to all connected clients.
*   **Dynamic Rerouting Agent (Model 3):** An Deep Q-Network (DQN) agent manages real-time path optimization within live SUMO (Simulation of Urban MObility) environments.
*   **Traffic Forecasting (Model 1):** Spatiotemporal models (LSTM+GCN) to predict upcoming gridlock dynamically up to 30 minutes in advance.
*   **Route Reliability Scoring (Model 2):** XGBoost-driven classifier identifying corridor stability based on time, event, weather, and traffic conditions.
*   **Intelligent Blockage Handling:** Automatically adapts to simulated accidents and sudden delays in real-time, recalculating ETA and new routes under 100ms.
*   **3-Tier Mobile Interfaces (Flutter):** Fully functional interfaces for Dispatch Centers, Ambulances/Vehicles, and Citizens to communicate seamlessly.
*   **India-Factor Engine:** Understands and correctly prices delays native to India, including monsoons, market congestion, and festival processions.

---

## 📁 System Architecture & Modules

The repository covers all components required for end-to-end usage:
*   `dynamic-rerouting/`: Our SUMO and RL-based Dynamic Routing backend (`unified_api.py`) featuring DQN-based path analysis and map configuration. Includes our core API orchestration.
*   `user_app/`: End-user mobile applications and ML implementations (OCR, Gemini/Groq LLM backends).
*   `hacky-backend/` & `Traffic_Model1/`: Additional integration routes bridging mobile endpoints to simulation traffic states.
*   `route-reliability-scoring/`: Jupyter notebooks implementing our XGBoost routing reliability classifier.

---

## ⚡ Quick Start Demo (2 Steps)

### **Step 1: Start the Backend Orchestrator**
```bash
cd dynamic-rerouting
pip install -r requirements.txt
python startup.py
```
*(Runs the FastAPI Hub over port 8000, starts SUMO simulation, and begins WebSocket propagation).*

### **Step 2: Start the Mobile Application**
```bash
cd user_app/main-el
flutter pub get
flutter run -d chrome
```

---

## 🎮 Running the Simulation 

1. Once the application loads, select **DISPATCH CENTER**.
2. Wait for a simulated incident and click **DISPATCH NOW**.
3. The platform will automatically launch a simulated vehicle connected directly to the Flutter frontend map natively.
4. **Observe Real-Time Dynamics:** In 2-4 minutes, the `blockage_simulator` injects a traffic accident. The DQN monitoring script identifies this anomaly and triggers autonomous rerouting instructions straight to the simulation.

## 🤝 Integrations & Technologies

*   **Backend:** Python 3, FastAPI, SUMO/TraCI, SQLite/Supabase, WebSockets
*   **AI/ML:** XGBoost, Scikit-Learn, PyTorch (DQN), Groq/Gemini/OpenAI GenAI handlers.
*   **Frontend:** Flutter/Dart, Flutter Map, OSRM.

*This system ensures high-criticality missions can bypass standard routing conventions to achieve unprecedented rescue speed, adapting instantaneously to rapidly changing city environments.*
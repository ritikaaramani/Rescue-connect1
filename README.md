# 🚑 RescueConnect: Unified Emergency Response System

![Platform](https://img.shields.io/badge/Platform-React_|_Flutter_|_FastAPI_|_SUMO-blue)
![AI Models](https://img.shields.io/badge/AI_Models-RL_(DQN)_|_LSTM+GCN_|_XGBoost_|_YOLO+Tesseract_|_Gemini-orange)

**RescueConnect** is a comprehensive, AI-driven emergency response orchestration platform. The system operates autonomously through a 3-Layer pipeline—starting from the moment a citizen posts an incident on social media, all the way to a system-guided ambulance navigating unpredictable city traffic using Deep Reinforcement Learning.

---

## 🏗️ The 3-Layer Architecture

RescueConnect is built chronologically across three distinct modules:

### 📱 Layer 1: Incident Detection & Reporting (The Simulator App)
Before an ambulance can be dispatched, the incident must be detected. This layer mimics crowdsourced intelligence and social media pipelines.
*   **The Interface:** A React-based citizen reporting app (`user_app/rescue_connect/simulator`).
*   **Functionality:** Allows citizens to upload photos, provide brief captions, and submit SOS reports (mimicking a social media feed like X or Instagram). 
*   **Data Ingestion:** Pushes unfiltered visual and textual data directly to the Supabase database.

### 🧠 Layer 2: Analysis & Authority Dashboard (ML Backend)
Raw citizen reports are useless without context. This layer serves as the "brain" for parsing, validating, and geolocating unstructured data. 
*   **The ML Pipeline (`user_app/rescue_connect/ml_backend`):** A FastAPI backend built to dissect the incoming Simulator posts.
    *   **Image Analysis:** Employs **Gemini Vision/Groq** to automatically classify the disaster (e.g., *Urban Flooding*, *Fire*, *Riot*).
    *   **OCR Pipeline:** Utilizes **YOLO + Tesseract OCR** to extract text from user-uploaded images (e.g., reading street signs in a flooded intersection or a shop name in the background).
    *   **NLP & Geolocation:** Uses **spaCy NER** to parse the post's caption and OCR results, cross-referencing OS Nominatim APIs to infer highly precise lat/long coordinates.
*   **Authority Dashboard (`user_app/rescue_connect/authority`):** A React-based command center for dispatchers. It maps validated incidents, displays AI "urgency scores" (1-10), and gives the dispatcher the 1-click power to hit **"DISPATCH NOW"**.

### 🚗 Layer 3: Dynamic Routing & Orchestration (SUMO Pipeline)
Once the Dispatcher validates the AI's findings in Layer 2 and deploys a vehicle, Layer 3 takes over to actually get the emergency vehicle to the scene.
*   **The Orchestrator:** Powered by FastAPI (`dynamic-rerouting/unified_api.py`) bridging the Flutter app with SUMO (Simulation of Urban MObility). 
*   **Traffic Forecasting (Model 1):** Spatiotemporal models (LSTM + GCN) predict congestion 5–30 mins out.
*   **Reliability Scoring (Model 2):** XGBoost evaluates current traffic to score corridor stability.
*   **Dynamic Rerouter (Model 3 - DQN Agent):** A deep reinforcement learning agent that instantaneously calculates detours in real-time if a simulated blockage, monsoon delay, or accident suddenly blocks the ambulance. Updates stream at 2 Hz via WebSockets directly into the Driver and Citizen Flutter App.

---

## 📁 Repository Structure and Module Breakdown

| Module Domain | Sub-Module | Description |
|---|---|---|
| **Layer 1 & 2** | `/user_app/rescue_connect/simulator/` | React app for end-users to simulate social media disaster posts. |
| **Layer 1 & 2** | `/user_app/rescue_connect/ml_backend/`| FastAPI server running YOLO, Tesseract, and Gemini for visual/text disaster extraction. |
| **Layer 1 & 2** | `/user_app/rescue_connect/authority/` | React dashboard for parsing AI-verified reports and dispatching fleets. |
| **Layer 3** | `/dynamic-rerouting/` | SUMO simulation and RL (DQN) engine backend. Contains TraCI logic and Bangalore geospatial routing (`.net.xml`). |
| **Layer 3** | `/Traffic_Model1/emergency_routing_flutter/` | Flutter app showing Live GPS positioning, OSRM routing, and 2Hz web socket updates. |

---

## ⚡ Quick Start & Full Integration Demo (10 Minutes)

Run the full pipeline from Citizen Report to Ambulance Rerouting.

### **Step 1: Start Layer 1 & 2 (Incident Generation & ML)**
Ensure your `user_app/rescue_connect/ml_backend/.env` has your valid API keys (Supabase, Gemini/Groq).
```bash
# Terminal 1: ML Backend
cd user_app/rescue_connect/ml_backend
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python main.py  # Runs on port 8000

# Terminal 2: Connect the Authority Dashboard
cd user_app/rescue_connect/authority
npm install && npm run dev  # Runs on port 5173

# Terminal 3: Setup the Citizen Simulator
cd user_app/rescue_connect/simulator
npm install && npm run dev  # Runs on port 5174
```
*Open Port 5174, create a disaster post (upload an image). Open Port 5173 to watch the ML backend parse text, geolocation, lock an Urgency Score, and prepare to dispatch.*

### **Step 2: Start Layer 3 (Routing & SUMO)**
Deploy our Core Intelligence & Traffic Simulation.
```bash
# Terminal 4
cd dynamic-rerouting
pip install -r requirements.txt
python startup.py
```

### **Step 3: Start the Flutter Vehicle Dashboard**
Open the Flutter app directly in your browser.
```bash
# Terminal 5
cd Traffic_Model1/emergency_routing_flutter
flutter pub get
flutter run -d chrome
```

### **Step 4: The Live Scenario**
1. Dispatch an incident from the Authority Dashboard (Layer 2) which talks to Layer 3. 
2. In the Flutter App, click the map to view the auto-assigned route.
3. **The Rerouting Event:** Within 2-4 minutes, our SUMO `blockage_simulator` automatically hits the route with an obstacle (e.g., simulating a sudden procession). 
4. The system identifies it within 30 seconds, autonomous route correction initiates (DQN agent), and the vehicle's new route flashes on the Flutter Map instantly (Green line = Traveled, Orange line = Planned, Cyan = Newly Rerouted).

---

## 🛠 Tech Stack Overview

*   **Machine Learning (Vision & NLP):** YOLO, Tesseract OCR, spaCy NER, Google Gemini Vision
*   **Machine Learning (Routing):** PyTorch (DQN RL Agent), XGBoost, Scikit-Learn
*   **Routing Simulator:** SUMO, TraCI Interface, OSRM
*   **Backends:** FastAPI, Python, WebSockets
*   **Frontends:** React, Vite (Web User/Authority Apps); Flutter, Dart (Cross-Platform Driver UI)
*   **Database:** Supabase (PostgreSQL)
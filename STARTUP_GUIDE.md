# Startup & Testing Guide

Follow these steps to run the integrated Emergency Routing System.

## 1. Prerequisites
- **Python**: Installed (3.12+ recommended).
- **SUMO**: Installed and `SUMO_HOME` environment variable set.
- **Flutter**: Installed and environment set up.

## 2. Start the Unified Backend
The backend unifies all three models and listens on port 8000.

```powershell
# Navigate to the dynamic-rerouting directory
cd "c:\Ritika\indore hacky\dynamic-rerouting"

# Activate your virtual environment
.\venv\Scripts\activate

# Install dependencies if you haven't already
pip install -r "c:\Ritika\indore hacky\REQUIREMENTS.txt"

# Run the Unified API
python .\api\unified_api.py
```
*The API is now live at `http://127.0.0.1:8000`. You can check `http://127.0.0.1:8000/health` in your browser.*

## 3. Run the Flutter App
```powershell
# Navigate to the Flutter project
cd "c:\Ritika\indore hacky\Traffic_Model1\emergency_routing_flutter"

# Get dependencies
flutter pub get

# Launch on your preferred device (Chrome, Emulator, or Windows)
flutter run -d chrome
```

## 4. How to Test
1.  **Dashboard Verification**: In the Flutter app, go to the **Dashboard** screen. Tap **"PREDICT ALL CITIES"**. You should see live congestion forecasts.
2.  **Reliability Check**: Observe the **"Route Reliability Scaling"** card. It now pulls live algorithmic scores from Model 2.
3.  **API Manual Test**: Run this command in a new terminal to verify reaching the orchestrator directly:
    ```powershell
    Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/route/comprehensive" -ContentType "application/json" -Body '{"origin": [28.6139, 77.2090], "destination": [28.5355, 77.3910], "city_name": "Delhi", "weather": "Rain"}'
    ```

## 5. Emergency Simulation Demo
To see the RL Agent (Model 3) with full pre-emption and siren logic in action:
```powershell
cd "c:\Ritika\indore hacky\dynamic-rerouting"
.\venv\Scripts\activate
python .\agent\evaluate_emergency.py
```

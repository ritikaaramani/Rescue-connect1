# 🚀 Quick Start Guide - Emergency Response Platform

## ⚡ 30-Second Setup

```bash
cd "c:\Ritika\indore hacky\dynamic-rerouting"
python startup.py
```

Server will start at: **http://localhost:8000**

---

## 📱 3-App Demo Setup (5 minutes)

### Terminal 1: Start Backend API
```bash
cd dynamic-rerouting
python startup.py
```
**Expected Output:**
```
✅ All checks passed
Starting Emergency Response Platform...
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Terminal 2: Dispatch Dashboard WebSocket
```bash
python -c "
import asyncio, websockets, json
async def ws():
    async with websockets.connect('ws://localhost:8000/ws/dispatch') as w:
        while 1:
            m = json.loads(await w.recv())
            print(f'📨 {m[\"type\"]}: {json.dumps(m, indent=2)[:300]}...')
asyncio.run(ws())
"
```

### Terminal 3: Vehicle App WebSocket
```bash
python -c "
import asyncio, websockets, json
async def ws():
    async with websockets.connect('ws://localhost:8000/ws/vehicle/UP-14-342') as w:
        while 1:
            m = json.loads(await w.recv())
            print(f'📢 {m[\"type\"]}: {json.dumps(m, indent=2)[:300]}...')
asyncio.run(ws())
"
```

### Terminal 4: Trigger Dispatch (in PowerShell)
```powershell
# Create incident
$incident = @{
    id = "INC-demo-001"
    reporter_id = "CITIZEN-001"
    location = @(22.7400, 75.8950)
    type = "accident"
    severity = 8
    description = "Multi-vehicle collision at Bhawarkuan Square"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8000/incident/report" `
  -Method POST -ContentType "application/json" -Body $incident

# Dispatch ambulance
Invoke-WebRequest -Uri `
  "http://localhost:8000/dispatch/comprehensive?incident_id=INC-demo-001&vehicle_id=UP-14-342&vehicle_start_lat=22.7533&vehicle_start_lon=75.8937&incident_lat=22.7400&incident_lon=75.8950&hospital_id=H-1&hospital_lat=22.7533&hospital_lon=75.8937" `
  -Method POST
```

---

## 📊 What You'll See

### Terminal 2 (Dispatch):
```
📨 INCIDENT_UPDATE: {
  "id": "INC-demo-001",
  "state": "DISPATCHED",
  "location": {"lat": 22.74, "lon": 75.895},
  ...
}
📨 VEHICLE_UPDATE: {
  "id": "UP-14-342",
  "lat": 22.7533,
  "lon": 75.8937,
  "speed_kmh": 65.0,
  "eta_minutes": 7.5,
  ...
}
📨 VEHICLE_UPDATE: {
  "id": "UP-14-342",
  "lat": 22.75352,
  "lon": 75.89355,
  "speed_kmh": 65.2,
  "eta_minutes": 7.4,
  ...
} [Updates every 0.5 seconds]
📨 REROUTE: {
  "vehicle_id": "UP-14-342",
  "old_eta_min": 8.0,
  "new_eta_min": 6.0,
  "reason": "Dynamic optimization - traffic ahead"
} [After ~30 seconds]
```

### Terminal 3 (Vehicle):
- Same messages, indicating vehicle receives all updates
- Driver sees: navigation map animates, ETA updates in real-time
- When reroute received, route map changes, NEW ETA displayed

---

## 🔗 API Endpoints Quick Reference

### Core Endpoints
- `POST /incident/report` - Report new incident
- `GET /hospitals/nearest?lat={lat}&lon={lon}` - Find nearest hospitals
- `POST /dispatch/comprehensive` - **Main** dispatch workflow
- `GET /incident/{id}/scene` - Get Digital Emergency Scene

### Simulation
- `POST /vehicle/start-simulation` - Start vehicle movement
- `GET /vehicle/{vehicle_id}/position` - Get current position
- `POST /vehicle/stop-simulation` - Stop vehicle

### Rerouting
- `POST /rerouting/evaluate` - Evaluate route alternatives
- `GET /ws/stats` - WebSocket connection stats

### Testing
- `GET /test/demo/full-flow` - Complete demo workflow
- `GET /test/demo/sample-incident` - Sample incident data
- `GET /test/demo/flow-diagram` - Visual flow diagram

---

## 📡 WebSocket Endpoints

| Endpoint | Role | Purpose |
|----------|------|---------|
| `ws://localhost:8000/ws/dispatch` | Dispatch | Receives all incident & vehicle updates |
| `ws://localhost:8000/ws/vehicle/{vehicle_id}` | Vehicle | Driver receives navigation & mission updates |
| `ws://localhost:8000/ws/citizen` | Citizen | Reports receive incident updates |

---

## 🧪 Single-Command Demo

Run everything at once:

```python
# demo.py
import subprocess
import webbrowser
import time

# Terminal 1: API
subprocess.Popen(['python', 'startup.py'])
time.sleep(3)

# Open documentation
webbrowser.open('http://localhost:8000/docs')

# Terminal 2-4: WebSockets
print("✅ API started at http://localhost:8000")
print("✅ Swagger UI opened")
print("✅ Ready for WebSocket connections")
```

---

## 🎯 Demo Talking Points

### What's Different from Your Existing System

| Feature | Before | Now |
|---------|--------|-----|
| **Real-Time Updates** | ❌ Polling | ✅ WebSockets (< 100ms latency) |
| **Dynamic Rerouting** | ❌ Static routes | ✅ DQN-powered, every 30s |
| **Visualization** | ❌ Static snapshots | ✅ Live vehicle animation |
| **Witness Reports** | ❌ Text only | ✅ Photos + Google Vision location inference |
| **Shared Incident Data** | ❌ Per-app silos | ✅ Digital Emergency Scene |
| **Vehicle Simulation** | ❌ Mock positions | ✅ Realistic movement with ETA tracking |

### Core Strength: **Dynamic Rerouting**

1. **Every 30 seconds**, system checks:
   - Current vehicle position
   - Traffic ahead
   - Alternative routes

2. **DQN model decides**: "Is alternative route better?"
   - Compares: ETA, reliability, congestion
   - **Action**: MAINTAIN or REROUTE

3. **If rerouting triggered**:
   - New route sent to vehicle
   - Driver sees map update
   - ETA changes (usually improves)
   - All clients notified in real-time

---

## 🐛 Troubleshooting

### "ModuleNotFoundError"
```bash
pip install -r requirements.txt
```

### "Connection refused" (WebSocket)
```bash
# Make sure API is running
curl http://localhost:8000/health
```

### "No module named 'models'"
```bash
# Run from correct directory
cd dynamic-rerouting/api
python -m uvicorn unified_api:app --reload
```

---

## 📚 Full Documentation

See [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md) for:
- Complete architecture
- All service descriptions
- Message format specification
- Database schema
- Production deployment

---

## ✅ Pre-Demo Checklist

- [ ] Python 3.8+ installed: `python --version`
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] API server starts: `python startup.py`
- [ ] Swagger UI opens: http://localhost:8000/docs
- [ ] WebSocket endpoint(s) respond: `curl http://localhost:8000/ws/stats`
- [ ] Sample incident created: `curl GET http://localhost:8000/test/demo/sample-incident`
- [ ] Test dispatch flow works

---

## 🎬 Live Demo Script (5 minutes)

**Time: 0:00 - Setup**
- Start API server
- Open Swagger UI
- Show WebSocket stats: 0 connections

**Time: 1:00 - Create Incident**
- POST to `/incident/report`
- Create: "Multi-vehicle accident at Main St"
- Show: Incident created, ID: INC-{timestamp}

**Time: 1:30 - Find Hospital**
- GET `/hospitals/nearest?lat=22.74&lon=75.895`
- Show: Apollo Hospital selected (5 ICU beds, 1.2 km away)

**Time: 2:00 - Dispatch Vehicle**
- POST to `/dispatch/comprehensive`
- Show: "Dispatching UP-14-342 ambulance"
- WebSocket stats now show: 1 dispatch, 1 vehicle connection

**Time: 2:30 - Watch Live Updates**
- Terminal 2 shows: VEHICLE_UPDATE messages flowing every 0.5s
- Vehicle moving on map (if integrated with Flutter)
- ETA: 8 min → 7:45 → 7:30 → ...

**Time: 3:30 - Trigger Rerouting**
- After ~30 seconds of movement
- Reroute notification appears
- Old ETA: 8 min → New ETA: 6 min
- All clients updated instantly

**Time: 4:30 - Show Witness Integration**
- POSTanother citizen report (aggregated nearby)
- Witness count increases
- Google Vision detected: "Apollo Hospital" landmark

**Time: 5:00 - Conclusion**
- Sum up: Real-time, dynamic, intelligent routing
- Show: All 3 interfaces working in sync via WebSockets
- Future: Scale to multiple incidents, vehicles, cities

---

## 🚀 Production Roadmap

After hackathon, to be production-ready:

1. **Database**: Migrate to PostgreSQL (Docker container)
2. **Security**: Add JWT authentication, API rate limiting
3. **Monitoring**: Prometheus metrics, error tracking (Sentry)
4. **Scaling**: Load balancing, multi-server WebSocket mesh
5. **Mobile**: Complete Flutter app UI refinement
6. **Mapping**: Integrate Mapbox/OSM for real maps
7. **SUMO Integration**: Connect to actual traffic simulator
8. **Load Testing**: 100+ concurrent vehicles, incidents

---

**🎉 You're ready to demo!**

Questions? See IMPLEMENTATION_GUIDE.md or check test endpoints at /test/

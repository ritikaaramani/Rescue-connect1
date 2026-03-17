import os
import time
import logging
import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from enum import Enum
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np
import copy
from sqlalchemy.orm import Session
import httpx

# Add parent directory to path  
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Try to load .env from the React Authority app
env_path = os.path.join(Path(__file__).parent.parent.parent, "user_app", "rescue_connect", "authority", ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
    
# Alias variables if they use the VITE_ prefix
if not os.environ.get("SUPABASE_URL") and os.environ.get("VITE_SUPABASE_URL"):
    os.environ["SUPABASE_URL"] = os.environ.get("VITE_SUPABASE_URL")
if not os.environ.get("SUPABASE_SERVICE_KEY") and os.environ.get("VITE_SUPABASE_ANON_KEY"):
    os.environ["SUPABASE_SERVICE_KEY"] = os.environ.get("VITE_SUPABASE_ANON_KEY")

# Import new modules
from websocket_manager import manager
from incident_service import IncidentService
from vehicle_simulator import simulation_daemon, GeoCalc
from models.db_schema import create_db_engine, init_db, Vehicle as VehicleDB, Hospital as HospitalDB
from orchestrator import orchestrator
from location_inference import location_inference_service
from dqn_rerouting_service import dqn_rerouting_service
from blockage_simulator import blockage_simulator, BlockageType
from test_integration import router as test_router
from supabase_bridge import supabase_bridge

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("UnifiedAPI")

# Database setup
try:
    db_engine = create_db_engine(use_postgres=True)
    init_db(db_engine)
except Exception as e:
    logger.warning(f"Database initialization failed: {e}. Using in-memory fallback.")
    db_engine = None

def get_db():
    """FastAPI dependency for getting DB session."""
    if db_engine is None:
        return None
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=db_engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(
    title="Unified Emergency Routing AI Orchestrator",
    description="Level 4 Autonomous Emergency Response System - Model Unification Brain",
    version="1.5.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Include test integration router
app.include_router(test_router)

# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

# --- State Enums ---
class IncidentState(str, Enum):
    REPORTED = "REPORTED"
    VERIFIED = "VERIFIED"
    DISPATCHED = "DISPATCHED"
    EN_ROUTE = "EN_ROUTE"
    ON_SCENE = "ON_SCENE"
    PATIENT_PICKED = "PATIENT_PICKED"
    COMPLETED = "COMPLETED"

class VehicleState(str, Enum):
    AVAILABLE = "AVAILABLE"
    DISPATCHED = "DISPATCHED"
    EN_ROUTE = "EN_ROUTE"
    AT_SCENE = "AT_SCENE"
    TRANSPORTING = "TRANSPORTING"
    RETURNING = "RETURNING"
    OFFLINE = "OFFLINE"

class UnifiedRoutingRequest(BaseModel):
    origin: List[float]  # [lat, lon]
    destination: Optional[List[float]] = None # Optional if finding hospital
    city_name: str
    emergency_type: str = "ambulance"
    criticality: str = "High"
    weather: str = "Clear"
    patient_id: Optional[str] = "P-102"

class IndiaFactor(BaseModel):
    name: str
    emoji: str
    delay_multiplier: float
    description: str

class Hospital(BaseModel):
    id: str
    name: str
    location: List[float]
    icu_beds_available: int
    trauma_specialty: bool
    distance_km: float = 0.0

class WitnessReport(BaseModel):
    reporter_id: str
    media_url: Optional[str] = None
    hazard_tags: List[str] = []
    text_notes: str = ""
    has_photo: bool = False

class IncidentReport(BaseModel):
    id: str
    reporter_id: str
    location: List[float]
    type: str # accident, pothole, protest
    severity: int # 1-10
    timestamp: str
    state: IncidentState = IncidentState.REPORTED
    assigned_vehicle_id: Optional[str] = None
    witness_reports: List[WitnessReport] = []
    
    # Shared Dashboard Fields
    video_feed_url: Optional[str] = None
    ambulance_eta_min: Optional[int] = None
    patient_condition: Optional[str] = "Stable"
    assigned_hospital_id: Optional[str] = None

class MLPipelineRequest(BaseModel):
    start: str = "hospital"
    destination: str = "accident_location"
    city: str = "Bengaluru"
    vehicle_id: str = "ambulance_01"
    current_speed: float = 25.0
    remaining_distance: float = 5200.0
    weather_coeff: float = 1.0

class UnifiedRoutingResponse(BaseModel):
    status: str
    city: str
    standard_eta_min: float
    ai_eta_min: float
    reliability_score: float
    confidence_interval: List[float]
    recommended_route_id: str
    active_factors: List[IndiaFactor]
    recommended_lane: str
    reasoning: str
    prediction_timestamp: str
    latency_ms: float

# ---------------------------------------------------------------------------
# Mock Data Store (In-Memory for Demo)
# ---------------------------------------------------------------------------

MOCK_HOSPITALS = [
    {"id": "H-1", "name": "Indore Apollo Hospital", "location": [22.7533, 75.8937], "icu_beds_available": 5, "trauma_specialty": True},
    {"id": "H-2", "name": "CHL Hospital", "location": [22.7441, 75.8901], "icu_beds_available": 2, "trauma_specialty": True},
    {"id": "H-3", "name": "Medanta Super Specialty", "location": [22.7600, 75.9000], "icu_beds_available": 12, "trauma_specialty": True},
    {"id": "H-4", "name": "Bombay Hospital Indore", "location": [22.7500, 75.9100], "icu_beds_available": 0, "trauma_specialty": False},
]

INCIDENT_LOG = []
MESSAGE_LOG = [
    {"from": "Dispatcher", "msg": "Ambulance UP-14-342, proceed to Sector 5.", "time": "10:00 AM"},
    {"from": "Driver", "msg": "En route. Weather is turning rainy.", "time": "10:02 AM"},
]

# ---------------------------------------------------------------------------
# Core Logic
# ---------------------------------------------------------------------------

def calculate_reliability_score(features: Dict[str, Any]) -> float:
    score = 0.95
    congestion = features.get("congestion", 0.3)
    score -= (congestion * 0.4)
    weather = features.get("weather", "Clear")
    weather_map = {"Clear": 0.0, "Rain": 0.15, "Fog": 0.1, "Storm": 0.2}
    score -= weather_map.get(weather, 0.0)
    
    # Impact of crowdsourced incidents
    recent_incidents = [i for i in INCIDENT_LOG if i["severity"] > 7]
    if recent_incidents:
        score -= (0.05 * len(recent_incidents))
        
    if features.get("criticality") == "High":
        score += 0.05
    return max(0.4, min(0.98, round(score, 2)))

def get_traffic_forecast(city: str) -> Dict[str, float]:
    base = 0.45 if city in ["Delhi", "Mumbai", "Bengaluru", "Indore"] else 0.3
    return {"t5": base, "t10": base+0.05, "t30": base+0.15}

def detect_india_factors(city: str, weather: str) -> List[IndiaFactor]:
    factors = []
    factors.append(IndiaFactor(name="Rush Hour", emoji="🕐", delay_multiplier=1.25, description="Peak office traffic"))
    if weather in ["Rain", "Storm"]:
        factors.append(IndiaFactor(name="Water Logging", emoji="🌧️", delay_multiplier=1.4, description="Major monsoon delay"))
    return factors

def calculate_distance(p1, p2):
    return np.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2) * 111.0 # Rough km

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "online", "models": ["M1-Traffic", "M2-Reliability", "M3-RL"], "version": "1.5.0-HIFI"}

@app.get("/hospitals/nearest", response_model=List[Hospital])
async def get_nearest_hospitals(lat: float, lon: float):
    """Finds best hospitals based on proximity and ICU availability."""
    results = []
    for h in MOCK_HOSPITALS:
        dist = calculate_distance([lat, lon], h["location"])
        results.append(Hospital(**h, distance_km=round(dist, 2)))
    
    # Sort by beds available (priority) then distance
    results.sort(key=lambda x: (-x.icu_beds_available, x.distance_km))
    return results[:3]

@app.post("/incident/report")
async def report_incident(report: IncidentReport):
    """Crowdsourced incident reporting point with Smart Witness Aggregation."""
    # Check for existing incident within ~200m
    # Rough approximation: 1 deg lat/lon is ~111km, so 200m is ~0.0018 deg
    for inc in INCIDENT_LOG:
        if inc.state in [IncidentState.REPORTED, IncidentState.VERIFIED, IncidentState.DISPATCHED]:
            dist_km = calculate_distance(report.location, inc.location)
            if dist_km < 0.2:  # Less than 200m
                # Aggregate as a witness report
                wit = WitnessReport(
                    reporter_id=report.reporter_id,
                    text_notes=f"Aggregated report of type: {report.type}",
                    hazard_tags=[report.type]
                )
                inc.witness_reports.append(wit)
                logger.info(f"Aggregated report {report.id} into existing incident {inc.id}")
                return {"status": "success", "message": "Report aggregated into nearby existing incident", "incident_id": inc.id}
    
    # Otherwise, create new incident
    INCIDENT_LOG.append(report)
    logger.info(f"New Incident Created: {report.type} at {report.location} (ID: {report.id})")
    return {"status": "success", "message": "Incident logged. All AI models notified.", "incident_id": report.id}

@app.post("/witness/report/{incident_id}")
async def add_witness_report(incident_id: str, report: WitnessReport):
    for inc in INCIDENT_LOG:
        if inc.id == incident_id:
            inc.witness_reports.append(report)
            return {"status": "success", "message": "Witness report attached"}
    raise HTTPException(status_code=404, detail="Incident not found")

@app.post("/vehicle/assign")
async def assign_vehicle(incident_id: str, vehicle_id: str):
    for inc in INCIDENT_LOG:
        if inc.id == incident_id:
            inc.assigned_vehicle_id = vehicle_id
            inc.state = IncidentState.DISPATCHED
            # Usually we'd update vehicle state too
            MESSAGE_LOG.append({"from": "Dispatcher", "msg": f"Vehicle {vehicle_id} assigned to incident {incident_id}", "time": time.strftime("%H:%M")})
            return {"status": "success", "message": f"Vehicle {vehicle_id} dispatched."}
    raise HTTPException(status_code=404, detail="Incident not found")

@app.get("/incidents/active")
async def get_active_incidents():
    """Fetch active incidents directly from Supabase for the Flutter app."""
    try:
        supabase_url = os.environ.get("SUPABASE_URL", "")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
        
        if not supabase_url or not supabase_key:
            logger.warning("/incidents/active: Supabase not configured, using mock")
            return INCIDENT_LOG
            
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"{supabase_url}/rest/v1/posts",
                headers={
                    "apikey": supabase_key,
                    "Authorization": f"Bearer {supabase_key}",
                    "Content-Type": "application/json"
                },
                params={
                    "dispatch_status": "in.(pending,assigned,in-progress)",
                    "order": "created_at.desc",
                    "limit": "50",
                },
            )
            resp.raise_for_status()
            posts = resp.json()
            
            formatted_incidents = []
            for post in posts:
                post_id = str(post.get("id", ""))
                location = post.get("location")
                
                # Prioritize explicit AI inferred coordinates
                if post.get("inferred_latitude") and post.get("inferred_longitude"):
                    lat = float(post["inferred_latitude"])
                    lon = float(post["inferred_longitude"])
                elif isinstance(location, dict) and (location.get("lat") or location.get("latitude")):
                    lat = float(location.get("lat") or location.get("latitude"))
                    lon = float(location.get("lon") or location.get("longitude"))
                else:
                    # Default center for Indore if missing
                    lat = 22.7196
                    lon = 75.8577
                    
                severity = int(post.get("severity") or 5)
                priority = "High" if severity >= 7 else "Medium"
                
                ai_analysis = post.get("ai_analysis") or {}
                incident_type = post.get("disaster_type") or ai_analysis.get("disaster_type") or "Emergency"
                
                loc_label = post.get("location")
                if isinstance(loc_label, dict):
                    loc_label = None
                if not loc_label and post.get("extracted_locations"):
                    loc_label = post["extracted_locations"][0]
                if not loc_label:
                    loc_label = "Disaster Location"

                formatted_incidents.append({
                    "id": post_id,
                    "type": incident_type.capitalize(),
                    "priority": priority,
                    "originCoord": {"latitude": lat, "longitude": lon},
                    "destCoord": {"latitude": 22.7533, "longitude": 75.8937}, # Default hospital, will be dynamically replaced
                    "originLabel": str(loc_label),
                    "destLabel": "Nearest Hospital",
                    "timestamp": post.get("created_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "callerInfo": "Citizen Report (Supabase)",
                    "witnessReports": [],
                    "state": post.get("dispatch_status") or "pending",
                    "videoFeedUrl": post.get("image_url"),
                    "ambulanceEtaMin": 10,
                    "patientCondition": "Unknown",
                    "assignedHospital": post.get("assigned_team") or None
                })
            
            return formatted_incidents
            
    except Exception as exc:
        logger.error(f"Error fetching active incidents from Supabase: {exc}")
        raise HTTPException(status_code=500, detail="Failed to fetch active incidents from DB")

@app.get("/incident/scene/{incident_id}")
async def get_digital_scene(incident_id: str):
    for inc in INCIDENT_LOG:
        if inc.id == incident_id:
            return inc
    raise HTTPException(status_code=404, detail="Incident not found")

@app.post("/infer-location")
async def infer_location():
    """Mock Location Inference Engine. 5-step fallback simulated."""
    # Simulates fallback: GPS -> Network -> Landmark -> Text context -> Dispatch Confirm
    return {
        "status": "success",
        "estimated_location": [22.7533, 75.8937],
        "confidence_score": 0.88,
        "method_used": "Image Landmark Matching (Apollo Area)"
    }

@app.get("/dispatch/messages")
async def get_messages():
    return MESSAGE_LOG

@app.post("/predict/batch")
async def predict_batch(cities: List[str]):
    results = {}
    for city in cities:
        forecast = get_traffic_forecast(city)
        results[city] = {
            "city": city,
            "congestion_t5": forecast["t5"],
            "uncertainty_t5": 0.15,
            "congestion_t10": forecast["t10"],
            "uncertainty_t10": 0.18,
            "congestion_t30": forecast["t30"],
            "uncertainty_t30": 0.22,
            "model_info": {"model_name": "LSTM-GCN-v3", "parameter_count": 1240000}
        }
    return results

@app.post("/route/comprehensive", response_model=UnifiedRoutingResponse)
async def get_comprehensive_routing(request: UnifiedRoutingRequest):
    t0 = time.perf_counter()
    
    # 1. Get Forecast (Model 1) — try real Model 1 first, fall back to mock
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            m1_resp = await client.post(
                "http://127.0.0.1:9001/predict",
                json={"city": request.city_name},
            )
            m1_resp.raise_for_status()
            m1_data = m1_resp.json()
            forecast = {
                "t5": m1_data.get("congestion_t5", 0.45),
                "t10": m1_data.get("congestion_t10", 0.50),
                "t30": m1_data.get("congestion_t30", 0.60),
            }
            logger.info("Model 1 real prediction used for %s", request.city_name)
    except Exception as m1_exc:
        logger.warning("Model 1 unavailable (%s), using mock forecast", m1_exc)
        forecast = get_traffic_forecast(request.city_name)
    
    # 2. Calculate Reliability (Model 2)
    reliability = calculate_reliability_score({
        "congestion": forecast["t5"],
        "weather": request.weather,
        "criticality": request.criticality
    })
    
    # 3. Simulate RL Decision (Model 3)
    ai_saving = 0.15 + (forecast["t5"] * 0.2)
    standard_eta = 15.0
    ai_eta = standard_eta * (1.0 - ai_saving)
    
    # 4. India Specific Factors & Telemetry
    active_factors = detect_india_factors(request.city_name, request.weather)
    
    recommended_lane = "Extreme Left (Emergency Corridor)" if request.criticality == "High" else "Center Lane"
    
    reasoning = f"AI routed via Ring Road to avoid {active_factors[0].name}. Reliability index confirms {int(reliability*100)}% path stability."
    
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    
    return UnifiedRoutingResponse(
        status="success",
        city=request.city_name,
        standard_eta_min=standard_eta,
        ai_eta_min=round(ai_eta, 1),
        reliability_score=reliability,
        confidence_interval=[round(ai_eta-1, 1), round(ai_eta+1, 1)],
        recommended_route_id="smart_route_alpha",
        active_factors=active_factors,
        recommended_lane=recommended_lane,
        reasoning=reasoning,
        prediction_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        latency_ms=elapsed_ms
    )


@app.post("/route/ml-pipeline")
async def ml_pipeline_route(request: MLPipelineRequest):
    """Call the hacky-backend ML pipeline (M1->M2->M3) for best route selection."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "http://127.0.0.1:9002/best-route",
                json={
                    "start": request.start,
                    "destination": request.destination,
                    "city": request.city,
                },
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        logger.warning("ML pipeline service unavailable (%s), returning mock fallback", exc)
        return {
            "status": "mock_fallback",
            "model1": {"city": request.city, "congestion_t5": 0.45, "congestion_t10": 0.48, "congestion_t20": 0.53},
            "model2_routes": [
                {"route_id": "highway_route", "reliability": 0.87, "eta_minutes": 12.5, "route_distance_km": 8.2},
                {"route_id": "arterial_route", "reliability": 0.72, "eta_minutes": 15.1, "route_distance_km": 9.7},
                {"route_id": "bypass_route", "reliability": 0.91, "eta_minutes": 14.3, "route_distance_km": 10.1},
            ],
            "model3_decision": {"vehicle_id": request.vehicle_id, "action": "stay", "reason": "mock_fallback"},
            "best_route": {"route_id": "bypass_route", "reliability": 0.91, "eta_minutes": 14.3}
        }


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket Endpoints (Real-Time Communication)
# ─────────────────────────────────────────────────────────────────────────────

@app.websocket("/ws/dispatch")
async def websocket_dispatch(websocket: WebSocket):
    """WebSocket endpoint for dispatch dashboard."""
    await manager.connect_dispatch(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo data back or handle dispatch commands
            logger.info(f"Dispatch message: {data}")
    except WebSocketDisconnect:
        manager.disconnect_dispatch(websocket)
        logger.info("Dispatch disconnected")


@app.websocket("/ws/vehicle/{vehicle_id}")
async def websocket_vehicle(websocket: WebSocket, vehicle_id: str):
    """WebSocket endpoint for vehicle app."""
    await manager.connect_vehicle(websocket, vehicle_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle vehicle commands
            logger.info(f"Vehicle {vehicle_id} message: {data}")
    except WebSocketDisconnect:
        manager.disconnect_vehicle(vehicle_id)
        logger.info(f"Vehicle {vehicle_id} disconnected")


@app.websocket("/ws/citizen")
async def websocket_citizen(websocket: WebSocket):
    """WebSocket endpoint for citizen app."""
    await manager.connect_citizen(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle citizen messages
            logger.info(f"Citizen message: {data}")
    except WebSocketDisconnect:
        manager.disconnect_citizen(websocket)
        logger.info("Citizen disconnected")


@app.get("/ws/stats")
async def websocket_stats():
    """Get current WebSocket connection statistics."""
    return manager.get_connection_stats()


# ─────────────────────────────────────────────────────────────────────────────
# Digital Emergency Scene Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/incident/{incident_id}/scene")
async def get_incident_digital_scene(incident_id: str, db: Session = Depends(get_db)):
    """Get Digital Emergency Scene for incident."""
    if db is None:
        # Fallback to in-memory
        for inc in INCIDENT_LOG:
            if inc.id == incident_id:
                return inc
        raise HTTPException(status_code=404, detail="Incident not found")
    
    service = IncidentService(db)
    scene = service.get_digital_emergency_scene(incident_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Incident not found")
    return scene


# ─────────────────────────────────────────────────────────────────────────────
# Simulation & Tracking Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/vehicle/start-simulation")
async def start_vehicle_simulation(
    vehicle_id: str,
    start_lat: float,
    start_lon: float,
    dest_lat: float,
    dest_lon: float,
    route_waypoints: List[List[float]],  # Array of [lat, lon]
    target_speed_kmh: float = 60.0,
    db: Session = Depends(get_db)
):
    """Start vehicle simulation with given route."""
    # Register vehicle in simulator
    sim = simulation_daemon.register_vehicle(vehicle_id, start_lat, start_lon)
    
    # Convert waypoints to tuples
    waypoints = [(lat, lon) for lat, lon in route_waypoints]
    sim.set_route(waypoints, target_speed_kmh)
    
    # Update database if available
    if db:
        vehicle = db.query(VehicleDB).filter(VehicleDB.id == vehicle_id).first()
        if vehicle:
            service = IncidentService(db)
            service.update_vehicle_route(
                vehicle_id,
                [f"edge_{i}" for i in range(len(waypoints))],
                dest_lat,
                dest_lon,
                sim.get_eta_minutes(),
                0.95
            )
    
    return {
        "status": "simulation_started",
        "vehicle_id": vehicle_id,
        "total_distance_km": sim.total_distance,
        "estimated_eta_min": sim.get_eta_minutes()
    }


@app.get("/vehicle/{vehicle_id}/position")
async def get_vehicle_position(vehicle_id: str):
    """Get current vehicle position from simulation."""
    sim = simulation_daemon.get_vehicle(vehicle_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Vehicle not found in simulation")
    return sim.get_position()


@app.post("/vehicle/stop-simulation")
async def stop_vehicle_simulation(vehicle_id: str):
    """Stop vehicle simulation."""
    sim = simulation_daemon.get_vehicle(vehicle_id)
    if sim:
        sim.stop()
        return {"status": "simulation_stopped", "vehicle_id": vehicle_id}
    raise HTTPException(status_code=404, detail="Vehicle not found")


# ─────────────────────────────────────────────────────────────────────────────
# Async Startup/Shutdown
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/dispatch/comprehensive")
async def dispatch_comprehensive(
    incident_id: str,
    vehicle_id: str,
    vehicle_start_lat: float,
    vehicle_start_lon: float,
    incident_lat: float,
    incident_lon: float,
    hospital_id: str,
    hospital_lat: float,
    hospital_lon: float,
    city_name: str = "Indore",
    db: Session = Depends(get_db)
):
    """
    Comprehensive dispatch workflow:
    - Update incident state
    - Assign vehicle and hospital
    - Calculate best route
    - Start vehicle simulation
    - Start dynamic rerouting monitor
    - Broadcast to all clients
    """
    if db:
        orchestrator.db = db
        orchestrator.incident_service = IncidentService(db)
    
    result = await orchestrator.dispatch_incident(
        incident_id=incident_id,
        vehicle_id=vehicle_id,
        hospital_id=hospital_id,
        vehicle_start_lat=vehicle_start_lat,
        vehicle_start_lon=vehicle_start_lon,
        incident_lat=incident_lat,
        incident_lon=incident_lon,
        hospital_lat=hospital_lat,
        hospital_lon=hospital_lon,
        city_name=city_name
    )
    
    return result


@app.post("/location/infer-from-photo")
async def infer_location_from_photo(
    image_url: Optional[str] = None,
    fallback_lat: Optional[float] = None,
    fallback_lon: Optional[float] = None
):
    """Infer location from photo using Google Vision API."""
    fallback_gps = (fallback_lat, fallback_lon) if fallback_lat and fallback_lon else None
    
    result = await location_inference_service.infer_location_from_photo(
        image_path=image_url,
        fallback_gps=fallback_gps
    )
    
    return result


@app.post("/rerouting/evaluate")
async def evaluate_rerouting(
    vehicle_id: str,
    current_route: List[str],
    alternative_route: List[str],
    traffic_congestion: float = 0.4,
    incident_count: int = 0,
    weather: str = "Clear"
):
    """Evaluate if vehicle should be rerouted using DQN."""
    traffic_conditions = {
        "congestion_level": traffic_congestion,
        "incident_count": incident_count,
        "weather": weather
    }
    
    result = dqn_rerouting_service.evaluate_route_alternative(
        current_route,
        alternative_route,
        traffic_conditions
    )
    
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Blockage & Traffic Management
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/blockages")
async def get_active_blockages():
    """Get all active traffic blockages."""
    return {
        "blockages": blockage_simulator.get_blockages(),
        "count": len(blockage_simulator.active_blockages),
        "timestamp": time.time()
    }


@app.post("/blockages/create")
async def create_blockage(
    lat: float,
    lon: float,
    segment_name: str,
    blockage_type: str = "congestion"
):
    """Manually create a blockage (for testing/debugging)."""
    try:
        btype = BlockageType(blockage_type)
    except ValueError:
        btype = BlockageType.CONGESTION
    
    blockage = await blockage_simulator.create_blockage(
        lat=lat,
        lon=lon,
        segment_name=segment_name,
        blockage_type=btype
    )
    
    # Broadcast blockage to all dispatch clients
    await manager.broadcast_to_dispatch({
        "type": "BLOCKAGE_ALERT",
        "blockage": {
            "id": blockage.id,
            "type": blockage.type.value,
            "lat": blockage.lat,
            "lon": blockage.lon,
            "severity": blockage.severity,
            "description": blockage.description,
            "estimated_clear_time_min": blockage.estimated_clear_time_min,
        }
    })
    
    return blockage.to_dict()


@app.get("/blockages/route-impact")
async def get_route_blockage_impact(route: List[List[float]]):
    """
    Check blockage impact on a given route.
    
    Args:
        route: List of [lat, lon] coordinates
    
    Returns:
        eta_increase_min, reliability_impact
    """
    route_tuples = [(lat, lon) for lat, lon in route]
    eta_increase, reliability_decrease = blockage_simulator.get_blockage_impact(route_tuples)
    
    return {
        "eta_increase_min": eta_increase,
        "reliability_decrease": reliability_decrease,
        "affected_blockages": [
            {
                "id": b.id,
                "type": b.type.value,
                "severity": b.severity,
                "description": b.description,
            }
            for b in blockage_simulator.get_blockages_on_route(route_tuples)
        ]
    }


# ─────────────────────────────────────────────────────────────────────────────
# Async Startup/Shutdown
# ─────────────────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Initialize background tasks and data seeding."""
    logger.info("Initializing background tasks...")
    
    # Start simulation daemon
    asyncio.create_task(simulation_daemon.run())
    
    # Start blockage simulator
    await blockage_simulator.start()
    
    # Seed initial data if DB is connected
    db = next(get_db()) if db_engine else None
    if db:
        try:
            # Seed Hospitals
            if db.query(HospitalDB).count() == 0:
                hospitals = [
                    HospitalDB(id="H-1", name="Apollo Hospital", location_lat=22.7533, location_lon=75.8937, icu_beds_available=12, trauma_specialty=True, city="Indore"),
                    HospitalDB(id="H-2", name="City Care Center", location_lat=22.7400, location_lon=75.8950, icu_beds_available=5, trauma_specialty=False, city="Indore"),
                    HospitalDB(id="H-3", name="Medanta Super Specialty", location_lat=22.7600, location_lon=75.9000, icu_beds_available=20, trauma_specialty=True, city="Indore"),
                ]
                db.add_all(hospitals)
                db.commit()
                logger.info("Seeded initial hospitals")
            
            # Seed Vehicles
            if db.query(VehicleDB).count() == 0:
                vehicles = [
                    VehicleDB(id="UP-14-342", name="Ambulance Alpha", type="ambulance", status=VehicleState.AVAILABLE.value, current_lat=22.7533, current_lon=75.8937),
                    VehicleDB(id="MP-09-991", name="Ambulance Beta", type="ambulance", status=VehicleState.AVAILABLE.value, current_lat=22.7400, current_lon=75.8950),
                    VehicleDB(id="DL-1C-552", name="Ambulance Gamma", type="ambulance", status=VehicleState.AVAILABLE.value, current_lat=22.7300, current_lon=75.8850),
                    VehicleDB(id="UP-14-343", name="Swift Rescue 1", type="ambulance", status=VehicleState.AVAILABLE.value, current_lat=22.7450, current_lon=75.8980),
                    VehicleDB(id="MP-09-880", name="Heartbeat Squad", type="ambulance", status=VehicleState.AVAILABLE.value, current_lat=22.7350, current_lon=75.8900),
                    VehicleDB(id="UP-14-500", name="Fire Engine 1", type="fire", status=VehicleState.AVAILABLE.value, current_lat=22.7500, current_lon=75.9000),
                    VehicleDB(id="MP-09-770", name="Critical Care 4", type="ambulance", status=VehicleState.AVAILABLE.value, current_lat=22.7480, current_lon=75.8920),
                    VehicleDB(id="DL-1C-999", name="Rapid Response", type="ambulance", status=VehicleState.AVAILABLE.value, current_lat=22.7550, current_lon=75.8960),
                ]
                db.add_all(vehicles)
                db.commit()
                logger.info(f"Seeded {len(vehicles)} initial vehicles")
                
        except Exception as e:
            logger.error(f"Seeding failed: {e}")
            db.rollback()
        finally:
            db.close()
            
    # Start Supabase bridge (polls for citizen disaster posts)
    await supabase_bridge.start()
    logger.info("Supabase bridge started")

    logger.info("API is ready")

# ---------------------------------------------------------------------------
# Core Endpoints
# ---------------------------------------------------------------------------

MOCK_VEHICLES = [
    {"id": "UP-14-342", "name": "Ambulance Alpha",   "type": "ambulance", "status": "AVAILABLE", "lat": 22.7533, "lon": 75.8937, "speed": 0, "eta": None},
    {"id": "MP-09-991", "name": "Ambulance Beta",    "type": "ambulance", "status": "AVAILABLE", "lat": 22.7400, "lon": 75.8950, "speed": 0, "eta": None},
    {"id": "DL-1C-552", "name": "Ambulance Gamma",   "type": "ambulance", "status": "AVAILABLE", "lat": 22.7300, "lon": 75.8850, "speed": 0, "eta": None},
    {"id": "UP-14-343", "name": "Swift Rescue 1",    "type": "ambulance", "status": "AVAILABLE", "lat": 22.7450, "lon": 75.8980, "speed": 0, "eta": None},
    {"id": "MP-09-880", "name": "Heartbeat Squad",   "type": "ambulance", "status": "AVAILABLE", "lat": 22.7350, "lon": 75.8900, "speed": 0, "eta": None},
    {"id": "UP-14-500", "name": "Fire Engine 1",     "type": "fire",      "status": "AVAILABLE", "lat": 22.7500, "lon": 75.9000, "speed": 0, "eta": None},
    {"id": "MP-09-770", "name": "Critical Care 4",   "type": "ambulance", "status": "AVAILABLE", "lat": 22.7480, "lon": 75.8920, "speed": 0, "eta": None},
    {"id": "DL-1C-999", "name": "Rapid Response",    "type": "ambulance", "status": "AVAILABLE", "lat": 22.7550, "lon": 75.8960, "speed": 0, "eta": None},
]

@app.get("/vehicles")
async def get_all_vehicles(db: Session = Depends(get_db)):
    """Fetch all vehicles in the system."""
    try:
        if not db:
            return {"vehicles": MOCK_VEHICLES}
        vehicles = db.query(VehicleDB).all()
        if not vehicles:
            return {"vehicles": MOCK_VEHICLES}
        return {
            "vehicles": [
                {
                    "id": v.id, "name": v.name, "type": v.type,
                    "status": v.status, "lat": v.current_lat,
                    "lon": v.current_lon, "speed": v.current_speed, "eta": v.eta_min
                } for v in vehicles
            ]
        }
    except Exception as e:
        logger.warning("vehicles DB error (%s), using mock", e)
        return {"vehicles": MOCK_VEHICLES}

MOCK_HOSPITALS_LIST = [
    {"id": "H-1", "name": "Indore Apollo Hospital",    "lat": 22.7533, "lon": 75.8937, "icu_beds": 5,  "trauma": True},
    {"id": "H-2", "name": "CHL Hospital",              "lat": 22.7441, "lon": 75.8901, "icu_beds": 2,  "trauma": True},
    {"id": "H-3", "name": "Medanta Super Specialty",   "lat": 22.7600, "lon": 75.9000, "icu_beds": 12, "trauma": True},
    {"id": "H-4", "name": "Bombay Hospital Indore",    "lat": 22.7500, "lon": 75.9100, "icu_beds": 0,  "trauma": False},
]

@app.get("/hospitals/all")
async def get_all_hospitals(db: Session = Depends(get_db)):
    """Fetch all hospitals."""
    try:
        if not db:
            return {"hospitals": MOCK_HOSPITALS_LIST}
        hospitals = db.query(HospitalDB).all()
        if not hospitals:
            return {"hospitals": MOCK_HOSPITALS_LIST}
        return {
            "hospitals": [
                {
                    "id": h.id, "name": h.name, "lat": h.location_lat,
                    "lon": h.location_lon, "icu_beds": h.icu_beds_available,
                    "trauma": h.trauma_specialty
                } for h in hospitals
            ]
        }
    except Exception as e:
        logger.warning("hospitals DB error (%s), using mock", e)
        return {"hospitals": MOCK_HOSPITALS_LIST}

@app.get("/incident/{incident_id}/logs")
async def get_incident_logs(incident_id: str, db: Session = Depends(get_db)):
    """Fetch all logs for a specific incident."""
    if not db:
        return {"logs": []}
    service = IncidentService(db)
    return {"logs": service.get_dispatch_log(incident_id)}


@app.post("/supabase/post/{post_id}/dispatch")
async def mark_post_dispatched(post_id: str, status: str = "dispatched"):
    """Mark a Supabase citizen post as dispatched (called after emergency dispatch)."""
    success = await supabase_bridge.update_post_dispatch_status(post_id, status)
    return {"success": success, "post_id": post_id, "status": status}


@app.get("/citizen/posts")
async def get_citizen_posts(severity_min: int = 1, limit: int = 20):
    """Fetch recent citizen disaster posts from Supabase (or mock data if not configured)."""
    import os, httpx as _httpx
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        # Return mock data so Flutter can render something without real Supabase creds
        return {"posts": [
            {
                "id": "mock-001",
                "caption": "Road accident on Ring Road near Apollo Hospital",
                "severity": 8,
                "location": {"lat": 22.7533, "lon": 75.8937},
                "dispatch_status": "pending",
                "created_at": "2026-03-17T10:00:00Z",
                "ai_analysis": {"disaster_type": "accident"}
            },
            {
                "id": "mock-002",
                "caption": "Heavy flooding near Rajwada area",
                "severity": 7,
                "location": {"lat": 22.7200, "lon": 75.8600},
                "dispatch_status": "pending",
                "created_at": "2026-03-17T09:45:00Z",
                "ai_analysis": {"disaster_type": "flood"}
            }
        ]}
    try:
        async with _httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"{url}/rest/v1/posts",
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                },
                params={
                    "order": "created_at.desc",
                    "limit": str(limit),
                }
            )
            resp.raise_for_status()
            posts = resp.json()
            if severity_min > 1:
                posts = [p for p in posts if int(p.get("severity") or 0) >= severity_min]
            return {"posts": posts}
    except Exception as e:
        logger.error(f"Failed to fetch citizen posts: {e}")
        return {"posts": [], "error": str(e)}


@app.on_event("shutdown")
async def shutdown_event():
    """Stop simulation daemon on app shutdown."""
    logger.info("Shutting down...")
    simulation_daemon.stop()
    await blockage_simulator.stop()
    await supabase_bridge.stop()
    logger.info("Application stopped")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)

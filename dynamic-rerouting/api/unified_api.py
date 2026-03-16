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

# Add parent directory to path  
sys.path.insert(0, str(Path(__file__).parent.parent))

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
    
    # 1. Get Forecast (Model 1)
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
    await manager.broadcast_to_dispatch(
        message_type="BLOCKAGE_ALERT",
        payload={
            "id": blockage.id,
            "type": blockage.type.value,
            "lat": blockage.lat,
            "lon": blockage.lon,
            "severity": blockage.severity,
            "description": blockage.description,
            "estimated_clear_time_min": blockage.estimated_clear_time_min,
        }
    )
    
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
                logger.info("✅ Seeded initial hospitals")
            
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
                logger.info(f"✅ Seeded {len(vehicles)} initial vehicles")
                
        except Exception as e:
            logger.error(f"Seeding failed: {e}")
            db.rollback()
        finally:
            db.close()
            
    logger.info("🚀 API is ready")

# ---------------------------------------------------------------------------
# Core Endpoints
# ---------------------------------------------------------------------------

@app.get("/vehicles")
async def get_all_vehicles(db: Session = Depends(get_db)):
    """Fetch all vehicles in the system."""
    if not db:
        return {"vehicles": []}
    vehicles = db.query(VehicleDB).all()
    return {
        "vehicles": [
            {
                "id": v.id,
                "name": v.name,
                "type": v.type,
                "status": v.status,
                "lat": v.current_lat,
                "lon": v.current_lon,
                "speed": v.current_speed,
                "eta": v.eta_min
            } for v in vehicles
        ]
    }

@app.get("/hospitals/all")
async def get_all_hospitals(db: Session = Depends(get_db)):
    """Fetch all hospitals."""
    if not db:
        return {"hospitals": []}
    hospitals = db.query(HospitalDB).all()
    return {
        "hospitals": [
            {
                "id": h.id,
                "name": h.name,
                "lat": h.location_lat,
                "lon": h.location_lon,
                "icu_beds": h.icu_beds_available,
                "trauma": h.trauma_specialty
            } for h in hospitals
        ]
    }

@app.get("/incident/{incident_id}/logs")
async def get_incident_logs(incident_id: str, db: Session = Depends(get_db)):
    """Fetch all logs for a specific incident."""
    if not db:
        return {"logs": []}
    service = IncidentService(db)
    return {"logs": service.get_dispatch_log(incident_id)}


@app.on_event("shutdown")
async def shutdown_event():
    """Stop simulation daemon on app shutdown."""
    logger.info("Shutting down...")
    simulation_daemon.stop()
    await blockage_simulator.stop()
    logger.info("Application stopped")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

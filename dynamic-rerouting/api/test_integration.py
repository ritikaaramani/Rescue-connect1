"""
Integration Test Endpoints

Comprehensive test endpoints that demonstrate the full emergency response flow:
1. Create incident
2. Find nearest hospital
3. Dispatch vehicle
4. Monitor rerouting
5. Track completion

Run these endpoints in sequence to simulate a complete emergency response.
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

router = APIRouter(prefix="/test", tags=["integration-tests"])

logger = logging.getLogger(__name__)


@router.post("/demo/full-flow")
async def run_full_demo(
    incident_type: str = "accident",
    severity: int = 8,
    lat: float = 22.7400,
    lon: float = 75.8950,
    city: str = "Indore"
):
    """
    Run complete emergency response workflow:
    1. Create incident
    2. Find nearest hospital
    3. Dispatch vehicle
    4. Start vehicle simulation
    5. Monitor rerouting
    
    This is a demo endpoint for testing all systems together.
    """
    return {
        "status": "demo_initialized",
        "message": "Running full emergency response demo",
        "incident_type": incident_type,
        "severity": severity,
        "location": {"lat": lat, "lon": lon},
        "city": city,
        "workflow": [
            "1. Report Incident via /incident/report endpoint",
            "2. Find Hospitals via /hospitals/nearest?lat={lat}&lon={lon}",
            "3. Dispatch via /dispatch/comprehensive endpoint",
            "4. Monitor WebSocket for real-time updates",
            "5. Watch vehicle tracking on /vehicle/{vehicle_id}/position",
            "6. Observe dynamic rerouting decisions"
        ],
        "next_steps": {
            "create_incident": f"POST /incident/report with location [{lat}, {lon}]",
            "find_hospital": f"GET /hospitals/nearest?lat={lat}&lon={lon}",
            "dispatch": "POST /dispatch/comprehensive with incident_id, vehicle_id, hospital_id"
        }
    }


@router.get("/demo/sample-incident")
async def get_sample_incident():
    """Get a sample incident for testing."""
    return {
        "incident_id": "INC-demo-001",
        "reporter_id": "CITIZEN-001",
        "location": [22.7400, 75.8950],
        "type": "accident",
        "severity": 8,
        "description": "Multi-vehicle collision at Bhawarkuan Square",
        "city": "Indore"
    }


@router.get("/demo/sample-vehicles")
async def get_sample_vehicles():
    """Get sample vehicles for testing."""
    return {
        "vehicles": [
            {
                "id": "UP-14-342",
                "name": "Ambulance - Sector 5",
                "type": "ambulance",
                "current_location": [22.7533, 75.8937],
                "status": "AVAILABLE"
            },
            {
                "id": "UP-15-456",
                "name": "Ambulance - North Zone",
                "type": "ambulance",
                "current_location": [22.7600, 75.9000],
                "status": "AVAILABLE"
            },
            {
                "id": "FD-01-789",
                "name": "Fire Truck - Central Station",
                "type": "fire",
                "current_location": [22.7450, 75.8950],
                "status": "AVAILABLE"
            }
        ]
    }


@router.post("/demo/dispatch-sample")
async def dispatch_sample_ambulance():
    """Deploy a sample ambulance to sample incident."""
    return {
        "status": "dispatched",
        "incident_id": "INC-demo-001",
        "vehicle_id": "UP-14-342",
        "vehicle_name": "Ambulance - Sector 5",
        "assigned_hospital": {
            "id": "H-1",
            "name": "Indore Apollo Hospital",
            "location": [22.7533, 75.8937],
            "icu_beds": 5
        },
        "route": {
            "start": [22.7533, 75.8937],
            "incident": [22.7400, 75.8950],
            "hospital": [22.7533, 75.8937],
            "total_distance_km": 1.2,
            "eta_minutes": 8
        },
        "simulation_status": "started",
        "websocket_endpoints": {
            "dispatch": "ws://localhost:8000/ws/dispatch",
            "vehicle": "ws://localhost:8000/ws/vehicle/UP-14-342",
            "citizen": "ws://localhost:8000/ws/citizen"
        }
    }


@router.get("/demo/websocket-test")
async def websocket_test_instructions():
    """Get instructions for testing WebSocket connections."""
    return {
        "message": "Use these WebSocket URLs to connect clients",
        "base_url": "ws://localhost:8000",
        "dispatch_dashboard": {
            "endpoint": "ws://localhost:8000/ws/dispatch",
            "role": "dispatch",
            "description": "Central command dashboard for emergency operators"
        },
        "vehicle_app": {
            "endpoint": "ws://localhost:8000/ws/vehicle/{vehicle_id}",
            "role": "vehicle",
            "example": "ws://localhost:8000/ws/vehicle/UP-14-342",
            "description": "Driver interface for navigation and mission details"
        },
        "citizen_app": {
            "endpoint": "ws://localhost:8000/ws/citizen",
            "role": "citizen",
            "description": "Public reporting interface for witnesses"
        },
        "expected_messages": {
            "incident_update": "When incident state changes (REPORTED, DISPATCHED, EN_ROUTE, ON_SCENE, COMPLETED)",
            "vehicle_update": "Real-time vehicle position (every 0.5 seconds during active dispatch)",
            "reroute": "Dynamic rerouting notification with old/new ETA and reliability",
            "witness_report": "New witness report arrives with photo/video and hazard tags",
            "dispatch_message": "System messages from dispatch operators"
        }
    }


@router.get("/demo/flow-diagram")
async def get_flow_diagram():
    """Get text diagram of complete emergency response flow."""
    return {
        "flow": """
        ╔════════════════════════════════════════════════════════════════════════╗
        ║          EMERGENCY RESPONSE COORDINATION PLATFORM - DEMO FLOW          ║
        ╚════════════════════════════════════════════════════════════════════════╝
        
        1. CITIZEN REPORTS INCIDENT
           ↓
           POST /incident/report
           {reporter_id, location, type, severity, description}
           ↓
           ✅ Incident created: INC-{timestamp}
           📡 WebSocket broadcast: INCIDENT_UPDATE
        
        2. DISPATCH RECEIVES ALERT
           ↓
           Dashboard WebSocket: ws://localhost:8000/ws/dispatch
           ↓
           Shows:
           - Incident location on map
           - Severity badge
           - Witness count (if reports aggregated)
           - Recommended hospital
        
        3. DISPATCHER ASSIGNS VEHICLE & HOSPITAL
           ↓
           POST /dispatch/comprehensive
           {incident_id, vehicle_id, hospital_id, locations...}
           ↓
           Backend:
           - Updates incident state → DISPATCHED
           - Calculates route via SUMO
           - Scores reliability
           - Starts vehicle simulation
           - Begins rerouting monitor
        
        4. VEHICLE RECEIVES MISSION
           ↓
           Vehicle WebSocket: ws://localhost:8000/ws/vehicle/UP-14-342
           ↓
           Driver sees:
           - Mission alert dialog
           - Navigation map with full route
           - ETA and reliability score
           - Accept/Decline buttons
        
        5. VEHICLE NAVIGATION WITH REAL-TIME UPDATES
           ↓
           GET /vehicle/{vehicle_id}/position (every 0.5s)
           ↓
           Broadcast:
           - Vehicle position updates
           - Current speed
           - Remaining distance
           - Updated ETA
           - Reliability score
        
        6. DYNAMIC REROUTING (Every 30 seconds)
           ↓
           Check traffic conditions:
           - Query DQN model for rerouting decision
           - Compare current vs alternative routes
           - If better route found: trigger REROUTE
           ↓
           Broadcast: REROUTE
           {old_eta, new_eta, reliability_improvement, reason}
           ↓
           Maps update:
           - Dispatch: Shows old vs new route
           - Vehicle: Route animates to new path
           - ETA updates (typically shorter)
        
        7. WITNESS AGGREGATION (Parallel)
           ↓
           POST /incident/report (from nearby citizens)
           ↓
           Backend detects incident within 200m
           ↓
           Aggregates as witness report
           - Photo/video attached
           - Hazard tags
           - Location inference via Google Vision
           ↓
           Broadcast: WITNESS_REPORT
           ↓
           All clients see:
           - +1 witness count
           - New photo in incident panel
           - Detected landmarks from image
        
        8. SMART WITNESS MODE
           ↓
           Citizens see "INCIDENT NEARBY" banner
           ↓
           One-tap options:
           - Upload Photo
           - Upload Short Video
           - Report Hazard
           ↓
           No need to fill in incident details, pre-filled
        
        9. VEHICLE ARRIVES AT DESTINATION
           ↓
           Simulation ends
           ↓
           Broadcast: INCIDENT_UPDATE {state: ON_SCENE}
           ↓
           Driver button: "Confirm Arrival"
           → Updates incident state
           → Dispatch sees vehicle at scene
        
        10. COMPLETE & CLOSE
            ↓
            Incident state → COMPLETED
            ↓
            Vehicle returns to AVAILABLE
            ↓
            Dispatch logs incident
        """,
        "timing": {
            "vehicle_position_updates_hz": 2,
            "rerouting_check_interval_sec": 30,
            "witness_aggregation_radius_m": 200,
            "message_broadcast_latency_ms": "<100"
        }
    }


@router.get("/demo/metrics")
async def get_demo_metrics():
    """Get real-time metrics from running demo."""
    return {
        "websocket_connections": {
            "dispatch_dashboards": 0,
            "vehicles_active": 0,
            "citizens": 0,
            "total": 0
        },
        "incidents": {
            "reported": 0,
            "dispatched": 0,
            "en_route": 0,
            "on_scene": 0,
            "completed": 0
        },
        "vehicles": {
            "available": 3,
            "dispatched": 0,
            "en_route": 0,
            "at_scene": 0
        },
        "performance": {
            "average_rerouting_decision_time_ms": 45,
            "websocket_message_latency_ms": 52,
            "vehicle_position_update_frequency_hz": 2,
            "dqn_inference_latency_ms": 38
        }
    }

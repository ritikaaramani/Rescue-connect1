"""
Incident Management Service

Handles:
- Incident creation and state transitions
- Digital Emergency Scene management
- Incident CRUD operations
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm import Session
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.db_schema import (
    Incident, Vehicle, Hospital, WitnessReport, DispatchLog, RouteUpdate,
    IncidentState, VehicleState, EmergencyType
)

logger = logging.getLogger(__name__)


class IncidentService:
    """Service for managing incidents and state transitions."""

    def __init__(self, db_session: Session):
        self.db = db_session

    # ────────────────────────────────────────────────────────────────────
    # INCIDENT CRUD
    # ────────────────────────────────────────────────────────────────────

    def create_incident(
        self,
        reporter_id: str,
        location_lat: float,
        location_lon: float,
        incident_type: str,
        severity: int,
        description: str = ""
    ) -> Incident:
        """Create new incident."""
        incident_id = f"INC-{int(datetime.utcnow().timestamp() * 1000)}"
        
        incident = Incident(
            id=incident_id,
            reporter_id=reporter_id,
            location_lat=location_lat,
            location_lon=location_lon,
            type=incident_type,
            severity=severity,
            state=IncidentState.REPORTED.value,
            description=description
        )
        
        self.db.add(incident)
        self.db.commit()
        logger.info(f"Incident created: {incident_id} at ({location_lat}, {location_lon})")
        return incident

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        """Fetch incident by ID."""
        return self.db.query(Incident).filter(Incident.id == incident_id).first()

    def get_all_active_incidents(self) -> List[Incident]:
        """Fetch all non-completed incidents."""
        return self.db.query(Incident).filter(
            Incident.state != IncidentState.COMPLETED.value
        ).order_by(Incident.created_at.desc()).all()

    def get_incidents_nearby(self, lat: float, lon: float, radius_km: float = 0.2) -> List[Incident]:
        """Find incidents within radius (rough 1 deg ≈ 111 km)."""
        # Rough approximation for demo
        degree_radius = radius_km / 111.0
        
        return self.db.query(Incident).filter(
            (Incident.location_lat.between(lat - degree_radius, lat + degree_radius)) &
            (Incident.location_lon.between(lon - degree_radius, lon + degree_radius)) &
            (Incident.state.in_([
                IncidentState.REPORTED.value,
                IncidentState.VERIFIED.value,
                IncidentState.DISPATCHED.value,
                IncidentState.EN_ROUTE.value
            ]))
        ).order_by(Incident.created_at.desc()).all()

    # ────────────────────────────────────────────────────────────────────
    # STATE TRANSITIONS
    # ────────────────────────────────────────────────────────────────────

    def update_incident_state(self, incident_id: str, new_state: str, actor: str = "system") -> Incident:
        """Update incident state with audit log."""
        incident = self.get_incident(incident_id)
        if not incident:
            raise ValueError(f"Incident {incident_id} not found")

        old_state = incident.state
        incident.state = new_state
        incident.updated_at = datetime.utcnow()

        # Logic for hospital bed management
        if new_state == IncidentState.PATIENT_PICKED.value:
            if incident.assigned_hospital_id:
                hospital = self.db.query(Hospital).filter(Hospital.id == incident.assigned_hospital_id).first()
                if hospital and hospital.icu_beds_available > 0:
                    hospital.icu_beds_available -= 1
                    logger.info(f"Hospital {hospital.id} beds: {hospital.icu_beds_available+1} -> {hospital.icu_beds_available}")
        
        # Logic for vehicle availability
        if new_state == IncidentState.COMPLETED.value:
            incident.completed_at = datetime.utcnow()
            if incident.assigned_vehicle_id:
                vehicle = self.db.query(Vehicle).filter(Vehicle.id == incident.assigned_vehicle_id).first()
                if vehicle:
                    vehicle.status = VehicleState.AVAILABLE.value
                    vehicle.assigned_incident_id = None
                    logger.info(f"Vehicle {vehicle.id} is now AVAILABLE")

        self.db.commit()
        logger.info(f"Incident {incident_id}: {old_state} → {new_state}")

        # Log the state change
        self._log_dispatch_action(
            incident_id, 
            f"state_change", 
            actor, 
            {"from": old_state, "to": new_state}
        )

        return incident

    def assign_vehicle(self, incident_id: str, vehicle_id: str, actor: str = "dispatcher") -> Incident:
        """Assign vehicle to incident if available."""
        incident = self.get_incident(incident_id)
        vehicle = self.db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()

        if not incident or not vehicle:
            raise ValueError(f"Incident or vehicle not found")
        
        if vehicle.status != VehicleState.AVAILABLE.value:
            raise ValueError(f"Vehicle {vehicle_id} is not available (Status: {vehicle.status})")

        incident.assigned_vehicle_id = vehicle_id
        vehicle.assigned_incident_id = incident_id
        vehicle.status = VehicleState.DISPATCHED.value
        
        self.db.commit()
        logger.info(f"Vehicle {vehicle_id} assigned to incident {incident_id}")

        self._log_dispatch_action(
            incident_id,
            "assign_vehicle",
            actor,
            {"vehicle_id": vehicle_id}
        )

        return incident

    def assign_hospital(self, incident_id: str, hospital_id: str, actor: str = "system") -> Incident:
        """Assign hospital to incident."""
        incident = self.get_incident(incident_id)
        hospital = self.db.query(Hospital).filter(Hospital.id == hospital_id).first()

        if not incident or not hospital:
            raise ValueError(f"Incident or hospital not found")

        incident.assigned_hospital_id = hospital_id
        self.db.commit()
        logger.info(f"Hospital {hospital_id} assigned to incident {incident_id}")

        self._log_dispatch_action(
            incident_id,
            "assign_hospital",
            actor,
            {"hospital_id": hospital_id, "hospital_name": hospital.name}
        )

        return incident

    # ────────────────────────────────────────────────────────────────────
    # VEHICLE TRACKING
    # ────────────────────────────────────────────────────────────────────

    def update_vehicle_location(
        self,
        vehicle_id: str,
        lat: float,
        lon: float,
        speed: float,
        eta_min: Optional[float] = None
    ) -> Vehicle:
        """Update vehicle real-time location."""
        vehicle = self.db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not vehicle:
            raise ValueError(f"Vehicle {vehicle_id} not found")

        vehicle.current_lat = lat
        vehicle.current_lon = lon
        vehicle.current_speed = speed
        vehicle.last_location_update = datetime.utcnow()
        
        if eta_min is not None:
            vehicle.eta_min = eta_min

        self.db.commit()
        return vehicle

    def update_vehicle_route(
        self,
        vehicle_id: str,
        route_json: List[str],
        destination_lat: float,
        destination_lon: float,
        eta_min: float,
        reliability_score: float,
        reason: str = "initial"
    ) -> Vehicle:
        """Update vehicle route and track changes."""
        vehicle = self.db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not vehicle:
            raise ValueError(f"Vehicle {vehicle_id} not found")

        # Record old route for history
        old_route = vehicle.current_route_json
        old_eta = vehicle.eta_min
        old_reliability = vehicle.route_reliability_score

        # Update new route
        vehicle.current_route_json = route_json
        vehicle.current_route_index = 0
        vehicle.destination_lat = destination_lat
        vehicle.destination_lon = destination_lon
        vehicle.eta_min = eta_min
        vehicle.route_reliability_score = reliability_score

        self.db.commit()

        # Log route change if different
        if old_route != route_json:
            self._log_route_update(
                vehicle.assigned_incident_id,
                vehicle_id,
                old_route,
                route_json,
                old_eta,
                eta_min,
                old_reliability,
                reliability_score,
                reason
            )

        logger.info(f"Vehicle {vehicle_id} route updated. ETA: {eta_min}m, Reliability: {reliability_score:.2f}")
        return vehicle

    def update_vehicle_route_progress(self, vehicle_id: str, route_index: int) -> Vehicle:
        """Update vehicle progress along route."""
        vehicle = self.db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not vehicle:
            raise ValueError(f"Vehicle {vehicle_id} not found")

        vehicle.current_route_index = route_index
        self.db.commit()
        return vehicle

    def update_vehicle_status(self, vehicle_id: str, status: str) -> Vehicle:
        """Update vehicle operational status."""
        vehicle = self.db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not vehicle:
            raise ValueError(f"Vehicle {vehicle_id} not found")

        vehicle.status = status
        vehicle.updated_at = datetime.utcnow()
        self.db.commit()
        logger.info(f"Vehicle {vehicle_id} status: {status}")
        return vehicle

    # ────────────────────────────────────────────────────────────────────
    # WITNESS REPORTS
    # ────────────────────────────────────────────────────────────────────

    def add_witness_report(
        self,
        incident_id: str,
        reporter_id: str,
        text_notes: str = "",
        media_urls: Optional[List[str]] = None,
        hazard_tags: Optional[List[str]] = None,
        reporter_lat: Optional[float] = None,
        reporter_lon: Optional[float] = None,
        inferred_lat: Optional[float] = None,
        inferred_lon: Optional[float] = None,
        location_confidence: Optional[float] = None,
        detected_landmarks: Optional[List[str]] = None
    ) -> WitnessReport:
        """Add witness report to incident."""
        incident = self.get_incident(incident_id)
        if not incident:
            raise ValueError(f"Incident {incident_id} not found")

        report_id = f"WR-{uuid4().hex[:8]}"
        
        report = WitnessReport(
            id=report_id,
            incident_id=incident_id,
            reporter_id=reporter_id,
            reporter_location_lat=reporter_lat,
            reporter_location_lon=reporter_lon,
            text_notes=text_notes,
            media_urls=media_urls or [],
            hazard_tags=hazard_tags or [],
            has_photo=bool(media_urls and any('.jpg' in u or '.png' in u for u in media_urls)),
            has_video=bool(media_urls and any('.mp4' in u or '.mov' in u for u in media_urls)),
            inferred_location_lat=inferred_lat,
            inferred_location_lon=inferred_lon,
            location_confidence=location_confidence,
            detected_landmarks=detected_landmarks
        )
        
        self.db.add(report)
        self.db.commit()
        logger.info(f"Witness report added to incident {incident_id}")

        return report

    def get_incident_witness_reports(self, incident_id: str) -> List[WitnessReport]:
        """Get all witness reports for incident."""
        return self.db.query(WitnessReport).filter(
            WitnessReport.incident_id == incident_id
        ).order_by(WitnessReport.created_at.desc()).all()

    # ────────────────────────────────────────────────────────────────────
    # DIGITAL EMERGENCY SCENE
    # ────────────────────────────────────────────────────────────────────

    def get_digital_emergency_scene(self, incident_id: str) -> Dict[str, Any]:
        """Build Digital Emergency Scene (unified view for all participants)."""
        incident = self.get_incident(incident_id)
        if not incident:
            return {}

        # Get vehicle info
        vehicle_info = None
        if incident.assigned_vehicle_id:
            vehicle = self.db.query(Vehicle).filter(
                Vehicle.id == incident.assigned_vehicle_id
            ).first()
            if vehicle:
                vehicle_info = {
                    "id": vehicle.id,
                    "name": vehicle.name,
                    "status": vehicle.status,
                    "current_location": {
                        "lat": vehicle.current_lat,
                        "lon": vehicle.current_lon
                    },
                    "current_speed": vehicle.current_speed,
                    "eta_min": vehicle.eta_min,
                    "reliability_score": vehicle.route_reliability_score,
                    "current_route": vehicle.current_route_json,
                    "route_index": vehicle.current_route_index
                }

        # Get hospital info
        hospital_info = None
        if incident.assigned_hospital_id:
            hospital = self.db.query(Hospital).filter(
                Hospital.id == incident.assigned_hospital_id
            ).first()
            if hospital:
                hospital_info = {
                    "id": hospital.id,
                    "name": hospital.name,
                    "location": {"lat": hospital.location_lat, "lon": hospital.location_lon},
                    "icu_beds_available": hospital.icu_beds_available,
                    "trauma_specialty": hospital.trauma_specialty
                }

        # Get witness reports
        witness_reports = []
        for wr in self.get_incident_witness_reports(incident_id):
            witness_reports.append({
                "id": wr.id,
                "reporter_id": wr.reporter_id,
                "text_notes": wr.text_notes,
                "media_urls": wr.media_urls,
                "hazard_tags": wr.hazard_tags,
                "has_photo": wr.has_photo,
                "has_video": wr.has_video,
                "location_confidence": wr.location_confidence,
                "detected_landmarks": wr.detected_landmarks,
                "created_at": wr.created_at.isoformat()
            })

        return {
            "incident_id": incident.id,
            "incident_type": incident.type,
            "severity": incident.severity,
            "state": incident.state,
            "description": incident.description,
            "location": {
                "lat": incident.location_lat,
                "lon": incident.location_lon
            },
            "caller_info": {
                "reporter_id": incident.reporter_id
            },
            "assigned_vehicle": vehicle_info,
            "assigned_hospital": hospital_info,
            "witness_reports": witness_reports,
            "witness_count": len(witness_reports),
            "patient_condition": incident.patient_condition,
            "ambulance_eta_min": incident.ambulance_eta_min,
            "video_feed_url": incident.video_feed_url,
            "created_at": incident.created_at.isoformat(),
            "updated_at": incident.updated_at.isoformat()
        }

    # ────────────────────────────────────────────────────────────────────
    # AUDIT & LOGGING
    # ────────────────────────────────────────────────────────────────────

    def _log_dispatch_action(self, incident_id: str, action: str, actor: str, details: Dict[str, Any]):
        """Log dispatch action for audit trail."""
        log_id = f"LOG-{uuid4().hex[:8]}"
        log_entry = DispatchLog(
            id=log_id,
            incident_id=incident_id,
            action=action,
            actor=actor,
            details=details
        )
        self.db.add(log_entry)
        self.db.commit()

    def _log_route_update(
        self,
        incident_id: str,
        vehicle_id: str,
        old_route: Any,
        new_route: Any,
        old_eta: Optional[float],
        new_eta: Optional[float],
        old_reliability: Optional[float],
        new_reliability: Optional[float],
        reason: str
    ):
        """Log route change for debugging."""
        update_id = f"RU-{uuid4().hex[:8]}"
        update = RouteUpdate(
            id=update_id,
            incident_id=incident_id,
            vehicle_id=vehicle_id,
            old_route_json=old_route,
            new_route_json=new_route,
            old_eta_min=old_eta,
            new_eta_min=new_eta,
            old_reliability_score=old_reliability,
            new_reliability_score=new_reliability,
            reason=reason
        )
        self.db.add(update)
        self.db.commit()

    def get_dispatch_log(self, incident_id: str) -> List[Dict[str, Any]]:
        """Get audit log for incident."""
        logs = self.db.query(DispatchLog).filter(
            DispatchLog.incident_id == incident_id
        ).order_by(DispatchLog.created_at).all()

        return [
            {
                "action": log.action,
                "actor": log.actor,
                "timestamp": log.created_at.isoformat(),
                "details": log.details
            }
            for log in logs
        ]

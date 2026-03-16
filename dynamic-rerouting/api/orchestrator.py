"""
Emergency Response Orchestration Service

Central service that orchestrates all components:
- Incident management
- Vehicle routing and simulation
- DQN-based rerouting
- WebSocket broadcasting
- Location inference
"""

import logging
import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from incident_service import IncidentService
from vehicle_simulator import simulation_daemon, GeoCalc
from dqn_rerouting_service import dqn_rerouting_service
from location_inference import location_inference_service
from websocket_manager import manager

logger = logging.getLogger(__name__)


class EmergencyResponseOrchestrator:
    """Orchestrates emergency response workflow."""

    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session
        self.incident_service = IncidentService(db_session) if db_session else None
        self.rerouting_checks_interval_sec = 30  # Check for rerouting every 30s
        self.active_rerouting_tasks: Dict[str, asyncio.Task] = {}

    async def dispatch_incident(
        self,
        incident_id: str,
        vehicle_id: str,
        hospital_id: str,
        vehicle_start_lat: float,
        vehicle_start_lon: float,
        incident_lat: float,
        incident_lon: float,
        hospital_lat: float,
        hospital_lon: float,
        city_name: str = "Indore"
    ) -> Dict[str, Any]:
        """
        Main dispatch workflow:
        1. Update incident state to DISPATCHED
        2. Calculate route via SUMO
        3. Start vehicle simulation
        4. Begin dynamic rerouting monitor
        5. Broadcast to all clients
        """
        
        logger.info(f"Dispatching incident {incident_id} to vehicle {vehicle_id}")

        # 1. Update incident state
        incident = self.incident_service.update_incident_state(
            incident_id,
            "DISPATCHED",
            actor="dispatcher"
        )

        # 2. Assign vehicle and hospital
        self.incident_service.assign_vehicle(incident_id, vehicle_id)
        self.incident_service.assign_hospital(incident_id, hospital_id)

        # 3. Calculate route (mock SUMO call)
        route_data = self._mock_calculate_route(
            vehicle_start_lat,
            vehicle_start_lon,
            incident_lat,
            incident_lon,
            hospital_lat,
            hospital_lon,
            city_name
        )

        # 4. Update vehicle with route
        self.incident_service.update_vehicle_route(
            vehicle_id,
            route_data["waypoints"],
            incident_lat,
            incident_lon,
            route_data["eta_min"],
            route_data["reliability_score"],
            reason="calculated"
        )

        # 5. Start vehicle simulation
        sim = simulation_daemon.register_vehicle(
            vehicle_id,
            vehicle_start_lat,
            vehicle_start_lon
        )
        waypoints = [(lat, lon) for lat, lon in route_data["waypoints"]]
        sim.set_route(waypoints, target_speed_kmh=60.0)

        # 6. Broadcast incident update
        scene = self.incident_service.get_digital_emergency_scene(incident_id)
        await manager.broadcast_incident_update(scene)

        # 7. Start dynamic rerouting monitor
        rerouting_task = asyncio.create_task(
            self._monitor_rerouting(incident_id, vehicle_id)
        )
        self.active_rerouting_tasks[vehicle_id] = rerouting_task

        logger.info(f"Dispatch complete. Vehicle {vehicle_id} en route. ETA: {route_data['eta_min']:.1f}m")

        return {
            "status": "dispatched",
            "incident_id": incident_id,
            "vehicle_id": vehicle_id,
            "route": route_data,
            "scene": scene
        }

    async def _monitor_rerouting(self, incident_id: str, vehicle_id: str):
        """
        Continuously monitor vehicle and trigger rerouting if beneficial.
        Runs every 30 seconds while vehicle is active.
        """
        logger.info(f"Started rerouting monitor for vehicle {vehicle_id}")

        while True:
            try:
                # Check if vehicle is still active
                sim = simulation_daemon.get_vehicle(vehicle_id)
                if not sim or not sim.is_active:
                    logger.info(f"Vehicle {vehicle_id} no longer active. Stopping monitor.")
                    break

                # Get current vehicle position and state
                vehicle_data = self.incident_service.get_incident(incident_id)
                if not vehicle_data or not vehicle_data.assigned_vehicle_id:
                    break

                # Get current vehicle sim position
                position = sim.get_position()

                # Check for blockages on the current route
                route_waypoints = [(w[0], w[1]) for w in vehicle_data.current_route_json] if vehicle_data.current_route_json else []
                if not route_waypoints:
                    await asyncio.sleep(self.rerouting_checks_interval_sec)
                    continue

                from blockage_simulator import blockage_simulator
                affected_blockages = blockage_simulator.get_blockages_on_route(route_waypoints)
                
                # Calculate real impact
                eta_increase, reliability_decrease = blockage_simulator.get_blockage_impact(route_waypoints)
                current_reliability = max(0.5, 0.95 - reliability_decrease)

                # Mock traffic conditions (could be expanded)
                traffic_conditions = {
                    "congestion_current": 0.4 + (0.3 * len(affected_blockages)),
                    "congestion_predicted": 0.5,
                    "incident_count": len(affected_blockages),
                    "weather": "Clear"
                }

                # Query DQN for rerouting decision
                current_state = {
                    "speed": position["speed_kmh"],
                    "distance_remaining": max(0, position["total_distance_km"] - position["distance_traveled_km"]),
                    "queue_length": len(affected_blockages),
                    "num_alternatives": 2
                }

                should_reroute, decision_details = dqn_rerouting_service.should_reroute(
                    vehicle_id=vehicle_id,
                    current_state=current_state,
                    traffic_prediction=traffic_conditions,
                    current_reliability=current_reliability,
                    alternative_reliability=0.92,
                    eta_delta_min=eta_increase  # Use real ETA increase as potential gain
                )

                logger.debug(f"Rerouting decision for {vehicle_id}: {decision_details['decision']}")

                # If rerouting recommended, trigger it
                if should_reroute:
                    await self._perform_reroute(
                        incident_id,
                        vehicle_id,
                        decision_details
                    )

                # Wait before next check
                await asyncio.sleep(self.rerouting_checks_interval_sec)

            except Exception as e:
                logger.error(f"Error in rerouting monitor for {vehicle_id}: {e}")
                await asyncio.sleep(self.rerouting_checks_interval_sec)

    async def _perform_reroute(
        self,
        incident_id: str,
        vehicle_id: str,
        decision_details: Dict[str, Any]
    ):
        """Execute rerouting: calculate new route, update vehicle, broadcast."""
        logger.info(f"Performing reroute for vehicle {vehicle_id}: {decision_details['decision']}")

        # Mock new route calculation
        new_route = self._mock_calculate_alternative_route(vehicle_id)

        # Update vehicle route
        self.incident_service.update_vehicle_route(
            vehicle_id,
            new_route["waypoints"],
            new_route["dest_lat"],
            new_route["dest_lon"],
            new_route["eta_min"],
            new_route["reliability_score"],
            reason="dqn_optimization"
        )

        # Update simulator with new route
        sim = simulation_daemon.get_vehicle(vehicle_id)
        if sim and sim.route_waypoints:
            waypoints = [(lat, lon) for lat, lon in new_route["waypoints"]]
            sim.set_route(waypoints, target_speed_kmh=60.0)

        # Broadcast rerouting to all
        await manager.broadcast_reroute(
            vehicle_id,
            {
                "old_eta_min": 12.0,  # Mock old ETA
                "new_eta_min": new_route["eta_min"],
                "old_reliability_score": 0.95,
                "new_reliability_score": new_route["reliability_score"],
                "reason": "Dynamic optimization - traffic ahead",
                "new_route_json": new_route["waypoints"]
            }
        )

        logger.info(f"Reroute broadcast for vehicle {vehicle_id}. New ETA: {new_route['eta_min']:.1f}m")

    # ────────────────────────────────────────────────────────────────────
    # Mock Routing (to be replaced with actual SUMO calls)
    # ────────────────────────────────────────────────────────────────────

    def _mock_calculate_route(
        self,
        start_lat: float,
        start_lon: float,
        dest_lat: float,
        dest_lon: float,
        hospital_lat: float,
        hospital_lon: float,
        city_name: str
    ) -> Dict[str, Any]:
        """Mock route calculation."""
        
        # Calculate distance from start to incident
        dist_to_incident = GeoCalc.haversine_distance(
            start_lat, start_lon, dest_lat, dest_lon
        )
        
        # Generate waypoints (mock: 5-10 intermediate points)
        num_waypoints = max(5, int(dist_to_incident / 2.0))
        waypoints = []
        for i in range(num_waypoints):
            fraction = i / max(num_waypoints - 1, 1)
            lat = start_lat + (dest_lat - start_lat) * fraction
            lon = start_lon + (dest_lon - start_lon) * fraction
            waypoints.append([lat, lon])
        
        # Add hospital as final waypoint
        waypoints.append([hospital_lat, hospital_lon])
        
        # Calculate ETA (assume 60 km/h average)
        total_dist = dist_to_incident + GeoCalc.haversine_distance(
            dest_lat, dest_lon, hospital_lat, hospital_lon
        )
        eta_min = (total_dist / 60.0) * 60.0
        
        return {
            "waypoints": waypoints,
            "dest_lat": hospital_lat,
            "dest_lon": hospital_lon,
            "total_distance_km": total_dist,
            "eta_min": eta_min,
            "reliability_score": 0.95
        }

    def _mock_calculate_alternative_route(self, vehicle_id: str) -> Dict[str, Any]:
        """Mock alternative route calculation (slightly shorter)."""
        return {
            "waypoints": [
                [22.7533, 75.8937],
                [22.7550, 75.8920],
                [22.7580, 75.8900]
            ],
            "dest_lat": 22.7600,
            "dest_lon": 75.9000,
            "eta_min": 9.0,  # Shorter than original 12 min
            "reliability_score": 0.92
        }


# Global instance
orchestrator = EmergencyResponseOrchestrator()

"""
Vehicle Simulator

Handles:
- Smooth vehicle movement along route
- Position generation for WebSocket broadcasting
- ETA tracking
- Route progress management
"""

import logging
import time
import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)


class GeoCalc:
    """Geodetic calculations for vehicle movement."""
    
    EARTH_RADIUS_KM = 6371.0
    
    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two lat/lon points in kilometers."""
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        
        return GeoCalc.EARTH_RADIUS_KM * c
    
    @staticmethod
    def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate bearing from point 1 to point 2 in degrees."""
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lon = math.radians(lon2 - lon1)
        
        y = math.sin(delta_lon) * math.cos(lat2_rad)
        x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon)
        
        bearing = math.degrees(math.atan2(y, x))
        return (bearing + 360) % 360
    
    @staticmethod
    def destination_point(lat: float, lon: float, bearing: float, distance_km: float) -> Tuple[float, float]:
        """Calculate destination point given start, bearing, and distance."""
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        bearing_rad = math.radians(bearing)
        
        angular_distance = distance_km / GeoCalc.EARTH_RADIUS_KM
        
        lat_2 = math.asin(
            math.sin(lat_rad) * math.cos(angular_distance) +
            math.cos(lat_rad) * math.sin(angular_distance) * math.cos(bearing_rad)
        )
        
        lon_2 = lon_rad + math.atan2(
            math.sin(bearing_rad) * math.sin(angular_distance) * math.cos(lat_rad),
            math.cos(angular_distance) - math.sin(lat_rad) * math.sin(lat_2)
        )
        
        return math.degrees(lat_2), math.degrees(lon_2)


class VehicleSimulator:
    """Simulates realistic vehicle movement along a route."""
    
    def __init__(self, vehicle_id: str, start_lat: float, start_lon: float):
        self.vehicle_id = vehicle_id
        self.current_lat = start_lat
        self.current_lon = start_lon
        self.current_speed = 0.0  # km/h
        self.target_speed = 60.0  # Ambulance typical speed
        self.max_speed = 80.0  # km/h
        
        # Route info
        self.route_waypoints: List[Tuple[float, float]] = []
        self.current_waypoint_index = 0
        self.total_distance = 0.0
        self.distance_traveled = 0.0
        
        # Timing
        self.start_time: Optional[datetime] = None
        self.estimated_arrival_time: Optional[datetime] = None
        self.last_update_time = datetime.utcnow()
        
        # State tracking
        self.is_active = False
        self.speed_variation = 0.0  # Random speed factor
        
        logger.info(f"VehicleSimulator initialized for {vehicle_id} at ({start_lat}, {start_lon})")

    def set_route(self, route_waypoints: List[Tuple[float, float]], target_speed: float = 60.0):
        """Set route as list of (lat, lon) waypoints."""
        self.route_waypoints = route_waypoints
        self.target_speed = target_speed
        self.current_waypoint_index = 0
        self.distance_traveled = 0.0
        self.start_time = datetime.utcnow()
        
        # Calculate total distance
        self.total_distance = 0.0
        for i in range(len(self.route_waypoints) - 1):
            lat1, lon1 = self.route_waypoints[i]
            lat2, lon2 = self.route_waypoints[i + 1]
            self.total_distance += GeoCalc.haversine_distance(lat1, lon1, lat2, lon2)
        
        # Calculate ETA
        travel_time_hours = self.total_distance / self.target_speed
        self.estimated_arrival_time = self.start_time + timedelta(hours=travel_time_hours)
        
        self.is_active = True
        logger.info(f"Route set: {len(self.route_waypoints)} waypoints, {self.total_distance:.2f}km, ETA: {travel_time_hours * 60:.1f}m")

    def get_eta_minutes(self) -> float:
        """Get estimated time to arrival in minutes."""
        if not self.estimated_arrival_time:
            return 0.0
        
        remaining = (self.estimated_arrival_time - datetime.utcnow()).total_seconds() / 60.0
        return max(0.0, remaining)

    def update_position(self, delta_time_seconds: float = 1.0):
        """Update vehicle position. Call this periodically (simulation step)."""
        if not self.is_active or not self.route_waypoints:
            return

        # Accelerate/decelerate towards target speed with some randomness
        self.speed_variation = 0.95 + (hash(self.vehicle_id + str(datetime.utcnow().timestamp())) % 10) / 100.0
        actual_target = self.target_speed * self.speed_variation
        
        # Smooth acceleration (reduced for more realistic startup)
        acceleration_rate = 0.05  # was 0.1
        if self.current_speed < actual_target:
            self.current_speed = min(self.current_speed + acceleration_rate, actual_target)
        else:
            self.current_speed = max(self.current_speed - acceleration_rate, actual_target)

        # Distance covered in this timestep (km)
        distance_this_step = (self.current_speed / 3600.0) * (delta_time_seconds / 1000.0)
        self.distance_traveled += distance_this_step

        # Find current position along route
        if self.current_waypoint_index >= len(self.route_waypoints) - 1:
            # Reached destination
            lat, lon = self.route_waypoints[-1]
            self.current_lat = lat
            self.current_lon = lon
            self.is_active = False
            logger.info(f"Vehicle {self.vehicle_id} reached destination")
            return

        # Get segment from current to next waypoint
        lat1, lon1 = self.route_waypoints[self.current_waypoint_index]
        lat2, lon2 = self.route_waypoints[self.current_waypoint_index + 1]
        segment_distance = GeoCalc.haversine_distance(lat1, lon1, lat2, lon2)

        # Check if we should move to next waypoint
        cumulative_distance = 0.0
        for i in range(self.current_waypoint_index):
            if i < len(self.route_waypoints) - 1:
                lat_i, lon_i = self.route_waypoints[i]
                lat_i1, lon_i1 = self.route_waypoints[i + 1]
                cumulative_distance += GeoCalc.haversine_distance(lat_i, lon_i, lat_i1, lon_i1)

        position_in_segment = self.distance_traveled - cumulative_distance

        # Advance to next waypoint if we've passed current one
        if position_in_segment > segment_distance:
            self.current_waypoint_index += 1
            if self.current_waypoint_index >= len(self.route_waypoints) - 1:
                lat, lon = self.route_waypoints[-1]
                self.current_lat = lat
                self.current_lon = lon
                self.is_active = False
                logger.info(f"Vehicle {self.vehicle_id} reached destination")
                return
            lat1, lon1 = self.route_waypoints[self.current_waypoint_index]
            lat2, lon2 = self.route_waypoints[self.current_waypoint_index + 1]
            segment_distance = GeoCalc.haversine_distance(lat1, lon1, lat2, lon2)
            position_in_segment = 0.0

        # Interpolate position within segment
        if segment_distance > 0:
            fraction = position_in_segment / segment_distance
            bearing_angle = GeoCalc.bearing(lat1, lon1, lat2, lon2)
            distance_to_move = fraction * segment_distance
            
            new_lat, new_lon = GeoCalc.destination_point(lat1, lon1, bearing_angle, distance_to_move)
            self.current_lat = new_lat
            self.current_lon = new_lon

        self.last_update_time = datetime.utcnow()

    def get_position(self) -> Dict[str, float]:
        """Get current position and telemetry."""
        return {
            "vehicle_id": self.vehicle_id,
            "lat": self.current_lat,
            "lon": self.current_lon,
            "speed_kmh": self.current_speed,
            "distance_traveled_km": self.distance_traveled,
            "total_distance_km": self.total_distance,
            "eta_minutes": self.get_eta_minutes(),
            "is_active": self.is_active,
            "waypoint_index": self.current_waypoint_index,
            "timestamp": datetime.utcnow().isoformat()
        }

    def stop(self):
        """Stop the vehicle."""
        self.is_active = False
        self.current_speed = 0.0
        logger.info(f"Vehicle {self.vehicle_id} stopped")


class VehicleSimulationDaemon:
    """Async daemon that updates all active vehicles and broadcasts positions."""
    
    def __init__(self):
        self.vehicles: Dict[str, VehicleSimulator] = {}
        self.running = False
        self.update_frequency_hz = 1  # was 2 (Updates per second)
        self.update_interval_ms = 1000 / self.update_frequency_hz
        
    def register_vehicle(self, vehicle_id: str, start_lat: float, start_lon: float) -> VehicleSimulator:
        """Register a new vehicle for simulation."""
        sim = VehicleSimulator(vehicle_id, start_lat, start_lon)
        self.vehicles[vehicle_id] = sim
        logger.info(f"Registered vehicle {vehicle_id}")
        return sim

    def get_vehicle(self, vehicle_id: str) -> Optional[VehicleSimulator]:
        """Get simulator for a vehicle."""
        return self.vehicles.get(vehicle_id)

    async def run(self):
        """Main daemon loop."""
        self.running = True
        logger.info("Vehicle simulation daemon started")

        while self.running:
            try:
                # Update all active vehicles
                for vehicle_id, sim in list(self.vehicles.items()):
                    if sim.is_active:
                        sim.update_position(delta_time_seconds=self.update_interval_ms)

                # Sleep until next update
                await asyncio.sleep(self.update_interval_ms / 1000.0)
            except Exception as e:
                logger.error(f"Error in vehicle simulation loop: {e}")
                await asyncio.sleep(0.1)

    def stop(self):
        """Stop the daemon."""
        self.running = False
        for sim in self.vehicles.values():
            sim.stop()
        logger.info("Vehicle simulation daemon stopped")


# Global instance
simulation_daemon = VehicleSimulationDaemon()

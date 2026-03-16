"""
Blockage Simulator - Adds realistic traffic blockages to the system

Simulates random traffic incidents, congestion, and blockages that affect
vehicle routing in real-time. Integrates with rerouting service.
"""

import asyncio
import random
import logging
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from websocket_manager import manager
except ImportError:
    manager = None

logger = logging.getLogger(__name__)


class BlockageType(str, Enum):
    """Types of traffic blockages."""
    ACCIDENT = "accident"
    CONGESTION = "congestion"
    ROADWORK = "roadwork"
    WEATHER = "weather"
    PROTEST = "protest"
    BREAKDOWN = "breakdown"


@dataclass
class TrafficBlockage:
    """Represents a traffic blockage on the route."""
    id: str
    type: BlockageType
    lat: float
    lon: float
    severity: float  # 0-1, where 1 is complete closure
    description: str
    created_at: datetime
    estimated_clear_time_min: float  # How long it takes to clear (minutes)
    affected_segments: List[Tuple[float, float]]  # List of (lat, lon) on affected route
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "lat": self.lat,
            "lon": self.lon,
            "severity": self.severity,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "estimated_clear_time_min": self.estimated_clear_time_min,
            "affected_segments": self.affected_segments,
        }


class BlockageSimulator:
    """Simulates and manages traffic blockages."""
    
    def __init__(self):
        self.active_blockages: Dict[str, TrafficBlockage] = {}
        self.blockage_counter = 0
        self.is_running = False
        
    async def start(self):
        """Start the blockage simulator background task."""
        self.is_running = True
        asyncio.create_task(self._blockage_generator_loop())
        logger.info("✅ Blockage simulator started")
    
    async def stop(self):
        """Stop the blockage simulator."""
        self.is_running = False
        logger.info("⏹️ Blockage simulator stopped")
    
    async def _blockage_generator_loop(self):
        """
        Main loop that randomly creates blockages:
        - Every 2-4 minutes, create 1-2 new blockages
        - Each blockage lasts 5-15 minutes
        - Keep total blockages low (1-3 at a time)
        """
        blockage_checks = [
            {
                "lat": 22.7400,
                "lon": 75.8950,
                "segment_name": "Bhawarkuan Square",
            },
            {
                "lat": 22.7533,
                "lon": 75.8937,
                "segment_name": "Apollo Hospital Road",
            },
            {
                "lat": 22.7450,
                "lon": 75.8980,
                "segment_name": "Main Street West",
            },
            {
                "lat": 22.7350,
                "lon": 75.8900,
                "segment_name": "NH-52 Junction",
            },
            {
                "lat": 22.7500,
                "lon": 75.9000,
                "segment_name": "City Hospital Road",
            },
        ]
        
        while self.is_running:
            try:
                # Wait 30-60 seconds before creating new blockage (was 2-4 minutes)
                wait_time = random.uniform(30, 60)
                await asyncio.sleep(wait_time)
                
                if not self.is_running:
                    break
                
                # Only create blockage if we have < 5 active ones (was <3, now more for demo)
                if len(self.active_blockages) < 5 and random.random() > 0.3:
                    num_blockages = random.randint(1, 2)
                    for _ in range(num_blockages):
                        if len(self.active_blockages) < 3:
                            blockage_spot = random.choice(blockage_checks)
                            blockage = await self.create_blockage(
                                lat=blockage_spot["lat"],
                                lon=blockage_spot["lon"],
                                segment_name=blockage_spot["segment_name"],
                            )
                            # Broadcast to all clients
                            if manager:
                                await manager.broadcast_to_dispatch({
                                    "type": "BLOCKAGE_ALERT",
                                    "blockage": blockage.to_dict()
                                })
                
                # Remove expired blockages
                now = datetime.now()
                expired = [
                    bid for bid, b in self.active_blockages.items()
                    if (now - b.created_at).total_seconds() > (b.estimated_clear_time_min * 60)
                ]
                for bid in expired:
                    self._clear_blockage(bid)
                    
            except Exception as e:
                logger.error(f"Error in blockage generator loop: {e}")
                await asyncio.sleep(5)
    
    async def create_blockage(
        self,
        lat: float,
        lon: float,
        segment_name: str,
        blockage_type: BlockageType = None,
    ) -> TrafficBlockage:
        """Create a new random blockage."""
        if blockage_type is None:
            blockage_type = random.choice(list(BlockageType))
        
        severity = random.uniform(0.3, 0.95)  # 30-95% closure
        clear_time = random.uniform(5, 15)  # 5-15 minutes
        
        blockage_id = f"BLK-{self.blockage_counter:04d}"
        self.blockage_counter += 1
        
        descriptions = {
            BlockageType.ACCIDENT: f"Vehicle collision on {segment_name}",
            BlockageType.CONGESTION: f"Heavy traffic congestion at {segment_name}",
            BlockageType.ROADWORK: f"Road maintenance/construction on {segment_name}",
            BlockageType.WEATHER: f"Severe weather affecting {segment_name}",
            BlockageType.PROTEST: f"Street protest blocking {segment_name}",
            BlockageType.BREAKDOWN: f"Vehicle breakdown causing traffic on {segment_name}",
        }
        
        blockage = TrafficBlockage(
            id=blockage_id,
            type=blockage_type,
            lat=lat,
            lon=lon,
            severity=severity,
            description=descriptions.get(blockage_type, f"Traffic blockage at {segment_name}"),
            created_at=datetime.now(),
            estimated_clear_time_min=clear_time,
            affected_segments=[(lat, lon)],  # In production, calculate affected route segments
        )
        
        self.active_blockages[blockage_id] = blockage
        logger.warning(f"🚨 NEW BLOCKAGE: {blockage.description} (severity: {severity:.0%})")
        
        return blockage
    
    def _clear_blockage(self, blockage_id: str):
        """Clear a blockage from the system."""
        if blockage_id in self.active_blockages:
            blockage = self.active_blockages.pop(blockage_id)
            logger.info(f"✅ BLOCKAGE CLEARED: {blockage.description}")
    
    def get_blockages(self) -> List[Dict[str, Any]]:
        """Get all active blockages."""
        return [b.to_dict() for b in self.active_blockages.values()]
    
    def get_blockages_on_route(
        self,
        route_waypoints: List[Tuple[float, float]],
        radius_km: float = 1.0,
    ) -> List[TrafficBlockage]:
        """
        Get blockages that affect the given route.
        
        Args:
            route_waypoints: List of (lat, lon) waypoints
            radius_km: Detection radius in kilometers
        
        Returns:
            List of blockages that intersect with the route
        """
        affected_blockages = []
        
        for blockage in self.active_blockages.values():
            # Check if blockage is near any waypoint
            for lat, lon in route_waypoints:
                distance = GeoCalc.haversine_distance(
                    lat, lon, blockage.lat, blockage.lon
                )
                if distance <= radius_km:
                    affected_blockages.append(blockage)
                    break
        
        return affected_blockages
    
    def get_blockage_impact(
        self,
        route_waypoints: List[Tuple[float, float]],
    ) -> Tuple[float, float]:
        """
        Calculate blockage impact on route:
        - eta_increase_min: Additional time due to blockages
        - reliability_decrease: How much blockage affects reliability
        
        Returns:
            (eta_increase_min, reliability_decrease)
        """
        affected_blockages = self.get_blockages_on_route(route_waypoints)
        
        if not affected_blockages:
            return 0.0, 0.0
        
        # Sum up impacts
        total_eta_increase = sum(
            b.estimated_clear_time_min * (b.severity * 0.7)  # Not 100% impact
            for b in affected_blockages
        )
        
        # Reliability decreases by blockage severity
        total_reliability_decrease = sum(
            b.severity * 0.15 for b in affected_blockages  # Each blockage: -15% for severe
        )
        
        return total_eta_increase, min(total_reliability_decrease, 0.5)  # Max 50% decrease


# Global simulator instance
blockage_simulator = BlockageSimulator()


# Haversine distance helper (import from vehicle_simulator in production)
class GeoCalc:
    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in km."""
        import math
        R = 6371  # Earth's radius in km
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

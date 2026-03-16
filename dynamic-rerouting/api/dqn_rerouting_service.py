"""
DQN-Based Dynamic Rerouting Service

Integrates the trained DQN model (Model 3) with real-time routing decisions.
Queries the model to determine if rerouting is beneficial based on:
- Current vehicle state
- Traffic conditions (from Model 1 predictions)
- Route reliability (from Model 2)
"""

import logging
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class DQNReroutingService:
    """Manages DQN-based rerouting decisions."""

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize DQN model for rerouting.
        
        Args:
            model_path: Path to trained DQN model (can be deferred)
        """
        self.model = None
        self.model_loaded = False
        self.model_path = model_path
        
        if model_path:
            self._load_model(model_path)

    def _load_model(self, model_path: str):
        """Load trained DQN model."""
        try:
            from stable_baselines3 import DQN
            
            if Path(model_path).exists():
                self.model = DQN.load(model_path)
                self.model_loaded = True
                logger.info(f"✅ DQN model loaded from {model_path}")
            else:
                logger.warning(f"⚠️ Model path not found: {model_path}")
                logger.warning("⚠️ Using mock rerouting decisions")
        except Exception as e:
            logger.warning(f"⚠️ Failed to load DQN model: {e}")
            logger.warning("⚠️ Using mock rerouting decisions")

    def should_reroute(
        self,
        vehicle_id: str,
        current_state: Dict[str, Any],
        traffic_prediction: Dict[str, Any],
        current_reliability: float,
        alternative_reliability: float,
        eta_delta_min: float
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Determine if vehicle should be rerouted using DQN policy.
        
        Args:
            vehicle_id: Vehicle identifier
            current_state: {speed, distance_remaining, queue_length, ...}
            traffic_prediction: From Model 1 (congestion forecast)
            current_reliability: Current route reliability score
            alternative_reliability: Potential new route reliability
            eta_delta_min: ETA improvement in minutes (positive = improvement)
            
        Returns:
            (should_reroute, decision_details)
        """
        
        # Build state vector for DQN
        state_vector = self._build_state_vector(
            current_state,
            traffic_prediction,
            current_reliability,
            alternative_reliability,
            eta_delta_min
        )

        if self.model_loaded and self.model:
            # Query DQN policy
            action, _ = self.model.predict(state_vector, deterministic=True)
            decision = int(action)
        else:
            # Mock decision: reroute if ETA improvement > 2 min and reliability > 0.80
            decision = 1 if (eta_delta_min > 2.0 and alternative_reliability > 0.80) else 0

        should_reroute = decision == 1  # Action 1 = reroute
        
        return should_reroute, {
            "vehicle_id": vehicle_id,
            "decision": "REROUTE" if should_reroute else "MAINTAIN",
            "state_vector": state_vector.tolist(),
            "dqn_action": int(decision),
            "eta_improvement_min": eta_delta_min,
            "current_reliability": current_reliability,
            "alternative_reliability": alternative_reliability,
            "model_used": "DQN" if self.model_loaded else "MOCK"
        }

    def _build_state_vector(
        self,
        current_state: Dict[str, Any],
        traffic_prediction: Dict[str, Any],
        current_reliability: float,
        alternative_reliability: float,
        eta_delta_min: float
    ) -> np.ndarray:
        """
        Build normalized state vector for DQN input.
        Expected state shape: (6,) - [speed, distance, density, pred_density, queue, alternatives]
        """
        
        # Extract and normalize values
        speed_kmh = current_state.get("speed", 0.0)
        distance_remaining_km = current_state.get("distance_remaining", 0.0)
        queue_length = current_state.get("queue_length", 0.0)
        congestion_current = traffic_prediction.get("congestion_current", 0.3)
        congestion_predicted = traffic_prediction.get("congestion_predicted", 0.4)
        num_alternatives = current_state.get("num_alternatives", 1.0)
        
        # Normalize to [0, 1]
        state = np.array([
            min(speed_kmh / 80.0, 1.0),              # Max speed ~80 km/h
            min(distance_remaining_km / 50.0, 1.0),  # Max distance ~50 km
            min(congestion_current, 1.0),            # 0.0 - 1.0
            min(congestion_predicted, 1.0),          # 0.0 - 1.0
            min(queue_length / 100.0, 1.0),          # Max queue ~100 vehicles
            min(num_alternatives / 5.0, 1.0)         # Max ~5 alternatives
        ], dtype=np.float32)
        
        return state

    def evaluate_route_alternative(
        self,
        current_route: List[str],
        alternative_route: List[str],
        traffic_conditions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate if alternative route is better than current.
        Returns comparison metrics.
        """
        
        # Mock route evaluation (in production, would compute from SUMO)
        current_eta = self._estimate_eta(current_route, traffic_conditions)
        alternative_eta = self._estimate_eta(alternative_route, traffic_conditions)
        
        # Reliability scoring
        current_reliability = self._compute_reliability(current_route, traffic_conditions)
        alternative_reliability = self._compute_reliability(alternative_route, traffic_conditions)
        
        eta_improvement = current_eta - alternative_eta
        
        return {
            "current_route": {
                "edges": current_route,
                "eta_min": current_eta,
                "reliability": current_reliability
            },
            "alternative_route": {
                "edges": alternative_route,
                "eta_min": alternative_eta,
                "reliability": alternative_reliability,
                "eta_improvement_min": eta_improvement,
                "reliability_improvement": alternative_reliability - current_reliability
            },
            "should_switch": eta_improvement > 2.0 and alternative_reliability > 0.80
        }

    def _estimate_eta(self, route: List[str], traffic: Dict[str, Any]) -> float:
        """Estimate ETA for a route given traffic conditions."""
        # Mock: assume each edge is ~1 km, speed varies by congestion
        num_edges = len(route)
        base_speed = 60.0  # km/h
        congestion_factor = 1.0 + (traffic.get("congestion_level", 0.3) * 0.5)
        actual_speed = base_speed / congestion_factor
        
        distance_km = num_edges * 1.0  # Assume 1 km per edge
        eta_minutes = (distance_km / actual_speed) * 60.0
        return eta_minutes

    def _compute_reliability(self, route: List[str], traffic: Dict[str, Any]) -> float:
        """Compute reliability score for a route."""
        # Base reliability
        reliability = 0.95
        
        # Reduce by congestion
        congestion = traffic.get("congestion_level", 0.3)
        reliability -= (congestion * 0.3)
        
        # Reduce by incidents on route
        num_incidents = traffic.get("incident_count", 0)
        reliability -= (num_incidents * 0.05)
        
        # Reduce by weather
        weather_impact = traffic.get("weather_impact", 0.0)
        reliability -= weather_impact
        
        return max(0.4, min(0.98, reliability))

    def get_rerouting_decision_history(self) -> List[Dict[str, Any]]:
        """Get historical rerouting decisions (for debugging)."""
        # In production, store in database
        return []


# Global instance
dqn_rerouting_service = DQNReroutingService()

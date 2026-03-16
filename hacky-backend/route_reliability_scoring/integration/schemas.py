"""
schemas.py — Shared type contracts for the integration pipeline.

Preserved from orchestrator/schemas.py during codebase cleanup.
These dataclasses define the shape of data flowing between Models 1, 2, and 3.

Currently the integration pipeline uses plain dicts for flexibility,
but these types are available for stricter typing when needed.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class VehicleState:
    """Telemetry for the vehicle being routed."""

    vehicle_id: str
    position: str           # current edge ID
    current_speed: float    # m/s
    remaining_distance: float  # meters to destination


@dataclass
class Model1Prediction:
    """
    Container for Model 1 output mapped from the /predict endpoint in
    external/Traffic_Model1/emergency-routing-model1/inference/api.py
    """

    city: str
    congestion_t5: float
    congestion_t10: float
    congestion_t20: float
    congestion_t30: float
    uncertainty_t5: float
    uncertainty_t10: float
    uncertainty_t20: float
    uncertainty_t30: float

    @property
    def predicted_density(self) -> float:
        """
        Convenience scalar used by Model 3 — we expose T+10 as the default
        predictive density ahead on the route.
        """
        return float(self.congestion_t10)


@dataclass
class RouteCandidate:
    """One candidate route for Model 2 / Model 3."""

    route_id: str
    edges: List[str]
    features: Dict[str, Any]  # Must contain the 17 Model 2 FEATURES


@dataclass
class Model2Output:
    """Aggregated output from Model 2 suitable to feed Model 3."""

    routes: List[Dict[str, Any]]  # Per-route results with reliability and ETA


@dataclass
class Model2ForModel3:
    """
    Minimal JSON-like view passed into Model 3's RoutingServiceAPI.
    Matches the format expected by dynamic-rerouting's predict_best_route().
    """

    congested_edges: List[str]
    queue_length: float


@dataclass
class RoutingDecision:
    """
    Final output of the full three-model pipeline.
    Mirrors dynamic-rerouting's predict_best_route() return shape.
    """

    vehicle_id: str
    action: str  # "stay" or "reroute"
    new_route: Optional[List[str]] = None

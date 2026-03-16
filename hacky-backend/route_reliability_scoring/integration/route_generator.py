"""
route_generator.py — Generates candidate routes for Model 2 scoring.

In production this would query a graph routing engine (OSRM, Valhalla, etc.)
or use SUMO's TraCI to compute k-shortest paths.

This module provides a mock implementation for local testing.
"""

from typing import Any, Dict, List


# Route templates representing different route strategies
_ROUTE_TEMPLATES = [
    {
        "suffix": "highway",
        "road_class": 2,           # highway
        "distance_factor": 1.3,    # longer but potentially faster
        "intersection_count": 4,
        "has_bridge": 1,
        "has_tunnel": 0,
        "has_rail_crossing": 0,
        "incidents_per_km_month": 0.3,
    },
    {
        "suffix": "arterial",
        "road_class": 1,           # arterial
        "distance_factor": 1.0,    # baseline distance
        "intersection_count": 12,
        "has_bridge": 0,
        "has_tunnel": 0,
        "has_rail_crossing": 0,
        "incidents_per_km_month": 0.7,
    },
    {
        "suffix": "local",
        "road_class": 0,           # local road
        "distance_factor": 0.9,    # shorter but slower
        "intersection_count": 18,
        "has_bridge": 0,
        "has_tunnel": 0,
        "has_rail_crossing": 1,
        "incidents_per_km_month": 1.2,
    },
    {
        "suffix": "bypass",
        "road_class": 2,           # highway bypass
        "distance_factor": 1.6,    # much longer, avoids city
        "intersection_count": 3,
        "has_bridge": 1,
        "has_tunnel": 1,
        "has_rail_crossing": 0,
        "incidents_per_km_month": 0.2,
    },
    {
        "suffix": "inner_ring",
        "road_class": 1,           # arterial ring road
        "distance_factor": 1.1,
        "intersection_count": 9,
        "has_bridge": 0,
        "has_tunnel": 0,
        "has_rail_crossing": 0,
        "incidents_per_km_month": 0.9,
    },
]


def generate_candidate_routes(
    start: str,
    destination: str,
    k: int = 3,
    base_distance_km: float = 5.0,
) -> List[Dict[str, Any]]:
    """
    Generate k candidate routes between start and destination.

    In production, replace this with calls to OSRM, Google Directions,
    or TraCI's findRoute/findIntermodalRoute.

    Parameters
    ----------
    start : str
        Starting location name (e.g. "hospital").
    destination : str
        Destination name (e.g. "accident_location").
    k : int
        Number of candidate routes to generate (max 5).
    base_distance_km : float
        Approximate direct-line distance between start and destination.

    Returns
    -------
    list of dict
        Each dict contains: route_id, edges, distance_km,
        road_class, intersection_count, has_bridge, has_tunnel,
        has_rail_crossing, incidents_per_km_month.
    """
    candidates = []

    for i in range(min(k, len(_ROUTE_TEMPLATES))):
        t = _ROUTE_TEMPLATES[i]
        dist = round(base_distance_km * t["distance_factor"], 2)

        # Generate mock edge IDs for this route
        n_edges = max(3, int(dist * 2))
        edges = [f"edge_{start}_{i}_{j}" for j in range(n_edges)]

        candidates.append(
            {
                "route_id": f"route_{start}_to_{destination}_{t['suffix']}",
                "edges": edges,
                "distance_km": dist,
                "road_class": t["road_class"],
                "intersection_count": t["intersection_count"],
                "has_bridge": t["has_bridge"],
                "has_tunnel": t["has_tunnel"],
                "has_rail_crossing": t["has_rail_crossing"],
                "incidents_per_km_month": t["incidents_per_km_month"],
            }
        )

    return candidates

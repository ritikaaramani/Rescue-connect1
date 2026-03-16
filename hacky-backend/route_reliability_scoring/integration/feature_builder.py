"""
feature_builder.py — Converts Model 1 output into Model 2 feature DataFrames.

Bridges the gap between:
  - Model 1: city-level congestion forecasts (t5, t10, t20, t30)
  - Model 2: per-route feature vectors (17 features per candidate route)

This module does NOT modify any external repository code.
"""

from datetime import datetime
from typing import Any, Dict, List

import numpy as np
import pandas as pd


def build_model2_features(
    model1_output: Dict[str, Any],
    candidate_routes: List[Dict[str, Any]],
    weather_coeff: float = 1.0,
) -> pd.DataFrame:
    """
    Build a DataFrame of Model 2 features for each candidate route.

    Parameters
    ----------
    model1_output : dict
        Output from Model 1's /predict endpoint, containing:
        congestion_t5, congestion_t10, congestion_t20, congestion_t30,
        uncertainty_t5..t30.

    candidate_routes : list of dict
        Each dict describes a candidate route with keys:
        - route_id: str
        - edges: list of str (edge IDs)
        - distance_km: float
        - road_class: int (0=local, 1=arterial, 2=highway)
        - intersection_count: int
        - has_bridge: int (0 or 1)
        - has_tunnel: int (0 or 1)
        - has_rail_crossing: int (0 or 1)
        - incidents_per_km_month: float (optional, default 0.5)

    weather_coeff : float
        Weather coefficient: 0.7=rain, 0.85=cloudy, 1.0=clear.

    Returns
    -------
    pd.DataFrame
        One row per route, with all 17 Model 2 FEATURES columns plus
        route_id and edges for traceability.
    """
    # Extract Model 1 predictions
    cong_t5 = float(model1_output.get("congestion_t5", 0.3))
    cong_t10 = float(model1_output.get("congestion_t10", 0.3))
    cong_t20 = float(model1_output.get("congestion_t20", 0.35))

    # Compute congestion variance from uncertainty values
    uncertainties = [
        model1_output.get("uncertainty_t5", 0.1),
        model1_output.get("uncertainty_t10", 0.12),
        model1_output.get("uncertainty_t20", 0.14),
        model1_output.get("uncertainty_t30", 0.16),
    ]
    congestion_variance = float(np.mean(uncertainties))

    # Time features
    now = datetime.now()
    hour = now.hour
    dow = now.weekday()
    is_rush = int(
        (8 <= hour <= 10) or (13 <= hour <= 14) or (18 <= hour <= 21)
    )
    is_weekend = int(dow >= 5)

    rows = []
    for route in candidate_routes:
        dist_km = route.get("distance_km", 5.0)

        # ETA formula matches Model 2's training data generation:
        # eta_minutes = route_distance_km * (1.2 + avg_congestion_score * 1.8)
        eta = dist_km * (1.2 + cong_t5 * 1.8)

        row = {
            # Traceability columns (not part of the 17 features)
            "route_id": route["route_id"],
            "edges": route.get("edges", []),
            # The 17 Model 2 features:
            "road_class": route.get("road_class", 1),
            "intersection_count": route.get("intersection_count", 5),
            "has_bridge": route.get("has_bridge", 0),
            "has_tunnel": route.get("has_tunnel", 0),
            "has_rail_crossing": route.get("has_rail_crossing", 0),
            "route_distance_km": dist_km,
            "congestion_variance": congestion_variance,
            "avg_congestion_score": cong_t5,      # ← From Model 1 T+5
            "predicted_score_T10": cong_t10,       # ← From Model 1 T+10
            "predicted_score_T20": cong_t20,       # ← From Model 1 T+20
            "incidents_per_km_month": route.get("incidents_per_km_month", 0.5),
            "hour_of_day": hour,
            "day_of_week": dow,
            "is_rush_hour": is_rush,
            "is_weekend": is_weekend,
            "weather_coeff": weather_coeff,
            "eta_minutes": round(eta, 2),
        }
        rows.append(row)

    return pd.DataFrame(rows)

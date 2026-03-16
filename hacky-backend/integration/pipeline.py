"""
pipeline.py — Integration pipeline: Model 1 → Model 2 → Model 3.

This module does NOT modify either external repository.
It imports from them and orchestrates the full prediction flow.

Usage (from project root):
    python -m integration.pipeline

Or programmatically:
    from integration.pipeline import run_emergency_pipeline
    result = run_emergency_pipeline(start="hospital", destination="accident_location")
"""

import sys
import json
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd

# Ensure project root is importable
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Model 2 imports (from project root)
from model2 import load_model2, score_routes

# Local integration imports
from integration.feature_builder import build_model2_features
from integration.route_generator import generate_candidate_routes


# ---------------------------------------------------------------------------
# Step 1: Model 1 — Traffic Prediction
# ---------------------------------------------------------------------------

def call_model1(city_name: str, use_mock: bool = True) -> Dict[str, Any]:
    """
    Call Model 1 for city-level congestion predictions.

    Parameters
    ----------
    city_name : str
        City name (e.g. "Bengaluru").
    use_mock : bool
        If True, return mock predictions instead of calling the live API.
        Set to False when Model 1's FastAPI server is running on port 8001.

    Returns
    -------
    dict with congestion_t5, congestion_t10, congestion_t20, congestion_t30
    and corresponding uncertainty values.
    """
    if use_mock:
        # Realistic mock that simulates moderate-to-high congestion
        rng = np.random.RandomState(42)
        base = 0.35 + rng.random() * 0.3  # range [0.35, 0.65]
        return {
            "city": city_name,
            "congestion_t5": round(base, 4),
            "congestion_t10": round(base + 0.03, 4),
            "congestion_t20": round(base + 0.08, 4),
            "congestion_t30": round(base + 0.12, 4),
            "uncertainty_t5": round(0.10 + rng.random() * 0.05, 4),
            "uncertainty_t10": round(0.12 + rng.random() * 0.05, 4),
            "uncertainty_t20": round(0.14 + rng.random() * 0.05, 4),
            "uncertainty_t30": round(0.16 + rng.random() * 0.05, 4),
            "latency_ms": 45.0,
        }
    else:
        import requests

        resp = requests.post(
            "http://127.0.0.1:8001/predict",
            json={"city_name": city_name},
            timeout=5,
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Step 2 & 3: Route Generation + Model 2 — Reliability Scoring
# ---------------------------------------------------------------------------

def score_candidate_routes(
    model1_output: Dict[str, Any],
    start: str,
    destination: str,
    num_routes: int = 3,
    weather_coeff: float = 1.0,
    model2: Any = None,
) -> pd.DataFrame:
    """Generate candidate routes, inject Model 1 features, and score with Model 2.

    This function is called from the main pipeline and can accept an optional
    preloaded Model 2 instance to avoid loading the XGBoost model on each call.

    Returns a DataFrame sorted by reliability (descending).
    """
    # Generate candidate routes
    candidates = generate_candidate_routes(
        start=start,
        destination=destination,
        k=num_routes,
    )

    # Build Model 2 feature matrix using Model 1 output
    features_df = build_model2_features(
        model1_output=model1_output,
        candidate_routes=candidates,
        weather_coeff=weather_coeff,
    )

    # Load Model 2 once if not explicitly provided
    model = model2 if model2 is not None else load_model2()
    scored = score_routes(model, features_df)

    # Sort by reliability descending
    scored = scored.sort_values("reliability", ascending=False).reset_index(
        drop=True
    )
    return scored


# ---------------------------------------------------------------------------
# Step 4: Model 3 — Dynamic Rerouting Decision
# ---------------------------------------------------------------------------

def call_model3(
    vehicle_state: Dict[str, Any],
    model1_output: Dict[str, Any],
    model2_scored: pd.DataFrame,
    use_mock: bool = True,
) -> Dict[str, Any]:
    """
    Call Model 3's RL agent for the final routing decision.

    Parameters
    ----------
    vehicle_state : dict
        Vehicle telemetry (vehicle_id, position, current_speed, remaining_distance).
    model1_output : dict
        Model 1 prediction result.
    model2_scored : pd.DataFrame
        Model 2 scored routes with reliability column.
    use_mock : bool
        If True, simulate the RL decision without SUMO/TraCI.
        Set to False when SUMO is running and models/best_model.zip exists.

    Returns
    -------
    dict with action ("stay" or "reroute") and optionally new_route.
    """
    # Convert Model 2 output to Model 3 format
    congested_edges = []
    queue_scores = []
    for _, row in model2_scored.iterrows():
        if row["reliability"] < 0.7:
            edges = row.get("edges", [])
            if isinstance(edges, list):
                congested_edges.extend(edges)
            queue_scores.append(1.0 - row["reliability"])

    unique_congested = sorted(set(congested_edges))
    avg_queue = float(np.mean(queue_scores)) if queue_scores else 0.0

    model2_for_m3 = {
        "congested_edges": unique_congested,
        "queue_length": avg_queue * 50.0,  # Scale to match M3's normalization
    }

    model1_for_m3 = {
        "predicted_density": model1_output.get("congestion_t10", 0.5),
    }

    if use_mock:
        # Simulate RL decision based on congestion level
        pred_density = model1_for_m3["predicted_density"]
        queue_len = model2_for_m3["queue_length"]
        # Simple heuristic mimicking the DQN's learned policy:
        # - High congestion or long queues → reroute to best-reliability route
        # - Otherwise → stay on current route
        if pred_density > 0.6 or queue_len > 25:
            best_route = model2_scored.iloc[0]
            edges = best_route.get("edges", [])
            return {
                "vehicle_id": vehicle_state["vehicle_id"],
                "action": "reroute",
                "new_route": edges if isinstance(edges, list) else [],
                "reason": f"congestion={pred_density:.2f}, queue={queue_len:.1f}",
            }
        else:
            return {
                "vehicle_id": vehicle_state["vehicle_id"],
                "action": "stay",
                "reason": f"congestion={pred_density:.2f} below threshold",
            }
    else:
        # Call the real RL agent (requires SUMO + trained model)
        dyn_root = _PROJECT_ROOT / "external" / "dynamic-rerouting"
        if str(dyn_root) not in sys.path:
            sys.path.insert(0, str(dyn_root))

        from api.routing_service import RoutingServiceAPI  # type: ignore

        model_path = str(dyn_root / "models" / "best_model")
        api = RoutingServiceAPI(model_path=model_path, env_net=None)

        return api.predict_best_route(
            vehicle_state=vehicle_state,
            model1_prediction=model1_for_m3,
            model2_congestion=model2_for_m3,
        )


# ---------------------------------------------------------------------------
# Full Pipeline
# ---------------------------------------------------------------------------

def run_emergency_pipeline(
    start: str = "hospital",
    destination: str = "accident_location",
    city_name: str = "Bengaluru",
    vehicle_id: str = "ambulance_01",
    current_speed: float = 25.0,
    remaining_distance: float = 5200.0,
    weather_coeff: float = 1.0,
    use_mock: bool = True,
    verbose: bool = True,
    model2: Any = None,
) -> Dict[str, Any]:
    """Run the complete emergency routing pipeline:
    Model 1 → Route Generator → Model 2 → Model 3.

    Parameters
    ----------
    start : str
        Starting location (e.g. "hospital").
    destination : str
        Destination location (e.g. "accident_location").
    city_name : str
        City for Model 1 prediction.
    vehicle_id : str
        Vehicle identifier.
    current_speed : float
        Current vehicle speed (m/s).
    remaining_distance : float
        Distance to destination (meters).
    weather_coeff : float
        Weather coefficient (0.7=rain, 0.85=cloudy, 1.0=clear).
    use_mock : bool
        Use mock predictions for M1 and M3 (no live server needed).
    verbose : bool
        Print pipeline steps to console.

    Returns
    -------
    dict with keys: model1, model2_routes, model3_decision, best_route.
    """
    if verbose:
        print("=" * 70)
        print("  EMERGENCY ROUTING PIPELINE")
        print(f"  {start} -> {destination} ({city_name})")
        print("=" * 70)

    # ── Step 1: Model 1 — Traffic Prediction ──────────────────────────
    if verbose:
        print("\n[Step 1] Model 1 — Traffic Prediction (LSTM+GCN)")
        print(f"  City: {city_name}")

    model1_output = call_model1(city_name, use_mock=use_mock)

    if verbose:
        print(f"  Congestion T+5:  {model1_output['congestion_t5']:.4f}")
        print(f"  Congestion T+10: {model1_output['congestion_t10']:.4f}")
        print(f"  Congestion T+20: {model1_output['congestion_t20']:.4f}")
        print(f"  Congestion T+30: {model1_output['congestion_t30']:.4f}")

    # ── Step 2: Route Generation + Model 2 — Reliability Scoring ─────
    if verbose:
        print(
            "\n[Step 2] Route Generation + Model 2 — Reliability Scoring (XGBoost)"
        )

    scored_routes = score_candidate_routes(
        model1_output=model1_output,
        start=start,
        destination=destination,
        num_routes=3,
        weather_coeff=weather_coeff,
        model2=model2,
    )

    if verbose:
        print(f"  Scored {len(scored_routes)} candidate routes:")
        for _, row in scored_routes.iterrows():
            rel = row["reliability"]
            if rel >= 0.7:
                tag = "[OK]"
            elif rel >= 0.5:
                tag = "[!!]"
            else:
                tag = "[XX]"
            rid = str(row["route_id"])
            print(
                f"    {tag} {rid:50s}  "
                f"reliability={rel:.3f}  "
                f"ETA={row['eta_minutes']:.1f} min  "
                f"dist={row['route_distance_km']:.1f} km"
            )

    # ── Step 3: Model 3 — Rerouting Decision ─────────────────────────
    vehicle_state = {
        "vehicle_id": vehicle_id,
        "position": f"edge_{start}_0_0",
        "current_speed": current_speed,
        "remaining_distance": remaining_distance,
    }

    if verbose:
        print("\n[Step 3] Model 3 — Dynamic Rerouting Decision (DQN)")

    model3_decision = call_model3(
        vehicle_state=vehicle_state,
        model1_output=model1_output,
        model2_scored=scored_routes,
        use_mock=use_mock,
    )

    if verbose:
        action = model3_decision["action"]
        icon = "REROUTE" if action == "reroute" else "STAY"
        print(f"  Decision: {icon}")
        if "reason" in model3_decision:
            print(f"  Reason: {model3_decision['reason']}")
        if action == "reroute" and model3_decision.get("new_route"):
            route_preview = model3_decision["new_route"][:5]
            print(f"  New route edges: {route_preview}...")

    # ── Summary ──────────────────────────────────────────────────────
    best_route = scored_routes.iloc[0]
    result = {
        "model1": model1_output,
        "model2_routes": scored_routes[
            ["route_id", "reliability", "eta_minutes", "route_distance_km"]
        ].to_dict("records"),
        "model3_decision": model3_decision,
        "best_route": {
            "route_id": str(best_route["route_id"]),
            "reliability": float(best_route["reliability"]),
            "eta_minutes": float(best_route["eta_minutes"]),
        },
    }

    if verbose:
        print("\n" + "=" * 70)
        print("  PIPELINE COMPLETE")
        print(f"  Best route: {best_route['route_id']}")
        print(f"  Reliability: {best_route['reliability']:.3f}")
        print(f"  ETA: {best_route['eta_minutes']:.1f} min")
        print(f"  Action: {model3_decision['action']}")
        print("=" * 70)

    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    result = run_emergency_pipeline(
        start="hospital",
        destination="accident_location",
        city_name="Bengaluru",
        vehicle_id="ambulance_01",
        current_speed=25.0,
        remaining_distance=5200.0,
        weather_coeff=1.0,
        use_mock=True,
        verbose=True,
    )

    print("\n\nFull JSON result:")
    print(json.dumps(result, indent=2, default=str))

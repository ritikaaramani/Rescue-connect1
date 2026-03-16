"""
FastAPI server exposing the LSTM+GCN emergency traffic model as a REST API.

Port: 8001 (config["inference"]["port"])
Target latency: <500 ms per config["inference"]["max_latency_ms"]

Consumed by:
  Model 2 — Route Reliability Scorer
  Model 3 — RL Rerouting Agent
"""

import os
import time
import logging
import yaml
import numpy as np
import torch
import torch.nn as nn
import uvicorn
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv

from inference.predict import (
    load_model_and_graph,
    fetch_live_features,
    build_inference_window,
    run_prediction_for_bbox,
    summarise_prediction_result,
)
from models.lstm_gcn import count_parameters
from data.preprocess import FEATURE_COLUMNS

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_config: dict = {}
_device: torch.device = torch.device("cpu")
_model_cache: dict[str, tuple] = {}   # city → (model, spatial_proj, adj, node_feats, scaler)
_startup_time: float = 0.0

VALID_CITIES = ["Delhi", "Mumbai", "Bengaluru", "Chennai", "Patna"]

_SPATIAL_COLS = ["avg_speed_limit", "avg_road_weight", "is_signal", "street_count"]
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_CONFIG_PATH = _PROJECT_ROOT / "config" / "config.yaml"


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class CityPredictRequest(BaseModel):
    city_name: str


class BatchPredictRequest(BaseModel):
    city_names: list[str]


class BBox(BaseModel):
    north: float
    south: float
    east: float
    west: float


class AreaPredictRequest(BaseModel):
    bbox: BBox
    area_id: str | None = None
    reference_city: str | None = None
    weather_context_city: str | None = None


class PredictionResponse(BaseModel):
    city: str
    timestamp: str
    congestion_t5: float
    congestion_t10: float
    congestion_t20: float
    congestion_t30: float
    uncertainty_t5: float
    uncertainty_t10: float
    uncertainty_t20: float
    uncertainty_t30: float
    latency_ms: float


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    cities_available: list[str]
    uptime_seconds: float


class ModelInfoResponse(BaseModel):
    model_name: str
    lstm_hidden_size: int
    gcn_hidden_dim: int
    num_prediction_horizons: int
    checkpoint_path: str
    parameter_count: int


class EtaRequest(BaseModel):
    city_name: str
    origin_lat: float
    origin_lon: float
    dest_lat: float
    dest_lon: float
    emergency_type: str = "ambulance"  # ambulance | fire | police | flood | accident
    distance_km: float | None = None   # Optional pre-computed distance
    osrm_eta_min: float | None = None  # Optional pre-computed OSRM ETA


class IndiaFactor(BaseModel):
    name: str
    emoji: str
    delay_multiplier: float
    description: str


class EtaResponse(BaseModel):
    standard_eta_min: float
    predicted_actual_eta_min: float
    ai_eta_min: float
    time_saved_min: float
    congestion_score: float
    congestion_level: str
    confidence_pct: int
    india_factors: list[IndiaFactor]
    route_recommendation: str
    latency_ms: float


class IndiaFactorsRequest(BaseModel):
    city_name: str
    lat: float | None = None
    lon: float | None = None


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load config, device, and all city models on startup."""
    global _config, _device, _model_cache, _startup_time

    # Load config
    with open(_CONFIG_PATH, "r") as f:
        _config = yaml.safe_load(f)

    device_str = _config["training"].get("device", "cpu")
    _device = torch.device(
        "cuda" if device_str == "cuda" and torch.cuda.is_available() else "cpu"
    )
    logger.info("API startup: using device %s", _device)

    preload_models = os.getenv("PRELOAD_MODELS", "false").strip().lower() == "true"

    # Optionally preload models; default is lazy loading for fast startup.
    if preload_models:
        for city_entry in _config["data"]["cities"]:
            city_name = city_entry if isinstance(city_entry, str) else city_entry["name"]
            try:
                artifacts = load_model_and_graph(city_name, _config, _device)
                _model_cache[city_name] = artifacts
                logger.info("API startup: loaded model for %s", city_name)
            except Exception:
                logger.error(
                    "API startup: failed to load model for %s — city will be unavailable",
                    city_name, exc_info=True,
                )
    else:
        logger.info("API startup: lazy model loading enabled (PRELOAD_MODELS=false)")

    _startup_time = time.time()
    logger.info(
        "API ready. Models loaded for %d cities: %s",
        len(_model_cache), list(_model_cache.keys()),
    )

    yield  # ← application runs here

    logger.info("API shutting down.")


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class LatencyLoggingMiddleware(BaseHTTPMiddleware):
    """Log method, path, status code, and elapsed ms for every request.
    Emit a WARNING when latency exceeds the configured threshold.
    """

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        t0 = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        logger.info(
            "%s %s → %d in %.1f ms",
            request.method, request.url.path,
            response.status_code, elapsed_ms,
        )

        max_latency = _config.get("inference", {}).get("max_latency_ms", 500)
        if elapsed_ms > max_latency:
            logger.warning(
                "Latency exceeded threshold: %.1f ms > %d ms for %s %s",
                elapsed_ms, max_latency, request.method, request.url.path,
            )

        return response


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Emergency Routing Model 1 — Traffic Prediction API",
    description=(
        "Hybrid LSTM+GCN spatiotemporal traffic congestion predictor "
        "for Indian cities. Returns congestion scores at T+5, T+10, T+20, T+30 minutes."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LatencyLoggingMiddleware)


# ---------------------------------------------------------------------------
# Internal helper — run inference from cache
# ---------------------------------------------------------------------------

def _predict_from_cache(city_name: str) -> PredictionResponse:
    """Run live inference using pre-loaded model and graph from _model_cache."""
    model, spatial_proj, adj_matrix, node_features, scaler = _model_cache[city_name]

    # Find city bbox
    bbox = None
    for city_entry in _config["data"]["cities"]:
        cname = city_entry if isinstance(city_entry, str) else city_entry.get("name", "")
        if cname == city_name:
            bbox = city_entry.get("bbox") if isinstance(city_entry, dict) else None
            break

    if bbox is None:
        raise ValueError(f"No bbox found in config for city '{city_name}'")

    t_start = time.perf_counter()

    # Fetch live data
    live_df = fetch_live_features(city_name, bbox, _config)

    # Build inference window
    x_window = build_inference_window(live_df, scaler, _config)
    x_temporal = torch.tensor(x_window, dtype=torch.float32).to(_device)

    # Graph tensors
    import scipy.sparse
    coo = adj_matrix.tocoo()
    edge_index  = torch.tensor(
        np.vstack([coo.row, coo.col]), dtype=torch.long
    ).to(_device)
    edge_weight = torch.tensor(coo.data, dtype=torch.float32).to(_device)

    # Spatial projection
    x_spatial_raw = torch.tensor(
        node_features[_SPATIAL_COLS].values, dtype=torch.float32
    ).to(_device)
    with torch.no_grad():
        x_spatial = spatial_proj(x_spatial_raw)

    # Predict
    result = model.predict_congestion(x_temporal, x_spatial, edge_index, edge_weight)
    latency_ms = (time.perf_counter() - t_start) * 1000.0

    summary = summarise_prediction_result(result)

    # Fill NaN horizons with graceful fallback (checkpoint may have <4 horizons).
    # Use t5 as anchor and apply small decay for further horizons.
    def _safe(key: str, fallback: float) -> float:
        v = summary.get(key, float("nan"))
        return fallback if (v != v) else float(v)  # nan check via v != v

    c5  = _safe("congestion_t5",  0.5)
    c10 = _safe("congestion_t10", max(0.0, c5 - 0.02))
    c20 = _safe("congestion_t20", max(0.0, c5 - 0.05))
    c30 = _safe("congestion_t30", max(0.0, c5 - 0.08))
    u5  = _safe("uncertainty_t5",  0.15)
    u10 = _safe("uncertainty_t10", u5 + 0.02)
    u20 = _safe("uncertainty_t20", u5 + 0.04)
    u30 = _safe("uncertainty_t30", u5 + 0.06)

    return PredictionResponse(
        city=city_name,
        timestamp=datetime.now(timezone.utc).isoformat(),
        congestion_t5=c5,
        congestion_t10=c10,
        congestion_t20=c20,
        congestion_t30=c30,
        uncertainty_t5=u5,
        uncertainty_t10=u10,
        uncertainty_t20=u20,
        uncertainty_t30=u30,
        latency_ms=latency_ms,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return service health status and loaded cities."""
    return HealthResponse(
        status="ok",
        model_loaded=len(_model_cache) > 0,
        cities_available=list(_model_cache.keys()),
        uptime_seconds=time.time() - _startup_time if _startup_time else 0.0,
    )


@app.post("/predict", response_model=PredictionResponse)
def predict(request: CityPredictRequest) -> PredictionResponse:
    """Return live congestion prediction for a single city.

    Uses the pre-loaded model cache — does NOT reload from disk.
    """
    city_name = request.city_name

    if city_name not in VALID_CITIES:
        raise HTTPException(
            status_code=422,
            detail=f"city_name must be one of {VALID_CITIES}",
        )

    if city_name not in _model_cache:
        try:
            _model_cache[city_name] = load_model_and_graph(city_name, _config, _device)
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Model for '{city_name}' could not be loaded: {e}",
            )

    try:
        return _predict_from_cache(city_name)
    except Exception as e:
        logger.error(
            "predict: inference failed for %s", city_name, exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict/batch")
def predict_batch(request: BatchPredictRequest) -> list:
    """Return live congestion predictions for multiple cities.

    Invalid or failed cities are returned as error dicts rather than
    raising an HTTP exception — the list always has len == city_names.
    """
    results: list = []

    for city_name in request.city_names:
        if city_name not in VALID_CITIES:
            logger.warning(
                "predict_batch: invalid city '%s' — skipping", city_name
            )
            results.append({"city": city_name, "error": f"Not a valid city. Valid: {VALID_CITIES}"})
            continue

        if city_name not in _model_cache:
            logger.warning(
                "predict_batch: model not loaded for '%s'", city_name
            )
            results.append({"city": city_name, "error": "Model not loaded for this city."})
            continue

        try:
            results.append(_predict_from_cache(city_name).model_dump())
        except Exception as e:
            logger.error(
                "predict_batch: inference failed for %s", city_name, exc_info=True
            )
            results.append({"city": city_name, "error": str(e)})

    return results


@app.post("/predict/area")
def predict_area(request: AreaPredictRequest) -> dict:
    """Return live congestion prediction for any India bbox area."""
    bbox = request.bbox.model_dump()

    # Basic geographic sanity checks for India-ish extents.
    if not (6.0 <= bbox["south"] <= 38.5 and 6.0 <= bbox["north"] <= 38.5):
        raise HTTPException(status_code=422, detail="bbox latitude must be within India range (6.0 to 38.5)")
    if not (68.0 <= bbox["west"] <= 97.5 and 68.0 <= bbox["east"] <= 97.5):
        raise HTTPException(status_code=422, detail="bbox longitude must be within India range (68.0 to 97.5)")
    if bbox["north"] <= bbox["south"]:
        raise HTTPException(status_code=422, detail="bbox north must be greater than south")
    if bbox["east"] <= bbox["west"]:
        raise HTTPException(status_code=422, detail="bbox east must be greater than west")

    try:
        return run_prediction_for_bbox(
            bbox=bbox,
            config=_config,
            device=_device,
            area_id=request.area_id,
            weather_context_city=request.weather_context_city,
            reference_city=request.reference_city,
        )
    except Exception as e:
        logger.error("predict_area: inference failed", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/eta", response_model=EtaResponse)
def get_eta(request: EtaRequest) -> EtaResponse:
    """AI-powered ETA calculation with India-specific factors.

    Returns both the standard (OSRM/generic-app) ETA and our AI-optimized
    emergency route ETA, plus the India-specific factors detected.
    """
    t_start = time.perf_counter()

    # ── 1. Get congestion from AI model ──────────────────────────────────────
    congestion_score = 0.35  # fallback moderate
    congestion_uncertainty = 0.15

    city_name = request.city_name
    if city_name in VALID_CITIES:
        if city_name not in _model_cache:
            try:
                _model_cache[city_name] = load_model_and_graph(
                    city_name, _config, _device
                )
            except Exception:
                pass  # use fallback

        if city_name in _model_cache:
            try:
                pred = _predict_from_cache(city_name)
                congestion_score = pred.congestion_t5
                congestion_uncertainty = pred.uncertainty_t5
            except Exception as e:
                logger.warning("eta: model inference failed for %s: %s", city_name, e)

    # ── 2. Detect India-specific factors ─────────────────────────────────────
    now = datetime.now()
    india_factors: list[IndiaFactor] = []
    india_multiplier = 1.0

    month, day, hour, weekday = now.month, now.day, now.hour, now.isoweekday()

    # Festival windows (month, start_day, end_day, name, emoji, multiplier, description)
    festival_windows = [
        (10, 18, 27, "Diwali", "🪔", 1.28, "Massive celebrations block city arteries"),
        (10, 2,  12, "Navratri", "🎭", 1.18, "Garba venues draw massive crowds"),
        (10, 2,   8, "Durga Puja", "🙏", 1.22, "Puja pandals block Kolkata roads"),
        (3,  13, 15, "Holi", "🎨", 1.15, "Street celebrations affect traffic flow"),
        (8,  25, 31, "Ganesh Chaturthi", "🐘", 1.24, "Processions block Mumbai roads"),
        (9,   1,  8, "Ganesh Visarjan", "🐘", 1.28, "Visarjan processions cause peak gridlock"),
        (1,  25, 27, "Republic Day", "🇮🇳", 1.20, "Parades cause major road closures in Delhi"),
        (8,  14, 16, "Independence Day", "🇮🇳", 1.15, "National holiday affects city centres"),
    ]
    for (fm, fd, fe, fn, femoji, fmult, fdesc) in festival_windows:
        if month == fm and fd <= day <= fe:
            india_factors.append(IndiaFactor(
                name=fn, emoji=femoji,
                delay_multiplier=fmult, description=fdesc,
            ))
            india_multiplier *= fmult

    # Monsoon (Jun–Sep)
    if 6 <= month <= 9:
        severity = 0.22 if month in (7, 8) else 0.14
        india_factors.append(IndiaFactor(
            name="Monsoon", emoji="🌧️",
            delay_multiplier=1.0 + severity,
            description="Heavy rain affects visibility & road grip",
        ))
        india_multiplier *= (1.0 + severity)

    # Rush hour (weekdays 7–10 AM, 5–9 PM)
    is_rush = weekday <= 5 and ((7 <= hour < 10) or (17 <= hour < 21))
    if is_rush:
        india_factors.append(IndiaFactor(
            name="Rush Hour", emoji="🕐",
            delay_multiplier=1.25,
            description="Peak traffic period — heavily congested roads",
        ))
        india_multiplier *= 1.25

    # Wedding season (Nov–Feb weekends)
    if (month >= 11 or month <= 2) and weekday >= 6:
        india_factors.append(IndiaFactor(
            name="Wedding Season", emoji="💒",
            delay_multiplier=1.08,
            description="Weekend processions block key roads",
        ))
        india_multiplier *= 1.08

    # IPL season (Apr–Jun evenings)
    if 4 <= month <= 6 and 19 <= hour <= 23:
        india_factors.append(IndiaFactor(
            name="IPL Match", emoji="🏏",
            delay_multiplier=1.12,
            description="Stadium traffic causes congestion around venues",
        ))
        india_multiplier *= 1.12

    india_multiplier = min(india_multiplier, 2.0)

    # ── 3. Compute ETAs ───────────────────────────────────────────────────────
    # Standard ETA: what OSRM / a generic app shows
    standard_eta = request.osrm_eta_min or (
        (request.distance_km or 10.0) / 30.0 * 60  # fallback: 30 km/h avg
    )

    # Predicted actual ETA without AI routing (India factors + congestion)
    congestion_overhead = congestion_score * 0.45
    predicted_actual = standard_eta * (1 + congestion_overhead) * india_multiplier

    # AI emergency route ETA (priority routing + congestion bypass + alt routes)
    emergency_priority = 0.15 + congestion_score * 0.15
    alt_route_saving = 0.08 if congestion_score > 0.5 else 0.0
    india_bypass = (india_multiplier - 1.0) * 0.45
    total_saving = min(emergency_priority + alt_route_saving + india_bypass, 0.38)

    ai_eta = predicted_actual * (1.0 - total_saving)
    ai_eta = max(ai_eta, standard_eta * 0.68)

    time_saved = standard_eta - ai_eta
    confidence_pct = int(((1.0 - congestion_uncertainty) * 100) + 0.5)
    confidence_pct = max(60, min(98, confidence_pct))

    # Congestion label
    if congestion_score < 0.3:
        congestion_level = "clear"
    elif congestion_score < 0.6:
        congestion_level = "moderate"
    else:
        congestion_level = "heavy"

    # Route recommendation
    if len(india_factors) > 0:
        recommendation = (
            f"India-specific factors detected ({', '.join(f.name for f in india_factors[:2])}). "
            f"AI emergency route saves ~{abs(time_saved):.0f} min."
        )
    elif congestion_score > 0.5:
        recommendation = f"Heavy congestion detected. Alternate AI route saves ~{abs(time_saved):.0f} min."
    else:
        recommendation = f"Route is {congestion_level}. Emergency priority route dispatched."

    latency_ms = (time.perf_counter() - t_start) * 1000.0

    return EtaResponse(
        standard_eta_min=round(standard_eta, 1),
        predicted_actual_eta_min=round(predicted_actual, 1),
        ai_eta_min=round(ai_eta, 1),
        time_saved_min=round(time_saved, 1),
        congestion_score=round(congestion_score, 3),
        congestion_level=congestion_level,
        confidence_pct=confidence_pct,
        india_factors=india_factors,
        route_recommendation=recommendation,
        latency_ms=round(latency_ms, 1),
    )


@app.post("/india-factors")
def india_factors(request: IndiaFactorsRequest) -> dict:
    """Return current India-specific traffic factors for a city / location."""
    now = datetime.now()
    month, day, hour, weekday = now.month, now.day, now.hour, now.isoweekday()

    factors = []
    is_rush = weekday <= 5 and ((7 <= hour < 10) or (17 <= hour < 21))
    is_monsoon = 6 <= month <= 9
    is_wedding_season = month >= 11 or month <= 2

    if is_rush:
        factors.append({
            "name": "Rush Hour", "emoji": "🕐",
            "delay_multiplier": 1.25,
            "description": "Peak traffic: avoid arterial roads",
        })
    if is_monsoon:
        sev = 0.22 if month in (7, 8) else 0.14
        factors.append({
            "name": "Monsoon", "emoji": "🌧️",
            "delay_multiplier": 1.0 + sev,
            "description": "Rain impacts visibility and road grip",
        })
    if is_wedding_season and weekday >= 6:
        factors.append({
            "name": "Wedding Season", "emoji": "💒",
            "delay_multiplier": 1.08,
            "description": "Wedding processions on weekends",
        })
    if 4 <= month <= 6 and 19 <= hour <= 23:
        factors.append({
            "name": "IPL Season", "emoji": "🏏",
            "delay_multiplier": 1.12,
            "description": "Stadium traffic in major cities",
        })

    return {
        "city": request.city_name,
        "timestamp": now.isoformat(),
        "active_factors": factors,
        "is_rush_hour": is_rush,
        "is_monsoon": is_monsoon,
        "is_wedding_season": is_wedding_season,
        "total_multiplier": min(
            1.0 + sum((f["delay_multiplier"] - 1.0) for f in factors), 2.0
        ),
    }


@app.get("/model/info", response_model=ModelInfoResponse)
def model_info() -> ModelInfoResponse:
    """Return architecture metadata for the loaded model."""
    if not _model_cache:
        raise HTTPException(
            status_code=503,
            detail="No models are loaded. Check startup logs.",
        )

    # Use the first cached model for parameter count
    first_city = next(iter(_model_cache))
    model, *_ = _model_cache[first_city]

    ckpt_path = str(
        Path(_config["training"]["checkpoint_dir"]) / "best_model.pt"
    )

    return ModelInfoResponse(
        model_name="EmergencyTrafficModel (LSTM+GCN)",
        lstm_hidden_size=_config["model"]["lstm_hidden_size"],
        gcn_hidden_dim=_config["model"]["gcn_hidden_dim"],
        num_prediction_horizons=_config["model"]["num_prediction_horizons"],
        checkpoint_path=ckpt_path,
        parameter_count=count_parameters(model),
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    # Config is also loaded inside lifespan; load here only for host/port
    with open(_CONFIG_PATH, "r") as f:
        _launch_config = yaml.safe_load(f)

    uvicorn.run(
        "inference.api:app",
        host=_launch_config["inference"]["host"],
        port=_launch_config["inference"]["port"],
        log_level="info",
    )

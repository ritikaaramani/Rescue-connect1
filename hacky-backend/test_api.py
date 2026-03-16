"""FastAPI server exposing the emergency routing pipeline.

API → pipeline → Model1 → Model2 → Model3

This module wraps the existing `integration.pipeline.run_emergency_pipeline`
function and exposes it via a simple REST API for the mobile app.

Run:
    uvicorn api_server:app --reload

Endpoints:
    POST /best-route
"""

import asyncio
import logging
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from route_reliability_scoring.integration.pipeline import run_emergency_pipeline
from route_reliability_scoring.model2 import load_model2

logger = logging.getLogger(__name__)


class BestRouteRequest(BaseModel):
    start: str
    destination: str
    city: str


class BestRouteResponse(BaseModel):
    route_id: str
    eta_minutes: float
    reliability: float
    decision: Dict[str, Any]


app = FastAPI(
    title="Emergency Routing API",
    description="Wrapper API for the emergency routing pipeline (M1 → M2 → M3).",
    version="1.0",
)

# Preload Model 2 once at startup and reuse it for all requests.
# This avoids loading the XGBoost model on every request.
_model2 = None


@app.on_event("startup")
def _startup_event() -> None:
    global _model2
    _model2 = load_model2()


@app.post("/best-route", response_model=BestRouteResponse)
async def best_route(request: BestRouteRequest) -> BestRouteResponse:
    """Return the best route, ETA, reliability, and rerouting decision."""

    logger.info(f"Processing best-route request: start={request.start}, destination={request.destination}, city={request.city}")

    try:
        # Run the full pipeline with timeout protection (30 seconds).
        # Model 2 is injected so it is not loaded per-request.
        result = await asyncio.wait_for(
            asyncio.to_thread(
                run_emergency_pipeline,
                start=request.start,
                destination=request.destination,
                city_name=request.city,
                use_mock=True,
                verbose=False,
                model2=_model2,
            ),
            timeout=30.0
        )
    except asyncio.TimeoutError:
        logger.error("Pipeline timeout for request: %s", request.dict())
        raise HTTPException(status_code=504, detail="Pipeline timeout")
    except Exception as e:
        logger.error("Pipeline failed for request %s: %s", request.dict(), str(e))
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")

    best_route = result["best_route"]
    decision = result.get("model3_decision", {})

    logger.info(f"Best route selected: {best_route['route_id']}, reliability={best_route['reliability']:.3f}")

    return BestRouteResponse(
        route_id=best_route["route_id"],
        eta_minutes=best_route["eta_minutes"],
        reliability=best_route["reliability"],
        decision=decision,
    )


@app.get("/health")
def health_check() -> Dict[str, Any]:
    """Health endpoint verifying service and Model 2 readiness."""

    return {
        "status": "ok",
        "model2_loaded": _model2 is not None,
        "service": "emergency-routing",
    }


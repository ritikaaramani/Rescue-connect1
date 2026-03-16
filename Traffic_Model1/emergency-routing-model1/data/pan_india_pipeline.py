"""
Pan-India data collection + preprocessing orchestration utilities.

This module lets you collect traffic/weather snapshots over a configurable
India-wide bbox grid and run preprocessing per grid area.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from data.fetch_traffic import fetch_all_sources, save_to_parquet
from data.fetch_weather import fetch_city_weather, merge_weather_with_traffic
from data.preprocess import run_preprocessing_pipeline

logger = logging.getLogger(__name__)


def _slugify_bbox(bbox: dict) -> str:
    return (
        f"n{bbox['north']:.2f}_s{bbox['south']:.2f}_e{bbox['east']:.2f}_w{bbox['west']:.2f}"
        .replace("-", "m")
        .replace(".", "p")
    )


def generate_india_grid_bboxes(
    min_lat: float = 8.0,
    max_lat: float = 36.0,
    min_lon: float = 69.0,
    max_lon: float = 96.0,
    step_lat: float = 1.0,
    step_lon: float = 1.0,
) -> list[dict]:
    """Generate rectangular bbox tiles covering India bounds."""
    bboxes: list[dict] = []

    lat = min_lat
    while lat < max_lat:
        next_lat = min(lat + step_lat, max_lat)
        lon = min_lon
        while lon < max_lon:
            next_lon = min(lon + step_lon, max_lon)
            bboxes.append(
                {
                    "north": next_lat,
                    "south": lat,
                    "east": next_lon,
                    "west": lon,
                }
            )
            lon = next_lon
        lat = next_lat

    return bboxes


def _default_weather_context_city(config: dict) -> str:
    first = config["data"]["cities"][0]
    return first if isinstance(first, str) else first["name"]


def collect_area_snapshot(
    bbox: dict,
    area_id: str,
    config: dict,
    weather_context_city: str | None = None,
) -> int:
    """Collect one merged traffic+weather snapshot for a grid area.

    Returns number of merged rows saved.
    """
    weather_city = weather_context_city or _default_weather_context_city(config)

    traffic_df = fetch_all_sources(bbox=bbox, config=config, city_name=area_id)
    if traffic_df.empty:
        logger.warning("collect_area_snapshot: no traffic rows for %s", area_id)
        return 0

    weather = fetch_city_weather(
        city_name=weather_city,
        lat=(bbox["north"] + bbox["south"]) / 2.0,
        lon=(bbox["east"] + bbox["west"]) / 2.0,
        config=config,
    )
    merged = merge_weather_with_traffic(traffic_df, weather)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    out_path = Path(config["data"]["raw_data_dir"]) / area_id / f"traffic_{timestamp}.parquet"
    save_to_parquet(merged, str(out_path))
    return len(merged)


def run_pan_india_collection_and_preprocessing(
    config: dict,
    step_lat: float = 1.0,
    step_lon: float = 1.0,
    max_areas: int | None = None,
    min_rows_required: int = 20,
) -> dict:
    """Collect and preprocess data over a pan-India grid.

    Areas with fewer than `min_rows_required` rows are skipped for preprocessing.
    """
    bboxes = generate_india_grid_bboxes(step_lat=step_lat, step_lon=step_lon)
    if max_areas is not None:
        bboxes = bboxes[:max_areas]

    processed_areas: list[str] = []
    skipped_areas: list[str] = []

    for bbox in bboxes:
        area_id = f"area_{_slugify_bbox(bbox)}"
        try:
            row_count = collect_area_snapshot(bbox=bbox, area_id=area_id, config=config)
            if row_count < min_rows_required:
                skipped_areas.append(area_id)
                logger.info(
                    "run_pan_india_collection_and_preprocessing: skipping %s (rows=%d < %d)",
                    area_id,
                    row_count,
                    min_rows_required,
                )
                continue

            run_preprocessing_pipeline(city_name=area_id, config=config)
            processed_areas.append(area_id)
            logger.info("run_pan_india_collection_and_preprocessing: processed %s", area_id)
        except Exception:
            skipped_areas.append(area_id)
            logger.error(
                "run_pan_india_collection_and_preprocessing: failed for %s",
                area_id,
                exc_info=True,
            )

    return {
        "total_areas": len(bboxes),
        "processed_count": len(processed_areas),
        "skipped_count": len(skipped_areas),
        "processed_areas": processed_areas,
        "skipped_areas": skipped_areas,
    }


if __name__ == "__main__":
    import yaml

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    with open("config/config.yaml", "r") as f:
        cfg = yaml.safe_load(f)

    summary = run_pan_india_collection_and_preprocessing(
        config=cfg,
        step_lat=1.0,
        step_lon=1.0,
        max_areas=10,
        min_rows_required=20,
    )
    logger.info("Pan-India collection summary: %s", summary)

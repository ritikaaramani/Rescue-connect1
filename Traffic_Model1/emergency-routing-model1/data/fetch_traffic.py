"""
Fetches real-time traffic speed and flow data from Mappls
(MapMyIndia), HERE Traffic API v7, and Ola Maps API for
Indian city bounding boxes.

All three sources are fetched and merged into a unified
DataFrame schema. Mappls data takes priority for Indian roads.
Results are stored as Parquet files partitioned by city and
timestamp for downstream use by preprocess.py.

Data flow:
    fetch_all_sources()
        ├── fetch_mappls_traffic()  [priority 1 — India coverage]
        ├── fetch_here_traffic()    [priority 2 — global fallback]
        └── fetch_ola_maps_traffic()[priority 3 — cab GPS data]
            └── save_to_parquet()

All API calls go through fetch_with_retry() with exponential
backoff. Never call requests.get() directly anywhere.
"""

import os
import time
import uuid
import logging
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INDIA_DEFAULT_FREE_FLOW_SPEED: float = 50.0

TRAFFIC_COLUMNS: list = [
    "segment_id",
    "road_name",
    "speed_kmph",
    "free_flow_speed_kmph",
    "latitude",
    "longitude",
    "road_class",
    "jam_factor",
    "confidence",
    "source",
    "fetched_at",
]

SOURCE_PRIORITY: dict = {"mappls": 0, "here": 1, "ola": 2}


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _cast_to_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Cast a DataFrame to the canonical TRAFFIC_COLUMNS dtypes.

    Any column not already present is created with its default value so
    downstream code always receives a fully-typed DataFrame.
    """
    defaults = {
        "segment_id": "",
        "road_name": "",
        "speed_kmph": np.nan,
        "free_flow_speed_kmph": INDIA_DEFAULT_FREE_FLOW_SPEED,
        "latitude": np.nan,
        "longitude": np.nan,
        "road_class": "",
        "jam_factor": -1.0,
        "confidence": 1.0,
        "source": "",
        "fetched_at": pd.NaT,
    }
    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = default

    # Reorder and keep only schema columns
    df = df[TRAFFIC_COLUMNS].copy()

    df["segment_id"] = df["segment_id"].astype(str)
    df["road_name"] = df["road_name"].astype(str)
    df["speed_kmph"] = pd.to_numeric(df["speed_kmph"], errors="coerce").astype("float64")
    df["free_flow_speed_kmph"] = pd.to_numeric(
        df["free_flow_speed_kmph"], errors="coerce"
    ).astype("float64")
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce").astype("float64")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce").astype("float64")
    df["road_class"] = df["road_class"].astype(str)
    df["jam_factor"] = pd.to_numeric(df["jam_factor"], errors="coerce").astype("float64")
    df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce").astype("float64")
    df["source"] = df["source"].astype(str)
    df["fetched_at"] = pd.to_datetime(df["fetched_at"], utc=True)

    # Replace free_flow_speed of 0 with the Indian default
    df.loc[df["free_flow_speed_kmph"] == 0.0, "free_flow_speed_kmph"] = (
        INDIA_DEFAULT_FREE_FLOW_SPEED
    )

    return df


def _empty_df() -> pd.DataFrame:
    """Return an empty DataFrame with the canonical TRAFFIC_COLUMNS schema."""
    return _cast_to_schema(pd.DataFrame(columns=TRAFFIC_COLUMNS))


# ---------------------------------------------------------------------------
# 1. fetch_with_retry
# ---------------------------------------------------------------------------

def fetch_with_retry(
    url: str,
    params: dict,
    headers: dict = {},
    max_retries: int = 3,
) -> dict:
    """Fetch a URL with exponential backoff retry logic.

    Parameters
    ----------
    url:         Fully-qualified endpoint URL.
    params:      Query-string parameters dict.
    headers:     Optional HTTP headers dict.
    max_retries: Maximum number of attempts before raising.

    Returns
    -------
    dict  Parsed JSON response body.

    Raises
    ------
    RuntimeError  On authentication failure (401/403) or all retries exhausted.
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code in (401, 403):
                logger.error("Authentication failed for %s", url)
                raise RuntimeError(
                    f"Authentication failed for {url} (HTTP {response.status_code})"
                )

            if response.status_code == 429:
                logger.warning(
                    "Rate-limited (HTTP 429) on %s — sleeping 60 s before retry", url
                )
                time.sleep(60)
                continue

            if response.status_code >= 500:
                logger.warning(
                    "Retry %d/%d for %s — HTTP %d",
                    attempt + 1,
                    max_retries,
                    url,
                    response.status_code,
                )
                time.sleep(2 ** attempt)
                continue

            response.raise_for_status()
            return response.json()

        except (requests.ConnectionError, requests.Timeout) as exc:
            logger.warning(
                "Retry %d/%d for %s — %s", attempt + 1, max_retries, url, exc
            )
            time.sleep(2 ** attempt)

        except RuntimeError:
            raise

        except Exception as exc:
            logger.warning(
                "Retry %d/%d for %s — unexpected error: %s",
                attempt + 1,
                max_retries,
                url,
                exc,
            )
            time.sleep(2 ** attempt)

    logger.error("All %d retries exhausted for %s", max_retries, url)
    raise RuntimeError(f"All {max_retries} retries exhausted for {url}")


# ---------------------------------------------------------------------------
# 2. fetch_mappls_traffic
# ---------------------------------------------------------------------------

def fetch_mappls_traffic(
    bbox: dict,
    api_key: str,
) -> pd.DataFrame:
    """Fetch traffic data from the Mappls (MapMyIndia) API.

    Parameters
    ----------
    bbox:    Dict with keys north, south, east, west (float).
    api_key: Mappls REST API key.

    Returns
    -------
    pd.DataFrame  Rows conform to TRAFFIC_COLUMNS schema.
    """
    url = f"https://apis.mappls.com/advancedmaps/v1/{api_key}/traffic_count"
    bbox_str = (
        f"{bbox['west']},{bbox['south']},{bbox['east']},{bbox['north']}"
    )
    params = {"bbox": bbox_str}

    try:
        data = fetch_with_retry(url, params=params)
    except Exception:
        logger.error("fetch_mappls_traffic failed for bbox %s", bbox, exc_info=True)
        return _empty_df()

    # Mappls may return the segment list under various keys
    segments = (
        data.get("trafficData")
        or data.get("results")
        or data.get("data")
        or data.get("features")
        or []
    )

    if not segments:
        logger.warning("fetch_mappls_traffic: empty response for bbox %s", bbox)
        return _empty_df()

    rows = []
    now = datetime.now(timezone.utc)
    for seg in segments:
        # Some responses nest properties inside a "properties" sub-dict
        props = seg.get("properties", seg)

        raw_ffs = props.get("free_flow_speed", INDIA_DEFAULT_FREE_FLOW_SPEED)
        ffs = (
            float(raw_ffs)
            if raw_ffs not in (None, 0, 0.0, "")
            else INDIA_DEFAULT_FREE_FLOW_SPEED
        )

        rows.append(
            {
                "segment_id": str(
                    props.get("tmc") or props.get("id") or uuid.uuid4()
                ),
                "road_name": str(props.get("road_name") or props.get("name") or ""),
                "speed_kmph": props.get("speed", np.nan),
                "free_flow_speed_kmph": ffs,
                "latitude": props.get("lat", np.nan),
                "longitude": props.get("lng", np.nan),
                "road_class": str(props.get("road_class") or props.get("frc") or ""),
                "jam_factor": props.get("jam_factor", -1.0),
                "confidence": 1.0,
                "source": "mappls",
                "fetched_at": now,
            }
        )

    return _cast_to_schema(pd.DataFrame(rows))


# ---------------------------------------------------------------------------
# 3. fetch_here_traffic
# ---------------------------------------------------------------------------

def fetch_here_traffic(
    bbox: dict,
    api_key: str,
) -> pd.DataFrame:
    """Fetch traffic flow data from HERE Traffic API v7.

    Parameters
    ----------
    bbox:    Dict with keys north, south, east, west (float).
    api_key: HERE REST API key.

    Returns
    -------
    pd.DataFrame  Rows conform to TRAFFIC_COLUMNS schema.
    """
    url = "https://data.traffic.hereapi.com/v7/flow"
    bbox_str = (
        f"bbox:{bbox['west']},{bbox['south']},{bbox['east']},{bbox['north']}"
    )
    params = {
        "locationReferencing": "shape",
        "in": bbox_str,
        "apiKey": api_key,
    }

    try:
        data = fetch_with_retry(url, params=params)
    except Exception:
        logger.error("fetch_here_traffic failed for bbox %s", bbox, exc_info=True)
        return _empty_df()

    results = data.get("results", [])
    if not results:
        logger.warning("fetch_here_traffic: empty response for bbox %s", bbox)
        return _empty_df()

    rows = []
    now = datetime.now(timezone.utc)
    for result in results:
        try:
            links = result["location"]["shape"]["links"]
        except (KeyError, TypeError):
            continue

        for link in links:
            try:
                points = link.get("points", [])
                if points:
                    mid = points[len(points) // 2]
                    lat = mid.get("lat", np.nan)
                    lng = mid.get("lng", np.nan)
                else:
                    lat, lng = np.nan, np.nan

                rows.append(
                    {
                        "segment_id": str(link.get("linkId", uuid.uuid4())),
                        "road_name": "",
                        "speed_kmph": link.get("speedUncapped", np.nan),
                        "free_flow_speed_kmph": link.get(
                            "freeFlow", INDIA_DEFAULT_FREE_FLOW_SPEED
                        ),
                        "latitude": lat,
                        "longitude": lng,
                        "road_class": "",
                        "jam_factor": link.get("jamFactor", -1.0),
                        "confidence": link.get("confidence", 1.0),
                        "source": "here",
                        "fetched_at": now,
                    }
                )
            except Exception:
                logger.error(
                    "fetch_here_traffic: error parsing link %s", link, exc_info=True
                )
                continue

    if not rows:
        logger.warning("fetch_here_traffic: no parseable links for bbox %s", bbox)
        return _empty_df()

    return _cast_to_schema(pd.DataFrame(rows))


# ---------------------------------------------------------------------------
# 4. fetch_ola_maps_traffic
# ---------------------------------------------------------------------------

_OLA_CONGESTION_MAP: dict = {
    "LOW": 2.0,
    "MEDIUM": 5.0,
    "HIGH": 8.0,
    "SEVERE": 10.0,
}


def fetch_ola_maps_traffic(
    bbox: dict,
    api_key: str,
) -> pd.DataFrame:
    """Fetch traffic data from the Ola Maps Routing API.

    Parameters
    ----------
    bbox:    Dict with keys north, south, east, west (float).
    api_key: Ola Maps API key (used as Bearer token).

    Returns
    -------
    pd.DataFrame  Rows conform to TRAFFIC_COLUMNS schema.
    """
    url = "https://api.olamaps.io/routing/v1/trafficData"
    bounds = f"{bbox['south']},{bbox['west']}|{bbox['north']},{bbox['east']}"
    params = {"bounds": bounds}
    headers = {
        "X-Request-Id": str(uuid.uuid4()),
        "Authorization": f"Bearer {api_key}",
    }

    try:
        data = fetch_with_retry(url, params=params, headers=headers)
    except Exception:
        logger.error("fetch_ola_maps_traffic failed for bbox %s", bbox, exc_info=True)
        return _empty_df()

    segments = data.get("trafficSegments", [])
    if not segments:
        logger.warning("fetch_ola_maps_traffic: empty response for bbox %s", bbox)
        return _empty_df()

    rows = []
    now = datetime.now(timezone.utc)
    for seg in segments:
        try:
            congestion = seg.get("congestionLevel", "")
            jam_factor = _OLA_CONGESTION_MAP.get(str(congestion).upper(), -1.0)

            raw_ffs = seg.get("freeFlowSpeed", INDIA_DEFAULT_FREE_FLOW_SPEED)
            ffs = (
                float(raw_ffs)
                if raw_ffs not in (None, 0, 0.0, "")
                else INDIA_DEFAULT_FREE_FLOW_SPEED
            )

            rows.append(
                {
                    "segment_id": str(seg.get("segmentId", uuid.uuid4())),
                    "road_name": "",
                    "speed_kmph": seg.get("currentSpeed", np.nan),
                    "free_flow_speed_kmph": ffs,
                    "latitude": seg.get("startLat", np.nan),
                    "longitude": seg.get("startLng", np.nan),
                    "road_class": "",
                    "jam_factor": jam_factor,
                    "confidence": 1.0,
                    "source": "ola",
                    "fetched_at": now,
                }
            )
        except Exception:
            logger.error(
                "fetch_ola_maps_traffic: error parsing segment %s", seg, exc_info=True
            )
            continue

    if not rows:
        logger.warning(
            "fetch_ola_maps_traffic: no parseable segments for bbox %s", bbox
        )
        return _empty_df()

    return _cast_to_schema(pd.DataFrame(rows))


# ---------------------------------------------------------------------------
# 5. save_to_parquet
# ---------------------------------------------------------------------------

def save_to_parquet(
    df: pd.DataFrame,
    output_path: str,
) -> None:
    """Persist a traffic DataFrame to a Parquet file.

    Parameters
    ----------
    df:          DataFrame conforming to TRAFFIC_COLUMNS schema.
    output_path: Destination file path (created if absent).
    """
    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_path, engine="pyarrow", compression="snappy", index=False)
        logger.info("Saved %d rows to %s", len(df), output_path)
    except Exception:
        logger.error(
            "save_to_parquet: failed to write %s", output_path, exc_info=True
        )
        raise


# ---------------------------------------------------------------------------
# 6. fetch_all_sources  (main entry point)
# ---------------------------------------------------------------------------

def fetch_all_sources(
    bbox: dict,
    config: dict,
    city_name: str,
) -> pd.DataFrame:
    """Fetch traffic from all three sources and merge with priority ordering.

    Mappls takes priority over HERE, which takes priority over Ola Maps.
    When the same segment_id appears in multiple sources, the highest-priority
    record is kept.

    A single source failure never stops the pipeline; the error is logged and
    the remaining sources are still queried.

    Parameters
    ----------
    bbox:       Dict with keys north, south, east, west (float).
    config:     Parsed config.yaml as a plain dict.
    city_name:  Human-readable city name used for the output path.

    Returns
    -------
    pd.DataFrame  Merged, deduplicated DataFrame conforming to TRAFFIC_COLUMNS.
                  Empty DataFrame (with schema) if all three sources fail.
    """
    mappls_key = os.getenv("MAPPLS_API_KEY", "")
    here_key = os.getenv("HERE_API_KEY", "")
    ola_key = os.getenv("OLA_MAPS_API_KEY", "")

    frames: list[pd.DataFrame] = []
    sources_used: list[str] = []

    # --- Mappls (priority 1) ---
    try:
        df_mappls = fetch_mappls_traffic(bbox, mappls_key)
        if not df_mappls.empty:
            frames.append(df_mappls)
            sources_used.append("mappls")
    except Exception:
        logger.error(
            "fetch_all_sources: Mappls fetcher raised unexpectedly for %s",
            city_name,
            exc_info=True,
        )

    # --- HERE (priority 2) ---
    try:
        df_here = fetch_here_traffic(bbox, here_key)
        if not df_here.empty:
            frames.append(df_here)
            sources_used.append("here")
    except Exception:
        logger.error(
            "fetch_all_sources: HERE fetcher raised unexpectedly for %s",
            city_name,
            exc_info=True,
        )

    # --- Ola Maps (priority 3) ---
    try:
        df_ola = fetch_ola_maps_traffic(bbox, ola_key)
        if not df_ola.empty:
            frames.append(df_ola)
            sources_used.append("ola")
    except Exception:
        logger.error(
            "fetch_all_sources: Ola Maps fetcher raised unexpectedly for %s",
            city_name,
            exc_info=True,
        )

    # --- All sources failed ---
    if not frames:
        logger.critical(
            "fetch_all_sources: all three sources failed for %s — returning empty DataFrame",
            city_name,
        )
        return _empty_df()

    # --- Merge and deduplicate ---
    combined = pd.concat(frames, ignore_index=True)

    # Add a numeric priority column so we can sort and keep the best record
    combined["_priority"] = combined["source"].map(SOURCE_PRIORITY).fillna(99)
    combined.sort_values("_priority", inplace=True)
    combined.drop_duplicates(subset=["segment_id"], keep="first", inplace=True)
    combined.drop(columns=["_priority"], inplace=True)
    combined.reset_index(drop=True, inplace=True)

    # --- Persist ---
    raw_dir = config["data"]["raw_data_dir"]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    output_path = f"{raw_dir}/{city_name}/traffic_{timestamp}.parquet"
    save_to_parquet(combined, output_path)

    logger.info(
        "fetch_all_sources: %d segments from %s for %s",
        len(combined),
        sources_used,
        city_name,
    )

    return combined

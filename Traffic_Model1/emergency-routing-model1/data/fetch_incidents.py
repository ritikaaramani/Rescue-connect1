"""
Fetches real-time road incident data for Indian cities from
Mappls Traffic API (primary) and Waze CCP public feed
(secondary).

Incidents — accidents, closures, roadblocks, hazards — are
used as spike-signal features in the LSTM model. When an
incident appears, adjacent road segments experience
congestion within minutes. This file provides early warning
before speed sensors detect the slowdown.

Data flow:
    fetch_all_incidents()
        ├── fetch_mappls_incidents()  [primary — India roads]
        └── fetch_waze_incidents()    [secondary — crowdsourced]

Imports fetch_with_retry from data.fetch_traffic.
Never call requests.get() directly.
"""

import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from math import radians, sin, cos, sqrt, atan2
from dotenv import load_dotenv
from data.fetch_traffic import fetch_with_retry

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Incident type to severity mapping (0=unknown, 1=minor,
# 2=moderate, 3=severe)
INCIDENT_SEVERITY_MAP: dict = {
    # Mappls incident types
    "ACCIDENT":          3,
    "ROAD_CLOSED":       3,
    "CONSTRUCTION":      2,
    "HAZARD":            2,
    "CONGESTION":        1,
    "POLICE":            1,
    "BROKEN_DOWN":       1,
    "LANE_CLOSED":       2,
    "FLOOD":             3,
    "ROAD_BLOCKED":      3,
    # Waze incident types
    "ACCIDENT_MAJOR":    3,
    "ACCIDENT_MINOR":    1,
    "JAM":               1,
    "ROAD_CLOSED_EVENT": 3,
    "HAZARD_ON_ROAD":    2,
    "HAZARD_WEATHER":    2,
    "POLICE_VISIBLE":    1,
    "default":           1,
}

# Output columns for incident DataFrame
INCIDENT_COLUMNS: list = [
    "incident_id",
    "incident_type",
    "severity",
    "latitude",
    "longitude",
    "description",
    "road_name",
    "reported_at",
    "source",
    "fetched_at",
]


# ---------------------------------------------------------------------------
# 1. _empty_incidents_df
# ---------------------------------------------------------------------------

def _empty_incidents_df() -> pd.DataFrame:
    """Return an empty DataFrame with the canonical INCIDENT_COLUMNS schema.

    All columns are present and cast to their correct dtypes so that callers
    can always rely on a fully-typed DataFrame regardless of API availability.
    """
    df = pd.DataFrame(columns=INCIDENT_COLUMNS)
    return _cast_incidents_schema(df)


# ---------------------------------------------------------------------------
# 2. _cast_incidents_schema
# ---------------------------------------------------------------------------

def _cast_incidents_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Enforce the canonical INCIDENT_COLUMNS schema on a raw incidents DataFrame.

    Any column not already present is created with its safe default value.
    Columns are reordered to exactly INCIDENT_COLUMNS. All dtypes are cast.

    Parameters
    ----------
    df: Raw DataFrame produced by a fetcher function.

    Returns
    -------
    pd.DataFrame  Schema-conformant incidents DataFrame.
    """
    defaults: dict = {
        "incident_id":   "",
        "incident_type": "",
        "severity":      0,
        "latitude":      np.nan,
        "longitude":     np.nan,
        "description":   "",
        "road_name":     "",
        "reported_at":   pd.NaT,
        "source":        "",
        "fetched_at":    pd.NaT,
    }

    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = default

    # Reorder and keep only schema columns
    df = df[INCIDENT_COLUMNS].copy()

    # String columns
    for col in ("incident_id", "incident_type", "description", "road_name", "source"):
        df[col] = df[col].astype(str)

    # Severity → int64 (fill NaN with 0 first)
    df["severity"] = pd.to_numeric(df["severity"], errors="coerce").fillna(0).astype("int64")

    # Float columns
    df["latitude"]  = pd.to_numeric(df["latitude"],  errors="coerce").astype("float64")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce").astype("float64")

    # Datetime columns (UTC-aware)
    df["reported_at"] = pd.to_datetime(df["reported_at"], utc=True, errors="coerce")
    df["fetched_at"]  = pd.to_datetime(df["fetched_at"],  utc=True, errors="coerce")

    return df


# ---------------------------------------------------------------------------
# 3. classify_incident_severity
# ---------------------------------------------------------------------------

def classify_incident_severity(incident_type: str) -> int:
    """Map an incident type string to a severity integer (0–3).

    The lookup is case-insensitive: the input is uppercased before the
    dictionary lookup. Unknown types fall back to INCIDENT_SEVERITY_MAP["default"].

    Parameters
    ----------
    incident_type: Raw incident type string from any API source.

    Returns
    -------
    int  Severity level in {0, 1, 2, 3}.  Never raises.
    """
    try:
        key = str(incident_type).strip().upper()
        return INCIDENT_SEVERITY_MAP.get(key, INCIDENT_SEVERITY_MAP["default"])
    except Exception:
        return INCIDENT_SEVERITY_MAP["default"]


# ---------------------------------------------------------------------------
# 4. fetch_mappls_incidents
# ---------------------------------------------------------------------------

def fetch_mappls_incidents(
    bbox: dict,
    api_key: str,
) -> pd.DataFrame:
    """Fetch road incidents from the Mappls Traffic API.

    Parameters
    ----------
    bbox:    Dict with keys north, south, east, west (float).
    api_key: Mappls REST API key.

    Returns
    -------
    pd.DataFrame  Schema-conformant incidents DataFrame.
    """
    import uuid as _uuid

    url = f"https://apis.mappls.com/advancedmaps/v1/{api_key}/traffic_incidents"
    bbox_str = f"{bbox['west']},{bbox['south']},{bbox['east']},{bbox['north']}"
    params = {"bbox": bbox_str}

    try:
        data = fetch_with_retry(url, params=params)
    except Exception:
        logger.error(
            "fetch_mappls_incidents: API call failed for bbox %s", bbox,
            exc_info=True,
        )
        return _empty_incidents_df()

    # Response envelope — try known keys in order
    incidents = (
        data.get("incidents")
        or data.get("results")
        or data.get("data")
        or data.get("features")
        or []
    )

    if not incidents:
        logger.warning(
            "fetch_mappls_incidents: empty response for bbox %s", bbox
        )
        return _empty_incidents_df()

    now = datetime.now(timezone.utc)
    rows = []

    for inc in incidents:
        # Some Mappls responses nest fields under "properties"
        props = inc.get("properties", inc)

        raw_type = str(props.get("type") or props.get("incident_type") or "").strip()
        severity = classify_incident_severity(raw_type)

        # Timestamp parsing with safe fallback
        raw_ts = props.get("timestamp") or props.get("reported_at")
        try:
            reported_at = pd.to_datetime(raw_ts, utc=True)
            if pd.isna(reported_at):
                reported_at = now
        except Exception:
            reported_at = now

        rows.append({
            "incident_id":   str(props.get("id") or props.get("incident_id") or _uuid.uuid4()),
            "incident_type": raw_type.upper() if raw_type else "UNKNOWN",
            "severity":      severity,
            "latitude":      props.get("lat", np.nan),
            "longitude":     props.get("lng", np.nan),
            "description":   str(props.get("description") or props.get("desc") or ""),
            "road_name":     str(props.get("road_name")   or props.get("name")  or ""),
            "reported_at":   reported_at,
            "source":        "mappls",
            "fetched_at":    now,
        })

    return _cast_incidents_schema(pd.DataFrame(rows))


# ---------------------------------------------------------------------------
# 5. fetch_waze_incidents
# ---------------------------------------------------------------------------

def fetch_waze_incidents(bbox: dict) -> pd.DataFrame:
    """Fetch crowd-sourced road alerts from the Waze CCP public feed.

    No API key is required — this is a public endpoint.  Waze is the
    secondary source so failures are logged at WARNING level.

    Parameters
    ----------
    bbox: Dict with keys north, south, east, west (float).

    Returns
    -------
    pd.DataFrame  Schema-conformant incidents DataFrame.
    """
    import uuid as _uuid

    url = "https://www.waze.com/live-map/api/georss"
    params = {
        "top":    bbox["north"],
        "bottom": bbox["south"],
        "left":   bbox["west"],
        "right":  bbox["east"],
        "env":    "row",
        "types":  "alerts,traffic",
    }

    try:
        data = fetch_with_retry(url, params=params)
    except Exception:
        logger.warning(
            "fetch_waze_incidents: API call failed for bbox %s", bbox,
            exc_info=True,
        )
        return _empty_incidents_df()

    alerts = data.get("alerts", [])
    if not alerts:
        logger.warning(
            "fetch_waze_incidents: no alerts in response for bbox %s", bbox
        )
        return _empty_incidents_df()

    now = datetime.now(timezone.utc)
    rows = []

    for alert in alerts:
        try:
            raw_type    = str(alert.get("type",    "") or "").strip().upper()
            raw_subtype = str(alert.get("subtype", "") or "").strip().upper()

            # Combine type and subtype
            incident_type = (
                f"{raw_type}_{raw_subtype}" if raw_subtype else raw_type
            )

            # Base severity from type string, then boost with report rating
            base_severity  = classify_incident_severity(incident_type)
            report_rating  = alert.get("reportRating", 0)
            try:
                report_rating = int(report_rating)
            except (TypeError, ValueError):
                report_rating = 0

            severity = min(base_severity + 1, 3) if report_rating >= 4 else base_severity

            # Location — Waze uses "x" for longitude, "y" for latitude
            location = alert.get("location", {})
            lat = location.get("y", np.nan)
            lng = location.get("x", np.nan)

            # Timestamp from pubMillis (milliseconds since epoch)
            pub_millis = alert.get("pubMillis")
            try:
                reported_at = pd.to_datetime(pub_millis, unit="ms", utc=True)
                if pd.isna(reported_at):
                    reported_at = now
            except Exception:
                reported_at = now

            rows.append({
                "incident_id":   str(alert.get("uuid") or _uuid.uuid4()),
                "incident_type": incident_type if incident_type else "UNKNOWN",
                "severity":      severity,
                "latitude":      lat,
                "longitude":     lng,
                "description":   str(alert.get("reportDescription") or ""),
                "road_name":     str(alert.get("street") or ""),
                "reported_at":   reported_at,
                "source":        "waze",
                "fetched_at":    now,
            })

        except Exception:
            logger.warning(
                "fetch_waze_incidents: error parsing alert %s", alert,
                exc_info=True,
            )
            continue

    if not rows:
        logger.warning(
            "fetch_waze_incidents: no parseable alerts for bbox %s", bbox
        )
        return _empty_incidents_df()

    return _cast_incidents_schema(pd.DataFrame(rows))


# ---------------------------------------------------------------------------
# 6. compute_incident_impact_score
# ---------------------------------------------------------------------------

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in kilometres between two points."""
    R = 6371.0  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


def compute_incident_impact_score(
    incidents_df: pd.DataFrame,
    bbox: dict,
) -> pd.DataFrame:
    """Add an `impact_score` column to incidents_df (enriched in place).

    Impact score = severity × (1 / (1 + distance_to_bbox_centre_km))

    Higher severity incidents closer to the bbox centre receive a higher
    score, making them more influential as model features.

    Parameters
    ----------
    incidents_df: DataFrame in INCIDENT_COLUMNS schema (may include extra cols).
    bbox:         Dict with keys north, south, east, west (float).

    Returns
    -------
    pd.DataFrame  Same DataFrame with an additional float64 `impact_score` column.
    """
    center_lat = (bbox["north"] + bbox["south"]) / 2.0
    center_lon = (bbox["east"]  + bbox["west"])  / 2.0

    def _row_score(row: pd.Series) -> float:
        try:
            lat = float(row["latitude"])
            lon = float(row["longitude"])
            if np.isnan(lat) or np.isnan(lon):
                return 0.0
            dist = _haversine_km(lat, lon, center_lat, center_lon)
            return float(row["severity"]) * (1.0 / (1.0 + dist))
        except Exception:
            return 0.0

    incidents_df["impact_score"] = incidents_df.apply(_row_score, axis=1).astype("float64")
    return incidents_df


# ---------------------------------------------------------------------------
# 7. fetch_all_incidents  (main entry point)
# ---------------------------------------------------------------------------

def fetch_all_incidents(
    bbox: dict,
    config: dict,
    city_name: str,
) -> pd.DataFrame:
    """Fetch incidents from all sources, merge, deduplicate, and score.

    Mappls takes priority for deduplication — when the same incident_id
    appears in both sources, the Mappls record is kept.

    Parameters
    ----------
    bbox:      Dict with keys north, south, east, west (float).
    config:    Parsed config.yaml as a plain dict (reserved for future use).
    city_name: Human-readable city name used in log messages.

    Returns
    -------
    pd.DataFrame  Merged, deduplicated, impact-scored incidents DataFrame.
                  Returns _empty_incidents_df() if all sources fail.
    """
    mappls_key = os.getenv("MAPPLS_API_KEY", "")

    frames: list[pd.DataFrame] = []
    mappls_count = 0
    waze_count   = 0

    # --- Mappls (primary) ---
    try:
        df_mappls = fetch_mappls_incidents(bbox, mappls_key)
        if not df_mappls.empty:
            frames.append(df_mappls)
            mappls_count = len(df_mappls)
    except Exception:
        logger.error(
            "fetch_all_incidents: Mappls fetcher raised unexpectedly for %s",
            city_name,
            exc_info=True,
        )

    # --- Waze (secondary) ---
    try:
        df_waze = fetch_waze_incidents(bbox)
        if not df_waze.empty:
            frames.append(df_waze)
            waze_count = len(df_waze)
    except Exception:
        logger.error(
            "fetch_all_incidents: Waze fetcher raised unexpectedly for %s",
            city_name,
            exc_info=True,
        )

    # --- All sources failed ---
    if not frames:
        logger.critical(
            "fetch_all_incidents: all sources failed for %s — returning empty DataFrame",
            city_name,
        )
        return _empty_incidents_df()

    # --- Merge ---
    combined = pd.concat(frames, ignore_index=True)

    # Priority deduplication: Mappls first (priority=0), Waze second (priority=1)
    _priority_map = {"mappls": 0, "waze": 1}
    combined["_priority"] = combined["source"].map(_priority_map).fillna(99)
    combined.sort_values("_priority", inplace=True)
    combined.drop_duplicates(subset=["incident_id"], keep="first", inplace=True)
    combined.drop(columns=["_priority"], inplace=True)
    combined.reset_index(drop=True, inplace=True)

    # --- Impact scoring ---
    combined = compute_incident_impact_score(combined, bbox)

    logger.info(
        "fetch_all_incidents: %d incidents (%d Mappls, %d Waze) for %s",
        len(combined),
        mappls_count,
        waze_count,
        city_name,
    )

    return combined


# ---------------------------------------------------------------------------
# 8. summarise_incidents
# ---------------------------------------------------------------------------

def summarise_incidents(
    incidents_df: pd.DataFrame,
    bbox: dict,
) -> dict:
    """Produce a flat feature dict from an incidents DataFrame.

    This dict is consumed directly by preprocess.py as model input features.
    All six keys are always present regardless of whether any incidents exist.

    Parameters
    ----------
    incidents_df: Output of fetch_all_incidents() — may be empty.
    bbox:         Bounding box dict (reserved for future distance normalisation).

    Returns
    -------
    dict  With keys: incident_flag, incident_count, max_severity,
          severe_count, nearest_incident_dist_km, mean_impact_score.
    """
    if incidents_df.empty:
        return {
            "incident_flag":             False,
            "incident_count":            0,
            "max_severity":              0,
            "severe_count":              0,
            "nearest_incident_dist_km":  np.nan,
            "mean_impact_score":         0.0,
        }

    center_lat = (bbox["north"] + bbox["south"]) / 2.0
    center_lon = (bbox["east"]  + bbox["west"])  / 2.0

    # nearest_incident_dist_km: minimum haversine distance to bbox centre
    def _dist(row: pd.Series) -> float:
        try:
            lat = float(row["latitude"])
            lon = float(row["longitude"])
            if np.isnan(lat) or np.isnan(lon):
                return np.nan
            return _haversine_km(lat, lon, center_lat, center_lon)
        except Exception:
            return np.nan

    distances = incidents_df.apply(_dist, axis=1)
    nearest   = float(distances.min()) if not distances.isna().all() else np.nan

    # mean_impact_score
    if "impact_score" in incidents_df.columns:
        mean_score = float(incidents_df["impact_score"].mean())
    else:
        mean_score = 0.0

    return {
        "incident_flag":             True,
        "incident_count":            int(len(incidents_df)),
        "max_severity":              int(incidents_df["severity"].max()),
        "severe_count":              int((incidents_df["severity"] == 3).sum()),
        "nearest_incident_dist_km":  nearest,
        "mean_impact_score":         mean_score,
    }

"""
Fetches weather data for Indian cities from OpenWeatherMap API
and India Meteorological Department (IMD).

Weather is a critical feature for Indian traffic prediction:
- Monsoon (Jun-Sep): rainfall causes 40-60% speed reduction
- Fog (Oct-Feb):     visibility < 50m causes gridlock in Delhi
- Cyclones:          Chennai/Odisha coastal road blockages
- Extreme heat:      45°C+ affects road surface and behaviour

Data flow:
    fetch_city_weather()
        ├── fetch_openweather()   [primary — real-time, global]
        └── fetch_imd_weather()   [secondary — India precision]
            └── merged via merge_weather_with_traffic()

Imports fetch_with_retry from data.fetch_traffic.
Never call requests.get() directly.
"""

import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from dotenv import load_dotenv
from data.fetch_traffic import fetch_with_retry

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Monsoon months by city region
# Key = city name (lowercase), Value = (start_month, end_month) inclusive
MONSOON_MONTHS: dict = {
    "mumbai":    (6, 9),
    "delhi":     (7, 9),
    "bengaluru": (6, 9),
    "chennai":   (10, 12),   # Northeast monsoon
    "patna":     (6, 9),
    "default":   (6, 9),
}

# Fog-prone cities and months (start_month, end_month) — wraps across year
FOG_MONTHS: dict = {
    "delhi": (11, 2),    # Nov-Feb (wraps: Nov, Dec, Jan, Feb)
    "patna": (11, 2),
}

# Rainfall thresholds for intensity classification (mm/hour)
RAIN_LIGHT    = 2.5
RAIN_MODERATE = 7.5
RAIN_HEAVY    = 35.5
RAIN_EXTREME  = 64.5

# IMD city codes for our 5 cities
IMD_CITY_CODES: dict = {
    "delhi":     "DEL",
    "mumbai":    "MUM",
    "bengaluru": "BLR",
    "chennai":   "CHN",
    "patna":     "PAT",
}

# Weather output columns
WEATHER_COLUMNS: list = [
    "city",
    "latitude",
    "longitude",
    "timestamp",
    "temperature_c",
    "feels_like_c",
    "humidity_pct",
    "precipitation_mm",
    "visibility_km",
    "wind_speed_kmph",
    "weather_condition",
    "monsoon_intensity",
    "fog_flag",
    "rain_category",
    "source",
]


# ---------------------------------------------------------------------------
# 6. _empty_weather_dict  (defined early — used by many functions below)
# ---------------------------------------------------------------------------

def _empty_weather_dict() -> dict:
    """Return a safe default weather dict covering all WEATHER_COLUMNS.

    Used as a fallback whenever an API call fails so that callers always
    receive a complete, type-correct dict instead of None.
    """
    return {
        "city":              "",
        "latitude":          np.nan,
        "longitude":         np.nan,
        "timestamp":         datetime.now(timezone.utc),
        "temperature_c":     np.nan,
        "feels_like_c":      np.nan,
        "humidity_pct":      np.nan,
        "precipitation_mm":  0.0,
        "visibility_km":     10.0,    # assume clear if unknown
        "wind_speed_kmph":   np.nan,
        "weather_condition": "unknown",
        "monsoon_intensity": 0.0,
        "fog_flag":          False,
        "rain_category":     "none",
        "source":            "unknown",
    }


# ---------------------------------------------------------------------------
# 1. fetch_openweather
# ---------------------------------------------------------------------------

def fetch_openweather(
    lat: float,
    lon: float,
    api_key: str,
    city: str = "",
) -> dict:
    """Fetch current weather from OpenWeatherMap for a lat/lon coordinate.

    Parameters
    ----------
    lat:     Latitude of the point to query.
    lon:     Longitude of the point to query.
    api_key: OpenWeatherMap API key (appid).
    city:    Optional city label carried through to the output dict.

    Returns
    -------
    dict  Flat weather observation dict with all WEATHER_COLUMNS keys.
          Returns _empty_weather_dict() on any failure.
    """
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat":   lat,
        "lon":   lon,
        "appid": api_key,
        "units": "metric",
    }

    try:
        data = fetch_with_retry(url, params=params)
    except Exception:
        logger.error(
            "fetch_openweather: API call failed for lat=%s lon=%s city=%s",
            lat, lon, city,
            exc_info=True,
        )
        return _empty_weather_dict()

    try:
        main        = data.get("main", {})
        wind        = data.get("wind", {})
        rain        = data.get("rain", {})
        weather_arr = data.get("weather", [{}])

        # visibility: API returns metres; divide by 1000 and cap at 10.0
        raw_vis     = data.get("visibility", 10000)
        visibility_km = min(float(raw_vis) / 1000.0, 10.0)

        # precipitation: 1-hour accumulation; default 0.0
        precipitation_mm = max(float(rain.get("1h", 0.0)), 0.0)

        # wind speed: API returns m/s; convert to km/h
        wind_speed_kmph = float(wind.get("speed", np.nan)) * 3.6

        return {
            "city":              city,
            "latitude":          float(lat),
            "longitude":         float(lon),
            "timestamp":         datetime.now(timezone.utc),
            "temperature_c":     float(main.get("temp",       np.nan)),
            "feels_like_c":      float(main.get("feels_like", np.nan)),
            "humidity_pct":      float(main.get("humidity",   np.nan)),
            "precipitation_mm":  precipitation_mm,
            "visibility_km":     visibility_km,
            "wind_speed_kmph":   wind_speed_kmph,
            "weather_condition": str(weather_arr[0].get("description", "unknown")),
            "monsoon_intensity": 0.0,   # computed later in fetch_city_weather
            "fog_flag":          False,  # computed later in fetch_city_weather
            "rain_category":     "none", # computed later in fetch_city_weather
            "source":            "openweather",
        }

    except Exception:
        logger.error(
            "fetch_openweather: response parsing failed for lat=%s lon=%s",
            lat, lon,
            exc_info=True,
        )
        return _empty_weather_dict()


# ---------------------------------------------------------------------------
# 2. fetch_imd_weather
# ---------------------------------------------------------------------------

def fetch_imd_weather(
    city: str,
    date: str,
) -> dict:
    """Fetch weather observation from IMD's public city forecast endpoint.

    IMD is the secondary source — it is often slow or unavailable.
    All failures are logged at WARNING level (not ERROR) so they never
    disrupt the primary OpenWeatherMap pipeline.

    Parameters
    ----------
    city: City name (case-insensitive). Must be one of the five target cities.
    date: Date string in "YYYY-MM-DD" format (used for logging context).

    Returns
    -------
    dict  Flat weather dict with all WEATHER_COLUMNS keys, or
          _empty_weather_dict() on any failure / unknown city.
    """
    city_key  = city.strip().lower()
    imd_code  = IMD_CITY_CODES.get(city_key)

    if imd_code is None:
        logger.warning(
            "fetch_imd_weather: unknown city '%s' — no IMD city code, skipping",
            city,
        )
        return _empty_weather_dict()

    url    = "https://imd.gov.in/pages/city_forecastdata.php"
    params = {"id": imd_code}

    try:
        data = fetch_with_retry(url, params=params)
    except Exception:
        logger.warning(
            "fetch_imd_weather: API call failed for city=%s date=%s",
            city, date,
            exc_info=True,
        )
        return _empty_weather_dict()

    try:
        # IMD's public endpoint structure varies; attempt to parse known fields.
        # Fields are extracted defensively — absent keys fall back to NaN/defaults.
        forecast = data.get("forecast", data)   # some responses nest under "forecast"

        temperature_c    = forecast.get("temp",          np.nan)
        humidity_pct     = forecast.get("rh",            np.nan)
        wind_speed_ms    = forecast.get("wind_speed",    np.nan)
        precipitation_mm = max(float(forecast.get("rainfall", 0.0)), 0.0)
        weather_cond     = str(forecast.get("weather",   "unknown"))

        # Convert wind m/s → km/h only if we actually got a numeric value
        try:
            wind_speed_kmph = float(wind_speed_ms) * 3.6
        except (TypeError, ValueError):
            wind_speed_kmph = np.nan

        result = _empty_weather_dict()
        result.update({
            "city":              city,
            "timestamp":         datetime.now(timezone.utc),
            "temperature_c":     temperature_c,
            "humidity_pct":      humidity_pct,
            "precipitation_mm":  precipitation_mm,
            "wind_speed_kmph":   wind_speed_kmph,
            "weather_condition": weather_cond,
            "source":            "imd",
        })
        return result

    except Exception:
        logger.warning(
            "fetch_imd_weather: response parsing failed for city=%s",
            city,
            exc_info=True,
        )
        return _empty_weather_dict()


# ---------------------------------------------------------------------------
# 3. compute_monsoon_intensity
# ---------------------------------------------------------------------------

def compute_monsoon_intensity(
    rainfall_mm: float,
    month: int,
    city: str = "default",
) -> float:
    """Compute a monsoon intensity score (0.0 – 1.0) from rainfall and month.

    Returns 0.0 when outside the monsoon window for the given city.
    Chennai uses the northeast monsoon (Oct–Dec) rather than the
    southwest monsoon used by the rest of India.

    Parameters
    ----------
    rainfall_mm: Hourly rainfall accumulation in mm.
    month:       Calendar month (1 = January … 12 = December).
    city:        City name (case-insensitive). Falls back to "default".

    Returns
    -------
    float  Monsoon intensity in [0.0, 1.0].
    """
    city_key = city.strip().lower()
    start_m, end_m = MONSOON_MONTHS.get(city_key, MONSOON_MONTHS["default"])

    # Determine whether 'month' falls inside the monsoon window.
    # All our windows fit within a single calendar year (no wrap-around).
    in_monsoon = start_m <= month <= end_m

    if not in_monsoon:
        return 0.0

    # Intensity thresholds (mm/hr)
    if rainfall_mm <= 0:
        return 0.0
    elif rainfall_mm < RAIN_LIGHT:
        return 0.2
    elif rainfall_mm < RAIN_MODERATE:
        return 0.4
    elif rainfall_mm < RAIN_HEAVY:
        return 0.6
    elif rainfall_mm < RAIN_EXTREME:
        return 0.8
    else:
        return 1.0


# ---------------------------------------------------------------------------
# 4. compute_fog_flag
# ---------------------------------------------------------------------------

def compute_fog_flag(
    visibility_km: float,
    month: int,
    city: str = "",
) -> bool:
    """Determine whether fog conditions are present.

    For cities in FOG_MONTHS, fog is flagged when visibility is below 0.5 km
    AND the month falls inside the city's fog season. For all other cities,
    dense fog (visibility < 0.2 km) is flagged regardless of month.

    FOG_MONTHS windows may wrap across a calendar year (e.g. Nov–Feb).

    Parameters
    ----------
    visibility_km: Current visibility in kilometres.
    month:         Calendar month (1 – 12).
    city:          City name (case-insensitive).

    Returns
    -------
    bool  True if fog conditions are detected.
    """
    city_key = city.strip().lower()

    if city_key in FOG_MONTHS:
        start_m, end_m = FOG_MONTHS[city_key]
        # Window may wrap across a year (e.g. Nov=11 to Feb=2)
        if start_m <= end_m:
            in_fog_season = start_m <= month <= end_m
        else:
            # Wraps: e.g. Nov(11) → Dec(12) → Jan(1) → Feb(2)
            in_fog_season = month >= start_m or month <= end_m

        fog_detected = visibility_km < 0.5 and in_fog_season

        # India-specific: extra alert for Delhi in peak fog months
        if fog_detected and city_key == "delhi" and month in (12, 1):
            logger.warning(
                "Dense fog alert: Delhi visibility %.2fkm — "
                "emergency vehicle delays highly probable",
                visibility_km,
            )

        return fog_detected

    # City not in FOG_MONTHS — flag only on truly dense fog
    return visibility_km < 0.2


# ---------------------------------------------------------------------------
# 5. classify_rain_category
# ---------------------------------------------------------------------------

def classify_rain_category(
    precipitation_mm: float,
) -> str:
    """Map hourly rainfall (mm) to a categorical string label.

    Categories align with IMD rainfall classification and are used as
    one-hot encoded features in preprocess.py.

    Parameters
    ----------
    precipitation_mm: Hourly rainfall accumulation in mm (must be >= 0).

    Returns
    -------
    str  One of: "none", "light", "moderate", "heavy", "very_heavy", "extreme".
    """
    if precipitation_mm == 0:
        return "none"
    elif precipitation_mm < RAIN_LIGHT:
        return "light"
    elif precipitation_mm < RAIN_MODERATE:
        return "moderate"
    elif precipitation_mm < RAIN_HEAVY:
        return "heavy"
    elif precipitation_mm < RAIN_EXTREME:
        return "very_heavy"
    else:
        return "extreme"


# ---------------------------------------------------------------------------
# 7. fetch_city_weather  (main entry point)
# ---------------------------------------------------------------------------

def fetch_city_weather(
    city_name: str,
    lat: float,
    lon: float,
    config: dict,
) -> dict:
    """Fetch and merge weather data from OpenWeatherMap (primary) and IMD (secondary).

    Derived features — monsoon_intensity, fog_flag, rain_category — are
    computed and injected into the returned dict so that callers receive a
    fully-featured observation ready for preprocess.py.

    Parameters
    ----------
    city_name: Human-readable city name (e.g. "Delhi").
    lat:       City centre latitude.
    lon:       City centre longitude.
    config:    Parsed config.yaml as a plain dict.

    Returns
    -------
    dict  Complete weather observation covering all WEATHER_COLUMNS keys.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY", "")

    # --- Primary source: OpenWeatherMap ---
    try:
        result = fetch_openweather(lat, lon, api_key, city=city_name)
    except Exception:
        logger.error(
            "fetch_city_weather: OpenWeatherMap call raised unexpectedly for %s",
            city_name,
            exc_info=True,
        )
        result = _empty_weather_dict()
        result["city"] = city_name

    # --- Secondary source: IMD ---
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        imd_result = fetch_imd_weather(city_name, today_str)
    except Exception:
        logger.warning(
            "fetch_city_weather: IMD call raised unexpectedly for %s",
            city_name,
            exc_info=True,
        )
        imd_result = _empty_weather_dict()

    # --- Merge: OpenWeatherMap wins; fill gaps from IMD ---
    _numeric_nan_fields = [
        "temperature_c", "feels_like_c", "humidity_pct",
        "precipitation_mm", "visibility_km", "wind_speed_kmph",
    ]
    for field in _numeric_nan_fields:
        ow_val  = result.get(field)
        imd_val = imd_result.get(field)
        # Fill if OpenWeatherMap value is NaN/None and IMD has a real value
        try:
            if (ow_val is None or np.isnan(float(ow_val))) and imd_val is not None:
                try:
                    if not np.isnan(float(imd_val)):
                        result[field] = imd_val
                except (TypeError, ValueError):
                    pass
        except (TypeError, ValueError):
            pass

    # Fill weather_condition from IMD if OWM returned "unknown"
    if result.get("weather_condition", "unknown") == "unknown":
        imd_cond = imd_result.get("weather_condition", "unknown")
        if imd_cond and imd_cond != "unknown":
            result["weather_condition"] = imd_cond

    # --- Apply dtype constraints ---
    try:
        result["precipitation_mm"] = max(float(result.get("precipitation_mm", 0.0)), 0.0)
    except (TypeError, ValueError):
        result["precipitation_mm"] = 0.0

    try:
        result["visibility_km"] = min(float(result.get("visibility_km", 10.0)), 10.0)
    except (TypeError, ValueError):
        result["visibility_km"] = 10.0

    # --- Derive monsoon / fog / rain features ---
    current_month = datetime.now(timezone.utc).month

    result["monsoon_intensity"] = compute_monsoon_intensity(
        rainfall_mm=result["precipitation_mm"],
        month=current_month,
        city=city_name,
    )
    result["fog_flag"] = compute_fog_flag(
        visibility_km=result["visibility_km"],
        month=current_month,
        city=city_name,
    )
    result["rain_category"] = classify_rain_category(result["precipitation_mm"])

    # Ensure city is set
    result["city"] = city_name

    logger.info(
        "fetch_city_weather: %s — %s, %.1fmm rain, monsoon_intensity=%.2f",
        city_name,
        result.get("weather_condition", "unknown"),
        result.get("precipitation_mm", 0.0),
        result.get("monsoon_intensity", 0.0),
    )

    return result


# ---------------------------------------------------------------------------
# 8. merge_weather_with_traffic
# ---------------------------------------------------------------------------

def merge_weather_with_traffic(
    traffic_df: pd.DataFrame,
    weather_dict: dict,
) -> pd.DataFrame:
    """Broadcast city-level weather onto every road segment in traffic_df.

    Weather is city-level — every segment receives the same observation.
    Added columns: temperature_c, precipitation_mm, visibility_km,
    wind_speed_kmph, monsoon_intensity, fog_flag, rain_category.

    Parameters
    ----------
    traffic_df:   DataFrame in TRAFFIC_COLUMNS schema from fetch_traffic.py.
    weather_dict: Single-city weather observation from fetch_city_weather().

    Returns
    -------
    pd.DataFrame  traffic_df enriched with weather columns. Returned unchanged
                  (with NaN weather columns) if weather_dict is empty or None.
    """
    _weather_broadcast_cols = [
        "temperature_c",
        "precipitation_mm",
        "visibility_km",
        "wind_speed_kmph",
        "monsoon_intensity",
        "fog_flag",
        "rain_category",
    ]

    if traffic_df.empty:
        return traffic_df

    if not weather_dict:
        # Attach NaN/default weather columns so schema is consistent
        for col in _weather_broadcast_cols:
            if col == "fog_flag":
                traffic_df[col] = False
            elif col == "rain_category":
                traffic_df[col] = "none"
            else:
                traffic_df[col] = np.nan
        return traffic_df

    for col in _weather_broadcast_cols:
        traffic_df[col] = weather_dict.get(col, np.nan)

    return traffic_df

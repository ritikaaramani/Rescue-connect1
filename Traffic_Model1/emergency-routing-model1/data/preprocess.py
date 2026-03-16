"""
Preprocesses raw traffic, weather, and incident data into
training-ready tensors for the LSTM+GCN model.

Pipeline:
    load_raw_parquet()
        → handle_missing_data()
        → compute_speed_ratio()
        → encode_temporal_features()
        → add_festival_feature()        [India-specific]
        → add_monsoon_score()           [India-specific]
        → add_incident_features()       [India-specific]
        → normalise_features()
        → create_sliding_windows()
        → split_train_val_test()
        → save_processed_tensors()

India-specific features:
  Festival calendar: Diwali, Navratri, Eid, Durga Puja,
    Republic Day, IPL matches, CBSE exam period
  Monsoon score: recomputed from precipitation + month
    using city-aware thresholds
  Incident features: from summarise_incidents() output

Output tensors consumed by models/lstm_gcn.py:
  X_train shape: (N, window_size, num_features)
  y_train shape: (N, num_horizons)
  adj_matrix:    sparse adjacency (num_nodes x num_nodes)
"""

import os
import pickle
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, date, timezone
from sklearn.preprocessing import MinMaxScaler
from scipy.sparse import csr_matrix, save_npz
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Features the LSTM receives per timestep per segment.
# Order matters — must match lstm_input_size=12 in config.
FEATURE_COLUMNS: list = [
    "speed_ratio",           # 1  — core target proxy
    "jam_factor",            # 2  — congestion level
    "hour_sin",              # 3  — cyclical hour encoding
    "hour_cos",              # 4
    "day_sin",               # 5  — cyclical day encoding
    "day_cos",               # 6
    "monsoon_intensity",     # 7  — India monsoon score
    "fog_flag",              # 8  — India fog indicator
    "precipitation_mm",      # 9  — rainfall
    "festival_intensity",    # 10 — India festival score
    "incident_severity",     # 11 — max incident severity
    "incident_flag",         # 12 — any incident present
]

# Indian festival calendar
# (month, day_start, day_end, intensity_score 0.0–1.0)
INDIA_FESTIVALS: list = [
    # Diwali window (Oct–Nov, varies — use Oct 20–Nov 5)
    (10, 20, 31, 1.0),
    (11,  1,  5, 1.0),
    # Navratri (Sep–Oct, 9 days)
    (10,  1, 10, 0.7),
    # Durga Puja (Oct, Bengal-heavy)
    (10,  5, 15, 0.8),
    # Eid al-Fitr window (Apr, approximate)
    (4,   8, 12, 0.8),
    # Eid al-Adha (Jun, approximate)
    (6,  15, 18, 0.7),
    # Holi (Mar)
    (3,  25, 26, 0.9),
    # Republic Day (Jan 26)
    (1,  26, 26, 0.6),
    # Independence Day (Aug 15)
    (8,  15, 15, 0.5),
    # CBSE Board Exams (Mar — morning rush)
    (3,   1, 31, 0.4),
    # IPL season (Mar–May — evening rush)
    (3,  22, 31, 0.3),
    (4,   1, 30, 0.3),
    (5,   1, 26, 0.3),
    # Christmas–New Year
    (12, 24, 31, 0.5),
    (1,   1,  2, 0.5),
]

# Monsoon windows per city (reimplemented inline, NOT imported)
_MONSOON_MONTHS: dict = {
    "mumbai":    (6, 9),
    "delhi":     (7, 9),
    "bengaluru": (6, 9),
    "chennai":   (10, 12),
    "patna":     (6, 9),
    "default":   (6, 9),
}

# Rainfall thresholds (mm/h) — same as fetch_weather.py
_RAIN_LIGHT    = 2.5
_RAIN_MODERATE = 7.5
_RAIN_HEAVY    = 35.5
_RAIN_EXTREME  = 64.5

# Default free-flow speed used when the value is missing / zero
_INDIA_DEFAULT_FREE_FLOW_SPEED = 50.0


# ---------------------------------------------------------------------------
# 1. load_raw_parquet
# ---------------------------------------------------------------------------

def load_raw_parquet(
    city_name: str,
    config: dict,
) -> pd.DataFrame:
    """Load and concatenate all raw Parquet files for a city.

    Files are sorted by filename (which embeds a timestamp) to maintain
    chronological order.

    Parameters
    ----------
    city_name: Human-readable city name (e.g. "Delhi").
    config:    Parsed config.yaml dict.

    Returns
    -------
    pd.DataFrame  Concatenated raw traffic (+weather) data.

    Raises
    ------
    FileNotFoundError  If no Parquet files are found.
    """
    raw_dir = config["data"]["raw_data_dir"]
    city_path = Path(raw_dir) / city_name

    parquet_files = sorted(city_path.rglob("*.parquet"))

    if not parquet_files:
        logger.error(
            "load_raw_parquet: no .parquet files found in '%s'", city_path
        )
        raise FileNotFoundError(
            f"No parquet files found for {city_name} in {city_path}"
        )

    frames = [pd.read_parquet(f) for f in parquet_files]
    df = pd.concat(frames, ignore_index=True)

    logger.info(
        "load_raw_parquet: loaded %d files, %d rows for %s",
        len(parquet_files), len(df), city_name,
    )
    return df


# ---------------------------------------------------------------------------
# 2. handle_missing_data
# ---------------------------------------------------------------------------

def handle_missing_data(df: pd.DataFrame) -> pd.DataFrame:
    """Impute and clean missing values in the raw DataFrame.

    Strategy:
      1. Replace jam_factor sentinels (-1.0) with NaN.
      2. Forward-fill then backward-fill all columns (short-gap fix).
      3. Per-segment median imputation for speed_kmph.
      4. Constant fill for free_flow_speed_kmph (50.0 km/h).
      5. Drop rows where speed_kmph is *still* NaN.

    Parameters
    ----------
    df: Raw DataFrame from load_raw_parquet().

    Returns
    -------
    pd.DataFrame  Cleaned DataFrame (rows may be fewer).

    Raises
    ------
    ValueError  If all rows are dropped.
    """
    n_before = len(df)

    # jam_factor sentinel → NaN
    if "jam_factor" in df.columns:
        df["jam_factor"] = df["jam_factor"].replace(-1.0, np.nan)

    # Forward-fill then backward-fill
    df = df.ffill().bfill()

    # Per-segment median imputation for speed_kmph
    if "speed_kmph" in df.columns and df["speed_kmph"].isna().any():
        if "segment_id" in df.columns:
            medians = df.groupby("segment_id")["speed_kmph"].transform("median")
            df["speed_kmph"] = df["speed_kmph"].fillna(medians)
        # Global median fallback
        df["speed_kmph"] = df["speed_kmph"].fillna(df["speed_kmph"].median())

    # free_flow_speed_kmph
    if "free_flow_speed_kmph" in df.columns:
        df["free_flow_speed_kmph"] = df["free_flow_speed_kmph"].fillna(
            _INDIA_DEFAULT_FREE_FLOW_SPEED
        )
        df.loc[
            df["free_flow_speed_kmph"] == 0.0, "free_flow_speed_kmph"
        ] = _INDIA_DEFAULT_FREE_FLOW_SPEED

    # Drop rows where speed_kmph is still missing
    if "speed_kmph" in df.columns:
        df = df.dropna(subset=["speed_kmph"])

    n_after = len(df)
    dropped = n_before - n_after

    logger.info(
        "handle_missing_data: %d rows dropped, %d remaining",
        dropped, n_after,
    )

    if n_after == 0:
        raise ValueError("Empty DataFrame after handle_missing_data")

    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 3. compute_speed_ratio
# ---------------------------------------------------------------------------

def compute_speed_ratio(df: pd.DataFrame) -> pd.DataFrame:
    """Add a 'speed_ratio' column: speed_kmph / free_flow_speed_kmph.

    Clipped to [0.0, 1.5] — values above 1.5 indicate data errors and are
    capped. A ratio of 0 means no movement; 1.0 means free-flow.

    Parameters
    ----------
    df: DataFrame with speed_kmph and free_flow_speed_kmph columns.

    Returns
    -------
    pd.DataFrame  Same DataFrame with 'speed_ratio' added.
    """
    ffs = df["free_flow_speed_kmph"].replace(0, np.nan)
    df["speed_ratio"] = (df["speed_kmph"] / ffs).clip(0.0, 1.5)

    sr = df["speed_ratio"]
    logger.info(
        "compute_speed_ratio: min=%.3f mean=%.3f max=%.3f",
        sr.min(), sr.mean(), sr.max(),
    )
    return df


# ---------------------------------------------------------------------------
# 4. encode_temporal_features
# ---------------------------------------------------------------------------

def encode_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add cyclical and binary temporal features derived from 'fetched_at'.

    Cyclical: hour_sin/cos, day_sin/cos, month_sin/cos.
    Binary:   is_weekend, is_rush_hour, is_night.

    Parameters
    ----------
    df: DataFrame with a 'fetched_at' datetime column (UTC).

    Returns
    -------
    pd.DataFrame  Enriched with 9 new temporal columns.
    """
    ts = pd.to_datetime(df["fetched_at"], utc=True)

    hour  = ts.dt.hour
    dow   = ts.dt.dayofweek   # Monday=0 … Sunday=6
    month = ts.dt.month

    two_pi = 2.0 * np.pi

    df["hour_sin"]  = np.sin(two_pi * hour / 24.0)
    df["hour_cos"]  = np.cos(two_pi * hour / 24.0)
    df["day_sin"]   = np.sin(two_pi * dow  / 7.0)
    df["day_cos"]   = np.cos(two_pi * dow  / 7.0)
    df["month_sin"] = np.sin(two_pi * month / 12.0)
    df["month_cos"] = np.cos(two_pi * month / 12.0)

    df["is_weekend"]   = (dow >= 5).astype(int)
    df["is_rush_hour"] = hour.isin([7, 8, 9, 17, 18, 19, 20]).astype(int)
    df["is_night"]     = ((hour < 6) | (hour >= 23)).astype(int)

    return df


# ---------------------------------------------------------------------------
# 5. add_festival_feature
# ---------------------------------------------------------------------------

def add_festival_feature(df: pd.DataFrame) -> pd.DataFrame:
    """Add 'festival_intensity' (0.0–1.0) and 'is_festival_day' (0/1).

    Uses the hardcoded INDIA_FESTIVALS calendar. When multiple festival
    windows overlap, the *maximum* intensity score is used.

    Parameters
    ----------
    df: DataFrame with a 'fetched_at' datetime column.

    Returns
    -------
    pd.DataFrame  Enriched with festival columns.
    """
    ts  = pd.to_datetime(df["fetched_at"], utc=True)
    m   = ts.dt.month.values
    d   = ts.dt.day.values

    intensity = np.zeros(len(df), dtype=np.float64)

    for f_month, f_start, f_end, f_score in INDIA_FESTIVALS:
        mask = (m == f_month) & (d >= f_start) & (d <= f_end)
        intensity = np.maximum(intensity, np.where(mask, f_score, 0.0))

    df["festival_intensity"] = intensity
    df["is_festival_day"]    = (intensity > 0.0).astype(int)

    n_festival = int((intensity > 0.0).sum())
    logger.info(
        "add_festival_feature: %d festival day rows detected", n_festival
    )
    return df


# ---------------------------------------------------------------------------
# 6. add_monsoon_score
# ---------------------------------------------------------------------------

def add_monsoon_score(
    df: pd.DataFrame,
    city_name: str,
) -> pd.DataFrame:
    """Recompute 'monsoon_intensity' from actual precipitation_mm in-row.

    Logic is reimplemented inline (not imported from fetch_weather.py) to
    avoid circular imports. Chennai uses the northeast monsoon (Oct–Dec);
    all other cities use Jun–Sep.

    Parameters
    ----------
    df:        DataFrame with 'fetched_at' and 'precipitation_mm' columns.
    city_name: City name used to select the monsoon window.

    Returns
    -------
    pd.DataFrame  With 'monsoon_intensity' column added/overwritten.
    """
    city_key = city_name.strip().lower()
    start_m, end_m = _MONSOON_MONTHS.get(city_key, _MONSOON_MONTHS["default"])

    ts    = pd.to_datetime(df["fetched_at"], utc=True)
    month = ts.dt.month.values

    in_monsoon = (month >= start_m) & (month <= end_m)

    precip = df["precipitation_mm"].values if "precipitation_mm" in df.columns \
        else np.zeros(len(df), dtype=np.float64)

    scores = np.where(
        ~in_monsoon, 0.0,
        np.where(
            precip <= 0,          0.0,
            np.where(
                precip < _RAIN_LIGHT,    0.2,
                np.where(
                    precip < _RAIN_MODERATE, 0.4,
                    np.where(
                        precip < _RAIN_HEAVY,    0.6,
                        np.where(
                            precip < _RAIN_EXTREME, 0.8,
                            1.0
                        )
                    )
                )
            )
        )
    )

    df["monsoon_intensity"] = scores.astype(np.float64)
    return df


# ---------------------------------------------------------------------------
# 7. add_incident_features
# ---------------------------------------------------------------------------

def add_incident_features(
    df: pd.DataFrame,
    incident_summary: dict,
) -> pd.DataFrame:
    """Broadcast city-level incident features onto every row.

    Parameters
    ----------
    df:               Traffic DataFrame (one row per segment × timestep).
    incident_summary: Dict from summarise_incidents() with keys
                      incident_flag, max_severity, etc.

    Returns
    -------
    pd.DataFrame  With 'incident_flag' and 'incident_severity' columns.
    """
    if not incident_summary:
        df["incident_flag"]     = 0.0
        df["incident_severity"] = 0.0
        return df

    df["incident_flag"]     = 1.0 if incident_summary.get("incident_flag", False) else 0.0
    df["incident_severity"] = float(incident_summary.get("max_severity", 0))
    return df


# ---------------------------------------------------------------------------
# 8. normalise_features
# ---------------------------------------------------------------------------

def normalise_features(
    df: pd.DataFrame,
    scaler: MinMaxScaler = None,
    fit: bool = True,
) -> tuple:
    """Scale FEATURE_COLUMNS to [0, 1] using MinMaxScaler.

    Parameters
    ----------
    df:     DataFrame containing (at least) FEATURE_COLUMNS.
    scaler: Pre-fitted MinMaxScaler (required when fit=False).
    fit:    If True, fit a fresh scaler; if False, transform only.

    Returns
    -------
    tuple  (scaled_df: pd.DataFrame, scaler: MinMaxScaler)
    """
    # Ensure all FEATURE_COLUMNS exist
    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            logger.warning(
                "normalise_features: missing column '%s' — filling with 0.0", col
            )
            df[col] = 0.0

    # Bool / int → float conversion
    if "fog_flag" in df.columns:
        df["fog_flag"] = df["fog_flag"].astype(float)
    if "incident_flag" in df.columns:
        df["incident_flag"] = df["incident_flag"].astype(float)

    feature_data = df[FEATURE_COLUMNS].values.astype(np.float64)

    # Replace any remaining NaN with 0 so the scaler doesn't fail
    feature_data = np.nan_to_num(feature_data, nan=0.0)

    if fit:
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaled = scaler.fit_transform(feature_data)
    else:
        if scaler is None:
            raise ValueError(
                "normalise_features: scaler must be provided when fit=False"
            )
        scaled = scaler.transform(feature_data)

    df[FEATURE_COLUMNS] = scaled

    return df, scaler


# ---------------------------------------------------------------------------
# 9. create_sliding_windows
# ---------------------------------------------------------------------------

def create_sliding_windows(
    df: pd.DataFrame,
    window_size: int = 12,
    horizon: int = 4,
) -> tuple:
    """Build supervised-learning (X, y) arrays from per-segment time series.

    Windows are created *per segment_id* to avoid mixing unrelated road
    segments. Within each segment, rows are sorted by 'fetched_at' so the
    window slides chronologically.

    X shape: (N, window_size, len(FEATURE_COLUMNS))
    y shape: (N, horizon)  — target is future 'speed_ratio' values.

    Parameters
    ----------
    df:          DataFrame with FEATURE_COLUMNS and 'segment_id' / 'fetched_at'.
    window_size: Number of past timesteps per sample.
    horizon:     Number of future timesteps to predict.

    Returns
    -------
    tuple  (X: np.ndarray float32, y: np.ndarray float32)
    """
    all_X: list[np.ndarray] = []
    all_y: list[np.ndarray] = []

    # Ensure sorting col exists
    sort_col = "fetched_at" if "fetched_at" in df.columns else None

    # Group by segment
    group_col = "segment_id" if "segment_id" in df.columns else None

    if group_col:
        groups = df.groupby(group_col)
    else:
        groups = [("_all", df)]

    speed_ratio_idx = FEATURE_COLUMNS.index("speed_ratio")

    for seg_id, seg_df in groups:
        if sort_col:
            seg_df = seg_df.sort_values(sort_col)

        features = seg_df[FEATURE_COLUMNS].values.astype(np.float32)
        n = len(features)

        if n < window_size + horizon:
            continue  # not enough data for even one sample

        for i in range(n - window_size - horizon + 1):
            x_window = features[i : i + window_size]
            y_target = features[
                i + window_size : i + window_size + horizon,
                speed_ratio_idx,
            ]
            all_X.append(x_window)
            all_y.append(y_target)

    if not all_X:
        logger.error(
            "create_sliding_windows: no valid windows produced "
            "(window_size=%d, horizon=%d)", window_size, horizon,
        )
        raise ValueError("No valid sliding windows could be created")

    X = np.stack(all_X).astype(np.float32)
    y = np.stack(all_y).astype(np.float32)

    n_segments = len(set(df[group_col])) if group_col else 1

    logger.info(
        "create_sliding_windows: %d samples from %d segments, window=%d",
        len(X), n_segments, window_size,
    )
    return X, y


# ---------------------------------------------------------------------------
# 10. split_train_val_test
# ---------------------------------------------------------------------------

def split_train_val_test(
    X: np.ndarray,
    y: np.ndarray,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
) -> tuple:
    """Chronological (temporal) train / val / test split.

    IMPORTANT: No random shuffling — traffic data is a time series.
    Order: [train | val | test].

    Parameters
    ----------
    X: Input features array  (N, window_size, num_features).
    y: Target array           (N, horizon).
    val_ratio:  Fraction of data for validation.
    test_ratio: Fraction of data for testing.

    Returns
    -------
    tuple  (X_train, X_val, X_test, y_train, y_val, y_test)
    """
    N = len(X)
    train_end = int(N * (1.0 - val_ratio - test_ratio))
    val_end   = int(N * (1.0 - test_ratio))

    X_train, y_train = X[:train_end],      y[:train_end]
    X_val,   y_val   = X[train_end:val_end], y[train_end:val_end]
    X_test,  y_test  = X[val_end:],          y[val_end:]

    logger.info(
        "split_train_val_test: train=%d val=%d test=%d",
        len(X_train), len(X_val), len(X_test),
    )
    return X_train, X_val, X_test, y_train, y_val, y_test


# ---------------------------------------------------------------------------
# 11. save_processed_tensors
# ---------------------------------------------------------------------------

def save_processed_tensors(
    X_train: np.ndarray,
    X_val: np.ndarray,
    X_test: np.ndarray,
    y_train: np.ndarray,
    y_val: np.ndarray,
    y_test: np.ndarray,
    scaler: MinMaxScaler,
    city_name: str,
    config: dict,
) -> None:
    """Persist all training artifacts (6 numpy arrays + 1 scaler pickle).

    Parameters
    ----------
    X_train … y_test: Numpy arrays from split_train_val_test().
    scaler:           Fitted MinMaxScaler from normalise_features().
    city_name:        City name used as subdirectory name.
    config:           Parsed config.yaml dict.

    Raises
    ------
    Exception  Re-raised on any IO failure.
    """
    processed_dir = config["data"]["processed_data_dir"]
    output_dir = Path(processed_dir) / city_name

    try:
        output_dir.mkdir(parents=True, exist_ok=True)

        arrays = {
            "X_train": X_train,
            "X_val":   X_val,
            "X_test":  X_test,
            "y_train": y_train,
            "y_val":   y_val,
            "y_test":  y_test,
        }

        for name, arr in arrays.items():
            fpath = output_dir / f"{name}.npy"
            np.save(str(fpath), arr)
            logger.info(
                "save_processed_tensors: saved %s — shape %s", fpath, arr.shape
            )

        scaler_path = output_dir / "scaler.pkl"
        with open(str(scaler_path), "wb") as f:
            pickle.dump(scaler, f)
        logger.info("save_processed_tensors: saved scaler to %s", scaler_path)

    except Exception:
        logger.error(
            "save_processed_tensors: failed for city %s", city_name,
            exc_info=True,
        )
        raise


# ---------------------------------------------------------------------------
# 12. run_preprocessing_pipeline  (main entry point)
# ---------------------------------------------------------------------------

def run_preprocessing_pipeline(
    city_name: str,
    config: dict,
    incident_summary: dict = None,
) -> tuple:
    """Execute the full preprocessing pipeline for a single city.

    Called by training/train.py. Every step is logged; failures are re-raised
    so the training orchestrator can decide how to proceed.

    Parameters
    ----------
    city_name:        City name (e.g. "Delhi").
    config:           Parsed config.yaml dict.
    incident_summary: Optional dict from summarise_incidents(). If None,
                      incident features default to 0.

    Returns
    -------
    tuple  (X_train, X_val, X_test, y_train, y_val, y_test, scaler)

    Raises
    ------
    Exception  Re-raised from any pipeline step — preprocessing failure
               is fatal for model training.
    """
    logger.info("run_preprocessing_pipeline: START for %s", city_name)

    try:
        # 1. Load raw data
        df = load_raw_parquet(city_name, config)

        # 2. Clean missing values
        df = handle_missing_data(df)

        # 3. Compute speed ratio (core target proxy)
        df = compute_speed_ratio(df)

        # 4. Temporal encoding
        df = encode_temporal_features(df)

        # 5. Festival calendar (India-specific)
        df = add_festival_feature(df)

        # 6. Monsoon score (India-specific, recomputed from data)
        df = add_monsoon_score(df, city_name)

        # 7. Incident features (if available)
        if incident_summary:
            df = add_incident_features(df, incident_summary)
        else:
            df = add_incident_features(df, {})

        # 8. Normalise to [0, 1]
        df, scaler = normalise_features(df, fit=True)

        # 9. Sliding windows (per-segment, chronological)
        window_size = config["data"]["window_size"]
        horizon     = len(config["data"]["prediction_horizons"])
        X, y = create_sliding_windows(df, window_size=window_size, horizon=horizon)

        # 10. Temporal split (NOT random shuffle)
        val_ratio  = config["data"]["val_ratio"]
        test_ratio = config["data"]["test_ratio"]
        X_train, X_val, X_test, y_train, y_val, y_test = split_train_val_test(
            X, y, val_ratio=val_ratio, test_ratio=test_ratio,
        )

        # 11. Persist all artifacts
        save_processed_tensors(
            X_train, X_val, X_test,
            y_train, y_val, y_test,
            scaler, city_name, config,
        )

        logger.info("run_preprocessing_pipeline: COMPLETE for %s", city_name)
        return X_train, X_val, X_test, y_train, y_val, y_test, scaler

    except Exception:
        logger.error(
            "run_preprocessing_pipeline: FAILED for %s", city_name,
            exc_info=True,
        )
        raise

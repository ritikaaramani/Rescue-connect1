"""
Offline evaluation of EmergencyTrafficModel against three baselines:
  1. Naive persistence  — last observed speed_ratio repeated
  2. Historical average — mean of input window
  3. API routing        — live Mappls + HERE speed_ratio as static prediction

Metrics reported per prediction horizon (T+5, T+10, T+20, T+30):
  MAE, RMSE, MAPE

Results are written to data/processed/evaluation_results.csv.
"""

import os
import yaml
import pickle
import logging
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from pathlib import Path
from scipy.sparse import csr_matrix
from dotenv import load_dotenv
from tabulate import tabulate

from models.lstm_gcn import EmergencyTrafficModel, build_model, count_parameters
from data.build_graph import build_city_graph
from data.fetch_traffic import fetch_all_sources
from data.preprocess import FEATURE_COLUMNS

load_dotenv()
logger = logging.getLogger(__name__)

# Horizon labels — aligns with prediction_horizons: [5, 10, 20, 30]
_HORIZONS = ["t5", "t10", "t20", "t30"]

# Node feature columns used for spatial projection
_SPATIAL_COLS = ["avg_speed_limit", "avg_road_weight", "is_signal", "street_count"]


# ---------------------------------------------------------------------------
# compute_metrics
# ---------------------------------------------------------------------------

def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Compute MAE, RMSE, and MAPE for a single horizon.

    Parameters
    ----------
    y_true: Ground-truth speed ratios  (N,).
    y_pred: Predicted speed ratios     (N,).

    Returns
    -------
    dict  Keys: mae, rmse, mape (all float).
    """
    mae  = float(np.mean(np.abs(y_true - y_pred)))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

    # MAPE: skip samples where y_true < 0.01 to avoid division by zero
    valid = y_true >= 0.01
    if valid.sum() > 0:
        mape = float(
            np.mean(np.abs((y_true[valid] - y_pred[valid]) / y_true[valid])) * 100.0
        )
    else:
        mape = float("nan")

    return {"mae": mae, "rmse": rmse, "mape": mape}


def _metrics_per_horizon(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Compute MAE/RMSE/MAPE for each of the 4 horizons and return flat dict."""
    result = {}
    for i, h in enumerate(_HORIZONS):
        m = compute_metrics(y_true[:, i], y_pred[:, i])
        result[f"mae_{h}"]  = m["mae"]
        result[f"rmse_{h}"] = m["rmse"]
        result[f"mape_{h}"] = m["mape"]
    return result


# ---------------------------------------------------------------------------
# load_test_data
# ---------------------------------------------------------------------------

def load_test_data(city_name: str, config: dict) -> tuple[np.ndarray, np.ndarray]:
    """Load X_test.npy and y_test.npy from the processed data directory.

    Parameters
    ----------
    city_name: City name (e.g. "Delhi").
    config:    Parsed config.yaml dict.

    Returns
    -------
    tuple  (X_test: float32 array, y_test: float32 array)

    Raises
    ------
    FileNotFoundError  If the numpy files are absent.
    """
    city_dir = Path(config["data"]["processed_data_dir"]) / city_name
    x_path = city_dir / "X_test.npy"
    y_path = city_dir / "y_test.npy"

    if not x_path.exists() or not y_path.exists():
        raise FileNotFoundError(
            f"Test tensors not found for {city_name} at {city_dir}. "
            "Run preprocess.py first."
        )

    X_test = np.load(str(x_path)).astype(np.float32)
    y_test = np.load(str(y_path)).astype(np.float32)

    logger.info(
        "load_test_data: %s — X_test=%s y_test=%s",
        city_name, X_test.shape, y_test.shape,
    )
    return X_test, y_test


# ---------------------------------------------------------------------------
# evaluate_model
# ---------------------------------------------------------------------------

def evaluate_model(
    model: EmergencyTrafficModel,
    X_test: np.ndarray,
    y_test: np.ndarray,
    adj_matrix: csr_matrix,
    node_features: pd.DataFrame,
    spatial_proj: nn.Linear,
    config: dict,
    device: torch.device,
) -> dict:
    """Run batched inference on X_test and compute per-horizon metrics.

    Parameters
    ----------
    model:         Trained EmergencyTrafficModel in eval mode.
    X_test:        (N, window_size, 12) float32.
    y_test:        (N, 4) float32 ground-truth speed_ratios.
    adj_matrix:    Scipy CSR adjacency matrix for the city.
    node_features: Per-node feature DataFrame.
    spatial_proj:  nn.Linear(4, 64) projection loaded from checkpoint.
    config:        Parsed config.yaml dict.
    device:        Inference device.

    Returns
    -------
    dict  Flat metrics dict with keys mae_t5 … mape_t30.
    """
    # Build static graph tensors (same for every batch)
    coo = adj_matrix.tocoo()
    edge_index  = torch.tensor(
        np.vstack([coo.row, coo.col]), dtype=torch.long
    ).to(device)
    edge_weight = torch.tensor(coo.data, dtype=torch.float32).to(device)

    x_spatial_raw = torch.tensor(
        node_features[_SPATIAL_COLS].values, dtype=torch.float32
    ).to(device)
    with torch.no_grad():
        x_spatial = spatial_proj(x_spatial_raw)

    batch_size = config["training"]["batch_size"]
    all_preds: list[np.ndarray] = []

    model.eval()
    with torch.no_grad():
        for start in range(0, len(X_test), batch_size):
            x_batch = torch.tensor(
                X_test[start : start + batch_size], dtype=torch.float32
            ).to(device)
            preds, _ = model(x_batch, x_spatial, edge_index, edge_weight)
            all_preds.append(preds.cpu().numpy())

    y_pred = np.concatenate(all_preds, axis=0)   # (N, 4)
    metrics = _metrics_per_horizon(y_test, y_pred)

    logger.info(
        "evaluate_model: MAE t5=%.4f t10=%.4f t20=%.4f t30=%.4f",
        metrics["mae_t5"], metrics["mae_t10"],
        metrics["mae_t20"], metrics["mae_t30"],
    )
    return metrics


# ---------------------------------------------------------------------------
# naive_persistence_baseline
# ---------------------------------------------------------------------------

def naive_persistence_baseline(
    X_test: np.ndarray,
    y_test: np.ndarray,
) -> dict:
    """Baseline: predict next value = last speed_ratio in window (X_test[:,-1,0]).

    Parameters
    ----------
    X_test: (N, window_size, 12).
    y_test: (N, 4).

    Returns
    -------
    dict  Same flat metric keys as evaluate_model.
    """
    last_value = X_test[:, -1, 0]              # (N,) — last speed_ratio
    y_pred = np.tile(last_value[:, None], (1, 4))  # broadcast to (N, 4)
    return _metrics_per_horizon(y_test, y_pred)


# ---------------------------------------------------------------------------
# historical_average_baseline
# ---------------------------------------------------------------------------

def historical_average_baseline(
    X_test: np.ndarray,
    y_test: np.ndarray,
) -> dict:
    """Baseline: predict next value = mean of speed_ratio over input window.

    Parameters
    ----------
    X_test: (N, window_size, 12).
    y_test: (N, 4).

    Returns
    -------
    dict  Same flat metric keys as evaluate_model.
    """
    window_mean = X_test[:, :, 0].mean(axis=1)    # (N,)
    y_pred = np.tile(window_mean[:, None], (1, 4)) # (N, 4)
    return _metrics_per_horizon(y_test, y_pred)


# ---------------------------------------------------------------------------
# api_routing_baseline
# ---------------------------------------------------------------------------

def api_routing_baseline(
    city_name: str,
    config: dict,
    num_samples: int = 50,
) -> dict:
    """Baseline: live Mappls + HERE speed_ratio used as static prediction.

    Fetches real traffic via fetch_all_sources(), computes speed_ratio for
    each segment, uses the median as the representative prediction for all
    4 horizons, then compares against y_test[:num_samples].

    Parameters
    ----------
    city_name:   City name (e.g. "Delhi").
    config:      Parsed config.yaml dict.
    num_samples: How many y_test rows to compare against.

    Returns
    -------
    dict  Same flat metric keys as evaluate_model, or np.nan on fetch failure.
    """
    _nan_result = {
        f"{m}_{h}": float("nan")
        for m in ("mae", "rmse", "mape")
        for h in _HORIZONS
    }

    # Find city bbox
    bbox = None
    for city in config["data"]["cities"]:
        cname = city if isinstance(city, str) else city.get("name", "")
        if cname == city_name:
            bbox = city.get("bbox") if isinstance(city, dict) else None
            break

    if bbox is None:
        logger.warning(
            "api_routing_baseline: no bbox found for %s — skipping", city_name
        )
        return _nan_result

    try:
        traffic_df = fetch_all_sources(bbox, config, city_name)
    except Exception:
        logger.warning(
            "api_routing_baseline: fetch_all_sources failed for %s", city_name,
            exc_info=True,
        )
        return _nan_result

    if traffic_df.empty:
        logger.warning(
            "api_routing_baseline: empty DataFrame returned for %s", city_name
        )
        return _nan_result

    # Compute speed_ratio per segment; guard against zero free_flow
    ffs = traffic_df["free_flow_speed_kmph"].replace(0, np.nan)
    traffic_df = traffic_df.copy()
    traffic_df["speed_ratio"] = (traffic_df["speed_kmph"] / ffs).clip(0.0, 1.5)

    api_speed_ratio = float(traffic_df["speed_ratio"].median())

    # Load y_test for comparison
    try:
        _, y_test = load_test_data(city_name, config)
    except Exception:
        logger.warning(
            "api_routing_baseline: failed to load y_test for %s", city_name,
            exc_info=True,
        )
        return _nan_result

    n = min(num_samples, len(y_test))
    y_true_slice = y_test[:n]
    y_pred = np.full((n, 4), api_speed_ratio, dtype=np.float32)

    return _metrics_per_horizon(y_true_slice, y_pred)


# ---------------------------------------------------------------------------
# run_evaluation  (MAIN ENTRY POINT)
# ---------------------------------------------------------------------------

def run_evaluation(config: dict) -> pd.DataFrame:
    """Full evaluation pipeline across all cities and all baselines.

    Parameters
    ----------
    config: Parsed config.yaml dict.

    Returns
    -------
    pd.DataFrame  Evaluation results (one row per city × model).
    """
    device_str = config["training"].get("device", "cpu")
    device = torch.device(
        "cuda" if device_str == "cuda" and torch.cuda.is_available() else "cpu"
    )
    logger.info("run_evaluation: using device %s", device)

    # Load checkpoint
    ckpt_path = (
        Path(config["training"]["checkpoint_dir"]) / "best_model.pt"
    )
    if not ckpt_path.exists():
        raise FileNotFoundError(f"Checkpoint not found at {ckpt_path}")

    ckpt = torch.load(str(ckpt_path), map_location=device)

    model = build_model(config).to(device)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    # Reconstruct spatial_proj
    gcn_input_dim = config["model"]["gcn_input_dim"]
    spatial_proj = nn.Linear(4, gcn_input_dim).to(device)
    if "spatial_proj_state_dict" in ckpt:
        spatial_proj.load_state_dict(ckpt["spatial_proj_state_dict"])
    else:
        logger.warning(
            "run_evaluation: 'spatial_proj_state_dict' not found in checkpoint "
            "— using randomly initialised projection"
        )
    spatial_proj.eval()

    logger.info(
        "run_evaluation: loaded checkpoint from %s (%s parameters)",
        ckpt_path, f"{count_parameters(model):,}",
    )

    cities = config["data"]["cities"]
    rows: list[dict] = []

    for city_entry in cities:
        city_name = city_entry if isinstance(city_entry, str) else city_entry["name"]
        logger.info("run_evaluation: evaluating city %s", city_name)

        try:
            X_test, y_test = load_test_data(city_name, config)
        except Exception:
            logger.error(
                "run_evaluation: skipping %s — failed to load test data",
                city_name, exc_info=True,
            )
            continue

        try:
            _, adj_matrix, node_feats = build_city_graph(city_name, config)
        except Exception:
            logger.error(
                "run_evaluation: skipping %s — failed to load graph",
                city_name, exc_info=True,
            )
            continue

        # --- Our model ---
        try:
            model_metrics = evaluate_model(
                model, X_test, y_test,
                adj_matrix, node_feats, spatial_proj,
                config, device,
            )
            rows.append({"city": city_name, "model": "lstm_gcn", **model_metrics})
        except Exception:
            logger.error(
                "run_evaluation: model eval failed for %s", city_name,
                exc_info=True,
            )

        # --- Naive persistence ---
        try:
            persist_metrics = naive_persistence_baseline(X_test, y_test)
            rows.append({"city": city_name, "model": "naive_persistence", **persist_metrics})
        except Exception:
            logger.error(
                "run_evaluation: persistence baseline failed for %s",
                city_name, exc_info=True,
            )

        # --- Historical average ---
        try:
            hist_metrics = historical_average_baseline(X_test, y_test)
            rows.append({"city": city_name, "model": "historical_average", **hist_metrics})
        except Exception:
            logger.error(
                "run_evaluation: historical baseline failed for %s",
                city_name, exc_info=True,
            )

        # --- API routing baseline (live fetch) ---
        try:
            api_metrics = api_routing_baseline(city_name, config)
            rows.append({"city": city_name, "model": "api_routing", **api_metrics})
        except Exception:
            logger.error(
                "run_evaluation: API baseline failed for %s",
                city_name, exc_info=True,
            )

    if not rows:
        raise ValueError("run_evaluation: no evaluation results produced")

    results_df = pd.DataFrame(rows)

    # Save CSV
    out_path = Path(config["data"]["processed_data_dir"]) / "evaluation_results.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(str(out_path), index=False)
    logger.info("run_evaluation: results saved to %s", out_path)

    # Summary table in logs
    display_cols = ["city", "model", "mae_t5", "mae_t10", "mae_t20", "mae_t30"]
    log_table = tabulate(
        results_df[display_cols].values.tolist(),
        headers=display_cols,
        tablefmt="github",
        floatfmt=".4f",
    )
    logger.info("run_evaluation summary:\n%s", log_table)

    return results_df


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    with open("config/config.yaml", "r") as f:
        _config = yaml.safe_load(f)
    run_evaluation(_config)

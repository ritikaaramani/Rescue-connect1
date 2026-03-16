"""
Shared pytest fixtures for the emergency-routing-model1 test suite.

All fixtures are zero-network — no real API calls or filesystem I/O
beyond tmp_path.
"""

import time
import pytest
import numpy as np
import pandas as pd
import torch
import yaml
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

from models.lstm_gcn import EmergencyTrafficModel


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------

@pytest.fixture
def config() -> dict:
    """Minimal but complete config dict matching all keys used by the system."""
    return {
        "data": {
            "window_size": 12,
            "prediction_horizons": [5, 10, 20, 30],
            "val_ratio": 0.1,
            "test_ratio": 0.1,
            "raw_data_dir": "data/raw",
            "processed_data_dir": "data/processed",
            "cities": [
                {
                    "name": "Delhi",
                    "bbox": {
                        "north": 28.88, "south": 28.40,
                        "east": 77.35, "west": 76.84,
                    },
                },
                {
                    "name": "Mumbai",
                    "bbox": {
                        "north": 19.27, "south": 18.89,
                        "east": 72.99, "west": 72.77,
                    },
                },
            ],
        },
        "model": {
            "lstm_input_size": 12,
            "lstm_hidden_size": 128,
            "lstm_num_layers": 2,
            "lstm_dropout": 0.2,
            "gcn_input_dim": 64,
            "gcn_hidden_dim": 128,
            "num_prediction_horizons": 4,
        },
        "training": {
            "epochs": 50,
            "batch_size": 32,
            "learning_rate": 0.001,
            "weight_decay": 0.0001,
            "early_stopping_patience": 7,
            "horizon_weights": [1.0, 0.9, 0.7, 0.5],
            "device": "cpu",
            "checkpoint_dir": "models/checkpoints",
        },
        "inference": {
            "host": "0.0.0.0",
            "port": 8001,
            "max_latency_ms": 500,
        },
        "apis": {
            "mappls_base_url": "https://apis.mappls.com",
            "here_base_url": "https://traffic.ls.hereapi.com",
            "ola_maps_base_url": "https://api.olamaps.io",
            "openweather_base_url": "https://api.openweathermap.org",
        },
    }


# ---------------------------------------------------------------------------
# sample_traffic_df
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_traffic_df() -> pd.DataFrame:
    """20-row DataFrame with all 11 TRAFFIC_COLUMNS."""
    n = 20
    now = datetime.now(timezone.utc).isoformat()
    return pd.DataFrame({
        "segment_id":           [f"seg_{i:03d}" for i in range(1, n + 1)],
        "road_name":            [f"Road {i}" for i in range(1, n + 1)],
        "speed_kmph":           [30.0] * n,
        "free_flow_speed_kmph": [60.0] * n,
        "latitude":             [28.6 + i * 0.01 for i in range(n)],
        "longitude":            [77.2 + i * 0.01 for i in range(n)],
        "road_class":           ["primary"] * n,
        "jam_factor":           [2.0] * n,
        "confidence":           [0.9] * n,
        "source":               ["mappls"] * n,
        "fetched_at":           [now] * n,
    })


# ---------------------------------------------------------------------------
# sample_weather_dict
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_weather_dict() -> dict:
    """Plausible weather dict for mid-monsoon Delhi."""
    return {
        "temperature_c":    32.5,
        "precipitation_mm": 12.0,
        "visibility_km":    4.0,
        "wind_speed_kmph":  18.0,
        "monsoon_intensity": 0.6,
        "fog_flag":          False,
        "rain_category":     "moderate",
    }


# ---------------------------------------------------------------------------
# sample_merged_df
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_merged_df(sample_traffic_df, sample_weather_dict) -> pd.DataFrame:
    """20-row DataFrame with 11 traffic + 7 weather columns = 18 total."""
    df = sample_traffic_df.copy()
    for col, val in sample_weather_dict.items():
        df[col] = val
    return df


# ---------------------------------------------------------------------------
# mock_model
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_model() -> MagicMock:
    """MagicMock of EmergencyTrafficModel with pre-set return values."""
    model = MagicMock(spec=EmergencyTrafficModel)
    model.predict_congestion.return_value = {
        "congestion_t5":   np.array([0.4]),
        "congestion_t10":  np.array([0.5]),
        "congestion_t20":  np.array([0.55]),
        "congestion_t30":  np.array([0.6]),
        "uncertainty_t5":  np.array([0.05]),
        "uncertainty_t10": np.array([0.06]),
        "uncertainty_t20": np.array([0.07]),
        "uncertainty_t30": np.array([0.08]),
    }
    model.forward.return_value = (
        torch.sigmoid(torch.randn(2, 4)),
        torch.abs(torch.randn(2, 4)),
    )
    return model


# ---------------------------------------------------------------------------
# mock_config_file
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_config_file(tmp_path: Path, config: dict) -> Path:
    """Write config fixture as YAML to tmp_path/config.yaml. Returns path."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(config))
    return config_path

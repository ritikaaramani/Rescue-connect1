"""
Tests for inference pipeline:
  inference.predict — fetch_live_features, build_inference_window,
                      run_prediction, run_batch_prediction
  inference.api     — FastAPI endpoints via TestClient

All network and filesystem I/O is mocked.
"""

import time
import pytest
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from unittest.mock import MagicMock, patch
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from pathlib import Path

from inference.predict import (
    fetch_live_features,
    build_inference_window,
    run_prediction,
    run_batch_prediction,
)
from data.preprocess import FEATURE_COLUMNS


# ═══════════════════════════════════════════════════════════
# Helper — build a complete sample_merged_df from scratch
# (avoids depending on conftest fixture for isolated tests)
# ═══════════════════════════════════════════════════════════

def _make_merged_df(n_rows: int = 20) -> pd.DataFrame:
    """Build a minimal DataFrame with all FEATURE_COLUMNS present."""
    df = pd.DataFrame({col: [0.5] * n_rows for col in FEATURE_COLUMNS})
    df["fetched_at"] = pd.Timestamp.utcnow().isoformat()
    return df


def _fitted_scaler(n_rows: int = 100) -> MinMaxScaler:
    from sklearn.preprocessing import MinMaxScaler
    scaler = MinMaxScaler()
    scaler.fit(np.random.default_rng(0).random((n_rows, len(FEATURE_COLUMNS))))
    return scaler


# ═══════════════════════════════════════════════════════════
# TestFetchLiveFeatures
# ═══════════════════════════════════════════════════════════

class TestFetchLiveFeatures:
    """Tests for fetch_live_features() live data fetch + merge."""

    _DELHI_BBOX = {"north": 28.88, "south": 28.40, "east": 77.35, "west": 76.84}

    @patch("inference.predict.merge_weather_with_traffic")
    @patch("inference.predict.fetch_city_weather")
    @patch("inference.predict.fetch_all_sources")
    def test_returns_dataframe(
        self, mock_fas, mock_fcw, mock_mwwt,
        sample_traffic_df, sample_weather_dict, sample_merged_df, config,
    ):
        mock_fas.return_value  = sample_traffic_df
        mock_fcw.return_value  = sample_weather_dict
        mock_mwwt.return_value = sample_merged_df

        result = fetch_live_features("Delhi", self._DELHI_BBOX, config)

        assert isinstance(result, pd.DataFrame)
        assert len(result.columns) == 18

    @patch("inference.predict.merge_weather_with_traffic")
    @patch("inference.predict.fetch_city_weather")
    @patch("inference.predict.fetch_all_sources")
    def test_raises_on_empty_df(
        self, mock_fas, mock_fcw, mock_mwwt,
        sample_traffic_df, sample_weather_dict, config,
    ):
        mock_fas.return_value  = sample_traffic_df
        mock_fcw.return_value  = sample_weather_dict
        mock_mwwt.return_value = pd.DataFrame()   # empty

        with pytest.raises(RuntimeError):
            fetch_live_features("Delhi", self._DELHI_BBOX, config)

    @patch("inference.predict.merge_weather_with_traffic")
    @patch("inference.predict.fetch_city_weather")
    @patch("inference.predict.fetch_all_sources")
    def test_calls_fetch_all_sources_with_correct_bbox(
        self, mock_fas, mock_fcw, mock_mwwt,
        sample_traffic_df, sample_weather_dict, sample_merged_df, config,
    ):
        mock_fas.return_value  = sample_traffic_df
        mock_fcw.return_value  = sample_weather_dict
        mock_mwwt.return_value = sample_merged_df

        fetch_live_features("Delhi", self._DELHI_BBOX, config)

        # bbox must be the first positional argument
        called_bbox = mock_fas.call_args[0][0]
        assert called_bbox == self._DELHI_BBOX


# ═══════════════════════════════════════════════════════════
# TestBuildInferenceWindow
# ═══════════════════════════════════════════════════════════

class TestBuildInferenceWindow:
    """Tests for sliding window construction from live DataFrame."""

    def test_output_shape_normal(self, config):
        """20 rows (≥ window_size) → shape (1, 12, 12)."""
        df     = _make_merged_df(n_rows=20)
        scaler = _fitted_scaler()

        result = build_inference_window(df, scaler, config)

        assert result.shape == (1, 12, 12), f"Got {result.shape}"

    def test_short_df_padded(self, config):
        """3 rows (< window_size=12) → padded to shape (1, 12, 12)."""
        df     = _make_merged_df(n_rows=3)
        scaler = _fitted_scaler()

        result = build_inference_window(df, scaler, config)

        assert result.shape == (1, 12, 12), f"Got {result.shape}"

    def test_long_df_truncated(self, config):
        """20 rows (> window_size=12) → truncated to shape (1, 12, 12)."""
        df     = _make_merged_df(n_rows=20)
        scaler = _fitted_scaler()

        result = build_inference_window(df, scaler, config)

        assert result.shape == (1, 12, 12), f"Got {result.shape}"


# ═══════════════════════════════════════════════════════════
# TestRunPrediction
# ═══════════════════════════════════════════════════════════

class TestRunPrediction:
    """Tests for the full single-city run_prediction() pipeline."""

    def _mock_artifacts(self, mock_model):
        """Return a 5-tuple matching load_model_and_graph output."""
        import scipy.sparse as sp
        mock_spatial_proj = MagicMock(spec=nn.Linear)
        mock_spatial_proj.return_value = torch.zeros(5, 64)  # (nodes, gcn_input)

        n = 5
        # Minimal 5×5 sparse identity adjacency
        adj = sp.eye(n, format="csr")

        node_feats = pd.DataFrame({
            "avg_speed_limit":  [50.0] * n,
            "avg_road_weight":  [0.8] * n,
            "is_signal":        [0] * n,
            "street_count":     [4] * n,
        })
        scaler = MagicMock(spec=MinMaxScaler)
        scaler.transform.return_value = np.zeros((12, 12), dtype=np.float32)

        return mock_model, mock_spatial_proj, adj, node_feats, scaler

    @patch("inference.predict.build_inference_window")
    @patch("inference.predict.fetch_live_features")
    @patch("inference.predict.load_model_and_graph")
    def test_returns_expected_keys(
        self, mock_lmag, mock_flf, mock_biw,
        mock_model, sample_merged_df, config,
    ):
        mock_lmag.return_value = self._mock_artifacts(mock_model)
        mock_flf.return_value  = sample_merged_df
        mock_biw.return_value  = np.zeros((1, 12, 12), dtype=np.float32)

        result = run_prediction("Delhi", config, torch.device("cpu"))

        required_keys = {
            "city", "timestamp",
            "congestion_t5", "congestion_t10", "congestion_t20", "congestion_t30",
            "uncertainty_t5", "uncertainty_t10", "uncertainty_t20", "uncertainty_t30",
            "latency_ms",
        }
        assert required_keys.issubset(set(result.keys()))

    @patch("inference.predict.build_inference_window")
    @patch("inference.predict.fetch_live_features")
    @patch("inference.predict.load_model_and_graph")
    def test_latency_ms_is_positive(
        self, mock_lmag, mock_flf, mock_biw,
        mock_model, sample_merged_df, config,
    ):
        mock_lmag.return_value = self._mock_artifacts(mock_model)
        mock_flf.return_value  = sample_merged_df
        mock_biw.return_value  = np.zeros((1, 12, 12), dtype=np.float32)

        result = run_prediction("Delhi", config, torch.device("cpu"))

        assert result["latency_ms"] > 0

    @patch("inference.predict.build_inference_window")
    @patch("inference.predict.fetch_live_features")
    @patch("inference.predict.load_model_and_graph")
    def test_city_name_in_result(
        self, mock_lmag, mock_flf, mock_biw,
        mock_model, sample_merged_df, config,
    ):
        mock_lmag.return_value = self._mock_artifacts(mock_model)
        mock_flf.return_value  = sample_merged_df
        mock_biw.return_value  = np.zeros((1, 12, 12), dtype=np.float32)

        result = run_prediction("Delhi", config, torch.device("cpu"))

        assert result["city"] == "Delhi"

    @patch("inference.predict.load_model_and_graph")
    @patch("inference.predict.fetch_live_features")
    def test_failed_city_returns_error_dict(
        self, mock_flf, mock_lmag,
        mock_model, config,
    ):
        mock_lmag.return_value = self._mock_artifacts(mock_model)
        mock_flf.side_effect   = RuntimeError("fetch failed")

        result = run_batch_prediction(["Delhi"], config, torch.device("cpu"))

        assert len(result) == 1
        assert "error" in result[0]
        assert result[0]["error"] is not None


# ═══════════════════════════════════════════════════════════
# TestBatchPrediction
# ═══════════════════════════════════════════════════════════

class TestBatchPrediction:
    """Tests for run_batch_prediction() multi-city orchestration."""

    def _good_result(self, city: str) -> dict:
        return {
            "city": city, "timestamp": "2026-01-01T00:00:00+00:00",
            "congestion_t5": 0.4, "congestion_t10": 0.5,
            "congestion_t20": 0.55, "congestion_t30": 0.6,
            "uncertainty_t5": 0.05, "uncertainty_t10": 0.06,
            "uncertainty_t20": 0.07, "uncertainty_t30": 0.08,
            "latency_ms": 12.3,
        }

    @patch("inference.predict.run_prediction")
    def test_returns_list_of_correct_length(self, mock_rp, config):
        mock_rp.side_effect = [
            self._good_result("Delhi"),
            self._good_result("Mumbai"),
        ]

        result = run_batch_prediction(
            ["Delhi", "Mumbai"], config, torch.device("cpu")
        )

        assert len(result) == 2

    @patch("inference.predict.run_prediction")
    def test_partial_failure_does_not_raise(self, mock_rp, config):
        mock_rp.side_effect = [
            self._good_result("Delhi"),
            RuntimeError("Mumbai exploded"),
        ]

        result = run_batch_prediction(
            ["Delhi", "Mumbai"], config, torch.device("cpu")
        )

        assert len(result) == 2
        # First succeeded
        assert result[0]["city"] == "Delhi"
        # Second failed — must have 'error' key
        assert "error" in result[1]


# ═══════════════════════════════════════════════════════════
# TestAPIEndpoints
# ═══════════════════════════════════════════════════════════

class TestAPIEndpoints:
    """Synchronous FastAPI endpoint tests via TestClient."""

    @pytest.fixture(autouse=True)
    def _setup_api_state(self, mock_model, config, sample_merged_df):
        """Patch module-level state in inference.api before each test."""
        import inference.api as api_module
        import scipy.sparse as sp
        import torch.nn as nn

        # Build fake cached artifacts for "Delhi"
        mock_spatial_proj = MagicMock(spec=nn.Linear)
        mock_spatial_proj.return_value = torch.zeros(5, 64)

        adj = sp.eye(5, format="csr")
        node_feats = pd.DataFrame({
            "avg_speed_limit":  [50.0] * 5,
            "avg_road_weight":  [0.8]  * 5,
            "is_signal":        [0]    * 5,
            "street_count":     [4]    * 5,
        })
        mock_scaler = MagicMock()
        mock_scaler.transform.return_value = np.zeros((12, 12), dtype=np.float32)

        # Inject state directly (bypasses lifespan)
        api_module._model_cache = {
            "Delhi": (mock_model, mock_spatial_proj, adj, node_feats, mock_scaler)
        }
        api_module._config       = config
        api_module._startup_time = time.time() - 10.0   # simulate 10 s uptime

        self._sample_merged_df = sample_merged_df

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from inference.api import app
        return TestClient(app)

    # --- /health ---

    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        for key in ("status", "model_loaded", "cities_available", "uptime_seconds"):
            assert key in data, f"Missing key: {key}"

    # --- POST /predict ---

    @patch("inference.api.fetch_live_features")
    @patch("inference.api.build_inference_window")
    def test_predict_valid_city(self, mock_biw, mock_flf, client):
        mock_flf.return_value = self._sample_merged_df
        mock_biw.return_value = np.zeros((1, 12, 12), dtype=np.float32)

        resp = client.post("/predict", json={"city_name": "Delhi"})

        assert resp.status_code == 200
        assert "congestion_t5" in resp.json()

    def test_predict_invalid_city(self, client):
        resp = client.post("/predict", json={"city_name": "InvalidCity"})
        assert resp.status_code == 422

    # --- POST /predict/batch ---

    @patch("inference.api.fetch_live_features")
    @patch("inference.api.build_inference_window")
    def test_predict_batch_valid(self, mock_biw, mock_flf, client):
        mock_flf.return_value = self._sample_merged_df
        mock_biw.return_value = np.zeros((1, 12, 12), dtype=np.float32)

        resp = client.post("/predict/batch", json={"city_names": ["Delhi"]})

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_predict_batch_invalid_city_skipped(self, client):
        resp = client.post(
            "/predict/batch", json={"city_names": ["InvalidCity"]}
        )
        # Must be 200, not 422 — invalid cities become error dicts
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert "error" in data[0]

    # --- GET /model/info ---

    def test_model_info_returns_200(self, client):
        resp = client.get("/model/info")
        assert resp.status_code == 200
        assert "parameter_count" in resp.json()

    # --- POST /predict/area ---

    @patch("inference.api.run_prediction_for_bbox")
    def test_predict_area_valid_bbox(self, mock_rpab, client):
        mock_rpab.return_value = {
            "area": "any_area",
            "reference_city": "Delhi",
            "weather_context_city": "Delhi",
            "bbox": {"north": 28.70, "south": 28.60, "east": 77.30, "west": 77.10},
            "timestamp": "2026-01-01T00:00:00+00:00",
            "latency_ms": 12.3,
            "congestion_t5": 0.4,
            "uncertainty_t5": 0.05,
        }

        resp = client.post(
            "/predict/area",
            json={
                "bbox": {"north": 28.70, "south": 28.60, "east": 77.30, "west": 77.10},
                "area_id": "any_area",
            },
        )

        assert resp.status_code == 200
        assert "congestion_t5" in resp.json()

    def test_predict_area_rejects_out_of_india_bbox(self, client):
        resp = client.post(
            "/predict/area",
            json={"bbox": {"north": 55.0, "south": 54.0, "east": 5.0, "west": 4.0}},
        )

        assert resp.status_code == 422

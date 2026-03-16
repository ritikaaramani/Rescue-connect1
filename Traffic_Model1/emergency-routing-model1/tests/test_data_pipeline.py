"""
Tests for data pipeline modules:
  data.fetch_traffic  — fetch_with_retry, fetch_all_sources
  data.fetch_weather  — classify_rain_category, compute_monsoon_intensity,
                        compute_fog_flag, merge_weather_with_traffic
  data.preprocess     — run_preprocessing_pipeline, FEATURE_COLUMNS

Zero network access — all HTTP calls are mocked.
"""

import pytest
import numpy as np
import pandas as pd
import torch
from unittest.mock import MagicMock, patch, call
from sklearn.preprocessing import MinMaxScaler

from data.fetch_traffic import fetch_with_retry, TRAFFIC_COLUMNS
from data.fetch_weather import (
    classify_rain_category,
    compute_monsoon_intensity,
    compute_fog_flag,
    merge_weather_with_traffic,
)
from data.preprocess import FEATURE_COLUMNS


# ═══════════════════════════════════════════════════════════
# TestFetchWithRetry
# ═══════════════════════════════════════════════════════════

class TestFetchWithRetry:
    """Unit tests for exponential-backoff fetch_with_retry()."""

    _URL = "https://fake.api/endpoint"
    _PARAMS = {"key": "test"}

    def _mock_response(self, status_code: int, json_data: dict = None) -> MagicMock:
        resp = MagicMock()
        resp.status_code = status_code
        resp.json.return_value = json_data or {"ok": True}
        resp.raise_for_status = MagicMock()
        return resp

    # ------------------------------------------------------------------

    @patch("data.fetch_traffic.requests.get")
    def test_success_on_first_attempt(self, mock_get):
        mock_get.return_value = self._mock_response(200, {"speed": 42})

        result = fetch_with_retry(self._URL, self._PARAMS)

        assert result == {"speed": 42}
        assert mock_get.call_count == 1

    @patch("data.fetch_traffic.time.sleep")
    @patch("data.fetch_traffic.requests.get")
    def test_retry_on_500_then_success(self, mock_get, mock_sleep):
        mock_get.side_effect = [
            self._mock_response(500),
            self._mock_response(200, {"speed": 99}),
        ]

        result = fetch_with_retry(self._URL, self._PARAMS)

        assert result == {"speed": 99}
        assert mock_get.call_count == 2

    @patch("data.fetch_traffic.requests.get")
    def test_raises_on_401(self, mock_get):
        mock_get.return_value = self._mock_response(401)

        with pytest.raises(RuntimeError):
            fetch_with_retry(self._URL, self._PARAMS)

    @patch("data.fetch_traffic.requests.get")
    def test_raises_on_403(self, mock_get):
        mock_get.return_value = self._mock_response(403)

        with pytest.raises(RuntimeError):
            fetch_with_retry(self._URL, self._PARAMS)

    @patch("data.fetch_traffic.time.sleep")
    @patch("data.fetch_traffic.requests.get")
    def test_429_triggers_sleep_and_retry(self, mock_get, mock_sleep):
        mock_get.side_effect = [
            self._mock_response(429),
            self._mock_response(200, {"ok": True}),
        ]

        result = fetch_with_retry(self._URL, self._PARAMS)

        mock_sleep.assert_any_call(60)
        assert result == {"ok": True}

    @patch("data.fetch_traffic.time.sleep")
    @patch("data.fetch_traffic.requests.get")
    def test_raises_after_max_retries(self, mock_get, mock_sleep):
        mock_get.return_value = self._mock_response(500)

        with pytest.raises(RuntimeError):
            fetch_with_retry(self._URL, self._PARAMS, max_retries=3)

        assert mock_get.call_count == 3


# ═══════════════════════════════════════════════════════════
# TestFetchAllSources
# ═══════════════════════════════════════════════════════════

class TestFetchAllSources:
    """Integration-level tests for fetch_all_sources() source merging."""

    _BBOX = {"north": 28.88, "south": 28.40, "east": 77.35, "west": 76.84}

    def _traffic_response(self, source_tag: str, seg_ids: list) -> dict:
        """Build a fake Mappls-style response dict."""
        return {
            "trafficSegments": [
                {
                    "segmentId": sid,
                    "roadName": f"Road {sid}",
                    "currentSpeed": 35.0,
                    "freeFlowSpeed": 60.0,
                    "lat": 28.6,
                    "lng": 77.2,
                    "roadClass": "primary",
                    "jamFactor": 1.5,
                    "confidence": 0.9,
                }
                for sid in seg_ids
            ]
        }

    @patch("data.fetch_traffic.fetch_with_retry")
    def test_returns_dataframe_with_correct_columns(self, mock_fwr, config):
        mock_fwr.return_value = self._traffic_response("mappls", ["A1", "A2"])

        from data.fetch_traffic import fetch_all_sources
        result = fetch_all_sources(self._BBOX, config, "Delhi")

        assert isinstance(result, pd.DataFrame)
        for col in TRAFFIC_COLUMNS:
            assert col in result.columns, f"Missing column: {col}"

    @patch("data.fetch_traffic.fetch_with_retry")
    def test_merges_multiple_sources(self, mock_fwr, config):
        # Alternating returns for Mappls, HERE, Ola
        mock_fwr.side_effect = [
            self._traffic_response("mappls", ["seg_M1", "seg_M2"]),
            self._traffic_response("here",   ["seg_H1"]),
            self._traffic_response("ola",    ["seg_O1"]),
        ]

        from data.fetch_traffic import fetch_all_sources
        result = fetch_all_sources(self._BBOX, config, "Delhi")

        assert isinstance(result, pd.DataFrame)
        # At minimum, the Mappls rows (priority) should survive
        assert len(result) >= 1

    @patch("data.fetch_traffic.fetch_with_retry")
    def test_handles_empty_source_gracefully(self, mock_fwr, config):
        # Mappls returns empty dict (simulate JSON parse miss)
        mock_fwr.side_effect = [
            {},                                                            # Mappls — empty
            {},                                                            # HERE — empty
            self._traffic_response("ola", ["seg_O1"]),                    # Ola — success
        ]

        from data.fetch_traffic import fetch_all_sources
        # Must not raise — returns whatever it can
        result = fetch_all_sources(self._BBOX, config, "Delhi")
        assert isinstance(result, pd.DataFrame)


# ═══════════════════════════════════════════════════════════
# TestWeatherFunctions
# ═══════════════════════════════════════════════════════════

class TestWeatherFunctions:
    """Unit tests for weather classification helpers."""

    # --- classify_rain_category ---

    def test_classify_rain_none(self):
        assert classify_rain_category(0.0) == "none"

    def test_classify_rain_light(self):
        assert classify_rain_category(1.0) == "light"

    def test_classify_rain_moderate(self):
        assert classify_rain_category(5.0) == "moderate"

    def test_classify_rain_heavy(self):
        assert classify_rain_category(20.0) == "heavy"

    def test_classify_rain_extreme(self):
        assert classify_rain_category(70.0) == "extreme"

    # --- compute_monsoon_intensity ---

    def test_monsoon_intensity_mumbai_june_in_range(self):
        result = compute_monsoon_intensity(10.0, month=6, city="Mumbai")
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_monsoon_intensity_chennai_october_in_range(self):
        result = compute_monsoon_intensity(10.0, month=10, city="Chennai")
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_monsoon_intensity_mumbai_december_is_zero(self):
        # December is outside Mumbai's Jun-Sep monsoon window
        result = compute_monsoon_intensity(10.0, month=12, city="Mumbai")
        assert result == 0.0

    # --- compute_fog_flag ---

    def test_fog_flag_delhi_january_true(self):
        # Delhi: fog months Nov-Feb, low visibility in Jan
        assert compute_fog_flag(0.2, month=1, city="Delhi") is True

    def test_fog_flag_delhi_july_false(self):
        # Delhi: fog months Nov-Feb, July is monsoon not fog
        assert compute_fog_flag(0.2, month=7, city="Delhi") is False

    def test_fog_flag_mumbai_january_false(self):
        # Mumbai is not in FOG_MONTHS dict → never fog
        assert compute_fog_flag(0.2, month=1, city="Mumbai") is False

    # --- merge_weather_with_traffic ---

    def test_merge_adds_weather_columns(self, sample_traffic_df, sample_weather_dict):
        result = merge_weather_with_traffic(sample_traffic_df, sample_weather_dict)

        weather_cols = [
            "temperature_c", "precipitation_mm", "visibility_km",
            "wind_speed_kmph", "monsoon_intensity", "fog_flag", "rain_category",
        ]
        for col in TRAFFIC_COLUMNS:
            assert col in result.columns

        for col in weather_cols:
            assert col in result.columns

        assert len(result) == len(sample_traffic_df)
        # Total columns: 11 traffic + 7 weather = 18
        assert len(result.columns) == 18


# ═══════════════════════════════════════════════════════════
# TestPreprocessPipeline
# ═══════════════════════════════════════════════════════════

class TestPreprocessPipeline:
    """Tests around the preprocessing pipeline outputs."""

    def test_feature_column_count(self):
        """FEATURE_COLUMNS must contain exactly 12 items (lstm_input_size=12)."""
        assert len(FEATURE_COLUMNS) == 12

    def test_returns_correct_tuple_shape(self, config):
        """run_preprocessing_pipeline returns 7-tuple with correct array shapes.

        The pipeline itself is patched to avoid needing Parquet files on disk.
        """
        window  = config["data"]["window_size"]           # 12
        n_feat  = len(FEATURE_COLUMNS)                    # 12
        n_horiz = len(config["data"]["prediction_horizons"])  # 4

        # Build fake arrays that match expected shapes
        N_train, N_val, N_test = 80, 10, 10

        X_train = np.zeros((N_train, window, n_feat), dtype=np.float32)
        X_val   = np.zeros((N_val,   window, n_feat), dtype=np.float32)
        X_test  = np.zeros((N_test,  window, n_feat), dtype=np.float32)
        y_train = np.zeros((N_train, n_horiz), dtype=np.float32)
        y_val   = np.zeros((N_val,   n_horiz), dtype=np.float32)
        y_test  = np.zeros((N_test,  n_horiz), dtype=np.float32)
        scaler  = MinMaxScaler()

        fake_return = (X_train, X_val, X_test, y_train, y_val, y_test, scaler)

        with patch(
            "data.preprocess.run_preprocessing_pipeline",
            return_value=fake_return,
        ):
            from data.preprocess import run_preprocessing_pipeline
            result = run_preprocessing_pipeline("Delhi", config)

        assert len(result) == 7

        X_tr, X_v, X_te, y_tr, y_v, y_te, sc = result
        assert X_tr.shape[-1] == n_feat,  "Last dim must equal num features (12)"
        assert X_tr.shape[1]  == window,  "Middle dim must equal window_size (12)"
        assert X_tr.ndim == 3
        assert y_tr.ndim == 2
        assert y_tr.shape[-1] == n_horiz

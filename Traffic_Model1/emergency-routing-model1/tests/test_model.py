"""
Unit tests for models.lstm_gcn.

All tests use real PyTorch operations (no mocking of torch).
Device: cpu throughout for portability and reproducibility.
"""

import pytest
import torch
import numpy as np

from models.lstm_gcn import EmergencyTrafficModel, build_model, count_parameters


# ═══════════════════════════════════════════════════════════
# Local fixtures
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def minimal_config() -> dict:
    """Smaller architecture so tests run fast on CPU."""
    return {
        "model": {
            "lstm_input_size":         12,
            "lstm_hidden_size":        64,   # reduced for speed
            "lstm_num_layers":          2,
            "lstm_dropout":           0.0,   # 0 avoids non-determinism warnings
            "gcn_input_dim":           16,   # reduced for speed
            "gcn_hidden_dim":          32,   # reduced for speed
            "num_prediction_horizons":  4,
        }
    }


@pytest.fixture
def built_model(minimal_config) -> EmergencyTrafficModel:
    """EmergencyTrafficModel built from minimal_config on CPU."""
    return build_model(minimal_config)


@pytest.fixture
def sample_batch() -> tuple:
    """Consistent random batch with 10 nodes and batch_size=2."""
    num_nodes  = 10
    batch_size = 2
    seq_len    = 12

    torch.manual_seed(42)
    x_temporal  = torch.randn(batch_size, seq_len, 12)
    x_spatial   = torch.randn(num_nodes, 16)      # gcn_input_dim=16
    edge_index  = torch.randint(0, num_nodes, (2, 20))
    edge_weight = torch.rand(20)

    return x_temporal, x_spatial, edge_index, edge_weight


# ═══════════════════════════════════════════════════════════
# TestEmergencyTrafficModel
# ═══════════════════════════════════════════════════════════

class TestEmergencyTrafficModel:
    """Comprehensive tests for the LSTM+GCN model forward pass and helpers."""

    # --- Type checks ---

    def test_build_model_returns_correct_type(self, built_model):
        assert isinstance(built_model, EmergencyTrafficModel)

    def test_count_parameters_positive(self, built_model):
        n = count_parameters(built_model)
        assert isinstance(n, int)
        assert n > 0

    # --- Output shapes ---

    def test_forward_output_shapes(self, built_model, sample_batch):
        x_temporal, x_spatial, edge_index, edge_weight = sample_batch
        predictions, uncertainty = built_model(
            x_temporal, x_spatial, edge_index, edge_weight
        )
        assert predictions.shape == (2, 4), f"Got {predictions.shape}"
        assert uncertainty.shape  == (2, 4), f"Got {uncertainty.shape}"

    # --- Value bounds ---

    def test_predictions_bounded_0_1(self, built_model, sample_batch):
        x_temporal, x_spatial, edge_index, edge_weight = sample_batch
        predictions, _ = built_model(x_temporal, x_spatial, edge_index, edge_weight)
        assert (predictions >= 0.0).all(), "Predictions below 0"
        assert (predictions <= 1.0).all(), "Predictions above 1"

    def test_uncertainty_positive(self, built_model, sample_batch):
        x_temporal, x_spatial, edge_index, edge_weight = sample_batch
        _, uncertainty = built_model(x_temporal, x_spatial, edge_index, edge_weight)
        assert (uncertainty > 0.0).all(), "Uncertainty must be > 0 (Softplus)"

    # --- predict_congestion() ---

    def test_predict_congestion_returns_correct_keys(self, built_model, sample_batch):
        x_temporal, x_spatial, edge_index, edge_weight = sample_batch
        result = built_model.predict_congestion(x_temporal, x_spatial, edge_index, edge_weight)
        expected_keys = {
            "congestion_t5",  "congestion_t10",  "congestion_t20",  "congestion_t30",
            "uncertainty_t5", "uncertainty_t10", "uncertainty_t20", "uncertainty_t30",
        }
        assert set(result.keys()) == expected_keys

    def test_predict_congestion_values_are_floats(self, built_model, sample_batch):
        x_temporal, x_spatial, edge_index, edge_weight = sample_batch
        result = built_model.predict_congestion(x_temporal, x_spatial, edge_index, edge_weight)
        for key, val in result.items():
            # Values may be scalar float or numpy float array
            scalar = float(np.mean(val))
            assert isinstance(scalar, float), f"{key} is not float-like: {type(val)}"

    # --- eval mode / no_grad ---

    def test_model_eval_mode_no_grad(self, built_model, sample_batch):
        x_temporal, x_spatial, edge_index, edge_weight = sample_batch
        built_model.eval()
        with torch.no_grad():
            predictions, uncertainty = built_model(
                x_temporal, x_spatial, edge_index, edge_weight
            )
        assert predictions is not None
        assert uncertainty is not None

    # --- NaN checks ---

    def test_no_nan_in_output(self, built_model, sample_batch):
        x_temporal, x_spatial, edge_index, edge_weight = sample_batch
        predictions, uncertainty = built_model(
            x_temporal, x_spatial, edge_index, edge_weight
        )
        assert not predictions.isnan().any(), "NaN in predictions"
        assert not uncertainty.isnan().any(), "NaN in uncertainty"

    # --- Variable batch sizes ---

    def test_different_batch_sizes(self, built_model, sample_batch):
        _, x_spatial, edge_index, edge_weight = sample_batch

        for batch_size in [1, 4, 8]:
            x_temporal = torch.randn(batch_size, 12, 12)
            predictions, uncertainty = built_model(
                x_temporal, x_spatial, edge_index, edge_weight
            )
            assert predictions.shape == (batch_size, 4), (
                f"batch_size={batch_size}: got {predictions.shape}"
            )
            assert uncertainty.shape == (batch_size, 4)

    # --- Optional edge_weight ---

    def test_edge_weight_optional(self, built_model, sample_batch):
        x_temporal, x_spatial, edge_index, _ = sample_batch
        # Should not raise when edge_weight is None
        predictions, uncertainty = built_model(
            x_temporal, x_spatial, edge_index, edge_weight=None
        )
        assert predictions.shape == (2, 4)
        assert uncertainty.shape  == (2, 4)

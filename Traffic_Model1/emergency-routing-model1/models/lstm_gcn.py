"""
Hybrid LSTM + Graph Convolutional Network for spatiotemporal
traffic prediction on Indian city road networks.

Architecture:
  1. LSTMEncoder        — bidirectional LSTM, temporal patterns
  2. GCNConv layers     — spatial propagation via road graph
  3. AttentionFusion    — learned weighting of temporal vs spatial
  4. PredictionHead     — congestion scores T+5,T+10,T+20,T+30
  5. UncertaintyHead    — confidence band per horizon

Input tensors:
  x_temporal: (batch, window_size, lstm_input_size=12)
  x_spatial:  (num_nodes, gcn_input_dim=64)
  edge_index: (2, num_edges) — PyG sparse format
  edge_weight:(num_edges,)   — india_weight values

Output:
  predictions:  (batch, 4) — sigmoid-bounded [0,1]
  uncertainty:  (batch, 4) — softplus-bounded >0

Target: MAE < 0.10 on normalised speed_ratio scale.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import logging
import importlib
from typing import Tuple, Dict, Optional

try:
    _pyg_nn = importlib.import_module("torch_geometric.nn")
    GCNConv = _pyg_nn.GCNConv
except ImportError:
    GCNConv = None

logger = logging.getLogger(__name__)


class _FallbackGCNConv(nn.Module):
    """Lightweight GCN fallback used when torch_geometric is unavailable."""

    def __init__(self, in_features: int, out_features: int) -> None:
        super().__init__()
        self.lin = nn.Linear(in_features, out_features, bias=False)
        self.bias = nn.Parameter(torch.zeros(out_features))

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_weight: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        num_nodes = x.size(0)
        device = x.device
        dtype = x.dtype

        row = edge_index[0].long()
        col = edge_index[1].long()

        if edge_weight is None:
            edge_weight = torch.ones(row.size(0), device=device, dtype=dtype)
        else:
            edge_weight = edge_weight.to(device=device, dtype=dtype)

        # Add self loops for numerical stability similar to standard GCN.
        self_loops = torch.arange(num_nodes, device=device)
        row = torch.cat([row, self_loops], dim=0)
        col = torch.cat([col, self_loops], dim=0)
        edge_weight = torch.cat(
            [edge_weight, torch.ones(num_nodes, device=device, dtype=dtype)],
            dim=0,
        )

        deg = torch.zeros(num_nodes, device=device, dtype=dtype)
        deg = deg.index_add(0, row, edge_weight)
        deg_inv_sqrt = deg.pow(-0.5)
        deg_inv_sqrt[torch.isinf(deg_inv_sqrt)] = 0.0
        norm = deg_inv_sqrt[row] * edge_weight * deg_inv_sqrt[col]

        out = torch.zeros_like(x)
        out = out.index_add(0, row, x[col] * norm.unsqueeze(-1))
        return self.lin(out) + self.bias


# ---------------------------------------------------------------------------
# GCNLayer
# ---------------------------------------------------------------------------

class GCNLayer(nn.Module):
    """Single graph convolutional layer wrapping PyG's GCNConv.

    Includes BatchNorm, ReLU, and Dropout for training stability
    on large Indian city road graphs (50k–200k nodes).
    """

    def __init__(
        self,
        in_features: int,
        out_features: int,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        conv_cls = GCNConv if GCNConv is not None else _FallbackGCNConv
        if GCNConv is None:
            logger.warning(
                "torch_geometric not found; using fallback graph convolution. "
                "Install torch-geometric for production-quality graph ops."
            )
        self.conv    = conv_cls(in_features, out_features)
        self.bn      = nn.BatchNorm1d(out_features)
        self.dropout = nn.Dropout(dropout)

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_weight: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """Run one graph convolution step.

        Parameters
        ----------
        x:           Node feature matrix  (num_nodes, in_features).
        edge_index:  Edge connectivity    (2, num_edges).
        edge_weight: Optional edge weights (num_edges,).

        Returns
        -------
        Tensor  (num_nodes, out_features)
        """
        x = self.conv(x, edge_index, edge_weight)
        x = self.bn(x)
        x = F.relu(x)
        x = self.dropout(x)
        return x


# ---------------------------------------------------------------------------
# LSTMEncoder
# ---------------------------------------------------------------------------

class LSTMEncoder(nn.Module):
    """Bidirectional LSTM temporal encoder.

    Bidirectional processing captures pre-congestion buildup patterns
    in both directions — critical for Indian rush-hour dynamics where
    congestion can build from either end of a corridor.
    """

    def __init__(
        self,
        input_size: int,
        hidden_size: int,
        num_layers: int,
        dropout: float,
    ) -> None:
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
            bidirectional=True,
        )
        self.output_dim = hidden_size * 2  # bidirectional doubles output

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Encode temporal sequences into a fixed-length representation.

        Parameters
        ----------
        x: (batch, seq_len, input_size)

        Returns
        -------
        Tensor  (batch, hidden_size * 2)
        """
        _, (h_n, _) = self.lstm(x)
        # h_n shape: (num_layers * 2, batch, hidden_size)
        # Last layer: forward = h_n[-2], backward = h_n[-1]
        h_forward  = h_n[-2]
        h_backward = h_n[-1]
        return torch.cat([h_forward, h_backward], dim=1)


# ---------------------------------------------------------------------------
# AttentionFusion
# ---------------------------------------------------------------------------

class AttentionFusion(nn.Module):
    """Learned attention weighting between temporal and spatial branches.

    During monsoon → spatial (flooded roads) matters more.
    During rush hour → temporal (periodic patterns) matters more.
    The network learns these trade-offs from data.
    """

    def __init__(
        self,
        lstm_dim: int,
        gcn_dim: int,
        fusion_dim: int,
    ) -> None:
        super().__init__()
        self.lstm_proj = nn.Linear(lstm_dim, fusion_dim)
        self.gcn_proj  = nn.Linear(gcn_dim,  fusion_dim)
        self.attn      = nn.Linear(fusion_dim * 2, 2)
        self.out_dim   = fusion_dim

    def forward(
        self,
        lstm_out: torch.Tensor,
        gcn_out: torch.Tensor,
    ) -> torch.Tensor:
        """Fuse temporal and spatial representations with attention.

        Parameters
        ----------
        lstm_out: (batch, lstm_dim)
        gcn_out:  (batch, gcn_dim)

        Returns
        -------
        Tensor  (batch, fusion_dim)
        """
        lstm_proj = F.relu(self.lstm_proj(lstm_out))
        gcn_proj  = F.relu(self.gcn_proj(gcn_out))

        combined = torch.cat([lstm_proj, gcn_proj], dim=-1)
        weights  = F.softmax(self.attn(combined), dim=-1)

        fused = weights[:, 0:1] * lstm_proj + weights[:, 1:2] * gcn_proj
        return fused


# ---------------------------------------------------------------------------
# EmergencyTrafficModel
# ---------------------------------------------------------------------------

class EmergencyTrafficModel(nn.Module):
    """Main hybrid LSTM+GCN model with attention fusion.

    Composes LSTMEncoder (temporal), two GCNLayers (spatial),
    AttentionFusion (weighting), and twin prediction / uncertainty heads.
    """

    def __init__(
        self,
        lstm_input_size: int = 12,
        lstm_hidden: int = 128,
        lstm_layers: int = 2,
        lstm_dropout: float = 0.2,
        gcn_input: int = 64,
        gcn_hidden: int = 128,
        fusion_dim: int = 128,
        num_horizons: int = 4,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()

        # --- Temporal branch ---
        self.lstm_encoder = LSTMEncoder(
            input_size=lstm_input_size,
            hidden_size=lstm_hidden,
            num_layers=lstm_layers,
            dropout=lstm_dropout,
        )
        lstm_out_dim = lstm_hidden * 2  # bidirectional

        # --- Spatial branch ---
        self.gcn1 = GCNLayer(gcn_input,  gcn_hidden, dropout)
        self.gcn2 = GCNLayer(gcn_hidden, gcn_hidden, dropout)

        # --- Fusion ---
        self.fusion = AttentionFusion(lstm_out_dim, gcn_hidden, fusion_dim)

        # --- Prediction head — bounded [0, 1] by Sigmoid ---
        self.pred_head = nn.Sequential(
            nn.Linear(fusion_dim, fusion_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(fusion_dim // 2, num_horizons),
            nn.Sigmoid(),
        )

        # --- Uncertainty head — bounded > 0 by Softplus ---
        self.uncertainty_head = nn.Sequential(
            nn.Linear(fusion_dim, fusion_dim // 2),
            nn.ReLU(),
            nn.Linear(fusion_dim // 2, num_horizons),
            nn.Softplus(),
        )

        logger.info(
            "EmergencyTrafficModel: lstm_in=%d lstm_h=%d gcn_in=%d "
            "gcn_h=%d fusion=%d horizons=%d",
            lstm_input_size, lstm_hidden, gcn_input,
            gcn_hidden, fusion_dim, num_horizons,
        )

    def forward(
        self,
        x_temporal: torch.Tensor,
        x_spatial: torch.Tensor,
        edge_index: torch.Tensor,
        edge_weight: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Full forward pass through temporal, spatial, and fusion stages.

        Parameters
        ----------
        x_temporal:  (batch, seq_len, lstm_input_size)
        x_spatial:   (num_nodes, gcn_input_dim)
        edge_index:  (2, num_edges)
        edge_weight: (num_edges,) optional india_weight values

        Returns
        -------
        tuple  (predictions: (batch, num_horizons),
                uncertainty: (batch, num_horizons))
        """
        # --- Temporal ---
        lstm_out = self.lstm_encoder(x_temporal)
        # lstm_out: (batch, lstm_hidden * 2)

        # --- Spatial ---
        gcn_out = self.gcn1(x_spatial, edge_index, edge_weight)
        gcn_out = self.gcn2(gcn_out, edge_index, edge_weight)
        # gcn_out: (num_nodes, gcn_hidden)

        # Mean-pool across all nodes → single graph embedding
        gcn_pooled = gcn_out.mean(dim=0, keepdim=True)
        gcn_pooled = gcn_pooled.expand(lstm_out.size(0), -1)
        # gcn_pooled: (batch, gcn_hidden)

        # --- Attention fusion ---
        fused = self.fusion(lstm_out, gcn_pooled)
        # fused: (batch, fusion_dim)

        # --- Heads ---
        predictions = self.pred_head(fused)
        uncertainty = self.uncertainty_head(fused)

        return predictions, uncertainty

    def predict_congestion(
        self,
        x_temporal: torch.Tensor,
        x_spatial: torch.Tensor,
        edge_index: torch.Tensor,
        edge_weight: Optional[torch.Tensor] = None,
    ) -> dict:
        """Return formatted congestion predictions as numpy arrays.

        Sets model to eval mode and uses torch.no_grad().

        Returns
        -------
        dict  Keys: congestion_t{5,10,20,30} and uncertainty_t{5,10,20,30}.
        """
        self.eval()
        with torch.no_grad():
            preds, unc = self.forward(
                x_temporal, x_spatial, edge_index, edge_weight,
            )
        horizons = [5, 10, 20, 30]
        result: dict = {}
        n_horizons = preds.size(1)

        for idx in range(n_horizons):
            if idx < len(horizons):
                suffix = f"t{horizons[idx]}"
            else:
                suffix = f"h{idx + 1}"
            result[f"congestion_{suffix}"] = preds[:, idx].cpu().numpy()
            result[f"uncertainty_{suffix}"] = unc[:, idx].cpu().numpy()

        return result


# ---------------------------------------------------------------------------
# Standalone helpers
# ---------------------------------------------------------------------------

def count_parameters(model: nn.Module) -> int:
    """Count the number of trainable parameters in a model."""
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def build_model(config: dict) -> EmergencyTrafficModel:
    """Instantiate EmergencyTrafficModel from a config dict.

    Reads all architecture hyper-parameters from config["model"].

    Parameters
    ----------
    config: Parsed config.yaml dict.

    Returns
    -------
    EmergencyTrafficModel  Ready for .to(device) and training.
    """
    m = config["model"]
    model = EmergencyTrafficModel(
        lstm_input_size=m["lstm_input_size"],
        lstm_hidden=m["lstm_hidden_size"],
        lstm_layers=m["lstm_num_layers"],
        lstm_dropout=m["lstm_dropout"],
        gcn_input=m["gcn_input_dim"],
        gcn_hidden=m["gcn_hidden_dim"],
        num_horizons=m["num_prediction_horizons"],
    )
    n_params = count_parameters(model)
    logger.info(
        "build_model: built EmergencyTrafficModel — %s parameters",
        f"{n_params:,}",
    )
    return model


def load_checkpoint_model(
    checkpoint_path: str,
    config: dict,
    device: torch.device,
) -> EmergencyTrafficModel:
    """Build a model from config, load weights from checkpoint, and eval().

    Parameters
    ----------
    checkpoint_path: Path to a .pt checkpoint file.
    config:          Parsed config.yaml dict.
    device:          Target device (cpu / cuda).

    Returns
    -------
    EmergencyTrafficModel  In eval mode on the specified device.

    Raises
    ------
    Exception  Re-raised on any load failure.
    """
    try:
        model = build_model(config).to(device)
        ckpt = torch.load(checkpoint_path, map_location=device)
        model.load_state_dict(ckpt["model_state_dict"])
        model.eval()
        logger.info("load_checkpoint_model: loaded checkpoint from %s", checkpoint_path)
        return model
    except Exception:
        logger.error(
            "load_checkpoint_model: failed to load from '%s'",
            checkpoint_path, exc_info=True,
        )
        raise

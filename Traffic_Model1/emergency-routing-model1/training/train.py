"""
Training loop for the LSTM+GCN emergency traffic prediction
model.

Features:
  - Weighted MSE loss across horizons (T+5 weighted most)
  - AdamW optimiser with cosine annealing LR schedule
  - Early stopping on validation loss
  - Gradient clipping (max_norm=1.0)
  - Checkpoint saving on every validation improvement
  - Loads preprocessed tensors from data/processed/

Usage:
  import yaml
  with open("config/config.yaml") as f:
      config = yaml.safe_load(f)
  train(config)
"""

import os
import yaml
import logging
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from pathlib import Path
from torch.utils.data import DataLoader, TensorDataset
from models.lstm_gcn import EmergencyTrafficModel, build_model
from data.build_graph import build_city_graph

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# compute_weighted_loss
# ---------------------------------------------------------------------------

def compute_weighted_loss(
    predictions: torch.Tensor,
    targets: torch.Tensor,
    weights: list,
) -> torch.Tensor:
    """Compute horizon-weighted MSE loss.

    Nearer horizons (T+5) are weighted more heavily because short-term
    accuracy is most critical for emergency vehicle routing decisions.

    Parameters
    ----------
    predictions: (batch, num_horizons) — model output.
    targets:     (batch, num_horizons) — ground truth speed_ratio.
    weights:     List of floats, e.g. [1.0, 0.9, 0.7, 0.5].

    Returns
    -------
    Tensor  Scalar weighted mean loss.
    """
    losses = []
    for i, w in enumerate(weights):
        mse = F.mse_loss(predictions[:, i], targets[:, i])
        losses.append(w * mse)
    return torch.stack(losses).mean()


# ---------------------------------------------------------------------------
# train_epoch
# ---------------------------------------------------------------------------

def train_epoch(
    model: EmergencyTrafficModel,
    dataloader: DataLoader,
    optimizer: optim.Optimizer,
    weights: list,
    device: torch.device,
    edge_index: torch.Tensor,
    edge_weight: torch.Tensor,
    x_spatial: torch.Tensor,
) -> float:
    """Train the model for one epoch.

    Includes gradient clipping at max_norm=1.0 to prevent exploding
    gradients on long LSTM sequences.

    Returns
    -------
    float  Average training loss over all batches.
    """
    model.train()
    total_loss = 0.0

    for X_batch, y_batch in dataloader:
        X_batch = X_batch.to(device)
        y_batch = y_batch.to(device)

        optimizer.zero_grad()
        predictions, _ = model(X_batch, x_spatial, edge_index, edge_weight)
        loss = compute_weighted_loss(predictions, y_batch, weights)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

        total_loss += loss.item()

    avg_loss = total_loss / max(len(dataloader), 1)
    return avg_loss


# ---------------------------------------------------------------------------
# validate_epoch
# ---------------------------------------------------------------------------

def validate_epoch(
    model: EmergencyTrafficModel,
    dataloader: DataLoader,
    weights: list,
    device: torch.device,
    edge_index: torch.Tensor,
    edge_weight: torch.Tensor,
    x_spatial: torch.Tensor,
) -> float:
    """Validate the model for one epoch (no gradients, no updates).

    Returns
    -------
    float  Average validation loss over all batches.
    """
    model.eval()
    total_loss = 0.0

    with torch.no_grad():
        for X_batch, y_batch in dataloader:
            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device)

            predictions, _ = model(X_batch, x_spatial, edge_index, edge_weight)
            loss = compute_weighted_loss(predictions, y_batch, weights)
            total_loss += loss.item()

    avg_loss = total_loss / max(len(dataloader), 1)
    return avg_loss


# ---------------------------------------------------------------------------
# save_checkpoint
# ---------------------------------------------------------------------------

def save_checkpoint(
    model: EmergencyTrafficModel,
    optimizer: optim.Optimizer,
    epoch: int,
    val_loss: float,
    path: str,
    spatial_proj: nn.Linear = None,
) -> None:
    """Persist model + optimiser state for later resumption or inference.

    Parameters
    ----------
    model:        Trained model.
    optimizer:    Optimiser with current momentum/state.
    epoch:        Current epoch number.
    val_loss:     Validation loss that triggered this save.
    path:         Destination file path.
    spatial_proj: Optional spatial projection layer (4 → gcn_input_dim).
                  If provided, its state dict is stored under
                  'spatial_proj_state_dict' so evaluate.py and predict.py
                  can reload it without retraining.
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    ckpt = {
        "epoch":                epoch,
        "model_state_dict":     model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "val_loss":             val_loss,
    }
    if spatial_proj is not None:
        ckpt["spatial_proj_state_dict"] = spatial_proj.state_dict()
    torch.save(ckpt, path)
    logger.info(
        "save_checkpoint: epoch=%d val_loss=%.6f → %s",
        epoch, val_loss, path,
    )


# ---------------------------------------------------------------------------
# load_checkpoint
# ---------------------------------------------------------------------------

def load_checkpoint(
    model: EmergencyTrafficModel,
    optimizer: optim.Optimizer,
    path: str,
) -> tuple:
    """Restore model + optimiser state from a saved checkpoint.

    Parameters
    ----------
    model:     Model instance (architecture must match).
    optimizer: Optimiser instance.
    path:      Checkpoint file path.

    Returns
    -------
    tuple  (model, optimizer, epoch: int, val_loss: float)
    """
    ckpt = torch.load(path, map_location="cpu")
    model.load_state_dict(ckpt["model_state_dict"])
    optimizer.load_state_dict(ckpt["optimizer_state_dict"])
    epoch    = ckpt["epoch"]
    val_loss = ckpt["val_loss"]
    logger.info(
        "load_checkpoint: loaded from %s, epoch=%d, val_loss=%.6f",
        path, epoch, val_loss,
    )
    return model, optimizer, epoch, val_loss


# ---------------------------------------------------------------------------
# train  (MAIN ENTRY POINT)
# ---------------------------------------------------------------------------

def train(config: dict) -> EmergencyTrafficModel:
    """Run the full training pipeline for the emergency traffic model.

    Steps:
      1. Setup device, checkpoint directory.
      2. Load preprocessed tensors for ALL cities.
      3. Load a representative road graph (first city) for the GCN.
      4. Build DataLoaders.
      5. Build model, optimiser, scheduler.
      6. Training loop with early stopping.
      7. Reload best checkpoint and return.

    Parameters
    ----------
    config: Parsed config.yaml dict.

    Returns
    -------
    EmergencyTrafficModel  Best-performing model (loaded from checkpoint).
    """
    # ------------------------------------------------------------------
    # Step 1 — Device & directories
    # ------------------------------------------------------------------
    device_str = config["training"]["device"]
    device = torch.device(
        "cuda" if device_str == "cuda" and torch.cuda.is_available() else "cpu"
    )
    logger.info("train: using device %s", device)

    checkpoint_dir = config["training"]["checkpoint_dir"]
    Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)
    best_ckpt_path = f"{checkpoint_dir}/best_model.pt"

    # ------------------------------------------------------------------
    # Step 2 — Load preprocessed tensors for all cities
    # ------------------------------------------------------------------
    cities = config["data"]["cities"]
    processed_base = config["data"]["processed_data_dir"]

    X_train_parts, y_train_parts = [], []
    X_val_parts,   y_val_parts   = [], []

    for city in cities:
        city_name = city if isinstance(city, str) else city["name"]
        city_dir = Path(processed_base) / city_name

        x_train_path = city_dir / "X_train.npy"
        y_train_path = city_dir / "y_train.npy"
        x_val_path   = city_dir / "X_val.npy"
        y_val_path   = city_dir / "y_val.npy"

        if not x_train_path.exists():
            logger.error(
                "train: missing preprocessed data for %s at %s",
                city_name, city_dir,
            )
            raise FileNotFoundError(
                f"Preprocessed tensors not found for {city_name} in {city_dir}. "
                "Run preprocess.py first."
            )

        X_train_parts.append(np.load(str(x_train_path)))
        y_train_parts.append(np.load(str(y_train_path)))
        X_val_parts.append(np.load(str(x_val_path)))
        y_val_parts.append(np.load(str(y_val_path)))

        logger.info("train: loaded tensors for %s", city_name)

    X_train_np = np.concatenate(X_train_parts, axis=0).astype(np.float32)
    y_train_np = np.concatenate(y_train_parts, axis=0).astype(np.float32)
    X_val_np   = np.concatenate(X_val_parts,   axis=0).astype(np.float32)
    y_val_np   = np.concatenate(y_val_parts,   axis=0).astype(np.float32)

    logger.info(
        "train: combined X_train=%s y_train=%s X_val=%s y_val=%s",
        X_train_np.shape, y_train_np.shape,
        X_val_np.shape, y_val_np.shape,
    )

    X_train_t = torch.tensor(X_train_np, dtype=torch.float32)
    y_train_t = torch.tensor(y_train_np, dtype=torch.float32)
    X_val_t   = torch.tensor(X_val_np,   dtype=torch.float32)
    y_val_t   = torch.tensor(y_val_np,   dtype=torch.float32)

    # ------------------------------------------------------------------
    # Step 3 — Load representative road graph for GCN
    # ------------------------------------------------------------------
    first_city = cities[0] if isinstance(cities[0], str) else cities[0]["name"]

    try:
        graph, adj, node_feats = build_city_graph(first_city, config)
    except Exception:
        logger.error(
            "train: failed to load graph for %s", first_city,
            exc_info=True,
        )
        raise

    # Convert sparse adjacency → PyG edge_index + edge_weight
    coo = adj.tocoo()
    edge_index = torch.tensor(
        np.vstack([coo.row, coo.col]),
        dtype=torch.long,
    ).to(device)
    edge_weight = torch.tensor(
        coo.data, dtype=torch.float32,
    ).to(device)

    # Node features → spatial input (4 numeric columns)
    spatial_col_names = ["avg_speed_limit", "avg_road_weight",
                         "is_signal", "street_count"]
    x_spatial_raw = torch.tensor(
        node_feats[spatial_col_names].values,
        dtype=torch.float32,
    ).to(device)

    # Project 4 → gcn_input_dim (default 64)
    gcn_input_dim = config["model"]["gcn_input_dim"]
    spatial_proj = nn.Linear(4, gcn_input_dim).to(device)

    logger.info(
        "train: graph loaded — %d nodes, %d edges, spatial projection 4→%d",
        len(graph.nodes), len(graph.edges), gcn_input_dim,
    )

    # ------------------------------------------------------------------
    # Step 4 — DataLoaders
    # ------------------------------------------------------------------
    batch_size = config["training"]["batch_size"]

    train_dataset = TensorDataset(X_train_t, y_train_t)
    val_dataset   = TensorDataset(X_val_t,   y_val_t)

    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=True,
    )
    val_loader = DataLoader(
        val_dataset, batch_size=batch_size, shuffle=False,
    )

    # ------------------------------------------------------------------
    # Step 5 — Model, optimiser, scheduler
    # ------------------------------------------------------------------
    model = build_model(config).to(device)

    # Include spatial_proj parameters in the optimiser
    all_params = list(model.parameters()) + list(spatial_proj.parameters())
    optimizer = optim.AdamW(
        all_params,
        lr=config["training"]["learning_rate"],
        weight_decay=config["training"]["weight_decay"],
    )
    total_epochs = config["training"]["epochs"]
    scheduler = optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=total_epochs,
    )

    weights  = config["training"]["horizon_weights"]
    patience = config["training"]["early_stopping_patience"]

    # ------------------------------------------------------------------
    # Step 6 — Training loop
    # ------------------------------------------------------------------
    best_val_loss  = float("inf")
    patience_count = 0

    logger.info(
        "train: starting training — %d epochs, batch_size=%d, patience=%d",
        total_epochs, batch_size, patience,
    )

    for epoch in range(1, total_epochs + 1):
        # Project spatial features fresh each epoch (grad flows through)
        x_spatial = spatial_proj(x_spatial_raw)

        try:
            train_loss = train_epoch(
                model, train_loader, optimizer, weights,
                device, edge_index, edge_weight, x_spatial,
            )
            val_loss = validate_epoch(
                model, val_loader, weights,
                device, edge_index, edge_weight, x_spatial,
            )
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                logger.error(
                    "train: CUDA OOM at epoch %d — consider reducing "
                    "batch_size (currently %d)",
                    epoch, batch_size, exc_info=True,
                )
            raise

        scheduler.step()
        current_lr = scheduler.get_last_lr()[0]

        logger.info(
            "Epoch %d/%d — train_loss=%.6f val_loss=%.6f lr=%.2e",
            epoch, total_epochs, train_loss, val_loss, current_lr,
        )

        if val_loss < best_val_loss:
            best_val_loss  = val_loss
            patience_count = 0
            save_checkpoint(model, optimizer, epoch, val_loss, best_ckpt_path,
                        spatial_proj=spatial_proj)
            logger.info("train: new best model saved (val_loss=%.6f)", val_loss)
        else:
            patience_count += 1
            if patience_count >= patience:
                logger.info(
                    "train: early stopping at epoch %d (patience=%d exhausted)",
                    epoch, patience,
                )
                break

    # ------------------------------------------------------------------
    # Step 7 — Reload best checkpoint
    # ------------------------------------------------------------------
    model, optimizer, _, _ = load_checkpoint(model, optimizer, best_ckpt_path)
    model = model.to(device)

    logger.info(
        "train: training complete. Best val_loss=%.6f", best_val_loss,
    )
    return model

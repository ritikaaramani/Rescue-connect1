"""
Pan-India training orchestrator.

Discovers preprocessed region directories and trains the existing model over
all regions that have enough samples.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import yaml

from training.train import train

logger = logging.getLogger(__name__)


def discover_trainable_regions(config: dict, min_train_samples: int = 1) -> list[str]:
    """Return processed region names that contain train tensors and scaler."""
    processed_root = Path(config["data"]["processed_data_dir"])
    if not processed_root.exists():
        return []

    regions: list[str] = []
    for region_dir in processed_root.iterdir():
        if not region_dir.is_dir():
            continue

        x_train = region_dir / "X_train.npy"
        y_train = region_dir / "y_train.npy"
        scaler = region_dir / "scaler.pkl"
        if not (x_train.exists() and y_train.exists() and scaler.exists()):
            continue

        try:
            n = int(np.load(str(x_train)).shape[0])
        except Exception:
            logger.warning("discover_trainable_regions: could not read %s", x_train)
            continue

        if n >= min_train_samples:
            regions.append(region_dir.name)

    return sorted(regions)


def run_pan_india_training(config: dict, min_train_samples: int = 1):
    """Train model using all discovered processed regions."""
    regions = discover_trainable_regions(config, min_train_samples=min_train_samples)
    if not regions:
        raise ValueError(
            "No trainable processed regions found. Run data pan-India collection/preprocessing first."
        )

    cfg = dict(config)
    cfg["data"] = dict(config["data"])
    cfg["data"]["cities"] = regions

    logger.info("run_pan_india_training: training on %d regions", len(regions))
    logger.info("run_pan_india_training: regions=%s", regions)
    return train(cfg)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    with open("config/config.yaml", "r") as f:
        config = yaml.safe_load(f)
    run_pan_india_training(config, min_train_samples=10)

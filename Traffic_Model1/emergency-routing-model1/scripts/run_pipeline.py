"""
End-to-end pipeline runner for the Emergency Routing Model.

Steps:
  1. Generate synthetic data (if data/raw/ is empty)
  2. Preprocess → sliding windows + scaler
  3. Train → best_model.pt checkpoint
  4. Evaluate → evaluation_results.csv
  5. Single-city prediction test

Usage:
    cd emergency-routing-model1
    python scripts/run_pipeline.py
"""

import os
import sys
import yaml
import logging
import numpy as np
import pandas as pd
import torch
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(str(PROJECT_ROOT))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pipeline")


def load_config() -> dict:
    config_path = PROJECT_ROOT / "config" / "config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def step1_generate_data(config: dict) -> None:
    """Generate synthetic data if raw directory is empty or has too few rows."""
    import shutil
    raw_dir = PROJECT_ROOT / config["data"]["raw_data_dir"]
    parquet_files = list(raw_dir.rglob("*.parquet")) if raw_dir.exists() else []

    # Check if existing data is sufficient (need >> window_size per segment)
    total_rows = 0
    if parquet_files:
        for pf in parquet_files:
            try:
                total_rows += len(pd.read_parquet(str(pf)))
            except Exception:
                pass
        logger.info("STEP 1: Found %d existing parquet files with %d total rows",
                     len(parquet_files), total_rows)

    if total_rows >= 1000:
        logger.info("STEP 1: Sufficient data exists, skipping generation")
        return

    # Remove stale data and regenerate
    if parquet_files:
        logger.warning("STEP 1: Existing data too small (%d rows). Deleting and regenerating...", total_rows)
        for city_entry in config["data"]["cities"]:
            city_name = city_entry if isinstance(city_entry, str) else city_entry["name"]
            city_dir = raw_dir / city_name
            if city_dir.exists():
                shutil.rmtree(str(city_dir))

    logger.info("STEP 1: Generating synthetic data...")
    from scripts.generate_synthetic_data import main as gen_main
    gen_main()
    logger.info("STEP 1: ✓ Data generation complete")


def step2_preprocess(config: dict) -> None:
    """Run preprocessing for all cities."""
    logger.info("STEP 2: Preprocessing data...")
    from data.preprocess import run_preprocessing_pipeline

    cities = config["data"]["cities"]
    for city_entry in cities:
        city_name = city_entry if isinstance(city_entry, str) else city_entry["name"]
        logger.info("  Processing %s...", city_name)

        try:
            result = run_preprocessing_pipeline(city_name, config)
            X_train = result[0]
            logger.info(
                "  ✓ %s: X_train shape = %s",
                city_name, X_train.shape,
            )
        except Exception as e:
            logger.error("  ✗ %s failed: %s", city_name, e)
            raise

    logger.info("STEP 2: ✓ Preprocessing complete for all cities")


def step3_train(config: dict) -> None:
    """Train the model."""
    logger.info("STEP 3: Training model...")

    # Use CPU and reduce epochs for quick demo
    config_copy = dict(config)
    config_copy["training"] = dict(config["training"])
    config_copy["training"]["device"] = "cpu"
    config_copy["training"]["epochs"] = 5       # Quick demo
    config_copy["training"]["batch_size"] = 16

    from training.train import train
    model = train(config_copy)

    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info("STEP 3: ✓ Training complete — %s parameters", f"{n_params:,}")


def step4_evaluate(config: dict) -> None:
    """Run evaluation (if tabulate is available)."""
    logger.info("STEP 4: Evaluating model...")
    try:
        from training.evaluate import run_evaluation
        run_evaluation(config)
        logger.info("STEP 4: ✓ Evaluation complete")
    except ImportError as e:
        logger.warning(
            "STEP 4: Skipping evaluation (missing dependency: %s). "
            "Install with: pip install tabulate", e,
        )
    except Exception as e:
        logger.warning("STEP 4: Evaluation failed (non-fatal): %s", e)


def step5_predict(config: dict) -> None:
    """Run a single prediction to test inference."""
    logger.info("STEP 5: Running test prediction...")

    from inference.predict import run_prediction

    device = torch.device("cpu")
    city_name = config["data"]["cities"][0]
    if isinstance(city_name, dict):
        city_name = city_name["name"]

    try:
        result = run_prediction(city_name, config, device)
        logger.info("STEP 5: ✓ Prediction result for %s:", city_name)
        for key, val in result.items():
            if isinstance(val, float):
                logger.info("    %s = %.4f", key, val)
            else:
                logger.info("    %s = %s", key, val)
    except Exception as e:
        logger.warning(
            "STEP 5: Prediction failed (expected without live API data): %s", e
        )


def main():
    print("=" * 60)
    print("Emergency Routing Model 1 — Full Pipeline")
    print("=" * 60)
    print()

    config = load_config()

    step1_generate_data(config)
    step2_preprocess(config)
    step3_train(config)
    step4_evaluate(config)
    step5_predict(config)

    print()
    print("=" * 60)
    print("Pipeline complete!")
    print()
    print("To start the API server:")
    print("    python -m inference.api")
    print()
    print("Then test with:")
    print("    curl http://localhost:8001/health")
    print("    curl -X POST http://localhost:8001/predict \\")
    print('         -H "Content-Type: application/json" \\')
    print('         -d \'{"city_name": "Delhi"}\'')
    print("=" * 60)


if __name__ == "__main__":
    main()

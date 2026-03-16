"""
Generate synthetic traffic + weather data for testing the full pipeline.

This script creates realistic-looking Parquet files in data/raw/{city}/
so that preprocess.py → train.py → predict.py can run end-to-end
WITHOUT needing real API keys.

Usage:
    cd emergency-routing-model1
    python scripts/generate_synthetic_data.py
"""

import os
import sys
import yaml
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from data.fetch_traffic import TRAFFIC_COLUMNS


def generate_city_data(
    city_name: str,
    bbox: dict,
    num_segments: int = 50,
    num_timesteps: int = 200,
) -> pd.DataFrame:
    """Generate synthetic traffic + weather rows for one city.

    Returns a DataFrame with all columns needed by preprocess.py:
      - 11 TRAFFIC_COLUMNS  (from fetch_traffic.py)
      - 7  weather columns  (from merge_weather_with_traffic)
    """
    rng = np.random.default_rng(hash(city_name) % 2**32)

    rows = []
    base_time = datetime(2025, 7, 15, 6, 0, 0, tzinfo=timezone.utc)

    road_classes = ["primary", "secondary", "tertiary", "residential", "trunk"]
    road_names = [f"{city_name}_Road_{i}" for i in range(num_segments)]

    for t_idx in range(num_timesteps):
        ts = base_time + timedelta(minutes=5 * t_idx)

        # Simulate rush-hour pattern
        hour = ts.hour
        if 8 <= hour <= 10 or 17 <= hour <= 20:
            speed_factor = 0.4 + rng.random() * 0.3   # slower
        elif 0 <= hour <= 5:
            speed_factor = 0.8 + rng.random() * 0.2   # faster
        else:
            speed_factor = 0.5 + rng.random() * 0.4   # moderate

        for seg_idx in range(num_segments):
            # Core traffic
            free_flow = 40.0 + rng.random() * 40.0  # 40–80 km/h
            speed = free_flow * speed_factor * (0.7 + 0.3 * rng.random())
            lat = bbox["south"] + rng.random() * (bbox["north"] - bbox["south"])
            lon = bbox["west"]  + rng.random() * (bbox["east"]  - bbox["west"])

            # Weather (city-level — same for all segments in this timestep)
            precipitation = max(0.0, rng.normal(5.0, 8.0))
            temperature   = 25.0 + rng.normal(0, 5)
            visibility    = min(10.0, max(0.1, rng.normal(8.0, 3.0)))
            wind_speed    = max(0.0, rng.normal(10, 5))

            # Monsoon intensity: high in Jul–Sep
            month = ts.month
            if 6 <= month <= 9:
                monsoon = min(1.0, precipitation / 64.5)
            else:
                monsoon = 0.0

            fog_flag = visibility < 0.5

            if precipitation == 0:
                rain_cat = "none"
            elif precipitation < 2.5:
                rain_cat = "light"
            elif precipitation < 7.5:
                rain_cat = "moderate"
            elif precipitation < 35.5:
                rain_cat = "heavy"
            elif precipitation < 64.5:
                rain_cat = "very_heavy"
            else:
                rain_cat = "extreme"

            rows.append({
                "segment_id":           f"seg_{city_name}_{seg_idx:04d}",
                "road_name":            road_names[seg_idx],
                "speed_kmph":           round(speed, 2),
                "free_flow_speed_kmph": round(free_flow, 2),
                "latitude":             round(lat, 6),
                "longitude":            round(lon, 6),
                "road_class":           rng.choice(road_classes),
                "jam_factor":           round(rng.random() * 10, 2),
                "confidence":           round(0.5 + 0.5 * rng.random(), 2),
                "source":               rng.choice(["mappls", "here", "ola"]),
                "fetched_at":           ts.isoformat(),
                # Weather columns
                "temperature_c":        round(temperature, 1),
                "precipitation_mm":     round(precipitation, 2),
                "visibility_km":        round(visibility, 2),
                "wind_speed_kmph":      round(wind_speed, 1),
                "monsoon_intensity":    round(monsoon, 3),
                "fog_flag":             bool(fog_flag),
                "rain_category":        rain_cat,
            })

    df = pd.DataFrame(rows)
    return df


def main():
    config_path = PROJECT_ROOT / "config" / "config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    cities = config["data"]["cities"]
    raw_dir = PROJECT_ROOT / config["data"]["raw_data_dir"]

    print(f"Generating synthetic data for {len(cities)} cities...")
    print(f"Output directory: {raw_dir}")

    for city_entry in cities:
        city_name = city_entry["name"]
        bbox = city_entry["bbox"]

        city_dir = raw_dir / city_name
        city_dir.mkdir(parents=True, exist_ok=True)

        df = generate_city_data(city_name, bbox, num_segments=50, num_timesteps=200)

        # Save as Parquet (preprocess.py expects *.parquet files)
        fname = f"traffic_synthetic_{city_name.lower()}_20250715.parquet"
        fpath = city_dir / fname
        df.to_parquet(str(fpath), index=False, engine="pyarrow")

        print(f"  ✓ {city_name}: {len(df)} rows → {fpath}")

    print("\nSynthetic data generation complete!")
    print("Next step: python scripts/run_pipeline.py")


if __name__ == "__main__":
    main()

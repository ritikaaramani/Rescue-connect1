import os
from typing import List, Dict, Any, Optional

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report


# Feature list must match the notebook
FEATURES: List[str] = [
    "road_class",
    "intersection_count",
    "has_bridge",
    "has_tunnel",
    "has_rail_crossing",
    "route_distance_km",
    "congestion_variance",
    "avg_congestion_score",
    "predicted_score_T10",
    "predicted_score_T20",
    "incidents_per_km_month",
    "hour_of_day",
    "day_of_week",
    "is_rush_hour",
    "is_weekend",
    "weather_coeff",
    "eta_minutes",
]


def simulate_route_data(n_samples: int = 5000) -> pd.DataFrame:
    """
    Lightweight port of the notebook's simulation so this module can be
    trained without the notebook if needed.
    """
    rng = np.random.RandomState(42)

    road_class = rng.choice([0, 1, 2], n_samples, p=[0.3, 0.4, 0.3])
    intersection_count = rng.randint(1, 25, n_samples)
    has_bridge = rng.binomial(1, 0.15, n_samples)
    has_tunnel = rng.binomial(1, 0.08, n_samples)
    has_rail_crossing = rng.binomial(1, 0.10, n_samples)
    route_distance_km = rng.uniform(1.0, 15.0, n_samples)
    congestion_variance = rng.uniform(0.0, 1.0, n_samples)
    avg_congestion_score = rng.uniform(0.0, 1.0, n_samples)
    predicted_score_T10 = np.clip(
        avg_congestion_score + rng.normal(0, 0.1, n_samples), 0, 1
    )
    predicted_score_T20 = np.clip(
        avg_congestion_score + rng.normal(0, 0.15, n_samples), 0, 1
    )
    incidents_per_km_month = np.clip(rng.exponential(0.5, n_samples), 0, 5)
    hour_of_day = rng.randint(0, 24, n_samples)
    day_of_week = rng.randint(0, 7, n_samples)
    is_rush_hour = (
        ((hour_of_day >= 8) & (hour_of_day <= 10))
        | ((hour_of_day >= 13) & (hour_of_day <= 14))
        | ((hour_of_day >= 18) & (hour_of_day <= 21))
    ).astype(int)
    is_weekend = (day_of_week >= 5).astype(int)
    weather_coeff = rng.choice([0.7, 0.85, 1.0], n_samples, p=[0.2, 0.3, 0.5])
    eta_minutes = route_distance_km * (1.2 + avg_congestion_score * 1.8)

    # Reliability label similar to notebook: 1 = reliable, 0 = not reliable
    base_prob = 0.65
    prob_reliable = (
        base_prob
        - 0.25 * avg_congestion_score
        - 0.20 * congestion_variance
        - 0.15 * incidents_per_km_month / 5.0
        - 0.10 * has_rail_crossing
        + 0.08 * (weather_coeff == 1.0).astype(float)
        + 0.05 * (road_class == 2).astype(float)
    )
    prob_reliable = np.clip(prob_reliable, 0.05, 0.95)
    label = rng.binomial(1, prob_reliable, n_samples)

    df = pd.DataFrame(
        {
            "road_class": road_class,
            "intersection_count": intersection_count,
            "has_bridge": has_bridge,
            "has_tunnel": has_tunnel,
            "has_rail_crossing": has_rail_crossing,
            "route_distance_km": route_distance_km,
            "congestion_variance": congestion_variance,
            "avg_congestion_score": avg_congestion_score,
            "predicted_score_T10": predicted_score_T10,
            "predicted_score_T20": predicted_score_T20,
            "incidents_per_km_month": incidents_per_km_month,
            "hour_of_day": hour_of_day,
            "day_of_week": day_of_week,
            "is_rush_hour": is_rush_hour,
            "is_weekend": is_weekend,
            "weather_coeff": weather_coeff,
            "eta_minutes": eta_minutes,
            "label": label,
        }
    )
    return df


def train_model2(
    df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Train an XGBoost model for route reliability.
    Returns a dict with the trained model and evaluation metrics.
    """
    if df is None:
        df = simulate_route_data()

    X = df[FEATURES]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        gamma=0.1,
        eval_metric="logloss",
        random_state=42,
    )

    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    pred = model.predict(X_test)
    prob = model.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, pred)
    auc = roc_auc_score(y_test, prob)
    cv_auc = cross_val_score(model, X, y, cv=5, scoring="roc_auc").mean()
    report = classification_report(
        y_test, pred, target_names=["Not Reliable", "Reliable"]
    )

    return {
        "model": model,
        "accuracy": acc,
        "auc": auc,
        "cv_auc": cv_auc,
        "report": report,
    }


def save_model2(model: xgb.XGBClassifier, path: str = "xgb_model.json") -> None:
    model.save_model(path)


def load_model2(path: str = "xgb_model.json") -> xgb.XGBClassifier:
    """
    Load a trained XGBoost model. Train a new one if the file does not exist.
    """
    if not os.path.exists(path):
        trained = train_model2()
        model = trained["model"]
        save_model2(model, path)
        return model

    model = xgb.XGBClassifier()
    model.load_model(path)
    return model


def score_routes(
    model: xgb.XGBClassifier,
    routes_df: pd.DataFrame,
    eta_low_margin: float = 1.0,
    eta_high_margin: float = 2.0,
) -> pd.DataFrame:
    """
    Core API for Model 2 used by the orchestrator.

    Input:
        routes_df: DataFrame with one row per candidate route and at least the
                   17 FEATURES columns.

    Output:
        Same DataFrame with extra columns:
            - reliability: probability of on-time arrival
            - eta_low: lower bound of ETA band
            - eta_high: upper bound of ETA band
    """
    missing = [f for f in FEATURES if f not in routes_df.columns]
    if missing:
        raise ValueError(f"Missing required features for Model 2: {missing}")

    X = routes_df[FEATURES]
    probs = model.predict_proba(X)[:, 1]

    result = routes_df.copy()
    result["reliability"] = probs

    if "eta_minutes" in result.columns:
        result["eta_low"] = result["eta_minutes"] - eta_low_margin
        result["eta_high"] = result["eta_minutes"] + eta_high_margin

    return result


__all__ = [
    "FEATURES",
    "simulate_route_data",
    "train_model2",
    "save_model2",
    "load_model2",
    "score_routes",
]


# Emergency Route Reliability Scoring

**Route reliability scoring for emergency vehicles** — predicts which route is most *reliable* (not just fastest) for ambulances and fire trucks.

## Overview

Traditional navigation apps choose the **fastest** route based on current traffic. That can be risky for emergency vehicles — a route that looks fast now may hit traffic spikes, railway crossing delays, or bottlenecks minutes later.

This project predicts **reliability**: the probability that a route delivers the emergency vehicle **within its estimated time window**. Instead of a single `"8 min ETA"`, dispatchers see:

| Route | Reliability | ETA |
|-------|-------------|-----|
| Route A — Highway   | 93% reliable | 9–10 min ✅ |
| Route B — Main Road | 69% reliable | 7–14 min ⚠️ |
| Route C — Streets   | 46% reliable | 8–17 min ❌ |

## Pipeline Position

```
Model 1 (Traffic Forecaster) → [Model 2: Route Scorer] → Model 3 (RL Agent)
```

This is **Model 2** in the emergency routing pipeline.

## How It Works

1. **Input:** 17 features per route (road type, congestion, incidents, weather, time of day, etc.)
2. **Model:** XGBoost classifier predicts whether the route arrives within ETA ± 2 min
3. **Output:** Reliability % and ETA confidence band per route
4. **Use:** Ranks all routes so the dispatcher can choose the most reliable one

## India-Specific Features

- **Monsoon season** (June–September) impact on road reliability
- **3 peak hour windows:** 9–11am, 1–2pm, 6–9pm
- **Railway crossings** weighted more (common in Indian cities)
- Higher congestion variance reflecting Indian urban traffic
- Simulated data aligned with **MoRTH 2023** city-level emergency response patterns

## Key Results

| Metric | Google Maps | This Model |
|--------|-------------|------------|
| Avg arrival time | 12.2 min | 12.0 min |
| Consistency (std dev) | ±3.4 min | ±1.1 min |
| Worst case (top 10%) | 16.6 min | 13.6 min |

> The average time is similar, but the model reduces the dangerous tail of long delays. In emergencies, the worst case matters most.

## Project Structure

```
emergency-routing/
├── README.md
├── requirements.txt
├── model2.py                         # Model 2 — XGBoost route reliability module
├── xgb_model.json                    # Trained model weights
│
├── integration/                      # Pipeline: Model 1 → Model 2 → Model 3
│   ├── __init__.py
│   ├── pipeline.py                   # Main orchestrator (mock + live modes)
│   ├── feature_builder.py            # Converts Model 1 output → Model 2 features
│   ├── route_generator.py            # Candidate route generation
│   └── schemas.py                    # Dataclasses for inputs/outputs
│
├── external/                         # External model repositories
│   ├── Traffic_Model1/               # Model 1 — LSTM+GCN traffic prediction
│   └── dynamic-rerouting/            # Model 3 — DQN rerouting agent
│
├── notebooks/
│   └── route_reliability_scoring.ipynb  # Training notebook with SHAP analysis
│
└── scripts/
    └── install_model1_deps.ps1       # Model 1 dependency installer
```

## Requirements

**Runtime (pipeline):**
- Python 3.12+
- xgboost
- scikit-learn
- pandas
- numpy
- requests
- PyYAML

**Notebook only (exploration):**
- matplotlib
- seaborn
- shap
- jupyter

## Getting Started

1. **Install runtime dependencies:**
   ```bash
   pip install xgboost scikit-learn pandas numpy requests pyyaml
   ```

2. **Run the full pipeline (mock mode — no servers needed):**
   ```bash
   py -3.12 -m integration.pipeline
   ```
   This runs Model 1 → Model 2 → Model 3 end-to-end with mock data.

3. **Run the notebook (for exploration):**
   - Open `notebooks/route_reliability_scoring.ipynb` in Jupyter or VS Code
   - Run cells to simulate data, train the model, and evaluate results

4. **Use Model 2 as a standalone module:**
   ```python
   from model2 import load_model2, score_routes, FEATURES
   import pandas as pd

   model = load_model2()  # loads xgb_model.json or trains a new one
   routes_df = pd.DataFrame([...])  # one row per route, must include FEATURES
   scored = score_routes(model, routes_df)
   ```

5. **Run the full three-model pipeline programmatically:**

   ```python
   from integration.pipeline import run_emergency_pipeline

   result = run_emergency_pipeline(
       start="hospital",
       destination="accident_location",
       city_name="Bengaluru",
       use_mock=True,   # set False when Model 1 API + SUMO are running
   )

   print(result["model3_decision"])
   # {'vehicle_id': 'ambulance_01', 'action': 'reroute', 'new_route': [...]}
   ```

   Under the hood this does:
   - Model 1: predict future congestion per city/road segment
   - Model 2: score each candidate route for reliability and ETA band
   - Model 3: RL agent decides stay/reroute based on predictions

## License

See repository for license details.

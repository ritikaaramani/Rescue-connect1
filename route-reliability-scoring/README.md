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
└── route_reliability_scoring.ipynb   # Main notebook (data, training, evaluation)
```

## Requirements

- Python 3.x
- xgboost
- scikit-learn
- pandas
- numpy
- matplotlib
- seaborn
- shap (for explainability)

## Getting Started

1. **Install dependencies:**
   ```bash
   pip install xgboost scikit-learn pandas numpy matplotlib seaborn shap
   ```

2. **Run the notebook:**
   - Open `route_reliability_scoring.ipynb` in Jupyter, Google Colab, or VS Code
   - Run cells in order to simulate data, train the model, and evaluate results

The notebook covers:
- Simulated dataset generation (5000 samples)
- Feature engineering (17 features)
- XGBoost and Random Forest training
- Model comparison and hyperparameter tuning
- SHAP-based explainability (why each route gets its score)

## License

See repository for license details.

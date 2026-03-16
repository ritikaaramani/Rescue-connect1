# Emergency Routing — Model 1: Spatiotemporal Traffic Prediction

## Overview
Model 1 predicts near-future congestion (T+5 to T+30 minutes) per road segment for Indian cities using live traffic, weather, and incident features.

## Architecture
The LSTM component models temporal behavior such as rush-hour periodicity and short-term trend shifts.
The GCN component models spatial spillover of congestion across connected road segments.
The hybrid head combines both embeddings to forecast multi-horizon congestion scores.

## Cities Covered
Delhi, Mumbai, Bengaluru, Chennai, Patna

## Setup
1. Clone repo
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill API keys
4. API key sources: Mappls (`https://developer.mappls.com`), HERE (`https://developer.here.com`), Ola Maps (`https://maps.olacabs.com/devportal`), OpenWeatherMap (`https://openweathermap.org/api`)

## Usage
### Fetch Data
Use the `data/` modules to pull traffic, weather, and incident data for configured city bounding boxes.

### Pan-India Grid Data Collection + Preprocessing
Run a grid collector that creates area-wise snapshots and preprocessing artifacts:

`python data/pan_india_pipeline.py`

This writes area folders under `data/raw/area_*` and `data/processed/area_*`.

### Train Model
Run the training entrypoint in `training/train.py` with settings from `config/config.yaml`.

To train on all discovered processed regions (cities + area tiles), run:

`python training/train_pan_india.py`

### Run Inference API
Start the FastAPI app from `inference/api.py` to serve `/predict` and batch prediction routes.

For arbitrary India locations, call:

`POST /predict/area`

with body:

`{"bbox": {"north": 19.15, "south": 19.05, "east": 72.95, "west": 72.82}}`

### OSMnx Note
`osmnx` is used for road graph extraction. If unavailable, the code falls back to a synthetic graph so tests and basic execution still work, but production inference quality requires a real OSMnx graph.

## API Reference
`POST /predict` accepts a `PredictionRequest` with a `bbox` object (`north`, `south`, `east`, `west`) and returns `PredictionResponse` containing per-segment congestion predictions.

## How This Connects to Model 2 and Model 3
Model 1 provides segment-level congestion forecasts that feed Model 2 for route reliability scoring and Model 3 for reinforcement-learning-based rerouting decisions.

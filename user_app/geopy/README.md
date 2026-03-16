# Geolocation Inference Module

A Python-based geolocation inference engine for disaster-related social media posts.

> **Responsibility**: Given a disaster-related post with image, caption, OCR text, and optional GPS, infer the most likely location and confidence.

## Features

- **Location Extraction**: Uses spaCy NER to extract place mentions from text
- **Geocoding**: Converts place names to coordinates via Nominatim
- **Confidence Scoring**: Rule-based explainable confidence (0-1 scale)
- **Ambiguity Detection**: Marks locations with confidence < 0.6 as ambiguous
- **Image Input Ready**: Accepts image for future visual context analysis (Phase-2)

## Setup

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm
```

## Usage

```python
from geo.geo_pipeline import resolve_location

post = {
    "post_id": "1",
    "caption": "Flood near Silk Board junction",
    "ocr_text": "Silk Board",
    "gps": None,
    "image_path": None
}

result = resolve_location(post)
print(result)
```

## Output Format

```json
{
    "post_id": "1",
    "location": "Silk Board Junction, Bengaluru",
    "latitude": 12.9177,
    "longitude": 77.6233,
    "confidence": 0.85,
    "is_ambiguous": false,
    "method": "OCR + caption"
}
```

## Project Structure

```
geo_module/
├── data/
│   ├── samples.json       # Test inputs
│   └── test_cases.json    # Validation cases
├── geo/
│   ├── extractor.py       # Text location extraction
│   ├── geocoder.py        # Geopy integration
│   ├── scorer.py          # Confidence logic
│   └── geo_pipeline.py    # Main pipeline
├── requirements.txt
└── README.md
```

## Running Tests

```bash
python -m geo.geo_pipeline
```

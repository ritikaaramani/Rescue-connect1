# Disaster Text Classification Module

A Python-based text analysis system for processing social media posts during disasters. This is a Phase-1 rule-based implementation that filters disaster-related content, classifies disaster types, extracts location information, and estimates urgency levels.

## What It Does

This module analyzes text from social media posts to:

- Filter out non-disaster-related posts
- Classify the type of disaster (flood, fire, earthquake, building collapse, explosion, etc.)
- Extract location clues using natural language processing
- Handle spelling mistakes and typos using fuzzy matching
- Estimate urgency based on linguistic patterns
- Output structured JSON for downstream geolocation processing

## How It Works

The system uses a rule-based approach with the following components:

1. **Disaster Detection**: Keyword matching to identify disaster-related content
2. **Classification**: Pattern-based categorization of disaster types
3. **Entity Extraction**: NLP-based identification of locations, numbers, and contextual information using spaCy
4. **Typo Handling**: Fuzzy string matching with RapidFuzz to correct common misspellings
5. **Urgency Estimation**: Scoring based on keywords indicating severity and time-sensitivity
6. **JSON Output**: Structured format containing classification, extracted entities, and urgency score

This is a Phase-1 implementation using deterministic rules rather than machine learning models.

## Requirements

- Python 3.11
- spaCy (with English language model)
- RapidFuzz

## How to Run (Windows)

1. Install Python 3.11 if not already installed

2. Install required dependencies:
```
pip install spacy rapidfuzz
python -m spacy download en_core_web_sm
```

3. Run the module:
```
python disaster_classifier.py
```

The script will process input text and output structured JSON containing the disaster classification, extracted location clues, and urgency score.

## Output Format

The module outputs JSON with the following structure:

```json
{
  "is_disaster": true,
  "disaster_type": "flood",
  "locations": ["Downtown", "Main Street"],
  "urgency_score": 0.85,
  "entities": {
    "numbers": ["100"],
    "time_references": ["now", "urgent"]
  }
}
```

This JSON is designed to be consumed by a downstream geolocation module for further processing.

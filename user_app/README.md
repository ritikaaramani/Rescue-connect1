# RescueConnect - Social Media Disaster Response System

An AI-powered disaster response platform that analyzes social media posts to detect, classify, and geolocate disaster events in real-time.

## 🌟 Features

- **AI Image Analysis** - Gemini-powered disaster detection from images
- **OCR Pipeline** - YOLO text detection + Tesseract for extracting text from images
- **Text Classification** - spaCy NER for entity extraction and disaster categorization
- **Geolocation** - Infer precise locations from text, captions, and image context
- **Authority Dashboard** - Real-time monitoring with interactive map view
- **Simulator** - Test posts for development and demo purposes

## 📁 Project Structure

```
social_media_response_app/
├── rescue_connect/
│   ├── authority/          # React dashboard for authorities
│   ├── ml_backend/         # FastAPI ML processing backend
│   │   ├── app/
│   │   │   ├── geo/        # Geolocation pipeline
│   │   │   ├── disaster_classifier.py
│   │   │   ├── image_analyzer.py
│   │   │   └── ocr_pipeline.py
│   │   └── main.py
│   └── simulator/          # React app for simulating posts
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- Supabase account
- Google Gemini API key

### 1. Clone & Setup Environment

```bash
git clone <repository-url>
cd social_media_response_app
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` in each service:

**ML Backend** (`rescue_connect/ml_backend/.env`):
```
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_service_key
GEMINI_API_KEY=your_gemini_key
```

**Authority Dashboard** (`rescue_connect/authority/.env`):
```
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_anon_key
VITE_ML_BACKEND_URL=http://localhost:8000
```

**Simulator** (`rescue_connect/simulator/.env`):
```
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_anon_key
```

### 3. Install Dependencies

```bash
# ML Backend
cd rescue_connect/ml_backend
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Authority Dashboard
cd ../authority
npm install

# Simulator
cd ../simulator
npm install
```

### 4. Start Services

```bash
# Terminal 1: ML Backend (port 8000)
cd rescue_connect/ml_backend
python main.py

# Terminal 2: Authority Dashboard (port 5173)
cd rescue_connect/authority
npm run dev

# Terminal 3: Simulator (port 5174)
cd rescue_connect/simulator
npm run dev
```

## 🔧 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/analyze` | POST | Analyze single image |
| `/process-post` | POST | Process post (image only) |
| `/process-full` | POST | Full pipeline: image + OCR + text + geo |
| `/update-status` | POST | Update post status |
| `/reset-ai` | POST | Reset AI analysis for re-processing |

## 🗺️ Full AI + Geo Pipeline

The `/process-full` endpoint runs the complete analysis:

1. **Image Analysis** - Gemini vision for disaster detection
2. **OCR Extraction** - YOLO + Tesseract for text in images
3. **Text Classification** - spaCy NER + keyword matching
4. **Geolocation** - Nominatim geocoding + scene analysis

### Example Output

```json
{
  "disaster_type": "flood",
  "severity": "high",
  "urgency_score": 8,
  "ocr_text": "Welcome to Kempegowda International Airport",
  "inferred_latitude": 13.1989,
  "inferred_longitude": 77.7068,
  "location_confidence": 0.85,
  "scene_type": "urban_flooding"
}
```

## 📊 Database Schema

Key columns in `posts` table:

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `image_url` | TEXT | Image URL |
| `caption` | TEXT | Post caption |
| `status` | TEXT | pending/verified/rejected/urgent |
| `disaster_type` | TEXT | flood/fire/earthquake/etc |
| `urgency_score` | INT | 1-10 urgency rating |
| `ocr_text` | TEXT | Extracted text from image |
| `inferred_latitude` | DECIMAL | Geo coordinates |
| `inferred_longitude` | DECIMAL | Geo coordinates |
| `ai_processed` | BOOLEAN | Processing status |

## 🛠️ Tech Stack

- **Frontend**: React, Vite, TailwindCSS, Leaflet
- **Backend**: FastAPI, Python
- **AI/ML**: Google Gemini, spaCy, YOLO, Tesseract
- **Database**: Supabase (PostgreSQL)
- **Geocoding**: Nominatim (OpenStreetMap)

## 📝 License

MIT License

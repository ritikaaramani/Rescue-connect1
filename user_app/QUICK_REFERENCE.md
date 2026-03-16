# RescueConnect - Quick Reference Guide

## 🎯 What It Does

**RescueConnect** is an AI-powered disaster response platform that:
1. Analyzes social media disaster reports (images + text)
2. Automatically detects disaster types (floods, fires, earthquakes, etc.)
3. Extracts location information from images and text
4. Assigns severity and urgency scores
5. Dispatches emergency response teams
6. Tracks incident resolution

---

## 🏗️ Architecture Overview

```
Simulator (Users) → ML Backend (Analysis) → Database → Authority Dashboard (Dispatch)
```

**Three Main Applications:**
- **Simulator** (Port 5174) - Victim reporting app
- **ML Backend** (Port 8000) - AI analysis engine
- **Authority Dashboard** (Port 5173) - Response management

---

## 🤖 ML Models & Tools - Complete List

### 1. **Vision/Image Analysis**
- **Google Gemini API** (Primary)
  - Models: gemini-2.0-flash, gemini-1.5-flash, gemini-1.5-pro
  - Detects: flood, fire, earthquake, collapse, explosion
  - Extracts: location hints, visible text, people affected
- **OpenAI GPT-4 Vision** (Fallback)
  - Model: gpt-4o

### 2. **Optical Character Recognition (OCR)**
- **YOLO v8n** (Text Detection)
  - Detects text regions in images
  - Lightweight: 3.2MB model
  - Fast real-time inference
  
- **Tesseract-OCR 5.x** (Text Recognition)
  - Converts detected text to strings
  - Windows path: `C:\Program Files\Tesseract-OCR\tesseract.exe`
  - Multi-language support

### 3. **Natural Language Processing (NLP)**
- **spaCy 3.7** (Named Entity Recognition)
  - Model: en_core_web_sm (40.5MB)
  - Extracts: Locations (GPE, LOC), Organizations, Persons, Numbers
  - Tags used:
    - `GPE`: Countries, cities, states
    - `LOC`: Mountains, bodies of water
    - `FAC`: Facilities, buildings, airports
    - `CARDINAL`: Numbers
    - `QUANTITY`: Measurements

- **RapidFuzz 3.0** (Fuzzy String Matching)
  - Keyword matching with 80% similarity threshold
  - Handles typos and variations
  - Keywords: flood, fire, earthquake, collapse, explosion

### 4. **Computer Vision - Scene Classification**
- **MobileNetV2** (CNN Transfer Learning)
  - PyTorch-based
  - 9 scene categories:
    1. Urban Road (city streets, signals)
    2. Bridge/Flyover (infrastructure)
    3. Residential (houses, colonies)
    4. Water/Flood (rivers, lakes)
    5. Rural (villages, farmland)
    6. Commercial (shops, malls)
    7. Landmark (temples, churches)
    8. Transit (stations, metro)
    9. Industrial (factories)
  - Training: 10 epochs, batch size 16, Adam optimizer
  - Data augmentation: rotation, flip, color jitter

### 5. **Image Processing**
- **OpenCV 4.8** - Image manipulation, resizing, format conversion
- **Pillow 11.0** - PIL for image I/O and preprocessing
- **NumPy 1.24** - Numerical computations

### 6. **Geolocation Stack**
- **geopy 2.4** (Geocoding Library)
  - Nominatim service (OpenStreetMap)
  - Free, no API key required
  - Rate limited: 1.1 second between requests
  - Region: India-focused (country_codes="in")
  - Timeout: 10 seconds per lookup

**Geocoding Features:**
- Spelling normalization for Indian names
  - "theagaraya" → "Sir Thyagaraya"
  - "mount road" → "Anna Salai"
- Recursive fallback (removes words incrementally)
- Result prioritization by type
- Location confidence scoring (0-1)

### 7. **Image Deduplication**
- **imagehash 4.3** (Perceptual Hashing)
  - Average Hash (aHash): Fast, detects large changes
  - Perceptual Hash (pHash): Accurate, slower
  - Hamming distance threshold: 10 bits
  - Time window: 2 hours (configurable)
  - Fallback: MD5 hash for exact matching

### 8. **Deep Learning Framework**
- **PyTorch 2.0+** (Training & inference)
- **Torchvision 0.15** (Pre-trained models)

### 9. **Text Extraction & Disaster Classification**
- **Keyword Matching Database:**
  - flood: inundation, water level, drowning, submerged
  - fire: flames, burning, smoke, wildfire
  - earthquake: quake, shaking, tremor
  - collapse: crumbled, fallen, cave-in
  - explosion: exploded, blast, bomb

- **Urgency Terms:** urgent, help, SOS, trapped, rescue, injured, dead, dying, emergency, critical, blood, ambulance
- **Urgency Scoring:** 0.2 points per term (0-1.0 max)

---

## 📊 Data Flow & Processing Pipeline

```
1. User uploads image + caption
        ↓
2. IMAGE DEDUPLICATION
   - Compute perceptual hash
   - Check against recent posts (2-hour window)
   - Alert if duplicate found
        ↓
3. PARALLEL ANALYSIS:
   ├─ Vision Model (Gemini/GPT-4)
   │  ├─ Disaster detection
   │  ├─ Severity assessment
   │  ├─ Location hints
   │  └─ People affected count
   │
   └─ OCR Pipeline
      ├─ YOLO text detection
      ├─ Tesseract text recognition
      └─ Extract visible text
        ↓
4. TEXT CLASSIFICATION
   ├─ spaCy NER entity extraction
   ├─ Fuzzy keyword matching
   ├─ Disaster type classification
   ├─ Urgency scoring
   └─ Location entity extraction
        ↓
5. GEOLOCATION INFERENCE
   ├─ Scene classification (MobileNetV2)
   ├─ Text location extraction
   ├─ Nominatim geocoding
   ├─ Context-aware query building
   └─ Confidence scoring
        ↓
6. DATA CONSOLIDATION
   ├─ Merge all results
   ├─ Calculate final scores
   └─ Prepare database record
        ↓
7. DATABASE STORAGE (Supabase)
   └─ Store analysis + location + hashes
        ↓
8. AUTHORITY DASHBOARD
   ├─ Display incidents
   ├─ Show on map
   ├─ Add to heatmap
   └─ Await dispatch action
        ↓
9. DISPATCH WORKFLOW
   ├─ pending → assigned → in-progress → resolved
   ├─ Assigned team tracking
   └─ Resolution notes capture
```

---

## 🔄 Key Processing Details

### Image Analysis (Vision Models)
**Input:** Image URL  
**Output:** 
- is_disaster: bool
- disaster_type: string
- severity: critical|high|medium|low
- detected_elements: array
- location_hints: array
- visible_text: string
- people_affected: none|few|many|crowd
- urgency_score: 1-10

**Flood Detection Rules:**
- ✅ Roads underwater, vehicles stuck
- ✅ Water in buildings/homes
- ✅ People wading knee-deep+ water
- ✅ Rivers overflowing
- ✅ Rescue boats on streets
- ❌ NOT: pools, beaches, wet roads, puddles

### OCR Pipeline (YOLO + Tesseract)
**Step 1:** YOLO detects text bounding boxes  
**Step 2:** Tesseract extracts text from each region  
**Output:** Full extracted text + confidence scores + bounding boxes

### Scene Classification
**Input:** Image  
**Process:** MobileNetV2 CNN inference  
**Output:** Scene type + location hints for that scene  
**Used for:** Disambiguating location queries (e.g., "Hospital" in residential vs commercial area)

### Geocoding (Nominatim)
**Input:** Location strings (from NER + image context)  
**Process:**
1. Normalize spelling for common Indian names
2. Combine locations for context ("Bangalore" + "Hospital" → specific hospital)
3. Query Nominatim with country_codes="in"
4. Rank results by type (roads prioritized for road queries)
5. Calculate confidence based on result certainty

**Output:**
- Latitude/Longitude
- Display name
- Confidence (0-1)
- Ambiguity flag
- Scene type match bonus (+0.15)

---

## 💾 Database Structure

**Primary Table:** `posts`
- id, user_id, caption, image_url
- disaster_type, severity, ai_description
- detected_elements[], ocr_text, visible_text
- status, dispatch_status
- location, inferred_latitude, inferred_longitude, location_confidence
- scene_type, extracted_locations[]
- urgency_score
- assigned_team, assigned_at, resolved_at, resolution_notes
- image_hash (for deduplication)
- created_at, updated_at

**Storage:** Supabase (PostgreSQL + Auth + File Storage)

---

## 🔧 All Dependencies

### Python ML Stack
```
fastapi>=0.115.0
uvicorn>=0.32.0
pydantic
python-dotenv
httpx>=0.27.0
pillow>=11.0.0
supabase>=2.10.0

# AI/ML APIs
openai>=1.55.0
google-generativeai>=0.8.0

# NLP
spacy>=3.7.0
rapidfuzz>=3.0.0

# OCR
pytesseract>=0.3.10
ultralytics>=8.0.0

# Computer Vision
opencv-python>=4.8.0
imagehash>=4.3.0

# Deep Learning
torch>=2.0.0
torchvision>=0.15.0

# Geolocation
geopy>=2.4.0
numpy>=1.24.0

# Utilities
python-multipart>=0.0.9
```

### System Requirements
- **Tesseract-OCR 5.x** (separate install)
- **Python 3.9+**
- **Node.js 18+** (for frontend)

### Frontend Dependencies
- React 18+
- Vite
- TailwindCSS
- Leaflet/Mapbox
- Lucide React icons
- Supabase JS client

---

## 🚀 Performance Metrics

### Model Sizes
- MobileNetV2: 12.2 MB
- spaCy model: 40.5 MB
- YOLO v8n: 3.2 MB
- Total: ~500 MB

### Inference Times
- Image analysis (Gemini): 2-5 seconds
- OCR (YOLO + Tesseract): 1-3 seconds
- Scene classification: 200-500 ms
- Geocoding: 1-2 seconds (rate limited)
- **Total per post: 5-12 seconds**

### Throughput
- Single backend: ~300-500 posts/hour
- Parallelizable components: image analysis + OCR run concurrently
- Database: Supports 10K+ concurrent users (Supabase)

---

## 📍 API Endpoints Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/analyze` | POST | Analyze single image |
| `/process-post` | POST | Full ML pipeline |
| `/check-duplicate` | POST | Image deduplication check |
| `/update-dispatch` | POST | Update incident status |
| `/update-status` | POST | Verify/reject post |
| `/reset-ai` | POST | Clear AI analysis |
| `/health` | GET | Health check |

---

## 🔐 Security

- API keys in environment variables
- Supabase RLS for row-level security
- CORS limited to known frontend URLs
- Private image storage bucket
- Rate limiting on geocoding (Nominatim)

---

## 📈 Key Metrics to Track

1. **Disaster Detection Accuracy:** Compare AI predictions vs ground truth
2. **Location Accuracy:** Compare inferred location vs actual GPS
3. **OCR Quality:** Confidence scores for extracted text
4. **Scene Classification:** F1 score across 9 categories
5. **Deduplication Rate:** % of duplicates caught
6. **Geocoding Success Rate:** % of locations successfully coded
7. **End-to-End Latency:** Time from upload to database store
8. **Dispatch Response Time:** Time from incident creation to team assignment

---

## 🎯 Typical Use Case

1. **Victim:** Posts image of flooded street in Chennai with caption "Anna Salai junction flooded"
2. **Simulator App:** 
   - Uploads image to Supabase storage
   - Checks for duplicates (none found)
   - Calls ML backend
3. **ML Backend:**
   - Gemini identifies: flood (severity=high)
   - YOLO+Tesseract extracts: "Anna Salai Signal"
   - spaCy NER: {"locations": ["Anna Salai", "Chennai"]}
   - MobileNetV2: "urban_road"
   - Nominatim: "Anna Salai, Teynampet, Chennai, India" (13.0448°N, 80.2263°E)
4. **Database:** Stores incident with coordinates, severity=high, urgency=8/10
5. **Authority Dashboard:**
   - Shows on map at coordinates
   - Colors red (high severity)
   - Displays AI analysis
   - Officer can assign team
6. **Dispatch:**
   - Team responds
   - Officer updates: "in-progress"
   - Upon completion: "resolved" with notes

---

**Report Created:** January 21, 2026

# RescueConnect - Comprehensive Technical Report

**Project Name:** RescueConnect - AI-Powered Social Media Disaster Response System  
**Current Date:** January 21, 2026  
**Project Status:** Active Development

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [System Components](#system-components)
5. [ML Models & Techniques](#ml-models--techniques)
6. [Data Processing Pipeline](#data-processing-pipeline)
7. [Database Schema](#database-schema)
8. [API Endpoints](#api-endpoints)
9. [Frontend Components](#frontend-components)
10. [Deployment & Configuration](#deployment--configuration)

---

## 🎯 Project Overview

### Purpose
RescueConnect is an intelligent disaster response platform that analyzes social media posts (images and text) in real-time to:
- **Detect** disaster events (floods, fires, earthquakes, etc.) from images
- **Classify** and categorize disaster types with severity levels
- **Extract** location information from images, captions, and OCR text
- **Dispatch** emergency response teams to affected areas
- **Track** incident resolution status and response effectiveness

### Key Features
1. **AI-Powered Image Analysis** - Gemini/OpenAI Vision for disaster detection
2. **OCR Text Extraction** - YOLO + Tesseract for extracting location clues from images
3. **NER (Named Entity Recognition)** - spaCy for extracting locations and entities
4. **Geolocation Pipeline** - Multi-method location inference (GPS, text, image context)
5. **Scene Classification** - CNN-based image scene recognition for location context
6. **Image Deduplication** - Perceptual hashing to prevent duplicate reports
7. **Real-time Dashboard** - Interactive maps, heatmaps, and dispatch management
8. **Authority Management System** - Role-based incident tracking and resolution

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Frontend Layer                             │
├──────────────┬──────────────────────────────┬────────────────────┤
│   Simulator  │    Authority Dashboard       │    MapView/Heatmap │
│  (Port 5174) │     (Port 5173)              │                    │
│   - Post     │  - View Reports              │  - Incident Map    │
│     Creation │  - Dispatch Management       │  - Heat Clusters   │
│   - Upload   │  - Status Tracking           │                    │
│   - Location │  - Resolution Notes          │                    │
└──────┬───────┴──────────────┬────────────────┴────────────────────┘
       │                      │
       │  HTTP/REST API       │
       ├──────────────────────┤
       │                      │
┌──────▼──────────────────────▼──────────────────────────────────────┐
│            FastAPI ML Backend (Port 8000)                          │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │ Main Router & API Endpoints                                │   │
│  │ - /analyze - Image analysis                               │   │
│  │ - /process-post - Full ML pipeline                        │   │
│  │ - /check-duplicate - Image deduplication                  │   │
│  │ - /update-dispatch - Incident status updates              │   │
│  └────────────────────────────────────────────────────────────┘   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐   │
│  │Image Analyzer│ │OCR Pipeline  │ │Disaster Classifier      │   │
│  │- Gemini API  │ │- YOLO v8n    │ │- spaCy NER             │   │
│  │- OpenAI GPT4 │ │- Tesseract   │ │- Keyword Matching      │   │
│  └──────────────┘ └──────────────┘ │- Urgency Scoring       │   │
│  ┌──────────────────────────────────┴─────────────────────────┐   │
│  │ Geolocation Pipeline                                       │   │
│  │ ┌──────────────┐ ┌────────────┐ ┌──────────────┐          │   │
│  │ │Location      │ │Scene       │ │Geocoding     │          │   │
│  │ │Extraction    │ │Classifier  │ │(Nominatim)   │          │   │
│  │ │- spaCy NER   │ │- MobileNetV2│ │- geopy       │          │   │
│  │ │- Regex       │ │- PyTorch   │ │- India Focus │          │   │
│  │ └──────────────┘ └────────────┘ └──────────────┘          │   │
│  └──────────────────────────────────────────────────────────────┘   │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │ Image Deduplication                                        │   │
│  │ - Perceptual Hashing (AHash + PHash)                       │   │
│  │ - Time-windowed duplicate detection                        │   │
│  └────────────────────────────────────────────────────────────┘   │
└──────┬────────────────────────────────────────────────────────────┘
       │
       │ Supabase SDK (PostgreSQL)
       │
┌──────▼──────────────────────────────────────────────────────────────┐
│                   Database Layer (Supabase)                         │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │ posts table                                              │       │
│  │ - Core post data (caption, image_url, status)           │       │
│  │ - AI analysis results (disaster_type, severity, etc.)   │       │
│  │ - Location data (lat, lon, location_confidence)         │       │
│  │ - OCR text and detected elements                        │       │
│  │ - Dispatch status and assigned team                     │       │
│  │ - Image hash for deduplication                          │       │
│  │ - Urgency & severity scores                             │       │
│  └──────────────────────────────────────────────────────────┘       │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │ Storage Bucket: disaster_images                          │       │
│  │ - User-uploaded images for analysis                      │       │
│  └──────────────────────────────────────────────────────────┘       │
└───────────────────────────────────────────────────────────────────┘
```

---

## 💻 Technology Stack

### Frontend (React + Vite)
```
├── React 18.2+
├── Vite (build tool)
├── TailwindCSS (styling)
├── Lucide React (icons)
├── Leaflet/Mapbox (map visualization)
└── Supabase JS Client (database)
```

### Backend (Python)
```
├── FastAPI 0.115.0+ (REST API framework)
├── Uvicorn 0.32.0+ (ASGI server)
├── Pydantic (data validation)
└── Python-dotenv (environment config)
```

### Machine Learning & AI
```
├── Vision Models:
│   ├── Google Gemini 2.0-flash/1.5-pro (image analysis)
│   ├── OpenAI GPT-4 Vision (alternative image analysis)
│   
├── NLP & Text Processing:
│   ├── spaCy 3.7.0 (Named Entity Recognition)
│   ├── rapidfuzz 3.0.0 (fuzzy string matching)
│   
├── Computer Vision:
│   ├── Ultralytics YOLO v8n (text detection in images)
│   ├── Tesseract-OCR 5.x (optical character recognition)
│   ├── OpenCV 4.8.0 (image processing)
│   ├── Pillow 11.0.0 (image manipulation)
│   
├── Scene Classification:
│   ├── PyTorch 2.0.0+ (deep learning framework)
│   ├── Torchvision 0.15.0 (vision models)
│   ├── MobileNetV2 (lightweight CNN for scene classification)
│   
└── Geolocation:
    ├── geopy 2.4.0 (geocoding - Nominatim)
    ├── NumPy 1.24.0 (numerical computing)
```

### Databases & APIs
```
├── Supabase (PostgreSQL + Auth + Storage)
├── Google Gemini API (free tier available)
├── OpenAI API (optional, paid)
└── Nominatim/OpenStreetMap (free geocoding)
```

### Utilities
```
├── HTTPX (async HTTP client)
├── imagehash 4.3.0 (perceptual hashing)
├── python-multipart (form data handling)
```

---

## 🔧 System Components

### 1. **Image Analyzer** (`image_analyzer.py`)

**Purpose:** Analyze disaster images using Vision Language Models

**Supported Providers:**
1. **Google Gemini** (Primary - Free)
   - Models: `gemini-2.0-flash`, `gemini-1.5-flash`, `gemini-1.5-pro`
   - Free tier available at https://aistudio.google.com
   - Automatic model fallback if primary model fails

2. **OpenAI GPT-4 Vision** (Secondary - Paid)
   - Model: `gpt-4o` (vision + language)
   - Requires API key and paid account

**Input:**
- Image URL

**Output:**
```json
{
    "is_disaster": boolean,
    "disaster_type": "flood|fire|earthquake|collapse|explosion|none",
    "severity": "critical|high|medium|low",
    "description": "string",
    "detected_elements": ["element1", "element2"],
    "location_hints": ["location1", "location2"],
    "visible_text": "string (all text visible in image)",
    "people_affected": "none|few|many|crowd",
    "urgency_score": 1-10
}
```

**Key Logic:**
- **Flood Detection Criteria:**
  - ✅ Submerged infrastructure (roads under water, stuck vehicles)
  - ✅ Water entering homes/shops/buildings
  - ✅ People/animals wading in knee-deep+ flood water
  - ✅ Rivers overflowing banks
  - ✅ Rescue operations (boats on streets)

- **False Positives Filtered:**
  - ❌ Recreational: water parks, pools, beaches
  - ❌ Weather: wet roads, puddles, rainy days
  - ❌ Controlled: canals, dams, fountains
  - ❌ Media: movies, screenshots, memes

---

### 2. **OCR Pipeline** (`ocr_pipeline.py`)

**Purpose:** Extract text from images to help identify locations and details

**Components:**

#### A. **YOLO v8n (Nano)** - Text Detection
- **Model:** YOLOv8n.pt (lightweight, 3.2M parameters)
- **Purpose:** Detect text regions in images
- **Input:** Image (various formats)
- **Output:** Bounding boxes around text regions
- **Configuration:** 
  - Pre-trained on text detection dataset
  - Fast inference suitable for real-time processing
  - Handles rotated and skewed text

#### B. **Tesseract-OCR** - Text Recognition
- **Version:** Tesseract-OCR 5.x
- **Purpose:** Convert detected text regions to actual text strings
- **Configuration:**
  - Path: `C:\Program Files\Tesseract-OCR\tesseract.exe` (Windows)
  - Supports multiple languages
  - Configurable with page segmentation modes

**Pipeline Flow:**
```
Image → YOLO Detection → Text Regions → Tesseract OCR → Extracted Text
```

**Output:**
```python
{
    "success": bool,
    "extracted_text": "concatenated text from all regions",
    "regions": [
        {
            "text": "detected text",
            "confidence": float (0-1),
            "bbox": [x1, y1, x2, y2]
        }
    ]
}
```

---

### 3. **Disaster Classifier** (`disaster_classifier.py`)

**Purpose:** Text-based disaster classification and urgency assessment

**Methods:**

#### A. **Keyword Matching with Fuzzy Matching**
- Uses `rapidfuzz` library (Levenshtein distance)
- Threshold: 80% similarity
- Catches variations and typos

**Keywords Database:**
```python
KEYWORDS = {
    "flood": ["flood", "inundation", "water level", "drowning", "submerged"],
    "fire": ["fire", "flames", "burning", "smoke", "wildfire"],
    "earthquake": ["earthquake", "quake", "shaking", "tremor"],
    "collapse": ["collapse", "collapsed", "crumbled", "cave-in"],
    "explosion": ["explosion", "exploded", "blast", "bomb"]
}
```

#### B. **Named Entity Recognition (NER)** - spaCy
- **Model:** `en_core_web_sm` (9.7M, lightweight)
- **NER Tags Used:**
  - `GPE` - Geopolitical entities (countries, cities)
  - `LOC` - Locations (mountain ranges, water bodies)
  - `FAC` - Facilities (buildings, airports, highways)
  - `CARDINAL` - Numbers/counts
  - `QUANTITY` - Measurements

#### C. **Urgency Scoring**
- **Urgency Terms:** urgent, help, SOS, trapped, rescue, injured, dead, dying, emergency, critical, blood, ambulance
- **Scoring:** +0.2 per term detected, capped at 1.0
- **Output:** Float between 0.0 and 1.0

**Functions:**

```python
keyword_gate(text) → bool
# Returns True if text contains disaster keywords

classify_events(text) → (List[str], float)
# Returns (matched_disaster_types, confidence_score)

extract_entities(text) → Dict
# Returns {"locations": [...], "numbers": [...]}

calculate_urgency(text) → float
# Returns urgency score 0.0-1.0

process_post(text) → Dict
# Full text analysis pipeline
```

---

### 4. **Geolocation Pipeline** (`geo/`)

**Purpose:** Infer precise geographic coordinates from posts using multiple methods

#### **A. Location Extraction** (`extractor.py`)

**Method 1: spaCy NER**
- Uses `en_core_web_sm` model
- Extracts GPE, LOC, FAC entities
- Handles capitalized phrases

**Method 2: Regex Patterns**
- Common Indian location formats
- Junction/Signal patterns
- Area names with suffixes (nagar, puram, halli, etc.)
- Multi-word place names

**Fallback:** If spaCy unavailable, uses regex only

---

#### **B. Scene Classification** (`scene_model.py`)

**Purpose:** Analyze image for scene context to disambiguate locations

**Model Architecture:**
- **Base Model:** MobileNetV2 (pretrained on ImageNet)
- **Architecture:** Lightweight CNN suitable for mobile/real-time
- **Fine-tuning:** Transfer learning on disaster scene dataset
- **Num Classes:** 10 scene types

**Scene Categories & Context:**
```python
SCENE_CATEGORIES = {
    0: "urban_road"      # City streets, signals, vehicles
    1: "bridge_flyover"  # Bridges, underpasses, overpasses
    2: "residential"     # Houses, apartments, colonies
    3: "water_flood"     # Rivers, lakes, flooded areas
    4: "rural"           # Villages, farmland, open areas
    5: "commercial"      # Shops, markets, malls
    6: "landmark"        # Temples, churches, monuments
    7: "transit"         # Bus stops, metro, railways
    8: "industrial"      # Factories, warehouses
    9: "unknown"         # Cannot determine
}
```

**Location Hints by Scene:**
```python
SCENE_LOCATION_HINTS = {
    "urban_road": ["junction", "signal", "road", "highway", "main road"],
    "bridge_flyover": ["bridge", "flyover", "underpass", "overpass"],
    "residential": ["layout", "nagar", "colony", "apartments"],
    "water_flood": ["lake", "river", "tank", "canal", "nala"],
    # ... etc
}
```

**Training:**
- Uses PyTorch with CUDA support (GPU acceleration)
- Data augmentation: rotation, flip, color jitter
- Optimizer: Adam
- Loss: Cross-entropy
- Batch size: 16
- Epochs: 10

---

#### **C. Geocoding** (`geocoder.py`)

**Service:** Nominatim (OpenStreetMap)
- **Library:** geopy 2.4.0
- **Free Tier:** No API key required
- **Rate Limiting:** 1.1 second between requests (Nominatim requirement)
- **Region Focus:** India (country_codes="in")
- **Timeout:** 10 seconds per request

**Features:**
1. **Spelling Normalization:** Handles common Indian name variations
   - "theagaraya" → "Sir Thyagaraya"
   - "pondy bazaar" → "Pondy Bazaar"
   - "mount road" → "Anna Salai"

2. **Recursive Fallback:** If exact match fails
   - Remove last word and retry
   - Example: "Sir Thyagaraya Road" → tries "Sir Thyagaraya"

3. **Result Prioritization:**
   - Roads: prioritize "highway" class results
   - Handles multiple results, ranks by relevance

---

#### **D. Location Resolution Pipeline** (`geo_pipeline.py`)

**Algorithm Flow:**
```
1. Extract Text Locations
   ├─ spaCy NER on caption + OCR text
   ├─ Regex patterns as fallback
   └─ Get location_hints from image analysis

2. Analyze Image (if available)
   └─ Scene classification for context

3. Priority Resolution:
   a) If GPS available
      └─ Use GPS coords, enhance with text locations
   
   b) If no GPS
      ├─ Sort extracted locations by specificity
      ├─ Create context-aware queries (location + context)
      ├─ Geocode to get coordinates
      └─ Boost confidence if scene matches location

4. Confidence Scoring
   ├─ Based on geocoding certainty
   ├─ Enhanced by scene matching
   └─ Flagged as ambiguous if low confidence
```

**Output:**
```json
{
    "post_id": "string",
    "location": "display name (e.g., 'Sir Thyagaraya Road, Chennai')",
    "latitude": float,
    "longitude": float,
    "confidence": 0.0-1.0,
    "is_ambiguous": bool,
    "method": "gps|text|image|none",
    "scene_analysis": {
        "scene_type": "urban_road",
        "confidence": 0.92,
        "location_hints": [...]
    }
}
```

---

### 5. **Image Deduplication** (`image_dedup.py`)

**Purpose:** Prevent duplicate reports of the same incident

**Method:** Perceptual Hashing
- Uses `imagehash` library
- Combines two hash types:
  1. **Average Hash (aHash)** - Fast, good for large changes
  2. **Perceptual Hash (pHash)** - More accurate, slower

**Comparison:**
- Hamming distance threshold: 10 bits
- Both hashes must be similar (AND logic)
- Graceful fallback: exact MD5 match

**Time Window:**
- Configurable (default: 2 hours)
- Recent posts checked against new upload
- Balances deduplication vs storage

**Output:**
```json
{
    "is_duplicate": bool,
    "existing_post": {
        "id": "post_id",
        "status": "verified|dispatched|urgent|pending",
        "disaster_type": "string",
        "location": "string"
    },
    "message": "descriptive message for user"
}
```

---

### 6. **Dispatch Management** (`main.py`)

**Dispatch Status Workflow:**
```
pending → assigned → in-progress → resolved
         ↓          ↓
       (rollback to pending/assigned allowed)
```

**State Machine:**
```python
VALID_TRANSITIONS = {
    "pending": ["assigned"],
    "assigned": ["in-progress", "pending"],
    "in-progress": ["resolved", "assigned"],
    "resolved": []  # Terminal state
}
```

**Dispatch Data:**
- `dispatch_status` - Current status
- `assigned_team` - Team name/ID
- `assigned_at` - Timestamp when assigned
- `resolved_at` - Timestamp when resolved
- `resolution_notes` - Notes added upon resolution

---

## 📊 Data Processing Pipeline

### End-to-End Post Processing Flow

```
User Post Created
        ↓
1. IMAGE DEDUPLICATION
   ├─ Download image
   ├─ Compute perceptual hash
   ├─ Check against recent posts (2-hour window)
   ├─ If duplicate: Alert user
   └─ If unique: Continue

2. IMAGE ANALYSIS (Parallel Processing)
   ├─ Vision Model Analysis (Gemini/GPT-4)
   │  ├─ is_disaster: bool
   │  ├─ disaster_type: string
   │  ├─ severity: critical|high|medium|low
   │  └─ location_hints: [...]
   │
   └─ OCR Text Extraction
      ├─ YOLO Detection: Find text regions
      ├─ Tesseract OCR: Convert to text
      └─ extracted_text: full text content

3. TEXT ANALYSIS
   ├─ Disaster Classifier
   │  ├─ Keyword matching (fuzzy)
   │  ├─ spaCy NER: Extract entities
   │  ├─ Classify events: [disaster_types]
   │  └─ Urgency score: 0.0-1.0
   │
   └─ Location Extraction
      ├─ spaCy NER: GPE, LOC, FAC
      ├─ Regex patterns: Common formats
      └─ extracted_locations: [location_strings]

4. GEOLOCATION INFERENCE
   ├─ Image Scene Classification
   │  ├─ MobileNetV2: Classify scene
   │  └─ Get scene-based location hints
   │
   ├─ Geocode Extracted Locations
   │  ├─ Create context-aware queries
   │  ├─ Nominatim lookup
   │  └─ Get coordinates + display name
   │
   └─ Resolve Final Location
      ├─ Combine GPS (if available)
      ├─ Image context boost
      ├─ Calculate confidence
      └─ Flag ambiguity

5. DATA CONSOLIDATION
   ├─ Merge all analysis results
   ├─ Calculate final urgency_score
   ├─ Combine severity + urgency → priority
   └─ Prepare database record

6. DATABASE UPDATE
   ├─ Store all analysis results
   ├─ Store image hash
   ├─ Set initial dispatch_status: pending
   └─ Update posts table

7. AUTHORITY DASHBOARD
   ├─ Display in appropriate filter
   ├─ Show on map (if coordinates available)
   ├─ Add to heatmap
   └─ Await dispatch action
```

---

## 🗄️ Database Schema

### Posts Table Structure
```sql
posts (
    id: UUID PRIMARY KEY,
    
    -- User & Content
    user_id: UUID (user who posted),
    caption: TEXT,
    image_url: VARCHAR,
    image_hash: VARCHAR,  -- Perceptual hash for deduplication
    
    -- AI Analysis Results
    ai_processed: BOOLEAN,
    disaster_type: VARCHAR (flood|fire|earthquake|etc),
    severity: VARCHAR (critical|high|medium|low),
    ai_description: TEXT,
    
    -- Detected Elements & Text
    detected_elements: TEXT[] (array of strings),
    ocr_text: TEXT (extracted from image),
    visible_text: TEXT (visible text in image),
    
    -- Status
    status: VARCHAR (pending|verified|rejected|urgent),
    dispatch_status: VARCHAR (pending|assigned|in-progress|resolved),
    
    -- Location Data
    location: VARCHAR,
    location_hints: TEXT[] (array of hints),
    extracted_locations: TEXT[] (from NER),
    inferred_latitude: NUMERIC,
    inferred_longitude: NUMERIC,
    location_confidence: NUMERIC (0-1),
    location_method: VARCHAR (gps|text|image|none),
    scene_type: VARCHAR (urban_road|bridge_flyover|etc),
    
    -- Scores
    urgency_score: NUMERIC (0-10),
    
    -- Dispatch
    assigned_team: VARCHAR,
    assigned_at: TIMESTAMP,
    resolved_at: TIMESTAMP,
    resolution_notes: TEXT,
    
    -- Metadata
    created_at: TIMESTAMP,
    updated_at: TIMESTAMP
)
```

### Storage Bucket: disaster_images
```
disaster_images/
├── {user_id}/{timestamp}.jpg
├── {user_id}/{timestamp}.jpg
└── ...
```

---

## 🔌 API Endpoints

### Base URL
```
http://localhost:8000
```

### Authentication
- Service Key in headers (Supabase)
- CORS enabled for localhost:5173, 5174, 5175, 3000

### Core Endpoints

#### 1. **POST /analyze**
Analyze a single image without database update

```json
Request:
{
    "image_url": "string",
    "post_id": "optional string"
}

Response:
{
    "is_disaster": bool,
    "disaster_type": "string",
    "severity": "string",
    "description": "string",
    "detected_elements": ["array"],
    "location_hints": "string",
    "people_affected": "string",
    "urgency_score": int
}
```

#### 2. **POST /process-post**
Full ML pipeline - analyze and update database

```json
Request:
{
    "post_id": "string"
}

Response:
{
    "success": bool,
    "message": "string",
    "results": {...analysis results...}
}
```

#### 3. **POST /check-duplicate**
Check if image is duplicate/similar

```json
Request:
{
    "image_url": "string",
    "hours_window": 2
}

Response:
{
    "is_duplicate": bool,
    "existing_post": {...post data...},
    "message": "string"
}
```

#### 4. **POST /update-dispatch**
Update incident dispatch status

```json
Request:
{
    "post_id": "string",
    "dispatch_status": "assigned|in-progress|resolved",
    "assigned_team": "optional string",
    "resolution_notes": "optional string"
}

Response:
{
    "success": bool,
    "post_id": "string",
    "new_status": "string"
}
```

#### 5. **POST /update-status**
Update post verification status

```json
Request:
{
    "post_id": "string",
    "status": "pending|verified|rejected|urgent"
}

Response:
{
    "success": bool
}
```

#### 6. **POST /reset-ai**
Reset AI analysis for a post

```json
Request:
{
    "post_id": "string"
}

Response:
{
    "success": bool
}
```

#### 7. **GET /health**
Health check endpoint

```json
Response:
{
    "status": "healthy",
    "openai_configured": bool,
    "gemini_configured": bool
}
```

---

## 🎨 Frontend Components

### Authority Dashboard (`authority/`)

#### Main Components:

1. **Dashboard** (`Dashboard.jsx`)
   - Statistics overview
   - Recent incidents
   - System health

2. **PostsTable** (`PostsTable.jsx`)
   - Filterable posts list
   - Disaster type badges
   - Severity indicators
   - AI analysis results display
   - Location information
   - **Resolution notes display** (newly added)
   - Action buttons (Verify, Reject, Process)

3. **DispatchView** (`DispatchView.jsx`)
   - Dispatch workflow
   - Team assignment
   - Status transitions
   - Resolution modal with notes

4. **MapView** (`MapView.jsx`)
   - Leaflet-based map
   - Incident markers
   - Location visualization

5. **HeatmapView** (`HeatmapView.jsx`)
   - Incident concentration
   - Heat cluster visualization

6. **Sidebar** (`Sidebar.jsx`)
   - Navigation
   - Filter controls
   - View toggles

### Simulator App (`simulator/`)

**Purpose:** Simulate disaster posts for testing

**Components:**
- Post creation form
- Image/video upload
- Location selection
- Disaster type selection
- Duplicate detection alerts
- Post preview

---

## ⚙️ Deployment & Configuration

### Environment Variables

#### ML Backend (`.env`)
```
# APIs
GEMINI_API_KEY=your-gemini-key
OPENAI_API_KEY=your-openai-key (optional)
MODEL_PROVIDER=gemini  # or openai

# Database
SUPABASE_URL=your-supabase-url
SUPABASE_SERVICE_KEY=your-service-key

# OCR
TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
```

#### Authority Dashboard (`.env`)
```
VITE_SUPABASE_URL=your-supabase-url
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_ML_BACKEND_URL=http://localhost:8000
```

#### Simulator (`.env`)
```
VITE_SUPABASE_URL=your-supabase-url
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_ML_BACKEND_URL=http://localhost:8000
```

### Installation & Startup

#### 1. ML Backend
```bash
cd rescue_connect/ml_backend
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python main.py
# Runs on http://0.0.0.0:8000
```

#### 2. Authority Dashboard
```bash
cd rescue_connect/authority
npm install
npm run dev
# Runs on http://localhost:5173
```

#### 3. Simulator
```bash
cd rescue_connect/simulator
npm install
npm run dev
# Runs on http://localhost:5174
```

### Dependencies Installation

#### Python ML Stack
```bash
# Core dependencies
pip install fastapi uvicorn python-multipart pydantic python-dotenv

# APIs
pip install httpx supabase google-generativeai openai

# Image processing
pip install pillow opencv-python

# ML Models
pip install torch torchvision spacy rapidfuzz pytesseract ultralytics

# Geolocation
pip install geopy numpy

# Utilities
pip install imagehash
```

#### System Dependencies
```
# Windows
- Tesseract-OCR: https://github.com/UB-Mannheim/tesseract/wiki
- Python 3.9+
- Visual C++ Build Tools (for PyTorch)

# Linux/Mac
apt-get install tesseract-ocr
```

---

## 📈 Performance & Scalability

### Model Sizes
- **MobileNetV2:** 12.2 MB (lightweight)
- **spaCy en_core_web_sm:** 40.5 MB
- **YOLO v8n:** 3.2 MB
- **Total ML deps:** ~500 MB

### Inference Times (Typical)
- Image analysis (Gemini): 2-5 seconds
- OCR (YOLO + Tesseract): 1-3 seconds
- Scene classification: 200-500 ms
- Geocoding: 1-2 seconds (rate limited)
- **Total per post:** 5-12 seconds

### Throughput
- Single backend instance: ~300-500 posts/hour
- Parallelizable: image analysis & OCR run in parallel
- Database: Supabase scales to 10K+ concurrent users

### Optimization Opportunities
1. Implement Celery/Redis for task queuing
2. GPU acceleration for PyTorch models
3. Caching for geocoding results
4. Image resizing before OCR

---

## 🔒 Security Considerations

1. **API Keys:** Use environment variables, never commit
2. **Supabase RLS:** Service key bypasses RLS for admin operations
3. **CORS:** Limited to known frontend URLs
4. **Image Storage:** Private Supabase bucket with auth required
5. **Rate Limiting:** Nominatim rate limiting built-in (1.1 sec/request)

---

## 🧪 Testing & Quality

### ML Model Evaluation
- Scene classifier: Test on labeled disaster images
- OCR: Test on various image quality levels
- Geocoding: Test on Indian location names and variations

### Unit Tests
- Image deduplication hash similarity
- Text classification keyword matching
- Entity extraction accuracy

### Integration Tests
- Full post processing pipeline
- API endpoint validation
- Database consistency

---

## 📝 Future Enhancements

1. **Multi-language Support:** Extend NER to Hindi, Tamil, Telugu
2. **Real-time Streaming:** WebSocket updates for live incidents
3. **Mobile App:** Native iOS/Android apps
4. **Advanced Analytics:** Predictive modeling for disaster hotspots
5. **Social Media Integration:** Direct post ingestion from Twitter, WhatsApp
6. **Voice Reporting:** Speech-to-text for accessibility
7. **Multi-modal Fusion:** Combine multiple modality signals
8. **Distributed Processing:** Scale to national disaster response

---

## 📚 References

### ML Models Used
- [Google Gemini Documentation](https://ai.google.dev/)
- [OpenAI Vision Documentation](https://platform.openai.com/)
- [spaCy NLP Library](https://spacy.io/)
- [Ultralytics YOLO](https://docs.ultralytics.com/)
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
- [PyTorch Documentation](https://pytorch.org/docs/)
- [MobileNetV2 Paper](https://arxiv.org/abs/1801.04381)
- [geopy Geocoding](https://geopy.readthedocs.io/)

### Libraries
- [FastAPI](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Supabase](https://supabase.com/docs)
- [Vite](https://vitejs.dev/)

---

**Report Generated:** January 21, 2026  
**Project Status:** Active & In Production  
**Last Updated:** Current Development


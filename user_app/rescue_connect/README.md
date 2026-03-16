# RescueConnect - Disaster Relief Platform

A social media simulator for disaster reporting with AI-powered flood detection.

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    SIMULATOR    │     │   ML BACKEND    │     │   AUTHORITY     │
│  (Victim App)   │────▶│  (AI Analysis)  │◀────│   (Dashboard)   │
│  localhost:5173 │     │  localhost:8000 │     │  localhost:5174 │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┴───────────────────────┘
                                 │
                         ┌───────▼───────┐
                         │   SUPABASE    │
                         │  (Database)   │
                         └───────────────┘
```

## 📁 Project Structure

```
rescue_connect/
├── simulator/          # React app for victims to post disaster reports
├── authority/          # React app for authorities to review/manage reports
├── ml_backend/         # FastAPI server with Gemini AI for flood detection
└── README.md
```

## 🚀 Getting Started

### Prerequisites
- Node.js 18+
- Python 3.10+
- Supabase account
- Gemini API key (free)

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/rescue_connect.git
cd rescue_connect
```

### 2. Setup ML Backend
```bash
cd ml_backend
cp .env.example .env
# Edit .env with your keys
pip install -r requirements.txt
python main.py
```

### 3. Setup Simulator
```bash
cd simulator
cp .env.example .env
# Edit .env with your Supabase keys
npm install
npm run dev
```

### 4. Setup Authority Dashboard
```bash
cd authority
cp .env.example .env
# Edit .env with your Supabase keys
npm install
npm run dev
```

## 🔑 Environment Variables

| Variable | Where to get it |
|----------|-----------------|
| `SUPABASE_URL` | Supabase Dashboard → Settings → API |
| `SUPABASE_SERVICE_KEY` | Supabase Dashboard → Settings → API (service_role) |
| `VITE_SUPABASE_ANON_KEY` | Supabase Dashboard → Settings → API (anon) |
| `GEMINI_API_KEY` | https://aistudio.google.com/app/apikey |

## 🤖 AI Model

Currently using **Google Gemini** for flood detection.

## 📝 License

MIT

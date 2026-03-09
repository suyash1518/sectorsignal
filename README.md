# SectorSignal 📊

> Regional stock sector intelligence — live scoring via Yahoo Finance + NLP sentiment

**India · US · Japan** — tells you which sectors are BUY / WATCH / AVOID right now, with real data.

---

## How It Works

```
Yahoo Finance (yfinance)  ──→  Price data, P/E, 52W high/low
Yahoo News RSS            ──→  Headlines per sector
VADER NLP                 ──→  Sentiment score from headlines
Macro keyword search      ──→  Is macro environment favorable?
                               ↓
                     Composite Score (0–100)
                               ↓
                     BUY / WATCH / AVOID signal
```

### Scoring Formula
| Factor | Weight | Source |
|---|---|---|
| Value (P/E + 52W discount) | 45% | yfinance |
| News Sentiment | 25% | Yahoo RSS + VADER |
| Macro Alignment | 30% | Yahoo News keyword analysis |

---

## Project Structure

```
sectorsignal/
├── backend/              ← FastAPI (deploy on Render)
│   ├── app/
│   │   ├── main.py          API endpoints
│   │   ├── scorer.py        Core scoring engine
│   │   └── sectors_config.py  Region/sector definitions
│   ├── requirements.txt
│   └── render.yaml          Render deployment config
│
└── frontend/             ← React + Vite (deploy on Vercel)
    ├── src/
    │   ├── App.jsx          Main UI
    │   └── main.jsx
    ├── package.json
    ├── vite.config.js
    └── vercel.json          Vercel deployment config
```

---

## 🚀 Deployment Guide

### Step 1 — Deploy Backend on Render

1. Push the `backend/` folder to a GitHub repo
2. Go to [render.com](https://render.com) → **New Web Service**
3. Connect your GitHub repo
4. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free
5. Deploy — your API will be at `https://your-app.onrender.com`
6. Test: visit `https://your-app.onrender.com/api/sectors/india`

### Step 2 — Deploy Frontend on Vercel

1. Push the `frontend/` folder to a GitHub repo (can be same repo)
2. Go to [vercel.com](https://vercel.com) → **New Project**
3. Import your repo, set **Root Directory** to `frontend/`
4. Add environment variable:
   - `VITE_API_URL` = `https://your-app.onrender.com`
5. Deploy — your app is live!

---

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/regions` | List all supported regions |
| `GET /api/sectors/{region}` | Full scored sector list (india/us/japan) |
| `GET /api/top-picks/{region}` | Only BUY signals |
| `GET /health` | Health check |

### Example Response
```json
{
  "region": "india",
  "label": "India",
  "sectors": [
    {
      "id": "coal",
      "name": "Coal & Mining",
      "score": 74.2,
      "signal": "BUY",
      "pe_ratio": 6.8,
      "pct_from_52w_high": -31.4,
      "sentiment_score": 61.3,
      "macro_score": 72.0,
      "price_trend": [42, 38, 35, 33, 31, ...],
      "sample_headlines": ["Coal India Q3 profit jumps...", ...]
    }
  ],
  "generated_at": "2026-03-09T17:00:00Z"
}
```

---

## Local Development

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
# API runs at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Frontend
```bash
cd frontend
cp .env.example .env
# Edit .env: VITE_API_URL=http://localhost:8000
npm install
npm run dev
# App runs at http://localhost:5173
```

---

## Adding More Regions

Edit `backend/app/sectors_config.py` — add a new key to `SECTORS_CONFIG` with:
- `label`, `currency`, `index_ticker`
- `sectors[]` with `id`, `name`, `tickers[]`, `news_keywords[]`, `macro_score_rule`

---

## Tech Stack
- **Backend:** Python, FastAPI, yfinance, feedparser, VADER, cachetools
- **Frontend:** React 18, Vite, vanilla CSS-in-JS
- **Deployment:** Render (backend) + Vercel (frontend)

---

*Not financial advice. For educational/research purposes only.*

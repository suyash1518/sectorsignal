# app/main.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import logging

from .scorer import score_region
from .sectors_config import SECTORS_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SectorSignal API",
    description="Regional stock sector intelligence — live scoring via Yahoo Finance + NLP",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this to your Vercel URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "name": "SectorSignal API",
        "version": "1.0.0",
        "regions": list(SECTORS_CONFIG.keys()),
        "docs": "/docs",
    }


@app.get("/api/regions")
def get_regions():
    """List all supported regions."""
    return {
        "regions": [
            {"id": k, "label": v["label"], "currency": v["currency"], "index": v["index_ticker"]}
            for k, v in SECTORS_CONFIG.items()
        ]
    }


@app.get("/api/sectors/{region}")
def get_sectors(region: str):
    """
    Get scored sectors for a region.
    Scores are cached for 30 minutes.
    Regions: india | us | japan
    """
    if region not in SECTORS_CONFIG:
        raise HTTPException(
            status_code=404,
            detail=f"Region '{region}' not found. Available: {list(SECTORS_CONFIG.keys())}"
        )

    try:
        data = score_region(region)
        return data
    except Exception as e:
        logger.error(f"Scoring error for {region}: {e}")
        raise HTTPException(status_code=500, detail=f"Scoring failed: {str(e)}")


@app.get("/api/top-picks/{region}")
def get_top_picks(region: str, limit: int = 3):
    """Returns only BUY-signal sectors, sorted by score."""
    if region not in SECTORS_CONFIG:
        raise HTTPException(status_code=404, detail=f"Region '{region}' not found.")

    data = score_region(region)
    buys = [s for s in data["sectors"] if s["signal"] == "BUY"][:limit]
    return {
        "region": region,
        "label": data["label"],
        "top_picks": buys,
        "generated_at": data["generated_at"],
    }


@app.get("/health")
def health():
    return {"status": "ok"}

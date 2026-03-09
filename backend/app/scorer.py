# app/scorer.py
import yfinance as yf
import feedparser
import numpy as np
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from cachetools import TTLCache, cached
from datetime import datetime
import logging

from .sectors_config import SECTORS_CONFIG, MACRO_RULES

logger = logging.getLogger(__name__)

# Cache results for 30 minutes to avoid hammering APIs
_cache = TTLCache(maxsize=50, ttl=1800)

vader = SentimentIntensityAnalyzer()

YAHOO_FINANCE_RSS = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
YAHOO_NEWS_SEARCH = "https://news.yahoo.com/rss/search?p={query}"


# ─────────────────────────────────────────────
# 1. PRICE / VALUATION DATA  (yfinance)
# ─────────────────────────────────────────────

def fetch_price_data(tickers: list[str]) -> dict:
    pe_ratios, pct_froms, trends = [], [], []

    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            
            # Use history for price trend (more reliable than info)
            hist = t.history(period="1y", interval="1mo")
            if not hist.empty:
                closes = hist["Close"].dropna().tolist()[-12:]
                if len(closes) >= 2:
                    trends.append(closes)
                    # Calculate pct from 52w high from history
                    high52 = max(closes)
                    current = closes[-1]
                    pct_from = round(((current - high52) / high52) * 100, 1)
                    pct_froms.append(pct_from)

            # Try info for PE
            info = t.info
            pe = info.get("trailingPE") or info.get("forwardPE")
            if pe and 0 < pe < 200:
                pe_ratios.append(pe)

        except Exception as e:
            logger.warning(f"yfinance error for {ticker}: {e}")

    def normalize_trend(series):
        mn, mx = min(series), max(series)
        if mx == mn:
            return [50] * len(series)
        return [round((v - mn) / (mx - mn) * 100, 1) for v in series]

    avg_trend = None
    if trends:
        max_len = max(len(t) for t in trends)
        padded = [t + [t[-1]] * (max_len - len(t)) for t in trends]
        avg_trend = [round(float(np.mean([row[i] for row in padded])), 1) for i in range(max_len)]
        avg_trend = normalize_trend(avg_trend)

    return {
        "pe_ratio": round(float(np.mean(pe_ratios)), 1) if pe_ratios else None,
        "pct_from_52w_high": round(float(np.mean(pct_froms)), 1) if pct_froms else None,
        "price_trend": avg_trend or [50] * 12,
    }


# ─────────────────────────────────────────────
# 2. NEWS SENTIMENT  (Yahoo RSS + VADER)
# ─────────────────────────────────────────────

def fetch_sentiment(tickers: list[str], keywords: list[str]) -> dict:
    """
    Pulls RSS headlines from Yahoo Finance for each ticker,
    runs VADER sentiment, returns compound score 0-100.
    Also fetches Yahoo News search for keywords.
    """
    headlines = []

    # Per-ticker Yahoo Finance RSS
    for ticker in tickers[:2]:  # limit to 2 tickers to keep it fast
        try:
            url = YAHOO_FINANCE_RSS.format(ticker=ticker)
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                headlines.append(entry.get("title", "") + " " + entry.get("summary", ""))
        except Exception as e:
            logger.warning(f"RSS error for {ticker}: {e}")

    # Keyword news search
    for kw in keywords[:2]:
        try:
            url = YAHOO_NEWS_SEARCH.format(query=kw.replace(" ", "+"))
            feed = feedparser.parse(url)
            for entry in feed.entries[:8]:
                headlines.append(entry.get("title", "") + " " + entry.get("summary", ""))
        except Exception as e:
            logger.warning(f"News search error for {kw}: {e}")

    if not headlines:
        return {"sentiment_score": 50, "headline_count": 0, "sample_headlines": []}

    scores = []
    for h in headlines:
        vs = vader.polarity_scores(h)
        scores.append(vs["compound"])  # -1 to +1

    avg_compound = float(np.mean(scores))
    # Convert -1..+1 → 0..100
    sentiment_0_100 = round((avg_compound + 1) / 2 * 100, 1)

    sample = [h[:120] for h in headlines[:3]]

    return {
        "sentiment_score": sentiment_0_100,
        "headline_count": len(headlines),
        "sample_headlines": sample,
    }


# ─────────────────────────────────────────────
# 3. MACRO SCORE  (keyword news search)
# ─────────────────────────────────────────────

def fetch_macro_score(macro_rule: str, region: str) -> float:
    """
    Searches Yahoo News for macro-relevant keywords.
    Returns 0-100 score based on positive news density.
    """
    if macro_rule == "neutral":
        return 55.0  # neutral baseline

    rule = MACRO_RULES.get(macro_rule, {})
    keywords = rule.get("keywords", [])

    if not keywords:
        return 50.0

    all_scores = []
    for kw in keywords[:3]:
        try:
            url = YAHOO_NEWS_SEARCH.format(query=kw.replace(" ", "+"))
            feed = feedparser.parse(url)
            for entry in feed.entries[:6]:
                text = entry.get("title", "") + " " + entry.get("summary", "")
                vs = vader.polarity_scores(text)
                all_scores.append(vs["compound"])
        except Exception as e:
            logger.warning(f"Macro news error: {e}")

    if not all_scores:
        return 50.0

    avg = float(np.mean(all_scores))
    return round((avg + 1) / 2 * 100, 1)


# ─────────────────────────────────────────────
# 4. COMPOSITE SCORE
# ─────────────────────────────────────────────

def compute_composite(
    pct_from_52w: float | None,
    pe_ratio: float | None,
    sentiment: float,
    macro: float,
) -> float:
    """
    Weights:
    - Value (P/E + distance from 52W high): 45%
    - Sentiment: 25%
    - Macro: 30%
    """
    # Value score: lower P/E and bigger discount from 52W = better
    value_score = 50.0  # default

    pe_score = 50.0
    if pe_ratio:
        # P/E < 10 = great (90), P/E > 35 = poor (10)
        pe_score = max(10, min(90, 90 - ((pe_ratio - 5) / 30) * 80))

    discount_score = 50.0
    if pct_from_52w is not None:
        # -40% from high = 90 (deep discount), at 52W high = 20
        discount_score = max(10, min(90, 20 + abs(min(pct_from_52w, 0)) * 1.75))

    value_score = (pe_score * 0.5 + discount_score * 0.5)

    composite = (
        value_score * 0.45 +
        sentiment * 0.25 +
        macro * 0.30
    )
    return round(min(99, max(1, composite)), 1)


def signal_from_score(score: float) -> str:
    if score >= 68:
        return "BUY"
    elif score >= 50:
        return "WATCH"
    else:
        return "AVOID"


# ─────────────────────────────────────────────
# 5. MAIN ENTRY POINT
# ─────────────────────────────────────────────

def score_region(region: str) -> dict:
    cache_key = f"{region}_{datetime.utcnow().strftime('%Y%m%d%H')}"  # hourly cache key
    if cache_key in _cache:
        return _cache[cache_key]

    config = SECTORS_CONFIG.get(region)
    if not config:
        raise ValueError(f"Unknown region: {region}")

    results = []
    for sector in config["sectors"]:
        logger.info(f"Scoring {region}/{sector['id']}...")

        # Fetch data
        price_data = fetch_price_data(sector["tickers"])
        sentiment_data = fetch_sentiment(sector["tickers"], sector["news_keywords"])
        macro = fetch_macro_score(sector["macro_score_rule"], region)

        score = compute_composite(
            pct_from_52w=price_data["pct_from_52w_high"],
            pe_ratio=price_data["pe_ratio"],
            sentiment=sentiment_data["sentiment_score"],
            macro=macro,
        )

        results.append({
            "id": sector["id"],
            "name": sector["name"],
            "tickers": sector["tickers"],
            "score": score,
            "signal": signal_from_score(score),
            "pe_ratio": price_data["pe_ratio"],
            "pct_from_52w_high": price_data["pct_from_52w_high"],
            "sentiment_score": round(sentiment_data["sentiment_score"], 1),
            "macro_score": round(macro, 1),
            "price_trend": price_data["price_trend"],
            "sample_headlines": sentiment_data["sample_headlines"],
            "headline_count": sentiment_data["headline_count"],
            "macro_rule": sector["macro_score_rule"],
            "macro_description": MACRO_RULES.get(sector["macro_score_rule"], {}).get("description", ""),
        })

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)

    output = {
        "region": region,
        "label": config["label"],
        "currency": config["currency"],
        "index_ticker": config["index_ticker"],
        "sectors": results,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    _cache[cache_key] = output
    return output

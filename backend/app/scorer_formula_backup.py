# app/scorer.py  (ML version)
# Replaces the formula-based scorer with real XGBoost predictions.

import yfinance as yf
import feedparser
import numpy as np
import pandas as pd
import pickle
import os
import requests
import logging
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from cachetools import TTLCache
from datetime import datetime

from .sectors_config import SECTORS_CONFIG, MACRO_RULES

logger = logging.getLogger(__name__)

_cache = TTLCache(maxsize=50, ttl=1800)
vader = SentimentIntensityAnalyzer()

YAHOO_FINANCE_RSS  = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
YAHOO_NEWS_SEARCH  = "https://news.yahoo.com/rss/search?p={query}"
YAHOO_CHART_API    = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1mo&range=1y"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# ── Load ML model ─────────────────────────────────────────
MODEL_PATH = os.path.join(os.path.dirname(__file__), "sector_model.pkl")
_model_bundle = None

def load_model():
    global _model_bundle
    if _model_bundle is None:
        if os.path.exists(MODEL_PATH):
            with open(MODEL_PATH, "rb") as f:
                _model_bundle = pickle.load(f)
            logger.info(f"✅ ML model loaded: {_model_bundle['model_name']} "
                        f"(accuracy={_model_bundle['accuracy']:.2f})")
        else:
            logger.warning("⚠ No model file found — falling back to formula scoring")
    return _model_bundle


# ── Price data ────────────────────────────────────────────

def fetch_price_data(tickers: list) -> dict:
    pe_ratios, pct_froms, trends = [], [], []
    mom_1m_list, mom_3m_list, mom_6m_list, vol_list, mr_list = [], [], [], [], []

    is_us = not any(t.endswith((".NS", ".T")) for t in tickers)
    alpha_key = os.getenv("ALPHA_VANTAGE_KEY", "demo")

    for ticker in tickers[:2]:
        try:
            if is_us and alpha_key != "demo":
                url = (f"https://www.alphavantage.co/query"
                       f"?function=TIME_SERIES_MONTHLY_ADJUSTED"
                       f"&symbol={ticker}&apikey={alpha_key}")
                r = requests.get(url, timeout=15)
                data = r.json()
                monthly = data.get("Monthly Adjusted Time Series", {})
                if monthly:
                    sorted_dates = sorted(monthly.keys())[-15:]
                    closes = [float(monthly[d]["5. adjusted close"]) for d in sorted_dates]
                else:
                    closes = []

                # PE from overview
                ov = requests.get(
                    f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={alpha_key}",
                    timeout=15).json()
                pe = ov.get("TrailingPE")
                if pe:
                    try:
                        pe_f = float(pe)
                        if 0 < pe_f < 200:
                            pe_ratios.append(pe_f)
                    except:
                        pass
            else:
                # Yahoo Finance chart API for NSE / TSE
                r = requests.get(YAHOO_CHART_API.format(ticker=ticker),
                                  headers=HEADERS, timeout=15)
                data = r.json()
                result = data.get("chart", {}).get("result", [])
                if not result:
                    continue
                raw = result[0]["indicators"]["quote"][0]["close"]
                closes = [c for c in raw if c is not None]

            if len(closes) < 4:
                continue

            closes = closes[-15:]  # keep up to 15 months
            trends.append(closes[-12:])

            current = closes[-1]
            high52  = max(closes[-12:]) if len(closes) >= 12 else max(closes)
            pct_from = ((current - high52) / high52) * 100
            pct_froms.append(pct_from)

            # Momentum features
            if len(closes) >= 2:
                mom_1m_list.append(((closes[-1] - closes[-2]) / closes[-2]) * 100)
            if len(closes) >= 4:
                mom_3m_list.append(((closes[-1] - closes[-4]) / closes[-4]) * 100)
            if len(closes) >= 7:
                mom_6m_list.append(((closes[-1] - closes[-7]) / closes[-7]) * 100)

            # Volatility
            if len(closes) >= 6:
                rets = pd.Series(closes).pct_change().dropna()
                vol_list.append(rets.iloc[-6:].std() * 100)

            # Mean reversion
            if len(closes) >= 6:
                ma6 = np.mean(closes[-6:])
                mr_list.append(((current - ma6) / ma6) * 100)

        except Exception as e:
            logger.warning(f"Price fetch error for {ticker}: {e}")

    def normalize(series):
        mn, mx = min(series), max(series)
        if mx == mn:
            return [50] * len(series)
        return [round((v - mn) / (mx - mn) * 100, 1) for v in series]

    avg_trend = None
    if trends:
        max_len = max(len(t) for t in trends)
        padded  = [t + [t[-1]] * (max_len - len(t)) for t in trends]
        avg_raw = [float(np.mean([row[i] for row in padded])) for i in range(max_len)]
        avg_trend = normalize(avg_raw)

    def avg(lst): return round(float(np.mean(lst)), 2) if lst else None

    return {
        "pe_ratio":          avg(pe_ratios),
        "pct_from_52w_high": avg(pct_froms),
        "momentum_1m":       avg(mom_1m_list),
        "momentum_3m":       avg(mom_3m_list),
        "momentum_6m":       avg(mom_6m_list),
        "volatility":        avg(vol_list),
        "mean_reversion":    avg(mr_list),
        "price_trend":       avg_trend or [50] * 12,
    }


# ── Sentiment ─────────────────────────────────────────────

def fetch_sentiment(tickers: list, keywords: list) -> dict:
    headlines = []
    for ticker in tickers[:2]:
        try:
            feed = feedparser.parse(YAHOO_FINANCE_RSS.format(ticker=ticker))
            for e in feed.entries[:10]:
                headlines.append(e.get("title", "") + " " + e.get("summary", ""))
        except Exception as e:
            logger.warning(f"RSS error {ticker}: {e}")

    for kw in keywords[:2]:
        try:
            feed = feedparser.parse(YAHOO_NEWS_SEARCH.format(query=kw.replace(" ", "+")))
            for e in feed.entries[:8]:
                headlines.append(e.get("title", "") + " " + e.get("summary", ""))
        except Exception as e:
            logger.warning(f"News error {kw}: {e}")

    if not headlines:
        return {"sentiment_score": 50.0, "headline_count": 0, "sample_headlines": []}

    scores = [vader.polarity_scores(h)["compound"] for h in headlines]
    avg_compound = float(np.mean(scores))
    sentiment_0_100 = round((avg_compound + 1) / 2 * 100, 1)

    return {
        "sentiment_score":   sentiment_0_100,
        "headline_count":    len(headlines),
        "sample_headlines":  [h[:120] for h in headlines[:3]],
    }


# ── Macro ─────────────────────────────────────────────────

def fetch_macro_score(macro_rule: str, region: str) -> float:
    if macro_rule == "neutral":
        return 55.0
    rule     = MACRO_RULES.get(macro_rule, {})
    keywords = rule.get("keywords", [])
    if not keywords:
        return 50.0
    all_scores = []
    for kw in keywords[:3]:
        try:
            feed = feedparser.parse(YAHOO_NEWS_SEARCH.format(query=kw.replace(" ", "+")))
            for e in feed.entries[:6]:
                text = e.get("title", "") + " " + e.get("summary", "")
                all_scores.append(vader.polarity_scores(text)["compound"])
        except:
            pass
    if not all_scores:
        return 50.0
    return round((float(np.mean(all_scores)) + 1) / 2 * 100, 1)


# ── ML prediction ─────────────────────────────────────────

def predict_with_model(features: dict, sentiment: float, macro: float) -> dict:
    """
    Use the trained XGBoost model to predict BUY probability.
    Falls back to formula if model not loaded.
    """
    bundle = load_model()

    feature_vector = [
        features.get("pct_from_52w_high") or 0,
        features.get("momentum_1m")       or 0,
        features.get("momentum_3m")       or 0,
        features.get("momentum_6m")       or 0,
        features.get("volatility")        or 0,
        features.get("mean_reversion")    or 0,
    ]

    if bundle is not None:
        model   = bundle["model"]
        scaler  = bundle["scaler"]
        buy_thr = bundle.get("buy_threshold",   0.55)
        wat_thr = bundle.get("watch_threshold", 0.40)

        X = np.array(feature_vector).reshape(1, -1)
        X_scaled = scaler.transform(X)
        buy_prob = float(model.predict_proba(X_scaled)[0][1])

        # Blend model probability with live sentiment + macro
        # (model was trained on price features only;
        #  sentiment/macro are live signals not in training data)
        blended_score = (buy_prob * 100 * 0.55) + (sentiment * 0.25) + (macro * 0.20)
        blended_score = round(min(99, max(1, blended_score)), 1)

        if buy_prob >= buy_thr:
            signal = "BUY"
        elif buy_prob >= wat_thr:
            signal = "WATCH"
        else:
            signal = "AVOID"

        return {
            "score":    blended_score,
            "signal":   signal,
            "buy_prob": round(buy_prob, 3),
            "model_used": bundle["model_name"],
        }

    else:
        # Fallback formula (no model file)
        pct   = features.get("pct_from_52w_high") or 0
        mom3  = features.get("momentum_3m")       or 0
        disc  = max(10, min(90, 20 + abs(min(pct, 0)) * 1.75))
        mom_s = max(10, min(90, 50 + mom3 * 1.5))
        score = disc * 0.40 + mom_s * 0.10 + sentiment * 0.25 + macro * 0.25
        score = round(min(99, max(1, score)), 1)
        signal = "BUY" if score >= 68 else ("WATCH" if score >= 50 else "AVOID")
        return {"score": score, "signal": signal, "buy_prob": None, "model_used": "formula"}


# ── Main entry point ──────────────────────────────────────

def score_region(region: str) -> dict:
    cache_key = f"{region}_{datetime.utcnow().strftime('%Y%m%d%H')}"
    if cache_key in _cache:
        return _cache[cache_key]

    config = SECTORS_CONFIG.get(region)
    if not config:
        raise ValueError(f"Unknown region: {region}")

    # Eagerly load model
    load_model()

    results = []
    for sector in config["sectors"]:
        logger.info(f"Scoring {region}/{sector['id']}...")

        price_data     = fetch_price_data(sector["tickers"])
        sentiment_data = fetch_sentiment(sector["tickers"], sector["news_keywords"])
        macro          = fetch_macro_score(sector["macro_score_rule"], region)
        prediction     = predict_with_model(price_data, sentiment_data["sentiment_score"], macro)

        results.append({
            "id":                sector["id"],
            "name":              sector["name"],
            "tickers":           sector["tickers"],
            "score":             prediction["score"],
            "signal":            prediction["signal"],
            "buy_probability":   prediction["buy_prob"],
            "model_used":        prediction["model_used"],
            "pe_ratio":          price_data["pe_ratio"],
            "pct_from_52w_high": price_data["pct_from_52w_high"],
            "momentum_1m":       price_data["momentum_1m"],
            "momentum_3m":       price_data["momentum_3m"],
            "sentiment_score":   round(sentiment_data["sentiment_score"], 1),
            "macro_score":       round(macro, 1),
            "price_trend":       price_data["price_trend"],
            "sample_headlines":  sentiment_data["sample_headlines"],
            "headline_count":    sentiment_data["headline_count"],
            "macro_rule":        sector["macro_score_rule"],
            "macro_description": MACRO_RULES.get(sector["macro_score_rule"], {}).get("description", ""),
        })

    results.sort(key=lambda x: x["score"], reverse=True)

    output = {
        "region":       region,
        "label":        config["label"],
        "currency":     config["currency"],
        "index_ticker": config["index_ticker"],
        "sectors":      results,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    _cache[cache_key] = output
    return output

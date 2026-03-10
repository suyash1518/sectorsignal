# model/1_collect_data.py  (fixed — uses Yahoo chart API directly)

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import warnings
warnings.filterwarnings("ignore")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

SECTORS = {
    "india_it":      {"tickers": ["TCS.NS", "INFY.NS", "WIPRO.NS"],         "region": "india"},
    "india_oil":     {"tickers": ["RELIANCE.NS", "ONGC.NS", "BPCL.NS"],     "region": "india"},
    "india_pharma":  {"tickers": ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS"],"region": "india"},
    "india_infra":   {"tickers": ["LT.NS", "NTPC.NS", "POWERGRID.NS"],      "region": "india"},
    "india_agri":    {"tickers": ["ITC.NS", "DABUR.NS", "MARICO.NS"],       "region": "india"},
    "india_coal":    {"tickers": ["COALINDIA.NS", "NMDC.NS"],               "region": "india"},
    "us_energy":     {"tickers": ["XLE", "CVX", "XOM"],                     "region": "us"},
    "us_financials": {"tickers": ["XLF", "JPM", "BAC"],                     "region": "us"},
    "us_tech":       {"tickers": ["QQQ", "AAPL", "MSFT"],                   "region": "us"},
    "us_health":     {"tickers": ["XLV", "JNJ", "UNH"],                     "region": "us"},
    "us_industrial": {"tickers": ["XLI", "CAT", "DE"],                      "region": "us"},
    "us_consumer":   {"tickers": ["XLP", "PG", "KO"],                       "region": "us"},
    "japan_auto":    {"tickers": ["7203.T", "7267.T"],                      "region": "japan"},
    "japan_semi":    {"tickers": ["8035.T", "6857.T"],                      "region": "japan"},
    "japan_bank":    {"tickers": ["8306.T", "8316.T"],                      "region": "japan"},
}

BENCHMARKS = {
    "india": "^NSEI",
    "us":    "^GSPC",
    "japan": "^N225",
}

def fetch_monthly_prices(ticker: str) -> pd.Series:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1mo&range=3y"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        data = r.json()
        result = data.get("chart", {}).get("result", [])
        if not result:
            url2 = url.replace("query1", "query2")
            r = requests.get(url2, headers=HEADERS, timeout=20)
            data = r.json()
            result = data.get("chart", {}).get("result", [])
        if not result:
            return pd.Series(dtype=float)
        timestamps = result[0].get("timestamp", [])
        closes     = result[0]["indicators"]["quote"][0].get("close", [])
        if not timestamps or not closes:
            return pd.Series(dtype=float)
        dates  = pd.to_datetime(timestamps, unit="s").to_period("M").to_timestamp()
        series = pd.Series(closes, index=dates).dropna()
        return series
    except Exception as e:
        print(f"    warning {ticker}: {e}")
        return pd.Series(dtype=float)

def avg_series(tickers: list) -> pd.Series:
    series_list = []
    for t in tickers:
        s = fetch_monthly_prices(t)
        time.sleep(0.4)
        if len(s) > 6:
            s_norm = s / s.iloc[0] * 100
            series_list.append(s_norm)
    if not series_list:
        return pd.Series(dtype=float)
    df = pd.concat(series_list, axis=1)
    return df.mean(axis=1)

def compute_features(prices: pd.Series, i: int) -> dict:
    if i < 3:
        return None
    w = prices.iloc[:i + 1]
    current = w.iloc[-1]
    last_12 = w.iloc[-12:] if len(w) >= 12 else w
    high_52w     = last_12.max()
    pct_from_52w = ((current - high_52w) / high_52w) * 100
    mom_1m = ((current - w.iloc[-2]) / w.iloc[-2]) * 100 if len(w) >= 2 else 0
    mom_3m = ((current - w.iloc[-4]) / w.iloc[-4]) * 100 if len(w) >= 4 else 0
    mom_6m = ((current - w.iloc[-7]) / w.iloc[-7]) * 100 if len(w) >= 7 else 0
    if len(w) >= 6:
        rets = w.pct_change().dropna()
        volatility = rets.iloc[-6:].std() * 100
        ma6 = w.iloc[-6:].mean()
        mean_rev = ((current - ma6) / ma6) * 100
    else:
        volatility = 0
        mean_rev = 0
    return {
        "pct_from_52w_high": round(pct_from_52w, 2),
        "momentum_1m":       round(mom_1m, 2),
        "momentum_3m":       round(mom_3m, 2),
        "momentum_6m":       round(mom_6m, 2),
        "volatility":        round(volatility, 2),
        "mean_reversion":    round(mean_rev, 2),
    }

def compute_label(sector: pd.Series, bench: pd.Series, i: int, fwd: int = 3):
    if i + fwd >= len(sector) or i + fwd >= len(bench):
        return None
    s_ret = (sector.iloc[i + fwd] - sector.iloc[i]) / sector.iloc[i] * 100
    b_ret = (bench.iloc[i + fwd]  - bench.iloc[i])  / bench.iloc[i]  * 100
    return 1 if (s_ret - b_ret) >= 5.0 else 0

def main():
    print("=" * 60)
    print("SectorSignal — Training Data Collection")
    print("=" * 60)

    print("\nFetching benchmark indices...")
    benchmarks = {}
    for region, ticker in BENCHMARKS.items():
        print(f"  {region}: {ticker} ...", end=" ", flush=True)
        s = fetch_monthly_prices(ticker)
        if len(s) > 6:
            benchmarks[region] = s
            print(f"OK ({len(s)} months)")
        else:
            print("FAILED")
        time.sleep(0.5)

    if not benchmarks:
        print("\nERROR: Could not fetch any benchmark data.")
        print("Check your internet connection and try again.")
        return

    rows = []
    for sector_id, info in SECTORS.items():
        region = info["region"]
        if region not in benchmarks:
            continue
        print(f"\nProcessing {sector_id}...")
        sector_prices = avg_series(info["tickers"])
        if len(sector_prices) < 6:
            print(f"  Not enough data, skipping")
            continue
        bench_prices = benchmarks[region]
        common       = sector_prices.index.intersection(bench_prices.index)
        s_aligned    = sector_prices.loc[common].reset_index(drop=True)
        b_aligned    = bench_prices.loc[common].reset_index(drop=True)
        dates        = common
        print(f"  OK: {len(common)} months")
        for i in range(3, len(s_aligned)):
            features = compute_features(s_aligned, i)
            if not features:
                continue
            label = compute_label(s_aligned, b_aligned, i)
            if label is None:
                continue
            rows.append({"sector_id": sector_id, "region": region, "date": dates[i], **features, "label": label})

    if not rows:
        print("\nERROR: No data collected. Wait 5 minutes and try again (rate limit).")
        return

    df = pd.DataFrame(rows)
    print(f"\n{'='*60}")
    print(f"Dataset: {len(df)} rows x {len(df.columns)} columns")
    print(f"BUY  (1): {df['label'].sum()} ({df['label'].mean()*100:.1f}%)")
    print(f"AVOID(0): {(df['label']==0).sum()} ({(1-df['label'].mean())*100:.1f}%)")
    df.to_csv("training_data.csv", index=False)
    print(f"\nSaved to training_data.csv")
    print("Next step: python 2_train_model.py")

if __name__ == "__main__":
    main()
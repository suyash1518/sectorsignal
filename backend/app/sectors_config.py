# app/sectors_config.py
# Maps regions → sectors → tickers + macro weights

SECTORS_CONFIG = {
    "india": {
        "label": "India",
        "currency": "INR",
        "index_ticker": "^NSEI",
        "sectors": [
            {
                "id": "coal",
                "name": "Coal & Mining",
                "tickers": ["COALINDIA.NS", "NMDC.NS", "HINDCOPPER.NS"],
                "news_keywords": ["coal india", "mining india", "NMDC", "coal sector"],
                "macro_score_rule": "high_inflation_energy_demand",  # benefits when energy demand high
            },
            {
                "id": "agriculture",
                "name": "Agriculture & FMCG",
                "tickers": ["ITC.NS", "DABUR.NS", "MARICO.NS", "UBL.NS"],
                "news_keywords": ["agriculture india", "monsoon", "MSP", "farm", "rural india", "FMCG"],
                "macro_score_rule": "rural_recovery",
            },
            {
                "id": "oil_gas",
                "name": "Oil & Gas",
                "tickers": ["RELIANCE.NS", "ONGC.NS", "BPCL.NS"],
                "news_keywords": ["oil gas india", "reliance", "ONGC", "crude oil india"],
                "macro_score_rule": "high_crude_price",
            },
            {
                "id": "infrastructure",
                "name": "Infrastructure",
                "tickers": ["LT.NS", "NTPC.NS", "POWERGRID.NS"],
                "news_keywords": ["infrastructure india", "L&T", "NTPC", "power grid india"],
                "macro_score_rule": "govt_capex",
            },
            {
                "id": "pharma",
                "name": "Pharma & Healthcare",
                "tickers": ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS"],
                "news_keywords": ["pharma india", "sun pharma", "dr reddy", "cipla", "FDA india"],
                "macro_score_rule": "neutral",
            },
            {
                "id": "it",
                "name": "Information Technology",
                "tickers": ["TCS.NS", "INFY.NS", "WIPRO.NS"],
                "news_keywords": ["TCS", "infosys", "wipro", "IT sector india"],
                "macro_score_rule": "usd_strength",
            },
        ],
    },
    "us": {
        "label": "United States",
        "currency": "USD",
        "index_ticker": "^GSPC",
        "sectors": [
            {
                "id": "energy",
                "name": "Energy",
                "tickers": ["XLE", "CVX", "XOM"],
                "news_keywords": ["US energy sector", "crude oil", "XLE", "chevron", "exxon"],
                "macro_score_rule": "high_crude_price",
            },
            {
                "id": "financials",
                "name": "Financials",
                "tickers": ["XLF", "JPM", "BAC"],
                "news_keywords": ["US banks", "financials", "JPMorgan", "fed rate", "XLF"],
                "macro_score_rule": "high_interest_rates",
            },
            {
                "id": "industrials",
                "name": "Industrials",
                "tickers": ["XLI", "CAT", "DE"],
                "news_keywords": ["US industrials", "caterpillar", "deere", "XLI", "manufacturing US"],
                "macro_score_rule": "govt_capex",
            },
            {
                "id": "technology",
                "name": "Technology",
                "tickers": ["QQQ", "AAPL", "MSFT"],
                "news_keywords": ["US tech", "nasdaq", "apple", "microsoft", "AI stocks"],
                "macro_score_rule": "low_interest_rates",
            },
            {
                "id": "healthcare",
                "name": "Healthcare",
                "tickers": ["XLV", "JNJ", "UNH"],
                "news_keywords": ["US healthcare", "pharma US", "JNJ", "UNH", "health insurance"],
                "macro_score_rule": "neutral",
            },
            {
                "id": "consumer",
                "name": "Consumer Staples",
                "tickers": ["XLP", "PG", "KO"],
                "news_keywords": ["consumer staples", "procter gamble", "coca cola", "XLP"],
                "macro_score_rule": "recession_hedge",
            },
        ],
    },
    "japan": {
        "label": "Japan",
        "currency": "JPY",
        "index_ticker": "^N225",
        "sectors": [
            {
                "id": "automotive",
                "name": "Automotive",
                "tickers": ["7203.T", "7267.T", "7201.T"],  # Toyota, Honda, Nissan
                "news_keywords": ["toyota", "honda", "japan auto", "EV japan", "nissan"],
                "macro_score_rule": "weak_yen",
            },
            {
                "id": "semiconductors",
                "name": "Semiconductors",
                "tickers": ["8035.T", "6857.T", "6146.T"],  # Tokyo Electron, Advantest, Disco
                "news_keywords": ["tokyo electron", "japan semiconductor", "chip japan", "TSMC japan"],
                "macro_score_rule": "usd_strength",
            },
            {
                "id": "banking",
                "name": "Banking",
                "tickers": ["8306.T", "8316.T", "8411.T"],  # Mitsubishi UFJ, Sumitomo, Mizuho
                "news_keywords": ["BOJ", "japan bank", "mitsubishi UFJ", "sumitomo", "yen rate"],
                "macro_score_rule": "high_interest_rates",
            },
            {
                "id": "retail",
                "name": "Retail & Consumer",
                "tickers": ["9983.T", "3382.T", "2802.T"],  # Fast Retailing, Seven & i, Ajinomoto
                "news_keywords": ["fast retailing", "uniqlo", "japan retail", "seven eleven japan"],
                "macro_score_rule": "domestic_consumption",
            },
        ],
    },
}

# Macro rules — simplified scoring based on global conditions
# These get fetched from news + macro indicators
MACRO_RULES = {
    "high_inflation_energy_demand": {
        "description": "Benefits when global inflation & energy demand are high",
        "keywords": ["energy demand", "coal demand", "inflation", "power shortage"],
    },
    "rural_recovery": {
        "description": "Benefits from good monsoon, MSP hikes, rural spending",
        "keywords": ["monsoon", "MSP", "rural", "farm income", "kharif", "rabi"],
    },
    "high_crude_price": {
        "description": "Benefits when crude oil prices are elevated",
        "keywords": ["crude oil price", "OPEC", "oil demand", "Brent crude"],
    },
    "govt_capex": {
        "description": "Benefits from government capital expenditure",
        "keywords": ["capex", "infrastructure spending", "budget", "government spending"],
    },
    "high_interest_rates": {
        "description": "Benefits from high interest rate environment",
        "keywords": ["rate hike", "fed rate", "interest rate", "RBI rate", "BOJ rate"],
    },
    "usd_strength": {
        "description": "Benefits from strong USD (export-oriented)",
        "keywords": ["dollar strength", "USD", "rupee depreciation", "yen weak"],
    },
    "weak_yen": {
        "description": "Benefits when yen is weak (boosts Japanese exports)",
        "keywords": ["weak yen", "yen depreciation", "dollar yen", "USDJPY"],
    },
    "low_interest_rates": {
        "description": "Benefits from low rates (growth stocks)",
        "keywords": ["rate cut", "fed cut", "dovish", "lower rates"],
    },
    "recession_hedge": {
        "description": "Defensive sector, benefits during uncertainty",
        "keywords": ["recession", "slowdown", "safe haven", "defensive stocks"],
    },
    "domestic_consumption": {
        "description": "Benefits from strong domestic demand",
        "keywords": ["domestic demand", "consumer spending", "retail sales"],
    },
    "neutral": {
        "description": "Sector score driven mainly by valuation and sentiment",
        "keywords": [],
    },
}

"""
NSE Smart Dashboard - Configuration
All URLs, constants, and settings in one place.
"""

from datetime import date

# ─── NSE Archive URLs ────────────────────────────────────────────────────────
# Post-July 2024 NSE switched to new UDiFF format.
# CM (equity) bhavcopy with delivery columns - use sec_bhavdata_full style
URL_CM_BHAV     = "https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{ddmmmyyyy}.csv"
# Old CM bhav (pre July 2024) - fallback
URL_CM_BHAV_OLD = "https://nsearchives.nseindia.com/content/historical/EQUITIES/{yyyy}/{mmm}/cm{ddmmmyyyy}bhav.csv.zip"

# MTO delivery file
URL_MTO         = "https://nsearchives.nseindia.com/archives/equities/mto/MTO_{ddmmyyyy}.DAT"

# FO UDiFF bhavcopy (post July 2024 format)
URL_FO_BHAV     = "https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{yyyymmdd}_F_0000.csv.zip"
# Old FO bhav (pre July 2024) - fallback
URL_FO_BHAV_OLD = "https://nsearchives.nseindia.com/content/historical/DERIVATIVES/{yyyy}/{mmm}/fo{ddmmmyyyy}bhav.csv.zip"

# FII/DII - NSE API endpoint (they discontinued the XLS file; use JSON API)
URL_FII_API     = "https://www.nseindia.com/api/fiidiiTradeReact"
# Fallback: participant OI file from NSE clearing
URL_PART_OI     = "https://nsearchives.nseindia.com/content/nsccl/fao_participant_oi_{ddmmyyyy}.csv"
URL_PART_VOL    = "https://nsearchives.nseindia.com/content/nsccl/fao_participant_vol_{ddmmyyyy}.csv"

# ─── NSE Holidays 2026 ───────────────────────────────────────────────────────
NSE_HOLIDAYS_2026 = {
    "2026-01-26",  # Republic Day
    "2026-02-18",  # Maha Shivaratri
    "2026-03-20",  # Holi
    "2026-04-02",  # Ram Navami (tentative)
    "2026-04-03",  # Good Friday
    "2026-04-14",  # Dr. Ambedkar Jayanti / Baisakhi
    "2026-05-01",  # Maharashtra Day
    "2026-08-15",  # Independence Day
    "2026-10-02",  # Gandhi Jayanti
    "2026-10-22",  # Dussehra (tentative)
    "2026-11-11",  # Diwali Laxmi Puja (tentative)
    "2026-11-12",  # Diwali Balipratipada (tentative)
    "2026-11-25",  # Guru Nanak Jayanti (tentative)
    "2026-12-25",  # Christmas
}

# ─── NIFTY 50 Stocks with Sectors ────────────────────────────────────────────
NIFTY50 = {
    "ADANIENT":    "Conglomerate",
    "ADANIPORTS":  "Infrastructure",
    "APOLLOHOSP":  "Healthcare",
    "ASIANPAINT":  "Consumer",
    "AXISBANK":    "Banking",
    "BAJAJ-AUTO":  "Auto",
    "BAJFINANCE":  "NBFC",
    "BAJAJFINSV":  "NBFC",
    "BPCL":        "Energy",
    "BHARTIARTL":  "Telecom",
    "BRITANNIA":   "FMCG",
    "CIPLA":       "Pharma",
    "COALINDIA":   "Metals",
    "DIVISLAB":    "Pharma",
    "DRREDDY":     "Pharma",
    "EICHERMOT":   "Auto",
    "GRASIM":      "Cement",
    "HCLTECH":     "IT",
    "HDFCBANK":    "Banking",
    "HDFCLIFE":    "Insurance",
    "HEROMOTOCO":  "Auto",
    "HINDALCO":    "Metals",
    "HINDUNILVR":  "FMCG",
    "ICICIBANK":   "Banking",
    "ITC":         "FMCG",
    "INDUSINDBK":  "Banking",
    "INFY":        "IT",
    "JSWSTEEL":    "Metals",
    "KOTAKBANK":   "Banking",
    "LT":          "Infrastructure",
    "M&M":         "Auto",
    "MARUTI":      "Auto",
    "NTPC":        "Energy",
    "NESTLEIND":   "FMCG",
    "ONGC":        "Energy",
    "POWERGRID":   "Energy",
    "RELIANCE":    "Energy",
    "SBILIFE":     "Insurance",
    "SBIN":        "Banking",
    "SUNPHARMA":   "Pharma",
    "TCS":         "IT",
    "TATACONSUM":  "FMCG",
    "TATAMOTORS":  "Auto",
    "TATASTEEL":   "Metals",
    "TECHM":       "IT",
    "TITAN":       "Consumer",
    "TRENT":       "Consumer",
    "ULTRACEMCO":  "Cement",
    "WIPRO":       "IT",
    "SHRIRAMFIN":  "NBFC",
}

# ─── Signal weights (must sum to 1.0) ────────────────────────────────────────
SIGNAL_WEIGHTS = {
    "price_trend":   0.20,
    "delivery":      0.20,
    "oi":            0.20,
    "volume":        0.10,
    "fii":           0.10,
    "sector":        0.10,
    "momentum":      0.05,
    "pcr":           0.05,
}

# ─── Signal thresholds ───────────────────────────────────────────────────────
DEL_HIGH_THRESHOLD  = 50.0   # delivery% considered high
DEL_LOW_THRESHOLD   = 30.0   # delivery% considered low
VOL_EXPANSION_RATIO = 1.5    # volume > 1.5x avg = expansion
OI_CHG_BULL_PCT     = 5.0    # OI change% for long buildup
OI_CHG_BEAR_PCT     = -5.0   # OI change% for short buildup
FII_BULL_THRESHOLD  = 500.0  # FII net buy ₹Cr = bullish
FII_BEAR_THRESHOLD  = -500.0 # FII net sell ₹Cr = bearish

# ─── Output paths ────────────────────────────────────────────────────────────
OUTPUT_EXCEL = "output/NSE_Dashboard.xlsx"
OUTPUT_HTML  = "output/index.html"
DB_PATH      = "history/nse_history.db"

# ─── Request headers (NSE blocks bare Python requests) ───────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection":      "keep-alive",
    "Referer":         "https://www.nseindia.com/",
}

DOWNLOAD_TIMEOUT  = 30   # seconds per request
DOWNLOAD_RETRIES  = 3    # retry count on failure
RETRY_WAIT        = 5    # seconds between retries

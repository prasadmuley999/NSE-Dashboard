"""
OI Parser
Parses FO UDiFF bhavcopy CSV to extract futures OI change per stock.
Handles both new UDiFF format (post July 2024) and old format.
"""

import io
import logging
from datetime import date

import pandas as pd

from config.config import NIFTY50

log = logging.getLogger(__name__)

# ─── UDiFF column names (new format post July 2024) ─────────────────────────
UDIFF_COLS = {
    "TckrSymb":   "symbol",
    "FinInstrmTp": "inst_type",     # FUTSTK, FUTIDX, OPTSTK, OPTIDX
    "XpryDt":     "expiry",
    "OptnTp":     "option_type",    # CE, PE, - (for futures)
    "StrkPric":   "strike",
    "OpnIntrst":  "oi",
    "ChngInOpnIntrst": "oi_chg",
    "TtlTradgVol": "volume",
    "SttlmPric":  "settle_price",
    "ClsPric":    "close",
    "PrvsClsgPric": "prev_close",
}

# ─── Old format column names ─────────────────────────────────────────────────
OLD_COLS = {
    "SYMBOL":       "symbol",
    "INSTRUMENT":   "inst_type",
    "EXPIRY_DT":    "expiry",
    "OPTION_TYP":   "option_type",
    "STRIKE_PR":    "strike",
    "OPEN_INT":     "oi",
    "CHG_IN_OI":    "oi_chg",
    "CONTRACTS":    "volume",
    "SETTLE_PR":    "settle_price",
    "CLOSE":        "close",
    "PREV_CLOSE":   "prev_close",
}


def _detect_format(df: pd.DataFrame) -> str:
    """Detect whether CSV is UDiFF or old format."""
    cols = set(df.columns)
    if "TckrSymb" in cols or "FinInstrmTp" in cols:
        return "udiff"
    if "SYMBOL" in cols and "INSTRUMENT" in cols:
        return "old"
    return "unknown"


def parse_fo_bhav(text: str | None, market_date: date) -> pd.DataFrame:
    """
    Parse FO bhavcopy text. Returns DataFrame with per-stock futures OI data.
    Columns: symbol, date, oi, oi_chg, oi_chg_pct, volume, settle_price
    """
    if not text:
        log.warning("FO Bhav: no data received")
        return pd.DataFrame()

    try:
        df = pd.read_csv(io.StringIO(text))
        fmt = _detect_format(df)
        log.info(f"FO Bhav format detected: {fmt} ({len(df)} rows)")

        if fmt == "udiff":
            col_map = {k: v for k, v in UDIFF_COLS.items() if k in df.columns}
            df.rename(columns=col_map, inplace=True)
            # Filter to stock futures (FUTSTK)
            if "inst_type" in df.columns:
                df = df[df["inst_type"].str.upper().isin(["FUTSTK", "FUTIDX"])].copy()

        elif fmt == "old":
            col_map = {k: v for k, v in OLD_COLS.items() if k in df.columns}
            df.rename(columns=col_map, inplace=True)
            if "inst_type" in df.columns:
                df = df[df["inst_type"].str.upper().isin(["FUTSTK", "FUTIDX"])].copy()

        else:
            log.error(f"FO Bhav: unrecognised format. Columns: {list(df.columns)[:10]}")
            return pd.DataFrame()

        # Normalise numeric columns
        for col in ["oi", "oi_chg", "volume", "settle_price"]:
            if col in df.columns:
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(",", ""), errors="coerce"
                ).fillna(0)

        df["symbol"] = df["symbol"].astype(str).str.strip().str.upper()
        df["date"]   = market_date

        # Aggregate by symbol (sum across expiries for total OI picture)
        agg = df.groupby("symbol").agg(
            oi=("oi", "sum"),
            oi_chg=("oi_chg", "sum"),
            volume=("volume", "sum"),
            settle_price=("settle_price", "last"),
        ).reset_index()

        agg["oi_chg_pct"] = agg.apply(
            lambda r: round((r["oi_chg"] / (r["oi"] - r["oi_chg"])) * 100, 2)
            if (r["oi"] - r["oi_chg"]) != 0 else 0.0,
            axis=1
        )
        agg["date"] = market_date

        # Keep only NIFTY 50 stocks
        agg = agg[agg["symbol"].isin(NIFTY50)].copy()
        log.info(f"FO Bhav: {len(agg)} NIFTY50 futures rows after aggregation")
        return agg.reset_index(drop=True)

    except Exception as e:
        log.error(f"FO Bhav parse error: {e}")
        return pd.DataFrame()


def classify_oi_signal(row: pd.Series) -> str:
    """
    Classify OI buildup signal for a single stock row.
    Requires: chg_pct (price change%), oi_chg_pct (OI change%)
    """
    price_up = row.get("chg_pct", 0) > 0
    oi_up    = row.get("oi_chg_pct", 0) > 0

    if price_up and oi_up:
        return "Long Buildup"
    elif price_up and not oi_up:
        return "Short Covering"
    elif not price_up and oi_up:
        return "Short Buildup"
    else:
        return "Long Unwinding"

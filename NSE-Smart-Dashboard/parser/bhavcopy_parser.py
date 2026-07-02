"""
Bhavcopy & MTO Parser
Parses NSE equity bhavcopy (sec_bhavdata_full format) and MTO delivery DAT file.
"""

import io
import logging
from datetime import date

import pandas as pd

from config.config import NIFTY50

log = logging.getLogger(__name__)


def parse_cm_bhav(text: str, market_date: date) -> pd.DataFrame:
    """
    Parse sec_bhavdata_full CSV.
    Columns: SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE,
             LOW_PRICE, LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY,
             TURNOVER_LACS, NO_OF_TRADES, DELIV_QTY, DELIV_PER
    Returns DataFrame with only EQ series, columns normalised.
    """
    if not text:
        log.error("CM Bhav: no data received")
        return pd.DataFrame()

    try:
        df = pd.read_csv(io.StringIO(text))
        df.columns = [c.strip() for c in df.columns]

        # Keep only EQ series
        df = df[df["SERIES"].str.strip() == "EQ"].copy()

        df.rename(columns={
            "SYMBOL":       "symbol",
            "PREV_CLOSE":   "prev_close",
            "OPEN_PRICE":   "open",
            "HIGH_PRICE":   "high",
            "LOW_PRICE":    "low",
            "CLOSE_PRICE":  "close",
            "TTL_TRD_QNTY": "volume",
            "DELIV_QTY":    "deliv_qty",
            "DELIV_PER":    "deliv_pct",
        }, inplace=True)

        df["symbol"]    = df["symbol"].str.strip()
        df["date"]      = market_date
        df["chg"]       = df["close"] - df["prev_close"]
        df["chg_pct"]   = ((df["chg"] / df["prev_close"]) * 100).round(2)

        keep = ["symbol", "date", "prev_close", "open", "high", "low",
                "close", "chg", "chg_pct", "volume", "deliv_qty", "deliv_pct"]
        df = df[keep].reset_index(drop=True)

        log.info(f"CM Bhav parsed: {len(df)} EQ rows")
        return df

    except Exception as e:
        log.error(f"CM Bhav parse error: {e}")
        return pd.DataFrame()


def parse_mto(text: str, market_date: date) -> pd.DataFrame:
    """
    Parse MTO_DDMMYYYY.DAT file.
    Format (comma-separated):
      20, Sr No, Symbol, Series, Traded Qty, Deliverable Qty, Del%
    Skip header rows (record type != 20).
    Returns DataFrame with symbol, traded_qty, deliv_qty, deliv_pct.
    """
    if not text:
        log.error("MTO: no data received")
        return pd.DataFrame()

    rows = []
    for line in text.splitlines():
        parts = line.split(",")
        if len(parts) < 7:
            continue
        if parts[0].strip() != "20":
            continue
        try:
            rows.append({
                "symbol":     parts[2].strip(),
                "series":     parts[3].strip(),
                "traded_qty": int(parts[4].strip()),
                "deliv_qty":  int(parts[5].strip()),
                "deliv_pct":  float(parts[6].strip()),
                "date":       market_date,
            })
        except (ValueError, IndexError):
            continue

    if not rows:
        log.error("MTO: no record-type-20 rows found")
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    # Keep only EQ series for consistency
    df = df[df["series"] == "EQ"].copy()
    log.info(f"MTO parsed: {len(df)} EQ rows")
    return df


def merge_bhav_mto(bhav: pd.DataFrame, mto: pd.DataFrame) -> pd.DataFrame:
    """
    Merge CM bhavcopy with MTO delivery data.
    MTO is authoritative for deliv_qty / deliv_pct (it includes client-level netting).
    Fallback to bhav delivery columns if MTO is missing a symbol.
    """
    if bhav.empty:
        return pd.DataFrame()

    if mto.empty:
        log.warning("MTO empty — using bhavcopy delivery columns")
        return bhav

    mto_slim = mto[["symbol", "traded_qty", "deliv_qty", "deliv_pct"]].rename(columns={
        "deliv_qty": "deliv_qty_mto",
        "deliv_pct": "deliv_pct_mto",
    })

    merged = bhav.merge(mto_slim, on="symbol", how="left")

    # Prefer MTO delivery values where available
    merged["deliv_qty"] = merged["deliv_qty_mto"].fillna(merged["deliv_qty"])
    merged["deliv_pct"] = merged["deliv_pct_mto"].fillna(merged["deliv_pct"])
    merged.drop(columns=["deliv_qty_mto", "deliv_pct_mto"], inplace=True)

    log.info(f"Merged bhav+MTO: {len(merged)} rows")
    return merged


def filter_nifty50(df: pd.DataFrame) -> pd.DataFrame:
    """Filter merged DataFrame to only NIFTY 50 stocks and add sector column."""
    if df.empty:
        return df
    n50 = df[df["symbol"].isin(NIFTY50)].copy()
    n50["sector"] = n50["symbol"].map(NIFTY50)
    log.info(f"NIFTY 50 rows: {len(n50)}")
    return n50.reset_index(drop=True)

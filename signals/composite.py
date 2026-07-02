"""
Signal Engine
Computes per-stock composite bullish/bearish scores for NIFTY50.
"""

import logging
from datetime import date

import pandas as pd

from config.config import (
    SIGNAL_WEIGHTS, DEL_HIGH_THRESHOLD, DEL_LOW_THRESHOLD,
    VOL_EXPANSION_RATIO, OI_CHG_BULL_PCT, OI_CHG_BEAR_PCT,
    FII_BULL_THRESHOLD, FII_BEAR_THRESHOLD,
)
from parser.oi_parser import classify_oi_signal

log = logging.getLogger(__name__)

# Signal labels by score bucket
SIGNAL_LABELS = [
    (80, "🟢 Strong Bullish",  5, "★★★★★ Strong Buy"),
    (60, "🟩 Weak Bullish",    4, "★★★★ Buy Watch"),
    (40, "⬜ Neutral",          3, "★★★ Neutral"),
    (20, "🟥 Weak Bearish",    2, "★★ Avoid"),
    ( 0, "🔴 Strong Bearish",  1, "★ Strong Avoid"),
]


def _score_delivery(row: pd.Series, hist_df: pd.DataFrame) -> float:
    """Score 0-100 based on delivery% vs today and vs 4-day avg."""
    del_today = row.get("deliv_pct", 0)
    symbol    = row.get("symbol", "")

    if hist_df.empty or "symbol" not in hist_df.columns:
        hist = pd.DataFrame()
    else:
        hist = hist_df[hist_df["symbol"] == symbol].sort_values("date", ascending=False)
    avg4 = hist["deliv_pct"].head(4).mean() if len(hist) >= 2 else del_today

    s = 50.0
    if del_today > DEL_HIGH_THRESHOLD:
        s += 25
    elif del_today < DEL_LOW_THRESHOLD:
        s -= 25

    diff_avg4 = del_today - avg4
    s += min(max(diff_avg4 * 1.5, -25), 25)

    return max(0, min(100, s))


def _score_price(row: pd.Series, hist_df: pd.DataFrame) -> float:
    """Score based on today's close vs prev closes (trend)."""
    symbol   = row.get("symbol", "")
    chg_pct  = row.get("chg_pct", 0)
    close    = row.get("close", 0)

    if hist_df.empty or "symbol" not in hist_df.columns:
        hist = pd.DataFrame()
    else:
        hist = hist_df[hist_df["symbol"] == symbol].sort_values("date", ascending=False)
    closes = hist["close"].head(4).tolist() if not hist.empty else []

    s = 50.0
    # Today's direction
    s += min(max(chg_pct * 5, -20), 20)

    # Trend: close above recent closes
    if closes:
        above = sum(1 for c in closes if close > c)
        s += (above / len(closes)) * 20 - 10

    return max(0, min(100, s))


def _score_oi(row: pd.Series) -> float:
    """Score based on OI change% and signal type."""
    oi_chg_pct = row.get("oi_chg_pct", 0)
    oi_signal  = row.get("oi_signal", "")

    s = 50.0
    if oi_signal == "Long Buildup":
        s += min(abs(oi_chg_pct) * 2, 30)
    elif oi_signal == "Short Covering":
        s += 15
    elif oi_signal == "Short Buildup":
        s -= min(abs(oi_chg_pct) * 2, 30)
    elif oi_signal == "Long Unwinding":
        s -= 15

    return max(0, min(100, s))


def _score_volume(row: pd.Series, hist_df: pd.DataFrame) -> float:
    """Score based on volume vs 5-day average."""
    symbol = row.get("symbol", "")
    vol    = row.get("volume", 0)

    if hist_df.empty or "symbol" not in hist_df.columns:
        hist = pd.DataFrame()
    else:
        hist = hist_df[hist_df["symbol"] == symbol].sort_values("date", ascending=False)
    avg5   = hist["volume"].head(5).mean() if len(hist) >= 2 else vol

    if avg5 == 0:
        return 50.0
    ratio = vol / avg5
    s = 50 + min(max((ratio - 1.0) * 40, -30), 30)
    return max(0, min(100, s))


def _score_fii(fii_net: float) -> float:
    """Score based on FII net buy/sell for the day."""
    if fii_net > FII_BULL_THRESHOLD:
        return min(50 + (fii_net / FII_BULL_THRESHOLD) * 25, 100)
    elif fii_net < FII_BEAR_THRESHOLD:
        return max(50 + (fii_net / abs(FII_BEAR_THRESHOLD)) * 25, 0)
    return 50.0


def _score_sector(symbol: str, sector: str, nifty_df: pd.DataFrame) -> float:
    """Score based on how many sector peers are bullish today."""
    peers = nifty_df[nifty_df["sector"] == sector]
    if len(peers) < 2:
        return 50.0
    bullish_peers = peers[peers["chg_pct"] > 0]
    ratio = len(bullish_peers) / len(peers)
    return ratio * 100


def _score_momentum(row: pd.Series, hist_df: pd.DataFrame) -> float:
    """Score based on 5-day price momentum."""
    symbol = row.get("symbol", "")
    close  = row.get("close", 0)
    if hist_df.empty or "symbol" not in hist_df.columns:
        hist = pd.DataFrame()
    else:
        hist = hist_df[hist_df["symbol"] == symbol].sort_values("date", ascending=False)
    if len(hist) < 5:
        return 50.0
    close_5d_ago = hist["close"].iloc[4]
    if close_5d_ago == 0:
        return 50.0
    mom = ((close - close_5d_ago) / close_5d_ago) * 100
    return max(0, min(100, 50 + mom * 4))


def _score_pcr(pcr: float) -> float:
    """
    Score based on Put-Call Ratio.
    PCR > 1.2 = bullish (more put buying = hedging, market will rise).
    PCR < 0.8 = bearish (more call buying = speculation, market may fall).
    """
    if pcr >= 1.5:
        return 80.0
    elif pcr >= 1.2:
        return 65.0
    elif pcr >= 0.8:
        return 50.0
    elif pcr >= 0.6:
        return 35.0
    else:
        return 20.0


def _label(score: float) -> tuple[str, int, str]:
    for threshold, label, stars, rec in SIGNAL_LABELS:
        if score >= threshold:
            return label, stars, rec
    return "🔴 Strong Bearish", 1, "★ Strong Avoid"


def compute_signals(
    nifty_df: pd.DataFrame,
    oi_df: pd.DataFrame,
    fii_row: pd.Series,
    hist_df: pd.DataFrame,
    pcr: float = 1.0,
    market_date: date = None,
) -> pd.DataFrame:
    """
    Compute composite signal for each NIFTY50 stock.

    Parameters
    ----------
    nifty_df   : today's price+delivery data (NIFTY50 only)
    oi_df      : today's OI data
    fii_row    : Series with fii_net, dii_net
    hist_df    : historical price data from SQLite (used for averages)
    pcr        : put-call ratio for NIFTY options (optional)
    market_date: date of the data
    """
    if nifty_df.empty:
        log.error("No NIFTY50 data to compute signals")
        return pd.DataFrame()

    # Merge OI into nifty_df
    if not oi_df.empty:
        oi_slim = oi_df[["symbol", "oi", "oi_chg", "oi_chg_pct", "settle_price"]].copy()
        df = nifty_df.merge(oi_slim, on="symbol", how="left")
        df["oi_signal"] = df.apply(classify_oi_signal, axis=1)
    else:
        df = nifty_df.copy()
        df["oi"]          = 0.0
        df["oi_chg"]      = 0.0
        df["oi_chg_pct"]  = 0.0
        df["settle_price"]= 0.0
        df["oi_signal"]   = "N/A"

    fii_net = float(fii_row.get("fii_net", 0)) if not fii_row.empty else 0.0

    rows = []
    w = SIGNAL_WEIGHTS

    for _, row in df.iterrows():
        s_del  = _score_delivery(row, hist_df)
        s_pri  = _score_price(row, hist_df)
        s_oi   = _score_oi(row)
        s_vol  = _score_volume(row, hist_df)
        s_fii  = _score_fii(fii_net)
        s_sec  = _score_sector(row["symbol"], row.get("sector", ""), df)
        s_mom  = _score_momentum(row, hist_df)
        s_pcr  = _score_pcr(pcr)

        composite = (
            w["delivery"]    * s_del +
            w["price_trend"] * s_pri +
            w["oi"]          * s_oi  +
            w["volume"]      * s_vol +
            w["fii"]         * s_fii +
            w["sector"]      * s_sec +
            w["momentum"]    * s_mom +
            w["pcr"]         * s_pcr
        )

        label, stars, rec = _label(composite)

        rows.append({
            "date":           str(market_date),
            "symbol":         row["symbol"],
            "sector":         row.get("sector", ""),
            "open":           row.get("open", 0),
            "close":          row.get("close", 0),
            "chg":            row.get("chg", 0),
            "chg_pct":        row.get("chg_pct", 0),
            "prev_close":     row.get("prev_close", 0),
            "volume":         row.get("volume", 0),
            "deliv_pct":      row.get("deliv_pct", 0),
            "deliv_qty":      row.get("deliv_qty", 0),
            "oi":             row.get("oi", 0),
            "oi_chg":         row.get("oi_chg", 0),
            "oi_chg_pct":     row.get("oi_chg_pct", 0),
            "oi_signal":      row.get("oi_signal", "N/A"),
            "score":          round(composite, 1),
            "signal_label":   label,
            "stars":          stars,
            "recommendation": rec,
            # component scores for transparency
            "s_delivery":     round(s_del, 1),
            "s_price":        round(s_pri, 1),
            "s_oi":           round(s_oi, 1),
            "s_volume":       round(s_vol, 1),
            "s_fii":          round(s_fii, 1),
            "s_sector":       round(s_sec, 1),
            "s_momentum":     round(s_mom, 1),
        })

    result = pd.DataFrame(rows).sort_values("score", ascending=False)
    log.info(f"Signals computed for {len(result)} stocks")
    return result.reset_index(drop=True)


def sector_summary(signals_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate signal data by sector."""
    if signals_df.empty:
        return pd.DataFrame()

    def sector_signal(row):
        avg = row["avg_score"]
        if avg >= 70: return "🟢 Strong Bullish"
        elif avg >= 55: return "🟩 Weak Bullish"
        elif avg >= 45: return "⬜ Neutral"
        elif avg >= 30: return "🟥 Weak Bearish"
        else: return "🔴 Strong Bearish"

    agg = signals_df.groupby("sector").agg(
        stocks      =("symbol",    "count"),
        avg_del_pct =("deliv_pct", "mean"),
        avg_chg_pct =("chg_pct",   "mean"),
        avg_oi_chg  =("oi_chg_pct","mean"),
        bullish     =("stars",     lambda x: (x >= 4).sum()),
        bearish     =("stars",     lambda x: (x <= 2).sum()),
        avg_score   =("score",     "mean"),
    ).reset_index()

    agg["avg_del_pct"] = agg["avg_del_pct"].round(2)
    agg["avg_chg_pct"] = agg["avg_chg_pct"].round(2)
    agg["avg_oi_chg"]  = agg["avg_oi_chg"].round(2)
    agg["avg_score"]   = agg["avg_score"].round(1)
    agg["sector_signal"] = agg.apply(sector_signal, axis=1)

    return agg.sort_values("avg_score", ascending=False)

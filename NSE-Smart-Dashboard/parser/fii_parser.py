"""
FII / DII & Participant Parser
Parses FII-DII JSON from NSE API and participant OI/vol CSV files.
"""

import io
import logging
from datetime import date

import pandas as pd

log = logging.getLogger(__name__)


def parse_fii_dii(raw: dict | None, market_date: date) -> pd.DataFrame:
    """
    Convert FII/DII dict (from archive_downloader) to a tidy DataFrame.
    Returns one-row DataFrame with columns:
      date, fii_buy, fii_sell, fii_net, dii_buy, dii_sell, dii_net
    """
    if not raw:
        log.warning("FII/DII: no data — returning zeros")
        raw = {}

    row = {
        "date":     market_date,
        "fii_buy":  raw.get("fii_buy",  0.0),
        "fii_sell": raw.get("fii_sell", 0.0),
        "fii_net":  raw.get("fii_net",  0.0),
        "dii_buy":  raw.get("dii_buy",  0.0),
        "dii_sell": raw.get("dii_sell", 0.0),
        "dii_net":  raw.get("dii_net",  0.0),
    }

    # If API returned net but not individual buy/sell, note it
    if row["fii_buy"] == 0 and row["fii_sell"] == 0 and row["fii_net"] != 0:
        log.warning("FII/DII: only net available, buy/sell missing")

    log.info(
        f"FII: Buy={row['fii_buy']:.2f} Sell={row['fii_sell']:.2f} "
        f"Net={row['fii_net']:.2f} | "
        f"DII: Buy={row['dii_buy']:.2f} Sell={row['dii_sell']:.2f} "
        f"Net={row['dii_net']:.2f}"
    )
    return pd.DataFrame([row])


def parse_participant_oi(text: str | None, market_date: date) -> pd.DataFrame:
    """
    Parse fao_participant_oi_DDMMYYYY.csv.
    NSE columns (typical):
      Client Type, Future Long, Future Short, Option Call Long,
      Option Call Short, Option Put Long, Option Put Short, Total Long, Total Short
    Returns DataFrame with participant OI by client type.
    """
    if not text:
        log.warning("Participant OI: no data")
        return pd.DataFrame()

    try:
        df = pd.read_csv(io.StringIO(text))
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        df["date"] = market_date

        # Standardise client_type column name
        for col in df.columns:
            if "client" in col or "category" in col:
                df.rename(columns={col: "client_type"}, inplace=True)
                break

        if "client_type" in df.columns:
            df["client_type"] = df["client_type"].str.strip()
            # Keep only summary rows (FII, DII, Client, Pro)
            keep = ["fii", "dii", "client", "pro", "fii/fpi"]
            df = df[df["client_type"].str.lower().isin(keep)].copy()

        log.info(f"Participant OI parsed: {len(df)} rows")
        return df

    except Exception as e:
        log.error(f"Participant OI parse error: {e}")
        return pd.DataFrame()


def parse_participant_vol(text: str | None, market_date: date) -> pd.DataFrame:
    """
    Parse fao_participant_vol_DDMMYYYY.csv.
    Same structure as OI file but for traded volume.
    """
    if not text:
        log.warning("Participant Vol: no data")
        return pd.DataFrame()

    try:
        df = pd.read_csv(io.StringIO(text))
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        df["date"] = market_date

        for col in df.columns:
            if "client" in col or "category" in col:
                df.rename(columns={col: "client_type"}, inplace=True)
                break

        if "client_type" in df.columns:
            df["client_type"] = df["client_type"].str.strip()
            keep = ["fii", "dii", "client", "pro", "fii/fpi"]
            df = df[df["client_type"].str.lower().isin(keep)].copy()

        log.info(f"Participant Vol parsed: {len(df)} rows")
        return df

    except Exception as e:
        log.error(f"Participant Vol parse error: {e}")
        return pd.DataFrame()

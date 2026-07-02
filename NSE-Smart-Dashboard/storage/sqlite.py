"""
SQLite Storage
Maintains historical NSE data across runs. Never overwrites existing records.
"""

import logging
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd

from config.config import DB_PATH

log = logging.getLogger(__name__)


def _conn() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    """Create tables if they don't exist."""
    with _conn() as con:
        cur = con.cursor()
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS daily_prices (
            date        TEXT,
            symbol      TEXT,
            open        REAL,
            high        REAL,
            low         REAL,
            close       REAL,
            prev_close  REAL,
            chg         REAL,
            chg_pct     REAL,
            volume      REAL,
            deliv_qty   REAL,
            deliv_pct   REAL,
            sector      TEXT,
            PRIMARY KEY (date, symbol)
        );

        CREATE TABLE IF NOT EXISTS oi_data (
            date        TEXT,
            symbol      TEXT,
            oi          REAL,
            oi_chg      REAL,
            oi_chg_pct  REAL,
            volume      REAL,
            settle_price REAL,
            oi_signal   TEXT,
            PRIMARY KEY (date, symbol)
        );

        CREATE TABLE IF NOT EXISTS fii_dii (
            date      TEXT PRIMARY KEY,
            fii_buy   REAL,
            fii_sell  REAL,
            fii_net   REAL,
            dii_buy   REAL,
            dii_sell  REAL,
            dii_net   REAL
        );

        CREATE TABLE IF NOT EXISTS signals (
            date            TEXT,
            symbol          TEXT,
            sector          TEXT,
            score           REAL,
            signal_label    TEXT,
            stars           INTEGER,
            recommendation  TEXT,
            del_signal      TEXT,
            oi_signal       TEXT,
            price_signal    TEXT,
            PRIMARY KEY (date, symbol)
        );

        CREATE TABLE IF NOT EXISTS run_log (
            run_time    TEXT,
            market_date TEXT,
            status      TEXT,
            message     TEXT
        );
        """)
    log.info("DB initialised")


def upsert_prices(df: pd.DataFrame):
    if df.empty:
        return
    with _conn() as con:
        df.to_sql("daily_prices", con, if_exists="append", index=False,
                  method="ignore")
    log.info(f"Prices stored: {len(df)} rows")


def upsert_oi(df: pd.DataFrame):
    if df.empty:
        return
    with _conn() as con:
        df.to_sql("oi_data", con, if_exists="append", index=False,
                  method="ignore")
    log.info(f"OI stored: {len(df)} rows")


def upsert_fii(df: pd.DataFrame):
    if df.empty:
        return
    with _conn() as con:
        df.to_sql("fii_dii", con, if_exists="append", index=False,
                  method="ignore")
    log.info(f"FII/DII stored: {len(df)} rows")


def upsert_signals(df: pd.DataFrame):
    if df.empty:
        return
    with _conn() as con:
        df.to_sql("signals", con, if_exists="append", index=False,
                  method="ignore")
    log.info(f"Signals stored: {len(df)} rows")


def log_run(market_date: date, status: str, message: str = ""):
    from datetime import datetime
    ts = datetime.now().isoformat(timespec="seconds")
    with _conn() as con:
        con.execute(
            "INSERT INTO run_log VALUES (?,?,?,?)",
            (ts, str(market_date), status, message)
        )


def get_history(symbol: str, n_days: int = 20) -> pd.DataFrame:
    """Return last n_days of price+delivery data for a symbol."""
    with _conn() as con:
        return pd.read_sql(
            f"SELECT * FROM daily_prices WHERE symbol=? ORDER BY date DESC LIMIT ?",
            con, params=(symbol, n_days)
        )


def get_all_history(n_days: int = 20) -> pd.DataFrame:
    """Return last n_days price data for all NIFTY50 stocks."""
    with _conn() as con:
        return pd.read_sql(
            "SELECT * FROM daily_prices ORDER BY date DESC LIMIT ?",
            con, params=(n_days * 50,)
        )


def get_fii_history(n_days: int = 10) -> pd.DataFrame:
    with _conn() as con:
        return pd.read_sql(
            "SELECT * FROM fii_dii ORDER BY date DESC LIMIT ?",
            con, params=(n_days,)
        )


def get_run_log(n: int = 30) -> pd.DataFrame:
    with _conn() as con:
        return pd.read_sql(
            "SELECT * FROM run_log ORDER BY run_time DESC LIMIT ?",
            con, params=(n,)
        )

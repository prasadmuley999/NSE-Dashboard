"""
NSE Smart Dashboard — Main Orchestrator
Run: python main.py
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

# ── Logging setup ─────────────────────────────────────────────────────────────
Path("history/logs").mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            f"history/logs/run_{datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%Y%m%d_%H%M')}.log",
            encoding="utf-8",
        ),
    ],
)
log = logging.getLogger("main")

from config.config   import OUTPUT_EXCEL, OUTPUT_HTML, DB_PATH
from downloader.market_date       import find_latest_market_date
from downloader.archive_downloader import make_session, download_all
from parser.bhavcopy_parser import parse_cm_bhav, parse_mto, merge_bhav_mto, filter_nifty50
from parser.oi_parser       import parse_fo_bhav
from parser.fii_parser      import parse_fii_dii, parse_participant_oi
from signals.composite      import compute_signals, sector_summary
from dashboard.excel_dashboard import generate_excel
from dashboard.html_dashboard  import generate_html
from storage.sqlite import (
    init_db, upsert_prices, upsert_oi, upsert_fii, upsert_signals,
    log_run, get_all_history, get_fii_history, get_run_log,
)


def main():
    log.info("=" * 60)
    log.info("NSE Smart Dashboard — starting")
    log.info("=" * 60)

    # ── 1. Init DB ─────────────────────────────────────────────────────────────
    init_db()

    # ── 2. Create HTTP session ─────────────────────────────────────────────────
    session = make_session()

    # ── 3. Find latest valid market date ──────────────────────────────────────
    try:
        market_date = find_latest_market_date(session)
    except RuntimeError as e:
        log.error(str(e))
        log_run(None, "FAILED", str(e))
        sys.exit(1)

    log.info(f"Market date: {market_date}")

    # ── 4. Download all archives ───────────────────────────────────────────────
    raw = download_all(session, market_date)

    # ── 5. Parse ───────────────────────────────────────────────────────────────
    bhav_df  = parse_cm_bhav(raw["cm_bhav"], market_date)
    mto_df   = parse_mto(raw["mto"], market_date)
    fo_df    = parse_fo_bhav(raw["fo_bhav"], market_date)
    fii_df   = parse_fii_dii(raw["fii_dii"], market_date)
    part_oi  = parse_participant_oi(raw["part_oi"], market_date)

    # Merge bhav + MTO, filter to NIFTY50
    merged   = merge_bhav_mto(bhav_df, mto_df)
    nifty_df = filter_nifty50(merged)

    if nifty_df.empty:
        msg = "NIFTY50 price data empty after parsing. Aborting."
        log.error(msg)
        log_run(market_date, "FAILED", msg)
        sys.exit(1)

    # ── 6. Store to DB ─────────────────────────────────────────────────────────
    price_store = nifty_df.copy()
    price_store["date"] = str(market_date)
    upsert_prices(price_store)

    if not fo_df.empty:
        fo_store = fo_df.copy()
        fo_store["date"] = str(market_date)
        upsert_oi(fo_store)

    if not fii_df.empty:
        upsert_fii(fii_df)

    # ── 7. Load historical data for signal computation ─────────────────────────
    hist_df  = get_all_history(n_days=25)
    fii_hist = get_fii_history(n_days=15)

    # ── 8. Compute signals ─────────────────────────────────────────────────────
    fii_series = fii_df.iloc[0] if not fii_df.empty else pd.Series()

    signals_df = compute_signals(
        nifty_df    = nifty_df,
        oi_df       = fo_df,
        fii_row     = fii_series,
        hist_df     = hist_df,
        pcr         = 1.0,          # PCR from option chain if available
        market_date = market_date,
    )

    if not signals_df.empty:
        sig_store = signals_df[["date","symbol","sector","score","signal_label","stars","recommendation","oi_signal"]].copy()
        sig_store.rename(columns={"signal_label":"del_signal"}, inplace=True)
        upsert_signals(sig_store)

    sector_df = sector_summary(signals_df)

    # ── 9. Load run log ────────────────────────────────────────────────────────
    run_log_df = get_run_log(n=30)

    # ── 10. Generate Excel ─────────────────────────────────────────────────────
    try:
        generate_excel(
            signals_df  = signals_df,
            fii_series  = fii_series,
            sector_df   = sector_df,
            hist_df     = hist_df,
            fii_hist    = fii_hist,
            run_log_df  = run_log_df,
            market_date = market_date,
            output_path = OUTPUT_EXCEL,
        )
    except Exception as e:
        log.error(f"Excel generation failed: {e}", exc_info=True)

    # ── 11. Generate HTML ──────────────────────────────────────────────────────
    try:
        generate_html(
            signals_df  = signals_df,
            fii_series  = fii_series,
            sector_df   = sector_df,
            hist_df     = hist_df,
            fii_hist    = fii_hist,
            market_date = market_date,
            output_path = OUTPUT_HTML,
        )
    except Exception as e:
        log.error(f"HTML generation failed: {e}", exc_info=True)

    # ── 12. Done ───────────────────────────────────────────────────────────────
    msg = f"Completed for {market_date} — {len(signals_df)} stocks processed"
    log.info(msg)
    log_run(market_date, "SUCCESS", msg)
    log.info("=" * 60)


if __name__ == "__main__":
    main()

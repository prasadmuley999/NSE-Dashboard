"""
Market Date Logic
Finds the latest valid NSE trading day by checking archive availability.
"""

import logging
from datetime import date, timedelta
from zoneinfo import ZoneInfo

import requests

from config.config import NSE_HOLIDAYS_2026, URL_MTO, HEADERS, DOWNLOAD_TIMEOUT

log = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


def ist_today() -> date:
    """Return today's date in IST."""
    from datetime import datetime
    return datetime.now(IST).date()


def ist_hour() -> int:
    """Return current hour in IST."""
    from datetime import datetime
    return datetime.now(IST).hour


def is_trading_day(d: date) -> bool:
    """Return True if d is a weekday and not an NSE holiday."""
    if d.weekday() >= 5:   # Saturday=5, Sunday=6
        return False
    return d.isoformat() not in NSE_HOLIDAYS_2026


def mto_url(d: date) -> str:
    return URL_MTO.replace("{ddmmyyyy}", d.strftime("%d%m%Y"))


def archive_exists(d: date, session: requests.Session) -> bool:
    """HEAD-check NSE MTO archive to confirm data is published for this date."""
    url = mto_url(d)
    try:
        r = session.head(url, headers=HEADERS, timeout=DOWNLOAD_TIMEOUT, allow_redirects=True)
        return r.status_code == 200
    except Exception as e:
        log.debug(f"Archive check failed for {d}: {e}")
        return False


def find_latest_market_date(session: requests.Session, max_lookback: int = 10) -> date:
    """
    Walk backwards from today (IST) to find the most recent date
    for which NSE archives are published.

    Rules:
    - Skip weekends and NSE holidays.
    - If it's before 19:00 IST, don't try today (files usually published ~18:30).
    - Verify by doing a HEAD request on the MTO file.
    """
    today = ist_today()
    hour  = ist_hour()

    start = today
    # Before 7 PM IST, today's files might not be up yet — start from yesterday
    if hour < 19:
        start = today - timedelta(days=1)
        log.info(f"Before 19:00 IST ({hour:02d}:xx) — starting search from {start}")

    candidate = start
    for _ in range(max_lookback):
        if is_trading_day(candidate):
            log.info(f"Checking archive availability for {candidate} …")
            if archive_exists(candidate, session):
                log.info(f"✅ Market date found: {candidate}")
                return candidate
            else:
                log.info(f"⚠️  No archive for {candidate}, stepping back.")
        candidate -= timedelta(days=1)

    raise RuntimeError(
        f"Could not find a valid market date in the last {max_lookback} days. "
        "Check NSE connectivity."
    )


def prev_trading_days(from_date: date, n: int) -> list[date]:
    """Return a list of n previous trading days (inclusive of from_date)."""
    result = []
    d = from_date
    while len(result) < n:
        if is_trading_day(d):
            result.append(d)
        d -= timedelta(days=1)
    return result

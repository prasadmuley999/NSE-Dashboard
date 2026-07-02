"""
Archive Downloader
Downloads NSE archive files for a given market date with retry logic.
"""

import io
import logging
import time
import zipfile
from datetime import date

import requests

from config.config import (
    HEADERS, DOWNLOAD_TIMEOUT, DOWNLOAD_RETRIES, RETRY_WAIT,
    URL_CM_BHAV, URL_MTO, URL_FO_BHAV, URL_FO_BHAV_OLD,
    URL_FII_API, URL_PART_OI, URL_PART_VOL,
)

log = logging.getLogger(__name__)


def make_session() -> requests.Session:
    """Create a requests session that looks like a browser to NSE."""
    s = requests.Session()
    s.headers.update(HEADERS)
    # Visit NSE homepage first to get cookies (NSE blocks direct archive access without cookies)
    try:
        s.get("https://www.nseindia.com", timeout=15)
    except Exception:
        pass
    return s


def _fetch(session: requests.Session, url: str, binary: bool = False):
    """Fetch URL with retry. Returns text or bytes, or None on failure."""
    for attempt in range(1, DOWNLOAD_RETRIES + 1):
        try:
            r = session.get(url, timeout=DOWNLOAD_TIMEOUT, allow_redirects=True)
            if r.status_code == 200:
                return r.content if binary else r.text
            log.warning(f"HTTP {r.status_code} for {url} (attempt {attempt})")
        except Exception as e:
            log.warning(f"Request error for {url} (attempt {attempt}): {e}")
        if attempt < DOWNLOAD_RETRIES:
            time.sleep(RETRY_WAIT)
    log.error(f"All {DOWNLOAD_RETRIES} attempts failed for {url}")
    return None


def _unzip_first(content: bytes) -> str | None:
    """Extract first file from a zip bytes payload and return as text."""
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            name = z.namelist()[0]
            return z.read(name).decode("utf-8", errors="replace")
    except Exception as e:
        log.error(f"ZIP extraction failed: {e}")
        return None


# ─── Individual downloaders ──────────────────────────────────────────────────

def download_cm_bhav(session: requests.Session, d: date) -> str | None:
    """Download equity bhavcopy CSV (sec_bhavdata_full format)."""
    ddmmmyyyy = d.strftime("%d%b%Y").upper()   # e.g. 01JUL2026
    url = URL_CM_BHAV.replace("{ddmmmyyyy}", ddmmmyyyy)
    log.info(f"CM Bhav: {url}")
    text = _fetch(session, url)
    if text:
        return text
    log.warning("CM Bhav: trying legacy format…")
    url2 = (URL_CM_BHAV.replace("{yyyy}", d.strftime("%Y"))
                       .replace("{mmm}", d.strftime("%b").upper())
                       .replace("{ddmmmyyyy}", ddmmmyyyy))
    content = _fetch(session, url2, binary=True)
    if content:
        return _unzip_first(content)
    return None


def download_mto(session: requests.Session, d: date) -> str | None:
    """Download MTO delivery file."""
    ddmmyyyy = d.strftime("%d%m%Y")
    url = URL_MTO.replace("{ddmmyyyy}", ddmmyyyy)
    log.info(f"MTO: {url}")
    return _fetch(session, url)


def download_fo_bhav(session: requests.Session, d: date) -> str | None:
    """Download FO bhavcopy (UDiFF format post July 2024)."""
    yyyymmdd = d.strftime("%Y%m%d")
    url = URL_FO_BHAV.replace("{yyyymmdd}", yyyymmdd)
    log.info(f"FO Bhav (UDiFF): {url}")
    content = _fetch(session, url, binary=True)
    if content:
        return _unzip_first(content)

    # Fallback: old format
    log.warning("FO Bhav: trying old format…")
    ddmmmyyyy = d.strftime("%d%b%Y").upper()
    url2 = (URL_FO_BHAV_OLD
            .replace("{yyyy}", d.strftime("%Y"))
            .replace("{mmm}", d.strftime("%b").upper())
            .replace("{ddmmmyyyy}", ddmmmyyyy))
    content2 = _fetch(session, url2, binary=True)
    if content2:
        return _unzip_first(content2)
    return None


def download_fii_dii(session: requests.Session) -> dict | None:
    """
    Download FII/DII data from NSE JSON API.
    Returns dict with keys: fii_buy, fii_sell, fii_net, dii_buy, dii_sell, dii_net
    """
    log.info(f"FII/DII API: {URL_FII_API}")
    text = _fetch(session, URL_FII_API)
    if not text:
        return None
    try:
        import json
        data = json.loads(text)
        # NSE API returns a list of records; first record is today
        if isinstance(data, list) and data:
            rec = data[0]
        elif isinstance(data, dict):
            rec = data
        else:
            return None

        def _f(v):
            try:
                return float(str(v).replace(",", ""))
            except Exception:
                return 0.0

        return {
            "fii_buy":  _f(rec.get("buyValue",  rec.get("fiiBuyValue",  0))),
            "fii_sell": _f(rec.get("sellValue", rec.get("fiiSellValue", 0))),
            "fii_net":  _f(rec.get("netValue",  rec.get("fiiNetValue",  0))),
            "dii_buy":  _f(rec.get("diiBuyValue",  0)),
            "dii_sell": _f(rec.get("diiSellValue", 0)),
            "dii_net":  _f(rec.get("diiNetValue",  0)),
        }
    except Exception as e:
        log.error(f"FII/DII parse error: {e}")
        return None


def download_participant_oi(session: requests.Session, d: date) -> str | None:
    """Download participant-wise OI file."""
    ddmmyyyy = d.strftime("%d%m%Y")
    url = URL_PART_OI.replace("{ddmmyyyy}", ddmmyyyy)
    log.info(f"Participant OI: {url}")
    return _fetch(session, url)


def download_participant_vol(session: requests.Session, d: date) -> str | None:
    """Download participant-wise volume file."""
    ddmmyyyy = d.strftime("%d%m%Y")
    url = URL_PART_VOL.replace("{ddmmyyyy}", ddmmyyyy)
    log.info(f"Participant Vol: {url}")
    return _fetch(session, url)


def download_all(session: requests.Session, d: date) -> dict:
    """
    Download all required files for date d.
    Returns dict with keys: cm_bhav, mto, fo_bhav, fii_dii, part_oi, part_vol
    All values are raw text (or dict for fii_dii), or None if unavailable.
    """
    log.info(f"=== Downloading archives for {d} ===")
    return {
        "cm_bhav":  download_cm_bhav(session, d),
        "mto":      download_mto(session, d),
        "fo_bhav":  download_fo_bhav(session, d),
        "fii_dii":  download_fii_dii(session),
        "part_oi":  download_participant_oi(session, d),
        "part_vol": download_participant_vol(session, d),
    }

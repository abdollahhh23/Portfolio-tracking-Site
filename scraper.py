"""
scraper.py — Core PSX HTML scraping logic.

PSX historical endpoint (dps.psx.com.pk/historical) responds to POST requests
with a raw HTML table — NOT JSON. This module handles that correctly.
"""

import datetime
import threading
import time
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta

# ── Logging ──────────────────────────────────────────────────────────────────
logger = logging.getLogger("psx.scraper")

# ── Constants ─────────────────────────────────────────────────────────────────
PSX_HISTORICAL_URL = "https://dps.psx.com.pk/historical"
PSX_SYMBOLS_URL    = "https://dps.psx.com.pk/symbols"

PERIOD_MAP: dict[str, Optional[int]] = {
    "1w":  7,
    "2w":  14,
    "1m":  30,
    "3m":  90,
    "6m":  180,
    "1y":  365,
    "2y":  730,
    "3y":  1095,
    "5y":  1825,
    "max": None,   # earliest available data (~2000-01-01)
}

DATE_FORMATS = ("%b %d, %Y", "%d-%b-%Y", "%Y-%m-%d", "%d/%m/%Y")

# ── Thread-local session pool ─────────────────────────────────────────────────
_local = threading.local()

def _session() -> requests.Session:
    """One persistent Session per thread — avoids TCP reconnect overhead."""
    if not hasattr(_local, "session"):
        s = requests.Session()
        s.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Referer":          "https://dps.psx.com.pk/",
            "X-Requested-With": "XMLHttpRequest",
            "Accept":           "text/html, */*; q=0.01",
            "Accept-Language":  "en-US,en;q=0.9",
            "Content-Type":     "application/x-www-form-urlencoded; charset=UTF-8",
        })
        _local.session = s
    return _local.session


# ── Date helpers ──────────────────────────────────────────────────────────────
def _parse_date(raw: str) -> Optional[datetime.date]:
    raw = raw.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    logger.warning("Could not parse date string: %r", raw)
    return None


def period_to_dates(period: str) -> tuple[datetime.date, datetime.date]:
    """Convert a period string like '6m' or '1y' to (start, end) dates."""
    period = period.lower()
    if period not in PERIOD_MAP:
        raise ValueError(
            f"Unknown period '{period}'. Valid values: {list(PERIOD_MAP)}"
        )
    end   = datetime.date.today()
    days  = PERIOD_MAP[period]
    start = datetime.date(2000, 1, 1) if days is None else end - datetime.timedelta(days=days)
    return start, end


def _month_range(start: datetime.date, end: datetime.date) -> list[datetime.date]:
    """Return a list of first-of-month dates spanning start..end."""
    months, cur = [], datetime.date(start.year, start.month, 1)
    ceiling     = datetime.date(end.year, end.month, 1)
    while cur <= ceiling:
        months.append(cur)
        cur += relativedelta(months=1)
    return months


# ── HTML parsing (the part that was broken) ───────────────────────────────────
def _parse_html_table(html: str) -> Optional[pd.DataFrame]:
    """
    Parse the HTML table that PSX returns and produce a tidy DataFrame.

    PSX returns something like:
        <table>
          <thead><tr><th>TIME</th><th>OPEN</th>...</tr></thead>
          <tbody><tr><td>Apr 30, 2025</td><td>1,234.56</td>...</tr></tbody>
        </table>

    The old psx-data-reader library broke because it assumed the date column
    was always named 'TIME', but PSX sometimes calls it 'Date' or similar,
    and the library tried json.loads() on HTML text.
    """
    soup = BeautifulSoup(html, "html.parser")

    # ── find headers ──────────────────────────────────────────────────────────
    headers = [th.get_text(strip=True) for th in soup.select("th")]
    if not headers:
        # PSX returns an empty body when the symbol doesn't exist or no data
        return None

    # ── collect rows ──────────────────────────────────────────────────────────
    row_data: dict[str, list] = defaultdict(list)
    for tr in soup.select("tbody tr"):
        cols = [td.get_text(strip=True) for td in tr.select("td")]
        if len(cols) != len(headers):
            continue                        # skip malformed rows
        for key, val in zip(headers, cols):
            row_data[key].append(val)

    if not row_data:
        return None

    df = pd.DataFrame(row_data)

    # ── identify and normalise the date column ────────────────────────────────
    # PSX has used 'TIME', 'Date', 'DATE', 'Dt' — match case-insensitively
    date_col = next(
        (c for c in df.columns if c.strip().upper() in ("TIME", "DATE", "DT")),
        None,
    )
    if date_col is None:
        logger.warning("No date column found. Headers were: %s", headers)
        return None

    df["Date"] = df[date_col].apply(_parse_date)
    df.drop(columns=[date_col], inplace=True)
    df.dropna(subset=["Date"], inplace=True)
    df.set_index("Date", inplace=True)
    df.index.name = "Date"

    # ── normalise column names → Title case ───────────────────────────────────
    df.rename(columns=lambda c: c.strip().title(), inplace=True)

    # ── strip commas / coerce numerics ────────────────────────────────────────
    for col in df.columns:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.strip()
        )
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


# ── Network layer ─────────────────────────────────────────────────────────────
def _fetch_month(
    symbol: str,
    year: int,
    month: int,
    retries: int = 3,
    backoff: float = 1.5,
) -> Optional[pd.DataFrame]:
    """POST to PSX for one (symbol, year, month) and return parsed DataFrame."""
    session = _session()
    payload = {"month": month, "year": year, "symbol": symbol.upper()}

    for attempt in range(1, retries + 1):
        try:
            resp = session.post(PSX_HISTORICAL_URL, data=payload, timeout=20)
            resp.raise_for_status()

            # ── CRITICAL FIX: PSX returns HTML, not JSON ──────────────────────
            # The old code did json.loads(resp.text) here — that's wrong.
            # We parse the HTML table directly.
            content_type = resp.headers.get("content-type", "")
            if "json" in content_type:
                # Future-proof: if PSX ever switches to JSON, log a warning
                logger.warning(
                    "Unexpected JSON response from PSX for %s %d/%02d. "
                    "Attempting HTML fallback.",
                    symbol, year, month,
                )

            return _parse_html_table(resp.text)

        except requests.HTTPError as e:
            logger.warning("HTTP %s for %s %d/%02d (attempt %d/%d)",
                           e.response.status_code, symbol, year, month, attempt, retries)
        except requests.RequestException as e:
            logger.warning("Request error for %s %d/%02d: %s (attempt %d/%d)",
                           symbol, year, month, e, attempt, retries)

        if attempt < retries:
            time.sleep(backoff * attempt)

    return None


# ── Public API ────────────────────────────────────────────────────────────────
def scrape(
    symbol: str,
    start: datetime.date,
    end: datetime.date,
    max_workers: int = 6,
) -> pd.DataFrame:
    """
    Fetch OHLCV history for *symbol* between *start* and *end*.

    Returns a pandas DataFrame indexed by Date with columns:
        Open, High, Low, Close, Volume (all float64)
    Returns an empty DataFrame if no data could be retrieved.
    """
    symbol  = symbol.strip().upper()
    months  = _month_range(start, end)
    frames  = []

    logger.info("Scraping %s | %s → %s | %d month-chunks",
                symbol, start, end, len(months))

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_map = {
            pool.submit(_fetch_month, symbol, d.year, d.month): d
            for d in months
        }
        for fut in as_completed(future_map):
            df = fut.result()
            if df is not None and not df.empty:
                frames.append(df)

    if not frames:
        logger.warning("No data returned for %s", symbol)
        return pd.DataFrame()

    combined = pd.concat(frames)
    combined = combined[~combined.index.duplicated(keep="first")]
    combined.sort_index(inplace=True)

    # Clip to the requested window (month chunks may overshoot)
    mask = (combined.index >= start) & (combined.index <= end)
    return combined.loc[mask]


def scrape_multiple(
    symbols: list[str],
    start: datetime.date,
    end: datetime.date,
) -> dict[str, pd.DataFrame]:
    """Scrape multiple tickers. Returns {SYMBOL: DataFrame}."""
    return {
        sym.upper(): df
        for sym in symbols
        if not (df := scrape(sym, start, end)).empty
    }


def get_all_tickers() -> pd.DataFrame:
    """Return a DataFrame of all PSX-listed symbols."""
    try:
        resp = requests.get(PSX_SYMBOLS_URL, timeout=10)
        resp.raise_for_status()
        return pd.read_json(resp.text)
    except Exception as e:
        logger.error("Failed to fetch ticker list: %s", e)
        return pd.DataFrame()

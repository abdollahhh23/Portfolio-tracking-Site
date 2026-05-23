#!/usr/bin/env python3
"""
PSX Stock Data Scraper
======================
Scrapes historical stock data from Pakistan Stock Exchange (dps.psx.com.pk).

Usage:
    python psx_scraper.py --ticker LUCK --period 1y
    python psx_scraper.py --ticker OGDC --start 2024-01-01 --end 2025-05-22
    python psx_scraper.py --ticker ENGRO --period 6m --output csv
    python psx_scraper.py --tickers LUCK OGDC ENGRO --period 3m

Requirements:
    pip install requests beautifulsoup4 pandas numpy python-dateutil tqdm
"""

import argparse
import datetime
import threading
import time
import sys
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dateutil.relativedelta import relativedelta

import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
PSX_HISTORICAL_URL = "https://dps.psx.com.pk/historical"
PSX_SYMBOLS_URL    = "https://dps.psx.com.pk/symbols"

PERIOD_MAP = {
    "1w":  7,
    "2w":  14,
    "1m":  30,
    "3m":  90,
    "6m":  180,
    "1y":  365,
    "2y":  730,
    "3y":  1095,
    "5y":  1825,
    "max": None,   # from 2000-01-01
}

# ─────────────────────────────────────────────
# Session management (thread-local)
# ─────────────────────────────────────────────
_local = threading.local()

def get_session() -> requests.Session:
    if not hasattr(_local, "session"):
        s = requests.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/124.0 Safari/537.36",
            "Referer": "https://dps.psx.com.pk/",
            "Accept-Language": "en-US,en;q=0.9",
        })
        _local.session = s
    return _local.session


# ─────────────────────────────────────────────
# Core scraping logic
# ─────────────────────────────────────────────
def fetch_month(symbol: str, year: int, month: int, retries: int = 3) -> pd.DataFrame | None:
    """POST to PSX and parse one month of OHLCV data for a symbol."""
    session = get_session()
    payload = {"month": month, "year": year, "symbol": symbol.upper()}

    for attempt in range(1, retries + 1):
        try:
            resp = session.post(PSX_HISTORICAL_URL, data=payload, timeout=15)
            resp.raise_for_status()
            return _parse_html_table(resp.text)
        except requests.RequestException as e:
            if attempt == retries:
                print(f"  ⚠  Failed {symbol} {year}/{month:02d} after {retries} attempts: {e}",
                      file=sys.stderr)
                return None
            time.sleep(1.5 * attempt)


def _parse_html_table(html: str) -> pd.DataFrame | None:
    """Parse the HTML table returned by PSX into a DataFrame."""
    soup = BeautifulSoup(html, "html.parser")
    headers = [th.get_text(strip=True) for th in soup.select("th")]

    if not headers:
        return None

    rows_data: dict = defaultdict(list)
    for row in soup.select("tr"):
        cols = [td.get_text(strip=True) for td in row.select("td")]
        if not cols:
            continue
        for key, val in zip(headers, cols):
            rows_data[key].append(val)

    if not rows_data:
        return None

    df = pd.DataFrame(rows_data, columns=headers)

    # Detect and parse the date column (PSX calls it "TIME" or "Date")
    date_col = next((c for c in df.columns if c.upper() in ("TIME", "DATE")), None)
    if date_col is None:
        return None

    def parse_date(s):
        for fmt in ("%b %d, %Y", "%d-%b-%Y", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        return pd.NaT

    df["Date"] = df[date_col].apply(parse_date)
    df.drop(columns=[date_col], inplace=True)
    df.set_index("Date", inplace=True)
    df.index.name = "Date"

    # Normalise column names
    df.rename(columns=str.title, inplace=True)

    # Strip commas and coerce to float
    for col in df.columns:
        df[col] = (
            df[col].astype(str)
                   .str.replace(",", "", regex=False)
                   .pipe(pd.to_numeric, errors="coerce")
        )

    return df


def _daterange(start: datetime.date, end: datetime.date) -> list[datetime.date]:
    """Return list of (year, month) first-of-month dates covering start→end."""
    dates = []
    cur = datetime.date(start.year, start.month, 1)
    limit = datetime.date(end.year, end.month, 1)
    while cur <= limit:
        dates.append(cur)
        cur += relativedelta(months=1)
    return dates


def scrape(symbol: str,
           start: datetime.date,
           end: datetime.date,
           max_workers: int = 6) -> pd.DataFrame:
    """Download and return OHLCV data for one symbol between start and end."""
    month_dates = _daterange(start, end)
    frames = []

    print(f"  Fetching {symbol.upper()} ({len(month_dates)} month-chunks) …")

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(fetch_month, symbol, d.year, d.month): d
            for d in month_dates
        }
        for fut in as_completed(futures):
            df = fut.result()
            if df is not None and not df.empty:
                frames.append(df)

    if not frames:
        print(f"  ⚠  No data returned for {symbol}.", file=sys.stderr)
        return pd.DataFrame()

    combined = pd.concat(frames)
    combined = combined[~combined.index.duplicated(keep="first")]
    combined.sort_index(inplace=True)

    # Clip to requested date window
    combined = combined.loc[
        (combined.index >= start) & (combined.index <= end)
    ]
    return combined


def scrape_multiple(symbols: list[str],
                    start: datetime.date,
                    end: datetime.date) -> dict[str, pd.DataFrame]:
    results = {}
    for sym in symbols:
        df = scrape(sym, start, end)
        if not df.empty:
            results[sym.upper()] = df
    return results


# ─────────────────────────────────────────────
# Utility: list all PSX tickers
# ─────────────────────────────────────────────
def get_all_tickers() -> pd.DataFrame:
    try:
        resp = requests.get(PSX_SYMBOLS_URL, timeout=10)
        resp.raise_for_status()
        return pd.read_json(resp.text)
    except Exception as e:
        print(f"Could not fetch ticker list: {e}", file=sys.stderr)
        return pd.DataFrame()


# ─────────────────────────────────────────────
# Output helpers
# ─────────────────────────────────────────────
def export_csv(df: pd.DataFrame, symbol: str, out_dir: str = "."):
    path = f"{out_dir}/{symbol}_psx.csv"
    df.to_csv(path)
    print(f"  ✓  Saved CSV → {path}")


def export_json(df: pd.DataFrame, symbol: str, out_dir: str = "."):
    path = f"{out_dir}/{symbol}_psx.json"
    df.reset_index(inplace=False).to_json(path, orient="records", date_format="iso", indent=2)
    print(f"  ✓  Saved JSON → {path}")


def export_excel(df: pd.DataFrame, symbol: str, out_dir: str = "."):
    path = f"{out_dir}/{symbol}_psx.xlsx"
    df.to_excel(path)
    print(f"  ✓  Saved Excel → {path}")


def print_table(df: pd.DataFrame, symbol: str, rows: int = 20):
    print(f"\n{'═'*60}")
    print(f"  {symbol.upper()} — last {min(rows, len(df))} rows")
    print(f"{'═'*60}")
    print(df.tail(rows).to_string())
    print(f"\nTotal rows: {len(df)}  |  "
          f"Date range: {df.index.min()} → {df.index.max()}")


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────
def resolve_dates(args) -> tuple[datetime.date, datetime.date]:
    end = datetime.date.today()

    if args.start and args.end:
        return (datetime.date.fromisoformat(args.start),
                datetime.date.fromisoformat(args.end))

    if args.period:
        p = args.period.lower()
        if p not in PERIOD_MAP:
            raise ValueError(f"Unknown period '{p}'. Choose from: {list(PERIOD_MAP)}")
        days = PERIOD_MAP[p]
        start = datetime.date(2000, 1, 1) if days is None else end - datetime.timedelta(days=days)
        return start, end

    # default: 1 year
    return end - datetime.timedelta(days=365), end


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="PSX Stock Data Scraper — fetch OHLCV history from dps.psx.com.pk",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python psx_scraper.py --ticker LUCK --period 1y
  python psx_scraper.py --ticker OGDC --start 2024-01-01 --end 2025-05-22 --output csv
  python psx_scraper.py --tickers LUCK OGDC ENGRO --period 6m --output excel
  python psx_scraper.py --list-tickers
        """,
    )
    g = p.add_mutually_exclusive_group()
    g.add_argument("--ticker",  metavar="SYMBOL", help="Single ticker symbol, e.g. LUCK")
    g.add_argument("--tickers", metavar="SYMBOL", nargs="+",
                   help="Multiple ticker symbols, e.g. LUCK OGDC ENGRO")

    p.add_argument("--period", metavar="PERIOD",
                   help=f"Time period: {', '.join(PERIOD_MAP.keys())}")
    p.add_argument("--start", metavar="YYYY-MM-DD", help="Start date (overrides --period)")
    p.add_argument("--end",   metavar="YYYY-MM-DD", help="End date (default: today)")

    p.add_argument("--output", choices=["print", "csv", "json", "excel", "all"],
                   default="print", help="Output format (default: print)")
    p.add_argument("--out-dir", default=".", metavar="DIR",
                   help="Directory to save exported files (default: current dir)")
    p.add_argument("--list-tickers", action="store_true",
                   help="Print all PSX tickers and exit")
    p.add_argument("--workers", type=int, default=6,
                   help="Parallel HTTP workers per ticker (default: 6)")
    return p


def main():
    parser = build_parser()
    args   = parser.parse_args()

    if args.list_tickers:
        df = get_all_tickers()
        if not df.empty:
            print(df.to_string(index=False))
        return

    symbols = []
    if args.ticker:
        symbols = [args.ticker]
    elif args.tickers:
        symbols = args.tickers
    else:
        parser.print_help()
        sys.exit(1)

    start, end = resolve_dates(args)
    print(f"\n  PSX Scraper  |  {', '.join(s.upper() for s in symbols)}")
    print(f"    Date range : {start} → {end}\n")

    results = {}
    for sym in symbols:
        df = scrape(sym, start, end, max_workers=args.workers)
        if not df.empty:
            results[sym.upper()] = df

    if not results:
        print("No data retrieved. Check your ticker symbols and internet connection.")
        sys.exit(1)

    for sym, df in results.items():
        fmt = args.output
        if fmt in ("print", "all"):
            print_table(df, sym)
        if fmt in ("csv", "all"):
            export_csv(df, sym, args.out_dir)
        if fmt in ("json", "all"):
            export_json(df, sym, args.out_dir)
        if fmt in ("excel", "all"):
            export_excel(df, sym, args.out_dir)


if __name__ == "__main__":
    main()
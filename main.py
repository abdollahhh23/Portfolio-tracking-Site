#!/usr/bin/env python3
"""
main.py — CLI for the PSX Stock Data Scraper.

Usage examples:
    python main.py --ticker LUCK --period 1y
    python main.py --ticker OGDC --start 2024-01-01 --end 2025-05-22
    python main.py --tickers LUCK OGDC ENGRO --period 6m --output csv
    python main.py --list-tickers

To run as an API server instead:
    uvicorn api:app --reload --port 8000
    Then open: http://localhost:8000/docs
"""

import argparse
import datetime
import json
import logging
import sys

import pandas as pd

from scraper import (
    scrape,
    scrape_multiple,
    get_all_tickers,
    period_to_dates,
    PERIOD_MAP,
)

logging.basicConfig(
    level   = logging.WARNING,          # quiet by default; use --verbose to see debug logs
    format  = "%(levelname)s: %(message)s",
)


# ── Output helpers ─────────────────────────────────────────────────────────────
def _print_table(df: pd.DataFrame, symbol: str, tail: int = 30):
    sep = "─" * 72
    print(f"\n{sep}")
    print(f"  {symbol}   {df.index.min()} → {df.index.max()}   ({len(df)} rows)")
    print(sep)
    pd.set_option("display.float_format", "{:,.2f}".format)
    pd.set_option("display.max_columns", 10)
    pd.set_option("display.width", 120)
    print(df.tail(tail).to_string())
    print()


def _save_csv(df: pd.DataFrame, symbol: str, out_dir: str):
    path = f"{out_dir}/{symbol}_psx.csv"
    df.to_csv(path)
    print(f"  ✓  CSV  → {path}")


def _save_json(df: pd.DataFrame, symbol: str, out_dir: str):
    path = f"{out_dir}/{symbol}_psx.json"
    records = df.reset_index().copy()
    records["Date"] = records["Date"].astype(str)
    records.to_json(path, orient="records", indent=2)
    print(f"  ✓  JSON → {path}")


def _save_excel(df: pd.DataFrame, symbol: str, out_dir: str):
    path = f"{out_dir}/{symbol}_psx.xlsx"
    df.to_excel(path)
    print(f"  ✓  XLSX → {path}")


# ── Date resolution ────────────────────────────────────────────────────────────
def _resolve_dates(args) -> tuple[datetime.date, datetime.date]:
    if args.start and args.end:
        try:
            return (
                datetime.date.fromisoformat(args.start),
                datetime.date.fromisoformat(args.end),
            )
        except ValueError:
            print("ERROR: Dates must be YYYY-MM-DD format.", file=sys.stderr)
            sys.exit(1)

    p = (args.period or "1y").lower()
    if p not in PERIOD_MAP:
        print(
            f"ERROR: Unknown period '{p}'. Valid: {list(PERIOD_MAP)}",
            file=sys.stderr,
        )
        sys.exit(1)

    return period_to_dates(p)


# ── CLI ────────────────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog        = "psx_scraper",
        description = "PSX Stock Data Scraper — fetch OHLCV history from Pakistan Stock Exchange",
        formatter_class = argparse.RawDescriptionHelpFormatter,
        epilog = """
Examples:
  python main.py --ticker LUCK --period 1y
  python main.py --ticker OGDC --start 2024-01-01 --end 2025-05-22 --output csv
  python main.py --tickers LUCK OGDC ENGRO --period 6m --output all
  python main.py --list-tickers

Valid periods: 1w  2w  1m  3m  6m  1y  2y  3y  5y  max
        """,
    )

    target = p.add_mutually_exclusive_group()
    target.add_argument("--ticker",      metavar="SYM",  help="Single ticker, e.g. LUCK")
    target.add_argument("--tickers",     metavar="SYM",  nargs="+", help="Multiple tickers")
    target.add_argument("--list-tickers", action="store_true", help="List all PSX symbols and exit")

    p.add_argument("--period",  metavar="PERIOD",       default="1y",
                   help="Time period (default: 1y)")
    p.add_argument("--start",   metavar="YYYY-MM-DD",
                   help="Custom start date (requires --end)")
    p.add_argument("--end",     metavar="YYYY-MM-DD",
                   help="Custom end date (requires --start)")
    p.add_argument("--output",  choices=["print", "csv", "json", "excel", "all"],
                   default="print", help="Output format (default: print)")
    p.add_argument("--out-dir", metavar="DIR", default=".",
                   help="Directory for saved files (default: current dir)")
    p.add_argument("--workers", type=int, default=6,
                   help="Parallel HTTP threads per ticker (default: 6)")
    p.add_argument("--verbose", action="store_true",
                   help="Enable debug logging")
    return p


def main():
    parser = build_parser()
    args   = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # ── list tickers ────────────────────────────────────────────────────────
    if args.list_tickers:
        df = get_all_tickers()
        if df.empty:
            print("Could not fetch ticker list. Check your internet connection.")
            sys.exit(1)
        print(df.to_string(index=False))
        return

    # ── resolve symbols ──────────────────────────────────────────────────────
    if args.ticker:
        symbols = [args.ticker.upper()]
    elif args.tickers:
        symbols = [s.upper() for s in args.tickers]
    else:
        parser.print_help()
        sys.exit(0)

    start, end = _resolve_dates(args)

    print(f"\n📈  PSX Scraper")
    print(f"    Ticker(s) : {', '.join(symbols)}")
    print(f"    Range     : {start}  →  {end}\n")

    # ── fetch ────────────────────────────────────────────────────────────────
    results: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        print(f"  Downloading {sym}…")
        df = scrape(sym, start, end, max_workers=args.workers)
        if df.empty:
            print(f"  ⚠  No data returned for {sym}. "
                  "Check the ticker symbol is correct.")
        else:
            print(f"  ✓  {len(df)} trading days loaded for {sym}")
            results[sym] = df

    if not results:
        print("\nNo data could be retrieved. Exiting.")
        sys.exit(1)

    # ── output ───────────────────────────────────────────────────────────────
    fmt = args.output
    for sym, df in results.items():
        if fmt in ("print", "all"):
            _print_table(df, sym)
        if fmt in ("csv", "all"):
            _save_csv(df, sym, args.out_dir)
        if fmt in ("json", "all"):
            _save_json(df, sym, args.out_dir)
        if fmt in ("excel", "all"):
            _save_excel(df, sym, args.out_dir)


if __name__ == "__main__":
    main()

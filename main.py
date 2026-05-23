#!/usr/bin/env python3
"""
PSX Stock Data Scraper
Fetches historical OHLCV data from the Pakistan Stock Exchange.
Run directly via:  bash run.sh
Or manually via:   python3 main.py --ticker LUCK --period 1y
"""

import argparse
import datetime
import json
import logging
import os
import sys

import pandas as pd

from scraper import PERIOD_MAP, get_all_tickers, period_to_dates, scrape

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

OUTPUT_DIR = "output"


# ── output helpers ────────────────────────────────────────────────────────────
def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def _to_export_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.reset_index().copy()
    out["Date"] = out["Date"].astype(str)
    return out


def _print_table(df: pd.DataFrame, symbol: str):
    sep = "─" * 72
    print(f"\n{sep}")
    print(f"  {symbol}   {df.index.min()} → {df.index.max()}   ({len(df)} trading days)")
    print(sep)
    pd.set_option("display.float_format", "{:,.2f}".format)
    pd.set_option("display.max_columns", 10)
    pd.set_option("display.width", 120)
    print(df.to_string())
    print()


def _save_csv(df: pd.DataFrame, symbol: str):
    _ensure_dir(OUTPUT_DIR)
    path = os.path.join(OUTPUT_DIR, f"{symbol}_psx.csv")
    _to_export_df(df).to_csv(path, index=False)
    print(f"  ✓  CSV   → {path}")


def _save_json(df: pd.DataFrame, symbol: str):
    _ensure_dir(OUTPUT_DIR)
    path = os.path.join(OUTPUT_DIR, f"{symbol}_psx.json")
    records = _to_export_df(df).to_dict(orient="records")
    with open(path, "w") as fh:
        json.dump({"symbol": symbol, "rows": len(records), "data": records}, fh, indent=2)
    print(f"  ✓  JSON  → {path}")


def _save_excel(df: pd.DataFrame, symbol: str):
    _ensure_dir(OUTPUT_DIR)
    path = os.path.join(OUTPUT_DIR, f"{symbol}_psx.xlsx")
    _to_export_df(df).to_excel(path, index=False)
    print(f"  ✓  Excel → {path}")


def _dispatch(df: pd.DataFrame, symbol: str, formats: list[str]):
    if "all" in formats:
        formats = ["print", "csv", "json", "excel"]
    if "print" in formats:
        _print_table(df, symbol)
    if "csv"   in formats:
        _save_csv(df, symbol)
    if "json"  in formats:
        _save_json(df, symbol)
    if "excel" in formats:
        _save_excel(df, symbol)


# ── date helpers ──────────────────────────────────────────────────────────────
def _resolve_dates(args) -> tuple[datetime.date, datetime.date]:
    if args.start and args.end:
        try:
            return (
                datetime.date.fromisoformat(args.start),
                datetime.date.fromisoformat(args.end),
            )
        except ValueError:
            print("ERROR: Dates must be YYYY-MM-DD.", file=sys.stderr)
            sys.exit(1)
    if args.start or args.end:
        print("ERROR: --start and --end must both be provided together.", file=sys.stderr)
        sys.exit(1)
    p = (args.period or "1y").lower()
    if p not in PERIOD_MAP:
        print(f"ERROR: Unknown period '{p}'. Valid: {list(PERIOD_MAP)}", file=sys.stderr)
        sys.exit(1)
    return period_to_dates(p)


# ── CLI ───────────────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="main.py",
        description="PSX Stock Data Scraper — fetch OHLCV history from Pakistan Stock Exchange.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES
  python3 main.py --ticker LUCK --period 1y
  python3 main.py --ticker OGDC --period 6m --output csv
  python3 main.py --tickers LUCK OGDC ENGRO --period 3m --output csv json
  python3 main.py --ticker LUCK --start 2024-01-01 --end 2025-05-22 --output excel
  python3 main.py --ticker LUCK --output all
  python3 main.py --list-tickers

VALID PERIODS
  1w   1 week        1y   1 year
  2w   2 weeks       2y   2 years
  1m   1 month       3y   3 years
  3m   3 months      5y   5 years
  6m   6 months      max  all data (~2000 onward)
        """,
    )

    src = p.add_mutually_exclusive_group()
    src.add_argument("--ticker",       metavar="SYM",       help="Single ticker, e.g. LUCK")
    src.add_argument("--tickers",      metavar="SYM", nargs="+", help="Multiple tickers, e.g. LUCK OGDC ENGRO")
    src.add_argument("--list-tickers", action="store_true", help="Print all PSX-listed symbols and exit")

    p.add_argument("--period",  metavar="PERIOD",     default="1y", help="Time period (default: 1y)")
    p.add_argument("--start",   metavar="YYYY-MM-DD", help="Custom start date (use with --end)")
    p.add_argument("--end",     metavar="YYYY-MM-DD", help="Custom end date (use with --start)")
    p.add_argument("--output",  metavar="FMT", nargs="+", default=["print"],
                   choices=["print", "csv", "json", "excel", "all"],
                   help="Output format(s): print csv json excel all  (default: print)")
    p.add_argument("--verbose", action="store_true", help="Show detailed logs")
    return p


def main():
    parser = build_parser()
    args   = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.list_tickers:
        df = get_all_tickers()
        if df.empty:
            print("Could not fetch ticker list. Check your internet connection.")
            sys.exit(1)
        print(df.to_string(index=False))
        return

    if args.ticker:
        symbols = [args.ticker.upper()]
    elif args.tickers:
        symbols = [s.upper() for s in args.tickers]
    else:
        parser.print_help()
        sys.exit(0)

    start, end = _resolve_dates(args)

    print(f"\n  Ticker(s) : {', '.join(symbols)}")
    print(f"  Range     : {start}  →  {end}")
    print(f"  Output    : {', '.join(args.output)}\n")

    for sym in symbols:
        print(f"  ⟳  Fetching {sym}...")
        df = scrape(sym, start, end)
        if df.empty:
            print(f"  ⚠  No data for {sym}. Check the ticker symbol.")
            continue
        print(f"  ✓  {len(df)} trading days retrieved.")
        _dispatch(df, sym, args.output)

    print()


if __name__ == "__main__":
    main()

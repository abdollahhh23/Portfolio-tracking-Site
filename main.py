#!/usr/bin/env python3
"""
main.py — PSX Stock Data Scraper · Entry Point

All default behaviour is controlled by config.py.
CLI flags override config values when provided.

Quick start:
    python main.py                          # uses config.py defaults
    python main.py --ticker LUCK            # override ticker only
    python main.py --ticker OGDC --period 6m --output csv json
    python main.py --tickers LUCK OGDC ENGRO --period 1y --output all
    python main.py --input-file tickers.csv --input-format csv
    python main.py --list-tickers
"""

import argparse
import datetime
import json
import logging
import os
import sys

import pandas as pd

import config
from scraper import (
    PERIOD_MAP,
    get_all_tickers,
    period_to_dates,
    scrape,
    scrape_multiple,
)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level  = logging.DEBUG if config.VERBOSE else logging.WARNING,
    format = "%(levelname)s: %(message)s",
)
logger = logging.getLogger("psx.main")

# ── Valid choices ─────────────────────────────────────────────────────────────
_FORMAT_CHOICES = ["print", "csv", "json", "excel", "all"]
_INPUT_CHOICES  = ["args", "csv", "json", "txt"]


# ═════════════════════════════════════════════════════════════════════════════
#  Input-file readers
# ═════════════════════════════════════════════════════════════════════════════
def _read_tickers_csv(path: str) -> list[str]:
    df = pd.read_csv(path)
    col = next(
        (c for c in df.columns if c.strip().lower() in ("symbol", "ticker", "tickers", "symbols")),
        None,
    )
    if col is None:
        raise ValueError(
            f"CSV '{path}' must have a column named 'symbol' or 'ticker'. "
            f"Found: {list(df.columns)}"
        )
    return [str(v).strip().upper() for v in df[col].dropna() if str(v).strip()]


def _read_tickers_json(path: str) -> list[str]:
    with open(path) as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError(f"JSON '{path}' must be a list of ticker strings, e.g. [\"LUCK\", \"OGDC\"]")
    return [str(v).strip().upper() for v in data if str(v).strip()]


def _read_tickers_txt(path: str) -> list[str]:
    tickers = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                tickers.append(line.upper())
    return tickers


def _load_tickers_from_file(fmt: str, path: str) -> list[str]:
    if not path:
        raise ValueError("INPUT_FILE must be set when INPUT_FORMAT is 'csv', 'json', or 'txt'.")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Input file not found: {path}")
    readers = {"csv": _read_tickers_csv, "json": _read_tickers_json, "txt": _read_tickers_txt}
    return readers[fmt](path)


# ═════════════════════════════════════════════════════════════════════════════
#  Date resolution
# ═════════════════════════════════════════════════════════════════════════════
def _resolve_dates(
    period:     str | None,
    start_str:  str | None,
    end_str:    str | None,
) -> tuple[datetime.date, datetime.date]:
    """
    Priority: explicit start+end > period > config defaults > "1y".
    """
    if start_str and end_str:
        try:
            return (
                datetime.date.fromisoformat(start_str),
                datetime.date.fromisoformat(end_str),
            )
        except ValueError:
            _die("Dates must be in YYYY-MM-DD format.")

    if start_str or end_str:
        _die("Both --start and --end are required when using a custom date range.")

    p = (period or "1y").lower()
    if p not in PERIOD_MAP:
        _die(f"Unknown period '{p}'. Valid: {list(PERIOD_MAP)}")
    return period_to_dates(p)


# ═════════════════════════════════════════════════════════════════════════════
#  Column filtering
# ═════════════════════════════════════════════════════════════════════════════
def _filter_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """
    Keep only the requested columns. 'Date' is always the index so it is
    excluded from the column filter but reattached on export.
    Unrecognised column names are warned about and skipped.
    """
    if not columns:
        return df

    wanted = [c.strip().title() for c in columns if c.strip().lower() != "date"]
    available = list(df.columns)
    valid   = [c for c in wanted if c in available]
    invalid = [c for c in wanted if c not in available]

    if invalid:
        print(f"  ⚠  Unknown column(s) ignored: {invalid}. "
              f"Available: {['Date'] + available}")

    return df[valid] if valid else df


# ═════════════════════════════════════════════════════════════════════════════
#  Output helpers
# ═════════════════════════════════════════════════════════════════════════════
def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def _to_export_df(df: pd.DataFrame, date_fmt: str) -> pd.DataFrame:
    """Reset index and format dates for export."""
    out = df.reset_index().copy()
    out["Date"] = out["Date"].apply(lambda d: d.strftime(date_fmt))
    return out


def _print_table(df: pd.DataFrame, symbol: str):
    sep = "─" * 72
    print(f"\n{sep}")
    print(f"  {symbol}   {df.index.min()} → {df.index.max()}   ({len(df)} trading days)")
    print(sep)
    pd.set_option("display.float_format", "{:,.2f}".format)
    pd.set_option("display.max_columns", 10)
    pd.set_option("display.width", 120)
    print(df.tail(30).to_string())
    print()


def _save_csv(df: pd.DataFrame, symbol: str, out_dir: str, date_fmt: str):
    _ensure_dir(out_dir)
    path = os.path.join(out_dir, f"{symbol}_psx.csv")
    _to_export_df(df, date_fmt).to_csv(path, index=False)
    print(f"  ✓  CSV   → {path}")


def _save_json(df: pd.DataFrame, symbol: str, out_dir: str, date_fmt: str):
    _ensure_dir(out_dir)
    path = os.path.join(out_dir, f"{symbol}_psx.json")
    records = _to_export_df(df, date_fmt).to_dict(orient="records")
    with open(path, "w") as fh:
        json.dump({"symbol": symbol, "rows": len(records), "data": records}, fh, indent=2)
    print(f"  ✓  JSON  → {path}")


def _save_excel(df: pd.DataFrame, symbol: str, out_dir: str, date_fmt: str):
    _ensure_dir(out_dir)
    path = os.path.join(out_dir, f"{symbol}_psx.xlsx")
    _to_export_df(df, date_fmt).to_excel(path, index=False)
    print(f"  ✓  Excel → {path}")


def _dispatch_output(
    df:       pd.DataFrame,
    symbol:   str,
    formats:  list[str],
    out_dir:  str,
    date_fmt: str,
):
    if "all" in formats:
        formats = ["print", "csv", "json", "excel"]
    if "print" in formats:
        _print_table(df, symbol)
    if "csv"   in formats:
        _save_csv(df, symbol, out_dir, date_fmt)
    if "json"  in formats:
        _save_json(df, symbol, out_dir, date_fmt)
    if "excel" in formats:
        _save_excel(df, symbol, out_dir, date_fmt)


# ═════════════════════════════════════════════════════════════════════════════
#  Misc
# ═════════════════════════════════════════════════════════════════════════════
def _die(msg: str):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def _validate_formats(formats: list[str]) -> list[str]:
    bad = [f for f in formats if f not in _FORMAT_CHOICES]
    if bad:
        _die(f"Unknown output format(s): {bad}. Valid: {_FORMAT_CHOICES}")
    return formats


# ═════════════════════════════════════════════════════════════════════════════
#  CLI
# ═════════════════════════════════════════════════════════════════════════════
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog    = "main.py",
        description = (
            "PSX Stock Data Scraper — fetch OHLCV history from the "
            "Pakistan Stock Exchange.\n"
            "Defaults are read from config.py; CLI flags override them."
        ),
        formatter_class = argparse.RawDescriptionHelpFormatter,
        epilog = f"""
EXAMPLES
  python main.py                                          use config.py defaults
  python main.py --ticker LUCK                           override ticker
  python main.py --ticker OGDC --period 6m               ticker + period
  python main.py --tickers LUCK OGDC ENGRO --period 3m   multiple tickers
  python main.py --ticker LUCK --start 2024-01-01 --end 2025-05-22
  python main.py --ticker LUCK --output csv json          two formats
  python main.py --ticker LUCK --output all               print + csv + json + excel
  python main.py --input-format csv --input-file tickers.csv
  python main.py --input-format json --input-file tickers.json
  python main.py --input-format txt --input-file tickers.txt
  python main.py --list-tickers

VALID PERIODS
  1w  2w  1m  3m  6m  1y  2y  3y  5y  max

INPUT FILE FORMATS
  CSV  — column named "symbol" or "ticker"
  JSON — list of strings: ["LUCK", "OGDC"]
  TXT  — one ticker per line; lines starting with # are comments
        """,
    )

    # ── what to fetch ─────────────────────────────────────────────────────────
    src = p.add_mutually_exclusive_group()
    src.add_argument("--ticker",       metavar="SYM",
                     help="Single ticker symbol (overrides config.TICKERS)")
    src.add_argument("--tickers",      metavar="SYM", nargs="+",
                     help="Multiple ticker symbols (overrides config.TICKERS)")
    src.add_argument("--list-tickers", action="store_true",
                     help="Print all PSX-listed symbols and exit")

    # ── input file ────────────────────────────────────────────────────────────
    p.add_argument("--input-format", choices=_INPUT_CHOICES, metavar="FMT",
                   help=f"How to read tickers: {_INPUT_CHOICES}  (default: config.INPUT_FORMAT)")
    p.add_argument("--input-file", metavar="PATH",
                   help="Path to CSV / JSON / TXT file of tickers")

    # ── time range ────────────────────────────────────────────────────────────
    p.add_argument("--period",  metavar="PERIOD",
                   help="Period shorthand, e.g. 6m  1y  max  (default: config.PERIOD)")
    p.add_argument("--start",   metavar="YYYY-MM-DD",
                   help="Custom start date (use with --end)")
    p.add_argument("--end",     metavar="YYYY-MM-DD",
                   help="Custom end date   (use with --start)")

    # ── columns ───────────────────────────────────────────────────────────────
    p.add_argument("--columns", metavar="COL", nargs="+",
                   help="Columns to include, e.g. --columns Date Close Volume  "
                        "(default: config.COLUMNS)")

    # ── output ────────────────────────────────────────────────────────────────
    p.add_argument("--output", metavar="FMT", nargs="+",
                   help=f"One or more output formats: {_FORMAT_CHOICES}  "
                        "(default: config.OUTPUT_FORMATS)")
    p.add_argument("--out-dir", metavar="DIR",
                   help="Directory for saved files  (default: config.OUTPUT_DIR)")

    # ── misc ──────────────────────────────────────────────────────────────────
    p.add_argument("--workers", type=int,
                   help="Parallel HTTP threads per ticker  (default: config.MAX_WORKERS)")
    p.add_argument("--verbose", action="store_true",
                   help="Enable debug logging  (default: config.VERBOSE)")
    return p


# ═════════════════════════════════════════════════════════════════════════════
#  Main
# ═════════════════════════════════════════════════════════════════════════════
def main():
    parser = _build_parser()
    args   = parser.parse_args()

    # ── apply verbosity ───────────────────────────────────────────────────────
    if args.verbose or config.VERBOSE:
        logging.getLogger().setLevel(logging.DEBUG)

    # ── list-tickers shortcut ─────────────────────────────────────────────────
    if args.list_tickers:
        df = get_all_tickers()
        if df.empty:
            _die("Could not fetch ticker list. Check your internet connection.")
        print(df.to_string(index=False))
        return

    # ── resolve: input format + file ─────────────────────────────────────────
    input_fmt  = args.input_format or config.INPUT_FORMAT
    input_file = args.input_file   or config.INPUT_FILE

    # ── resolve: ticker list ──────────────────────────────────────────────────
    if args.ticker:
        symbols = [args.ticker.upper()]
    elif args.tickers:
        symbols = [s.upper() for s in args.tickers]
    elif input_fmt != "args":
        try:
            symbols = _load_tickers_from_file(input_fmt, input_file)
        except (ValueError, FileNotFoundError) as exc:
            _die(str(exc))
    elif config.TICKERS:
        symbols = [s.upper() for s in config.TICKERS]
    else:
        parser.print_help()
        print("\nERROR: No tickers specified. Use --ticker, --tickers, "
              "set TICKERS in config.py, or use --input-format / --input-file.",
              file=sys.stderr)
        sys.exit(1)

    if not symbols:
        _die("Ticker list is empty after reading input.")

    # ── resolve: date range ───────────────────────────────────────────────────
    period    = args.period    or config.PERIOD
    start_str = args.start     or config.START_DATE
    end_str   = args.end       or config.END_DATE
    start, end = _resolve_dates(period, start_str, end_str)

    # ── resolve: columns ──────────────────────────────────────────────────────
    columns = args.columns or config.COLUMNS

    # ── resolve: output ───────────────────────────────────────────────────────
    formats = _validate_formats(list(args.output or config.OUTPUT_FORMATS))
    out_dir = args.out_dir or config.OUTPUT_DIR
    workers = args.workers or config.MAX_WORKERS
    date_fmt = config.DATE_FORMAT

    # ── banner ────────────────────────────────────────────────────────────────
    print(f"\n{'═'*60}")
    print(f"  PSX Stock Data Scraper")
    print(f"{'─'*60}")
    print(f"  Ticker(s)  : {', '.join(symbols)}")
    print(f"  Range      : {start}  →  {end}")
    print(f"  Columns    : {', '.join(columns) if columns else 'all'}")
    print(f"  Output     : {', '.join(formats)}")
    if "all" not in formats and any(f in formats for f in ("csv","json","excel")):
        print(f"  Directory  : {out_dir}/")
    print(f"{'═'*60}\n")

    # ── fetch ─────────────────────────────────────────────────────────────────
    results: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        print(f"  ⟳  Fetching {sym} …")
        df = scrape(sym, start, end, max_workers=workers)
        if df.empty:
            print(f"  ⚠  No data for {sym}. Verify the ticker symbol.")
        else:
            df = _filter_columns(df, columns)
            print(f"  ✓  {len(df)} rows · {len(df.columns)} column(s) · {sym}")
            results[sym] = df

    if not results:
        _die("No data retrieved for any ticker. Exiting.")

    # ── output ────────────────────────────────────────────────────────────────
    print()
    for sym, df in results.items():
        _dispatch_output(df, sym, formats, out_dir, date_fmt)

    print(f"\n  Done — {len(results)} ticker(s) processed.\n")


if __name__ == "__main__":
    main()

"""
api.py — FastAPI REST API wrapping the PSX scraper.

Run locally:
    uvicorn api:app --reload --port 8000

Endpoints:
    GET /health
    GET /tickers
    GET /stock/{symbol}?period=1y
    GET /stock/{symbol}?start=2024-01-01&end=2025-05-22
    GET /stocks?symbols=LUCK,OGDC,ENGRO&period=6m
"""

import datetime
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from scraper import (
    scrape,
    scrape_multiple,
    get_all_tickers,
    period_to_dates,
    PERIOD_MAP,
)

# ── App setup ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

app = FastAPI(
    title       = "PSX Stock Data API",
    description = "Scrapes historical OHLCV data from the Pakistan Stock Exchange (dps.psx.com.pk)",
    version     = "1.0.0",
    docs_url    = "/docs",
    redoc_url   = "/redoc",
)

# Allow all origins while in development — lock this down before going public
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _resolve_dates(
    period: Optional[str],
    start:  Optional[str],
    end:    Optional[str],
) -> tuple[datetime.date, datetime.date]:
    """
    Priority: explicit start/end > period > default (1y).
    Raises HTTPException on bad input.
    """
    if start or end:
        if not (start and end):
            raise HTTPException(
                status_code=400,
                detail="Both 'start' and 'end' are required when using custom date range.",
            )
        try:
            return (
                datetime.date.fromisoformat(start),
                datetime.date.fromisoformat(end),
            )
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Dates must be in YYYY-MM-DD format.",
            )

    p = (period or "1y").lower()
    if p not in PERIOD_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown period '{p}'. Valid: {list(PERIOD_MAP)}",
        )
    return period_to_dates(p)


def _df_to_records(df) -> list[dict]:
    """Convert DataFrame to a list of dicts safe for JSON serialisation."""
    if df.empty:
        return []
    df = df.reset_index()
    df["Date"] = df["Date"].astype(str)
    # Round floats to 2dp; keep Volume as int where possible
    for col in df.columns:
        if col == "Date":
            continue
        if col.lower() == "volume":
            df[col] = df[col].fillna(0).astype(int)
        else:
            df[col] = df[col].round(2)
    return df.to_dict(orient="records")


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["meta"])
def health():
    """Liveness check."""
    return {"status": "ok", "timestamp": datetime.datetime.utcnow().isoformat() + "Z"}


@app.get("/tickers", tags=["meta"])
def list_tickers():
    """Return all PSX-listed ticker symbols."""
    df = get_all_tickers()
    if df.empty:
        raise HTTPException(status_code=502, detail="Could not fetch ticker list from PSX.")
    return df.to_dict(orient="records")


@app.get("/stock/{symbol}", tags=["data"])
def get_stock(
    symbol: str,
    period: Optional[str] = Query(None, description=f"Period shorthand: {list(PERIOD_MAP)}"),
    start:  Optional[str] = Query(None, description="Start date YYYY-MM-DD (use with end)"),
    end:    Optional[str] = Query(None, description="End date YYYY-MM-DD (use with start)"),
):
    """
    Fetch historical OHLCV data for a single PSX ticker.

    ### Examples
    - `/stock/LUCK?period=1y`
    - `/stock/OGDC?period=6m`
    - `/stock/ENGRO?start=2024-01-01&end=2025-05-22`
    """
    sym = symbol.strip().upper()
    date_start, date_end = _resolve_dates(period, start, end)

    df = scrape(sym, date_start, date_end)

    if df.empty:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No data found for '{sym}' between {date_start} and {date_end}. "
                "Check the ticker symbol and try again."
            ),
        )

    records = _df_to_records(df)
    return {
        "symbol":     sym,
        "start":      str(date_start),
        "end":        str(date_end),
        "rows":       len(records),
        "data":       records,
    }


@app.get("/stocks", tags=["data"])
def get_multiple_stocks(
    symbols: str = Query(..., description="Comma-separated ticker symbols, e.g. LUCK,OGDC,ENGRO"),
    period:  Optional[str] = Query(None, description=f"Period: {list(PERIOD_MAP)}"),
    start:   Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end:     Optional[str] = Query(None, description="End date YYYY-MM-DD"),
):
    """
    Fetch historical OHLCV data for multiple PSX tickers in one call.

    ### Example
    - `/stocks?symbols=LUCK,OGDC,ENGRO&period=3m`
    """
    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not sym_list:
        raise HTTPException(status_code=400, detail="At least one symbol is required.")
    if len(sym_list) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 symbols per request.")

    date_start, date_end = _resolve_dates(period, start, end)
    results = scrape_multiple(sym_list, date_start, date_end)

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for any of: {sym_list}",
        )

    return {
        "start":   str(date_start),
        "end":     str(date_end),
        "symbols": {
            sym: {
                "rows": len(records := _df_to_records(df)),
                "data": records,
            }
            for sym, df in results.items()
        },
    }

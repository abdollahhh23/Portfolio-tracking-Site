# PSX Stock Data Scraper / API

Fetches historical OHLCV (Open, High, Low, Close, Volume) data
from the Pakistan Stock Exchange data portal (`dps.psx.com.pk`).

## Why the old code broke

The PSX endpoint returns an **HTML table**, not JSON.
The previous `main.py` called `json.loads()` on the HTML response,
which threw `"Failed to decode JSON data from the server"`.
This codebase fixes that by parsing the HTML directly with BeautifulSoup.

---

## Installation

```bash
pip install -r requirements.txt
```

---

## File layout

```
psx_api/
├── scraper.py       # Core scraping logic (HTML → DataFrame)
├── api.py           # FastAPI REST server
├── main.py          # CLI entry point
└── requirements.txt
```

---

## CLI usage

```bash
# Single ticker, 1 year
python main.py --ticker LUCK --period 1y

# Single ticker, custom range, save CSV
python main.py --ticker OGDC --start 2024-01-01 --end 2025-05-22 --output csv

# Multiple tickers, 6 months, save everything
python main.py --tickers LUCK OGDC ENGRO --period 6m --output all

# List all PSX tickers
python main.py --list-tickers

# Debug mode
python main.py --ticker LUCK --period 1m --verbose
```

### Valid periods

| Flag | Duration |
|------|----------|
| `1w` | 1 week   |
| `2w` | 2 weeks  |
| `1m` | 1 month  |
| `3m` | 3 months |
| `6m` | 6 months |
| `1y` | 1 year   |
| `2y` | 2 years  |
| `3y` | 3 years  |
| `5y` | 5 years  |
| `max`| All available (~2000 onward) |

---

## API server usage

```bash
uvicorn api:app --reload --port 8000
```

Then visit **http://localhost:8000/docs** for the interactive Swagger UI.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness check |
| `GET` | `/tickers` | All PSX ticker symbols |
| `GET` | `/stock/{symbol}` | Single ticker OHLCV |
| `GET` | `/stocks` | Multiple tickers OHLCV |

### Query parameters for `/stock/{symbol}` and `/stocks`

| Param | Example | Notes |
|-------|---------|-------|
| `period` | `?period=6m` | Shorthand (see table above) |
| `start` | `?start=2024-01-01` | Use with `end` |
| `end` | `?end=2025-05-22` | Use with `start` |

### Example API calls

```
GET /stock/LUCK?period=1y
GET /stock/OGDC?start=2024-01-01&end=2025-05-22
GET /stocks?symbols=LUCK,OGDC,ENGRO&period=3m
```

### Example JSON response

```json
{
  "symbol": "LUCK",
  "start": "2024-05-23",
  "end": "2025-05-23",
  "rows": 247,
  "data": [
    {
      "Date": "2024-05-23",
      "Open": 972.50,
      "High": 985.00,
      "Low": 965.25,
      "Close": 980.00,
      "Volume": 245000
    }
  ]
}
```

---

## How the scraper works

1. Converts the requested date range into a list of (year, month) pairs.
2. Fires parallel POST requests to `dps.psx.com.pk/historical` — one per month.
3. Parses each HTML table response with BeautifulSoup (no JSON involved).
4. Concatenates, deduplicates, and sorts the resulting DataFrames.
5. Returns the final clipped DataFrame or JSON.

Parallelism is controlled by `--workers` (CLI) or `max_workers` in `scraper.scrape()`.
Default is 6 threads per ticker, which gives good speed without hammering PSX.

---

## Going public checklist

Before exposing this API on the internet:

- [ ] Add rate limiting (e.g. `slowapi`)
- [ ] Add auth (API key header or JWT)
- [ ] Lock down CORS origins in `api.py`
- [ ] Add a caching layer (Redis / in-memory TTL cache) to avoid re-scraping the same data
- [ ] Add request logging / monitoring
- [ ] Deploy behind a reverse proxy (nginx/caddy) with HTTPS
- [ ] Respect PSX's Terms of Service regarding data redistribution

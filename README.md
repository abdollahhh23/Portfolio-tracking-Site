# PSX Stock Data API

Fetch historical **OHLCV** (Open · High · Low · Close · Volume) data for any
ticker on the Pakistan Stock Exchange — via CLI, Python import, or a live
REST API you can deploy to the internet for free.

---

## Table of contents

1. [Quick start (local)](#1-quick-start-local)
2. [Configuration](#2-configuration)
3. [CLI usage](#3-cli-usage)
4. [REST API](#4-rest-api)
5. [Deploy for free on Render](#5-deploy-for-free-on-render)
6. [Keep it awake with UptimeRobot](#6-keep-it-awake-with-uptimerobot)
7. [Other free platforms](#7-other-free-platforms)
8. [Python module usage](#8-python-module-usage)
9. [Project layout](#9-project-layout)
10. [Data & legal notice](#10-data--legal-notice)

---

## 1. Quick start (local)

```bash
# Clone the repo
git clone https://github.com/your-username/psx-scraper.git
cd psx-scraper

# Install dependencies (Python 3.10+)
pip install -r requirements.txt

# Fetch data straight away — no config needed
python main.py --ticker LUCK --period 1y

# Or run the API server locally
uvicorn api:app --reload --port 8000
# → open http://localhost:8000/docs
```

---

## 2. Configuration

Open **`config.py`** — the single file you need to edit before running.
Every setting is documented inline.

```python
# config.py — the only file you need to touch

TICKERS        = ["LUCK", "OGDC", "ENGRO"]    # stocks to fetch
PERIOD         = "1y"                           # how far back
START_DATE     = None                           # or "2023-01-01"
END_DATE       = None                           # or "2025-05-22"

COLUMNS        = ["Date", "Open", "High", "Low", "Close", "Volume"]

OUTPUT_FORMATS = ["csv", "json"]                # print / csv / json / excel / all
OUTPUT_DIR     = "output"

INPUT_FORMAT   = "args"                         # args / csv / json / txt
INPUT_FILE     = None
```

After editing, just run:

```bash
python main.py
```

CLI flags always override `config.py`.

---

## 3. CLI usage

### Tickers

```bash
python main.py --ticker LUCK                          # single ticker
python main.py --tickers LUCK OGDC ENGRO              # multiple
python main.py --input-format csv --input-file tickers.csv   # from file
python main.py --list-tickers                         # all PSX symbols
```

### Time range

```bash
python main.py --ticker LUCK --period 6m
python main.py --ticker LUCK --start 2024-01-01 --end 2025-05-22
```

| Period flag | Window |
|-------------|--------|
| `1w` | 1 week |
| `2w` | 2 weeks |
| `1m` | 1 month |
| `3m` | 3 months |
| `6m` | 6 months |
| `1y` | 1 year *(default)* |
| `2y` | 2 years |
| `3y` | 3 years |
| `5y` | 5 years |
| `max` | All available (~2000 onward) |

### Output format

```bash
python main.py --ticker LUCK --output print          # terminal table
python main.py --ticker LUCK --output csv            # saves LUCK_psx.csv
python main.py --ticker LUCK --output json           # saves LUCK_psx.json
python main.py --ticker LUCK --output csv json       # both files
python main.py --ticker LUCK --output all            # print + csv + json + excel
python main.py --ticker LUCK --output csv --out-dir ./data
```

### Columns

```bash
python main.py --ticker LUCK --columns Date Close Volume
python main.py --ticker LUCK --columns Date Open High Low Close
```

### Input files

**CSV** — must have a column named `symbol` or `ticker`:
```csv
symbol
LUCK
OGDC
ENGRO
```
```bash
python main.py --input-format csv --input-file tickers.csv --period 6m --output csv
```

**JSON** — a list of strings:
```json
["LUCK", "OGDC", "ENGRO"]
```
```bash
python main.py --input-format json --input-file tickers.json --period 1y --output json
```

**Plain text** — one ticker per line, `#` lines are comments:
```
# Blue-chip
LUCK
OGDC

# Banks
HBL
MCB
```
```bash
python main.py --input-format txt --input-file tickers.txt --period 3m --output csv json
```

---

## 4. REST API

Start the server:

```bash
uvicorn api:app --reload --port 8000
```

Interactive docs at **http://localhost:8000/docs** (Swagger UI).

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Welcome + links |
| `GET` | `/ping` | Keep-alive for uptime monitors → returns `"pong"` |
| `GET` | `/health` | Liveness check with UTC timestamp |
| `GET` | `/tickers` | All PSX-listed symbols |
| `GET` | `/stock/{symbol}` | Single ticker OHLCV |
| `GET` | `/stocks` | Multiple tickers in one call |

### Query parameters

| Param | Example | Notes |
|-------|---------|-------|
| `period` | `?period=6m` | Shorthand period |
| `start` | `?start=2024-01-01` | Use together with `end` |
| `end` | `?end=2025-05-22` | Use together with `start` |

### Example requests

```
GET /stock/LUCK?period=1y
GET /stock/OGDC?start=2024-01-01&end=2025-05-22
GET /stocks?symbols=LUCK,OGDC,ENGRO&period=3m
```

### Example response (`/stock/LUCK?period=1y`)

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
      "Low":  965.25,
      "Close": 980.00,
      "Volume": 245000
    }
  ]
}
```

---

## 5. Deploy for free on Render

**Render** gives you a free HTTPS API with zero configuration and no credit
card required. This is the recommended deployment path.

### Step 1 — Push your code to GitHub

```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/your-username/psx-scraper.git
git push -u origin main
```

### Step 2 — Create a Render Web Service

1. Go to [render.com](https://render.com) and sign up (free, no card).
2. Click **New → Web Service**.
3. Connect your GitHub account and select your repository.
4. Render auto-detects the `Dockerfile`. Confirm these settings:

   | Setting | Value |
   |---------|-------|
   | Environment | Docker |
   | Region | Pick closest to Pakistan (Singapore or Frankfurt) |
   | Instance type | **Free** |
   | Health check path | `/ping` |

5. Click **Deploy**. Wait ~2 minutes.

Your API is now live at:

```
https://psx-api.onrender.com/docs
https://psx-api.onrender.com/stock/LUCK?period=1y
```

### Step 3 — (Optional) Lock down CORS

By default the API allows all origins (`*`). To restrict it to your own
frontend, add an environment variable in Render's dashboard:

```
Key:   ALLOWED_ORIGINS
Value: https://yoursite.com,https://app.yoursite.com
```

No code change needed — `api.py` reads this automatically.

---

## 6. Keep it awake with UptimeRobot

Render's free tier sleeps after **15 minutes of inactivity** (60-second cold
start on the next request). Fix this for free with UptimeRobot:

1. Sign up at [uptimerobot.com](https://uptimerobot.com) (free tier: 50 monitors).
2. Click **Add New Monitor**:

   | Setting | Value |
   |---------|-------|
   | Monitor Type | HTTP(s) |
   | Friendly Name | PSX API |
   | URL | `https://psx-api.onrender.com/ping` |
   | Monitoring Interval | **5 minutes** |

3. Save. UptimeRobot pings `/ping` every 5 minutes — your API stays warm 24/7.

> You also get free downtime email alerts as a bonus.

---

## 7. Other free platforms

| Platform | Free forever | Card needed | Cold starts | Notes |
|----------|:---:|:---:|:---:|-------|
| **Render** ✓ | ✅ | ❌ | ~60 s | Best default choice |
| **Railway** | ⚠️ trial credit | ❌ | None | Credit runs out; needs card after |
| **Fly.io** | ✅ | ✅ | None | Best performance; card required |
| **PythonAnywhere** | ✅ | ❌ | None | Blocks outbound HTTP — won't work |

### Running with Docker locally

```bash
docker build -t psx-api .
docker run -p 8000:8000 psx-api
# → http://localhost:8000/docs
```

---

## 8. Python module usage

`scraper.py` is importable — no CLI or server needed:

```python
import datetime
from scraper import scrape, scrape_multiple, period_to_dates

# Single ticker
df = scrape("LUCK", datetime.date(2024, 1, 1), datetime.date(2025, 5, 22))
print(df.head())

# Period shorthand
start, end = period_to_dates("6m")
df = scrape("OGDC", start, end)

# Multiple tickers → dict of DataFrames
results = scrape_multiple(
    ["LUCK", "OGDC", "ENGRO"],
    datetime.date(2024, 1, 1),
    datetime.date(2025, 5, 22),
)
for symbol, df in results.items():
    print(symbol, df.shape)
```

---

## 9. Project layout

```
psx-scraper/
├── config.py          ← EDIT THIS — all settings live here
├── main.py            ← CLI entry point
├── scraper.py         ← core scraping engine (importable)
├── api.py             ← FastAPI REST server
├── Dockerfile         ← container definition (Render / Railway / Fly.io)
├── .dockerignore
├── .gitignore
├── requirements.txt
├── README.md
└── output/            ← generated files land here (auto-created, git-ignored)
```

---

## 10. Data & legal notice

Historical market data is sourced live from
[dps.psx.com.pk](https://dps.psx.com.pk), which is operated by
**Pakistan Stock Exchange Limited (PSX)** and **CS Solutions (Pvt.) Ltd**.

- This project is open-source and provided for **educational and
  non-commercial use**.
- PSX data is the intellectual property of PSX / CS Solutions. Redistribution
  or commercial use of the data may require a licence from PSX's Market Data
  Team: **marketdatarequest@psx.com.pk**.
- This software is licensed under the **MIT License** — see `LICENSE`.

---

## Common PSX tickers

| Symbol | Company |
|--------|---------|
| LUCK | Lucky Cement |
| OGDC | Oil & Gas Development Co. |
| ENGRO | Engro Corporation |
| HBL | Habib Bank Limited |
| PSO | Pakistan State Oil |
| MARI | Mari Petroleum |
| MCB | MCB Bank |
| UBL | United Bank Limited |
| HUBC | Hub Power Company |
| EFERT | Engro Fertilizers |

Run `python main.py --list-tickers` to see every listed symbol.

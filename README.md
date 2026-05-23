# PSX Stock Data Scraper

Download historical stock data from the Pakistan Stock Exchange directly to your computer — as a CSV, JSON, or Excel file.

---

## What it does

You give it a ticker symbol (like `LUCK` or `OGDC`) and a time range, and it downloads that stock's daily **Open, High, Low, Close, and Volume** data and saves it to a file on your computer.

---

## Requirements

- Python 3.10 or newer — download from [python.org](https://www.python.org/downloads/)
- An internet connection

That's it. All other dependencies are installed automatically on first run.

---

## The easiest way to run it — `run.sh`

Double-click `run.sh`, or open a terminal in the project folder and type:

```bash
bash run.sh
```

It will ask you three questions — one at a time:

```
Step 1 of 3 — Ticker
  Enter one or more PSX ticker symbols separated by spaces.
  Ticker(s): LUCK

Step 2 of 3 — Time Range
  [1]  1 week
  [2]  1 month
  [3]  3 months
  [4]  6 months
  [5]  1 year       (default)
  [6]  2 years
  [7]  5 years
  [8]  All available data (from ~2000)
  [9]  Custom date range
  Choice [1-9]: 5

Step 3 of 3 — Output Format
  [1]  Print to terminal   (default)
  [2]  Save as CSV
  [3]  Save as JSON
  [4]  Save as Excel (.xlsx)
  [5]  CSV + JSON
  [6]  All formats
  Choice [1-6]: 2
```

Done. Your file appears in the `output/` folder.

> **Windows users:** If double-clicking doesn't work, right-click `run.sh` → "Open with" → Git Bash. Or just use the command line examples below.

---

## Running from the command line

If you prefer to skip the prompts and run it directly:

### Get data for one stock

```bash
python3 main.py --ticker LUCK --period 1y
```

### Get data for multiple stocks at once

```bash
python3 main.py --tickers LUCK OGDC ENGRO --period 6m
```

### Use a custom date range instead of a period

```bash
python3 main.py --ticker LUCK --start 2024-01-01 --end 2025-05-22
```

### Choose your output format

```bash
# Print to terminal (default — no file saved)
python3 main.py --ticker LUCK --period 1y --output print

# Save as CSV
python3 main.py --ticker LUCK --period 1y --output csv

# Save as JSON
python3 main.py --ticker LUCK --period 1y --output json

# Save as Excel
python3 main.py --ticker LUCK --period 1y --output excel

# Save as both CSV and JSON
python3 main.py --ticker LUCK --period 1y --output csv json

# Save everything (print + CSV + JSON + Excel)
python3 main.py --ticker LUCK --period 1y --output all
```

### See all available PSX tickers

```bash
python3 main.py --list-tickers
```

---

## Use cases

### I want the last year of data for one stock, saved as a spreadsheet

```bash
python3 main.py --ticker LUCK --period 1y --output excel
```

Opens as `output/LUCK_psx.xlsx` in Excel or Google Sheets.

---

### I want to compare multiple stocks over 6 months

```bash
python3 main.py --tickers LUCK OGDC ENGRO HBL --period 6m --output csv
```

Saves a separate CSV for each ticker: `LUCK_psx.csv`, `OGDC_psx.csv`, etc.

---

### I want data for a specific date range (e.g. before and after an event)

```bash
python3 main.py --ticker PSO --start 2024-03-01 --end 2024-09-30 --output csv
```

---

### I want to quickly glance at recent prices without saving a file

```bash
python3 main.py --ticker MARI --period 1m --output print
```

Prints a table directly in the terminal.

---

### I want everything — all formats, multiple years

```bash
python3 main.py --ticker ENGRO --period 5y --output all
```

Saves `ENGRO_psx.csv`, `ENGRO_psx.json`, `ENGRO_psx.xlsx` and also prints to terminal.

---

### I don't know the ticker symbol for a company

```bash
python3 main.py --list-tickers
```

Prints every symbol listed on PSX. Find your company, note the symbol, then run your query.

---

## Output files

All saved files go into the `output/` folder inside the project directory. It's created automatically if it doesn't exist.

| Format | Filename | Opens with |
|--------|----------|------------|
| CSV | `SYMBOL_psx.csv` | Excel, Google Sheets, pandas |
| JSON | `SYMBOL_psx.json` | Any text editor, Python, JavaScript |
| Excel | `SYMBOL_psx.xlsx` | Excel, Google Sheets, LibreOffice |

---

## Valid period values

| Flag | Data window |
|------|-------------|
| `1w` | Last 1 week |
| `2w` | Last 2 weeks |
| `1m` | Last 1 month |
| `3m` | Last 3 months |
| `6m` | Last 6 months |
| `1y` | Last 1 year *(default)* |
| `2y` | Last 2 years |
| `3y` | Last 3 years |
| `5y` | Last 5 years |
| `max` | All data from ~2000 onward |

---

## Common ticker symbols

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

Run `python3 main.py --list-tickers` for the full list.

---

## Project files

```
psx-scraper/
├── run.sh           ← run this to start (interactive, one click)
├── main.py          ← the script (use directly from command line)
├── scraper.py       ← handles all the data fetching (don't edit)
├── requirements.txt ← Python dependencies
├── README.md
└── output/          ← your downloaded files appear here
```

---

## License

MIT — free to use, modify, and share.  
Data sourced from [dps.psx.com.pk](https://dps.psx.com.pk) — for educational and non-commercial use.
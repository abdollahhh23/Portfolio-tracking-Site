# =============================================================================
#  config.py  —  PSX Scraper · Central Configuration
#  ============================================================================
#
#  THIS IS THE ONLY FILE YOU NEED TO EDIT.
#
#  Fork this repo, open this file, fill in your preferences below, then run:
#
#      python main.py                  ← uses every setting defined here
#      python main.py --ticker ENGRO   ← overrides just the ticker at runtime
#
#  Every setting here can also be overridden from the command line.
#  CLI flags always win over config.py values.
#
# =============================================================================


# ─────────────────────────────────────────────────────────────────────────────
#  1.  TICKERS
#      Which PSX symbols to fetch.
#      • Single ticker  →  TICKERS = ["LUCK"]
#      • Multiple       →  TICKERS = ["LUCK", "OGDC", "ENGRO", "HBL"]
#      • Leave empty    →  [] means the CLI --ticker / --tickers flag is required
#
#  Common PSX tickers for reference:
#      LUCK   – Lucky Cement          OGDC  – Oil & Gas Dev. Co.
#      ENGRO  – Engro Corporation     HBL   – Habib Bank Limited
#      PSO    – Pakistan State Oil     MARI  – Mari Petroleum
#      MCB    – MCB Bank               UBL   – United Bank Limited
#      HUBC   – Hub Power Company      EFERT – Engro Fertilizers
# ─────────────────────────────────────────────────────────────────────────────
TICKERS: list[str] = ["LUCK"]


# ─────────────────────────────────────────────────────────────────────────────
#  2.  TIME RANGE
#      Option A — use a shorthand period (recommended for most users):
#
#          PERIOD = "1y"    # last 1 year   (default)
#
#      Option B — use explicit start/end dates (overrides PERIOD):
#
#          START_DATE = "2023-01-01"
#          END_DATE   = "2025-05-22"
#
#      Set START_DATE / END_DATE to None to use PERIOD instead.
#
#  Valid period strings:
#      "1w"   1 week        "6m"   6 months
#      "2w"   2 weeks       "1y"   1 year   ← default
#      "1m"   1 month       "2y"   2 years
#      "3m"   3 months      "3y"   3 years
#                           "5y"   5 years
#                           "max"  all data (from ~2000-01-01)
# ─────────────────────────────────────────────────────────────────────────────
PERIOD: str             = "1y"
START_DATE: str | None  = None      # e.g. "2023-01-01"  or  None
END_DATE:   str | None  = None      # e.g. "2025-05-22"  or  None


# ─────────────────────────────────────────────────────────────────────────────
#  3.  COLUMNS  (what to include in the output)
#      PSX provides: Date, Open, High, Low, Close, Volume
#
#      List only the columns you want. Order is preserved.
#      Always include "Date" — it is the row index.
#
#      Examples:
#          COLUMNS = ["Date", "Close", "Volume"]       # close + volume only
#          COLUMNS = ["Date", "Open", "High", "Low", "Close", "Volume"]  # all
# ─────────────────────────────────────────────────────────────────────────────
COLUMNS: list[str] = ["Date", "Open", "High", "Low", "Close", "Volume"]


# ─────────────────────────────────────────────────────────────────────────────
#  4.  OUTPUT FORMAT
#      What to do with the data once fetched.
#
#      "print"   → pretty-print a table to the terminal
#      "csv"     → save  <TICKER>_psx.csv
#      "json"    → save  <TICKER>_psx.json
#      "excel"   → save  <TICKER>_psx.xlsx
#      "all"     → do all four of the above
#
#      You can also combine specific formats:
#          OUTPUT_FORMATS = ["csv", "json"]   # save both but don't print
#          OUTPUT_FORMATS = ["print", "csv"]  # print and also save CSV
# ─────────────────────────────────────────────────────────────────────────────
OUTPUT_FORMATS: list[str] = ["print", "csv"]


# ─────────────────────────────────────────────────────────────────────────────
#  5.  INPUT FORMAT  (for programmatic / pipeline use)
#      When another script feeds tickers into this scraper, set this to
#      tell main.py how to read them.
#
#      "args"    → tickers come from CLI flags (default, most common)
#      "csv"     → read tickers from a CSV file  (see INPUT_FILE below)
#      "json"    → read tickers from a JSON file (see INPUT_FILE below)
#      "txt"     → read tickers from a plain text file, one per line
#
#  INPUT_FILE:
#      Path to the file when INPUT_FORMAT is "csv", "json", or "txt".
#      CSV  → must have a column named "symbol" or "ticker"
#      JSON → must be a list of strings, e.g. ["LUCK", "OGDC"]
#      TXT  → one ticker per line, blank lines and # comments ignored
# ─────────────────────────────────────────────────────────────────────────────
INPUT_FORMAT: str       = "args"
INPUT_FILE:   str | None = None     # e.g. "tickers.csv"  or  "tickers.json"


# ─────────────────────────────────────────────────────────────────────────────
#  6.  OUTPUT DIRECTORY
#      Where CSV / JSON / Excel files are saved.
#      Use "." for the current directory, or provide any relative/absolute path.
#      The directory is created automatically if it doesn't exist.
# ─────────────────────────────────────────────────────────────────────────────
OUTPUT_DIR: str = "output"


# ─────────────────────────────────────────────────────────────────────────────
#  7.  PERFORMANCE
#      MAX_WORKERS — parallel HTTP threads used per ticker.
#      Higher = faster for long date ranges, but be respectful to PSX servers.
#      Recommended: 4–8. Do not exceed 12.
# ─────────────────────────────────────────────────────────────────────────────
MAX_WORKERS: int = 6


# ─────────────────────────────────────────────────────────────────────────────
#  8.  MISC
#      VERBOSE — set True to print detailed debug logs (useful for dev/testing)
#      DATE_FORMAT — how dates appear in CSV/JSON output
#          "%Y-%m-%d"   →  2025-05-22   (ISO 8601, recommended)
#          "%d/%m/%Y"   →  22/05/2025
#          "%d-%b-%Y"   →  22-May-2025
# ─────────────────────────────────────────────────────────────────────────────
VERBOSE:     bool = False
DATE_FORMAT: str  = "%Y-%m-%d"

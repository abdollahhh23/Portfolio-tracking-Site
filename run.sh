#!/usr/bin/env bash
# =============================================================================
#  run.sh  —  PSX Stock Data Scraper
#  Double-click this file or run:  bash run.sh
# =============================================================================

set -e

# ── colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

print_header() {
  echo ""
  echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════╗${RESET}"
  echo -e "${CYAN}${BOLD}║       PSX Stock Data Scraper             ║${RESET}"
  echo -e "${CYAN}${BOLD}║       Pakistan Stock Exchange            ║${RESET}"
  echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════╝${RESET}"
  echo ""
}

print_header

# ── check Python ──────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  echo -e "${RED}ERROR: Python 3 is not installed or not in PATH.${RESET}"
  echo "  Download it from https://www.python.org/downloads/"
  exit 1
fi

# ── install dependencies if needed ───────────────────────────────────────────
echo -e "${YELLOW}Checking dependencies...${RESET}"
python3 -c "import requests, bs4, pandas, dateutil" 2>/dev/null || {
  echo -e "${YELLOW}Installing required packages...${RESET}"
  pip install -r requirements.txt --quiet
  echo -e "${GREEN}Done.${RESET}"
}
echo ""

# ── ticker ────────────────────────────────────────────────────────────────────
echo -e "${BOLD}Step 1 of 3 — Ticker${RESET}"
echo "  Enter one or more PSX ticker symbols separated by spaces."
echo "  Examples: LUCK   |   OGDC   |   LUCK OGDC ENGRO HBL"
echo "  (Leave blank and press Enter to see all available tickers)"
echo ""
read -rp "  Ticker(s): " TICKER_INPUT

if [[ -z "$TICKER_INPUT" ]]; then
  echo ""
  echo -e "${YELLOW}Fetching all available PSX tickers...${RESET}"
  python3 main.py --list-tickers
  echo ""
  read -rp "  Now enter ticker(s): " TICKER_INPUT
  if [[ -z "$TICKER_INPUT" ]]; then
    echo -e "${RED}No ticker entered. Exiting.${RESET}"
    exit 1
  fi
fi

# ── period ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}Step 2 of 3 — Time Range${RESET}"
echo "  Choose how much historical data you want:"
echo ""
echo "    [1]  1 week"
echo "    [2]  1 month"
echo "    [3]  3 months"
echo "    [4]  6 months"
echo "    [5]  1 year       (default)"
echo "    [6]  2 years"
echo "    [7]  5 years"
echo "    [8]  All available data (from ~2000)"
echo "    [9]  Custom date range"
echo ""
read -rp "  Choice [1-9] (press Enter for 1 year): " PERIOD_CHOICE

case "$PERIOD_CHOICE" in
  1) PERIOD_ARG="--period 1w" ;;
  2) PERIOD_ARG="--period 1m" ;;
  3) PERIOD_ARG="--period 3m" ;;
  4) PERIOD_ARG="--period 6m" ;;
  5|"") PERIOD_ARG="--period 1y" ;;
  6) PERIOD_ARG="--period 2y" ;;
  7) PERIOD_ARG="--period 5y" ;;
  8) PERIOD_ARG="--period max" ;;
  9)
    echo ""
    read -rp "  Start date (YYYY-MM-DD): " START_DATE
    read -rp "  End date   (YYYY-MM-DD): " END_DATE
    if [[ -z "$START_DATE" || -z "$END_DATE" ]]; then
      echo -e "${RED}Both start and end dates are required. Exiting.${RESET}"
      exit 1
    fi
    PERIOD_ARG="--start $START_DATE --end $END_DATE"
    ;;
  *)
    echo -e "${YELLOW}Unrecognised choice — defaulting to 1 year.${RESET}"
    PERIOD_ARG="--period 1y"
    ;;
esac

# ── output format ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}Step 3 of 3 — Output Format${RESET}"
echo "  How do you want the data?"
echo ""
echo "    [1]  Print to terminal                     (default)"
echo "    [2]  Save as CSV"
echo "    [3]  Save as JSON"
echo "    [4]  Save as Excel (.xlsx)"
echo "    [5]  CSV + JSON"
echo "    [6]  All formats  (print + CSV + JSON + Excel)"
echo ""
read -rp "  Choice [1-6] (press Enter to print): " FORMAT_CHOICE

case "$FORMAT_CHOICE" in
  1|"") FORMAT_ARG="--output print" ;;
  2)    FORMAT_ARG="--output csv" ;;
  3)    FORMAT_ARG="--output json" ;;
  4)    FORMAT_ARG="--output excel" ;;
  5)    FORMAT_ARG="--output csv json" ;;
  6)    FORMAT_ARG="--output all" ;;
  *)
    echo -e "${YELLOW}Unrecognised choice — defaulting to print.${RESET}"
    FORMAT_ARG="--output print"
    ;;
esac

# ── build ticker args ─────────────────────────────────────────────────────────
read -ra TICKERS <<< "$TICKER_INPUT"
if [[ ${#TICKERS[@]} -eq 1 ]]; then
  TICKER_ARG="--ticker ${TICKERS[0]}"
else
  TICKER_ARG="--tickers ${TICKERS[*]}"
fi

# ── run ───────────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${YELLOW}Fetching data...${RESET}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""

python3 main.py $TICKER_ARG $PERIOD_ARG $FORMAT_ARG

echo ""
echo -e "${GREEN}${BOLD}Done!${RESET}"

# ── output location reminder ──────────────────────────────────────────────────
if [[ "$FORMAT_ARG" != *"print"* ]] || [[ "$FORMAT_ARG" == *"all"* ]]; then
  echo -e "  Files saved to: ${BOLD}./output/${RESET}"
fi

echo ""
read -rp "Press Enter to exit..." _

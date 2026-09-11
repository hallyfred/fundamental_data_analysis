import os
from pathlib import Path

from dotenv import load_dotenv

# Resolve the absolute project root.
# '__file__' points to this config module.
# The first parent is the config directory.
# The second parent is the project root.
PROJECT_ROOT = Path(__file__).parent.parent


ENV_FILE = PROJECT_ROOT / ".env"


# Load only the project-specific environment file.
load_dotenv(dotenv_path=ENV_FILE)


BASE_URL = "https://www.alphavantage.co/query"
TIMEOUT = 30
BATCH_SIZE = 5
API_LIMIT_PER_DAY = 25
REQUESTS_PER_TICKER_DAY = 5

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
BUCKET_BRONZE = os.getenv("BUCKET_BRONZE", "")

# API budget strategy documented in the README:
# The Alpha Vantage free tier allows 25 requests per day.
# Five endpoints allow at most five companies per daily run.
# The 35-company pool is split into seven groups of five.
# The deterministic weekly cycle repeats without random rotation.
WEEKDAY_SYMBOLS = {
    0: ["AAPL", "MSFT", "GOOGL", "AMZN", "META"],
    1: ["JPM", "JNJ", "WMT", "XOM", "NVDA"],
    2: ["INTC", "AMD", "NFLX", "PFE", "COST"],
    3: ["KO", "PG", "UNH", "HD", "V"],
    4: ["DIS", "CRM", "IBM", "NKE", "MCD"],
    5: ["T", "CVX", "XLE", "ABBV", "MRK"],
    6: ["BA", "CAT", "GE", "C", "GS"],
}


SYMBOLS = [symbol for group in WEEKDAY_SYMBOLS.values() for symbol in group]
ENDPOINTS_API = {
    "balance_sheet": "BALANCE_SHEET",
    "income_statement": "INCOME_STATEMENT",
    "cash_flow": "CASH_FLOW",
    "earnings": "EARNINGS",
    "overview": "OVERVIEW",
}


def build_ticker_batches(symbols=None, batch_size: int = BATCH_SIZE):
    ordered_symbols = list(symbols or SYMBOLS)
    return [ordered_symbols[index : index + batch_size] for index in range(0, len(ordered_symbols), batch_size)]


def enumerate_ticker_batches(symbols=None, batch_size: int = BATCH_SIZE):
    ordered_symbols = list(symbols or SYMBOLS)
    return list(enumerate(build_ticker_batches(ordered_symbols, batch_size=batch_size)))


def get_symbols_for_day(day_index: int):
    weekday = day_index % 7
    return WEEKDAY_SYMBOLS.get(weekday, [])


def get_batch_for_day(day_index: int, symbols=None, batch_size: int = BATCH_SIZE):
    if symbols is None:
        return get_symbols_for_day(day_index)

    batches = build_ticker_batches(symbols=symbols, batch_size=batch_size)
    if not batches:
        return []
    return batches[day_index % len(batches)]

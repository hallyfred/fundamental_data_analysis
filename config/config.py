import os
from pathlib import Path

from dotenv import load_dotenv

# 1. Encontra o caminho absoluto da pasta raiz do projeto
# '__file__' é este próprio arquivo (config.py)
# '.parent' sobe para a pasta 'config'
# '.parent' de novo sobe para a pasta raiz ('fundamental_data_analysis')
CAMINHO_RAIZ = Path(__file__).parent.parent


caminho_env = CAMINHO_RAIZ / ".env"


# 3. Força o load_dotenv a ler ESSE arquivo específico
load_dotenv(dotenv_path=caminho_env)


BASE_URL = "https://www.alphavantage.co/query"
TIMEOUT = 30
BATCH_SIZE = 5
API_LIMIT_PER_DAY = 25
REQUESTS_PER_TICKER_DAY = 5

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
BUCKET_BRONZE = os.getenv("BUCKET_BRONZE", "")

# Estratégia exata do README:
# Alpha Vantage free tier aceita 25 requisições/dia.
# Para 5 endpoints, cada dia só pode processar 5 empresas.
# Temos 35 empresas em 7 grupos de 5, um grupo por dia da semana.
# O mesmo ciclo se repete mensalmente, sem necessidade de rotação aleatória.
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

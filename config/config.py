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

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
PROJECT_ID  = os.getenv("GCP_PROJECT_ID", "")
BUCKET_BRONZE = os.getenv("BUCKET_BRONZE", "")

#SYMBOLS = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "JPM", "JNJ", "WMT", "XOM", "NVDA"]


SYMBOLS = ["AAPL"]

ENDPOINTS_API = {
    "balance_sheet": "BALANCE_SHEET",
    "income_statement": "INCOME_STATEMENT",
    "cash_flow": "CASH_FLOW",
    "earnings": "EARNINGS",
    "overview": "OVERVIEW"
}
from datetime import date
import json
import requests
from extract.cash_flow import extract_cash_flow
from extract.overview import extract_overview
from src.extract.api_client import AlphaVantageAPIClient

from config.config import BASE_URL, ALPHA_VANTAGE_API_KEY, SYMBOLS

def extract_balance_sheet():
    print('Extracting balance sheet data for symbols...')
    function = "BALANCE_SHEET"

    files_generated = []

    client = AlphaVantageAPIClient(BASE_URL, ALPHA_VANTAGE_API_KEY)

    for symbol in SYMBOLS:
        try:
            files = client.get(function, symbol)

            file_name = f"balance_sheet_{symbol}_{date.today()}.json"

            if not files:
                raise ValueError(f"No data returned for symbol {symbol}")

            with open(file_name, 'w') as f:
                json.dump(files, f)

            files_generated.append(file_name)
            print(f"Balance sheet data for {symbol} saved to {file_name}")
        except Exception as e:
            print(f"Error occurred while extracting balance sheet data for {symbol}: {e}")

    return files_generated

if __name__ == "__main__":
    extract_balance_sheet()
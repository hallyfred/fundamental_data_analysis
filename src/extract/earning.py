from datetime import date
import json
import requests
from extract.overview import extract_overview
from src.extract.api_client import AlphaVantageAPIClient

from config.config import BASE_URL, ALPHA_VANTAGE_API_KEY, SYMBOLS

def extract_earnings():
    print('Extracting earnings data for symbols...')
    function = "earnings"

    files_generated = []

    client = AlphaVantageAPIClient(BASE_URL, ALPHA_VANTAGE_API_KEY)

    for symbol in SYMBOLS:
        try:
            files = client.get(function, symbol)

            file_name = f"earnings_{symbol}_{date.today()}.json"

            if not files:
                raise ValueError(f"No data returned for symbol {symbol}")

            with open(file_name, 'w') as f:
                json.dump(files, f)

            files_generated.append(file_name)
            print(f"Earnings data for {symbol} saved to {file_name}")
        except Exception as e:
            print(f"Error occurred while extracting earnings data for {symbol}: {e}")

    return files_generated

if __name__ == "__main__":
    extract_earnings()
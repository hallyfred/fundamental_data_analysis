from datetime import date
import json
import requests
from extract.overview import extract_overview
from src.extract.api_client import AlphaVantageAPIClient

from config.config import BASE_URL, ALPHA_VANTAGE_API_KEY, SYMBOLS

def extract_income_statement():
    print('Extracting income statement data for symbols...')
    function = "INCOME_STATEMENT"

    files_generated = []

    client = AlphaVantageAPIClient(BASE_URL, ALPHA_VANTAGE_API_KEY)

    for symbol in SYMBOLS:
        try:
            files = client.get(function, symbol)

            file_name = f"income_statement_{symbol}_{date.today()}.json"

            if not files:
                raise ValueError(f"No data returned for symbol {symbol}")

            with open(file_name, 'w') as f:
                json.dump(files, f)

            files_generated.append(file_name)
            print(f"Income statement data for {symbol} saved to {file_name}")

        except ValueError as e:
            print(f"Value error for {symbol}: {e}")
            print(f"Error occurred while extracting income statement data for {symbol}: {e}")
            break  # Exit the loop if a ValueError occurs for a symbol
            
        except Exception as e:
            print(f"Error occurred while extracting income statement data for {symbol}: {e}")

    return files_generated

if __name__ == "__main__":
    extract_income_statement()
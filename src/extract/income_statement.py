from datetime import date
import json
import os
import requests
from src.extract.api_client import AlphaVantageAPIClient

from src.load.loader import GCPSLoader
from config.config import BASE_URL, ALPHA_VANTAGE_API_KEY, SYMBOLS, PROJECT_ID, BUCKET_BRONZE

def extract_income_statement():
    print('Extracting income statement data for symbols...')
    function = "INCOME_STATEMENT"

    today = date.today()
    files_generated = []

    gcp_loader = GCPSLoader(project_id=PROJECT_ID, bucket_name=BUCKET_BRONZE)
    client = AlphaVantageAPIClient(BASE_URL, ALPHA_VANTAGE_API_KEY)

    for symbol in SYMBOLS:
        try:
            files = client.get(function, symbol)


            file_name = f"income_statement_{symbol}_{today}.json"

            if not files:
                
                raise ValueError(f"No data returned for symbol {symbol}")


            with open(file_name, 'w') as f:
                json.dump(files, f)

            # Upload the generated file to GCP


            destination_blob_name = f"financial/income_statement/year={today.year}/month={today.month:02d}/day={today.day:02d}/{file_name}"
            files_to_upload = gcp_loader.upload_file(file_name, destination_blob_name)

            if files_to_upload:
                os.remove(file_name)  # Remove the local file after successful upload
                print(f"Uploaded {file_name} to GCP bucket and removed local file.")

            files_generated.append(destination_blob_name)    

        except ValueError as e:
            print(f"Value error for {symbol}: {e}")

            break # Exit the loop if a ValueError occurs for a symbol

        except Exception as e:
            print(f"Error occurred while extracting income statement data for {symbol}: {e}")

    return files_generated

if __name__ == "__main__":
    extract_income_statement()
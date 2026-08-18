from datetime import date 
import time
import json
import os
from src.extract.api_client import AlphaVantageAPIClient
from src.utils.logger import setup_logger, log_extraction, upload_and_clean_log
from src.utils.helpers import count_real_rows
from src.load.loader import GCPSLoader
from config.config import BASE_URL, ALPHA_VANTAGE_API_KEY, SYMBOLS, PROJECT_ID, BUCKET_BRONZE

def extract_overview():
    logger = setup_logger()
    print( "Extracting overview data for symbols...")
    function = "overview"

    today = date.today()
    files_generated = []

    gcp_loader = GCPSLoader(project_id=PROJECT_ID, bucket_name=BUCKET_BRONZE)
    client = AlphaVantageAPIClient(BASE_URL, ALPHA_VANTAGE_API_KEY)

    for symbol in SYMBOLS:

        length = 0
        file_size_mb = 0.0

        start_time = time.perf_counter() #start the timer

        try:
            files = client.get(function, symbol)

            file_name = f"overview_{symbol}_{today}.json"

            if not files:
                length = 0
                raise ValueError(f"No data returned for symbol {symbol}")

            with open(file_name, 'w') as f:
                json.dump(files, f)

            # Get the size of the file in MB
            file_size_mb = os.path.getsize(file_name) / (1024 * 1024) 
            print(f"File {file_name} created with size: {file_size_mb:.4f} MB.")

            # Count the number of real rows in the JSON data
            length = count_real_rows(files)
            print(f"Number of real rows for {symbol}: {length}")

            # Upload the generated file to GCP

            destination_blob_name = f"financial/overview/year={today.year}/month={today.month:02d}/day={today.day:02d}/{file_name}"
            files_to_upload = gcp_loader.upload_file(file_name, destination_blob_name)

            if files_to_upload:
                os.remove(file_name)  # Remove the local file after successful upload
                print(f"Uploaded {file_name} to GCP bucket and removed local file.")

            files_generated.append(destination_blob_name)

            # Calculate the time taken for the extraction and saving process
            time_seconds = time.perf_counter() - start_time
            print(f"Time taken to extract and save data for {symbol}: {time_seconds:.2f} seconds.")    

            log_extraction(
                logger=logger,
                status="SUCCESS",
                stage_location_bucket=BUCKET_BRONZE,
                last_updated=today.isoformat(),
                endpoint=function,
                symbol=symbol,
                rows=length,
                size=round(file_size_mb, 6),
                time_seconds=round(time_seconds, 3),
                error_message=None
            )

        except ValueError as e:
            time_seconds = time.perf_counter() - start_time
            print(f"Value error for {symbol}: {e}")

            log_extraction(
                logger=logger,
                status="ERROR",
                stage_location_bucket=BUCKET_BRONZE,
                last_updated=today.isoformat(),
                endpoint=function,
                symbol=symbol,
                rows=length,
                size=round(file_size_mb, 6),
                time_seconds=round(time_seconds, 3),
                error_message=e
            )

            break # Exit the loop if a ValueError occurs for a symbol

        except Exception as e:
            time_seconds = time.perf_counter() - start_time
            print(f"Error occurred while extracting overview data for {symbol}: {e}")

            # LOG THE GENERIC ERROR 
            log_extraction(
                logger=logger,
                status="ERROR",
                stage_location_bucket=BUCKET_BRONZE,
                last_updated=today.isoformat(),
                endpoint=function,
                symbol=symbol,
                rows=length,
                size=round(file_size_mb, 6),
                time_seconds=round(time_seconds, 3),
                error_message=e
            )

    #Releases the Python process log file.
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    log_destination = f"financial/overview/metadata/year={today.year}/month={today.month:02d}/day={today.day:02d}/overview_extraction.log"
    upload_and_clean_log(gcp_loader, 'extraction.log', log_destination)

    return files_generated

if __name__ == "__main__":
    extract_overview()
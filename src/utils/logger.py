import logging
import json
from datetime import datetime, timezone
import os


def setup_logger(file_name='extraction.log'):
    "setting up a basic file log"
    logger = logging.getLogger('extraction_logger')
    logger.setLevel(logging.INFO)

    # Avoid the duplication of log messages if the logger is already set up
    if not logger.handlers:
        handler = logging.FileHandler(file_name, encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(handler)

    return logger

def log_extraction(logger, status, stage_location_bucket,last_updated, endpoint, symbol, rows=0, size=0.0, time_seconds=0.0, error_message=None):
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "stage_location_bucket": stage_location_bucket,
        "last_updated": last_updated,
        "endpoint": endpoint,
        "symbol": symbol,
        "rows_processed": rows,
        "size_mb": size,
        "time_seconds": time_seconds,
        "error_message": str(error_message) if error_message else None
    }

    #transform the dictionary into a JSON string object and log it
    logger.info(json.dumps(log_entry))


def upload_and_clean_log(gcp_loader, local_log_file, destination_log_path):
    """
    Uploads the local log file to GCP and removes it from the local machine.
    """
    if os.path.exists(local_log_file):
        log_uploaded = gcp_loader.upload_file(local_log_file, destination_log_path)
        
    if log_uploaded:
            os.remove(local_log_file)
    print(f"Log successfully uploaded to {destination_log_path} and removed locally.")







 
import os as _os
import sys

sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
import json
import os
import tempfile
import time
from datetime import date

from pydantic import ValidationError

from config.config import ALPHA_VANTAGE_API_KEY, BASE_URL, BUCKET_BRONZE, ENDPOINTS_API, PROJECT_ID, get_symbols_for_day
from src.extract.api_client import AlphaVantageAPIClient, AlphaVantageRateLimitError
from src.extract.batch import ExtractionBatch
from src.extract.contract import BalanceSheetSchema, has_extra_fields
from src.load.loader import GCPSLoader
from src.utils.helpers import count_real_rows
from src.utils.logger import log_batch_summary, log_extraction, setup_logger, upload_and_clean_log
from src.utils.watermark import WatermarkManager


def extract_balance_sheet(symbols: list[str] | None = None, run_id: str | None = None):
    logger = setup_logger()
    logger.run_id = run_id
    function = ENDPOINTS_API["balance_sheet"]
    today = date.today()

    if symbols is None:
        symbols = get_symbols_for_day(today.weekday())

    logger.info(f"Starting extraction for balance_sheet for {len(symbols)} symbols: {symbols}")
    files_generated = []
    batch = ExtractionBatch(endpoint=function, symbols=list(symbols), run_id=run_id)

    gcp_loader = GCPSLoader(project_id=PROJECT_ID, bucket_name=BUCKET_BRONZE)
    watermark = WatermarkManager(gcp_loader=gcp_loader, endpoint="balance_sheet")
    client = AlphaVantageAPIClient(BASE_URL, ALPHA_VANTAGE_API_KEY, max_retries=1)

    for symbol in symbols:
        length = 0
        file_size_mb = 0.0
        file_path = None

        start_time = time.perf_counter()

        try:
            raw_data = client.get(function, symbol)

            file_name = f"balance_sheet_{symbol}_{today}.json"
            file_path = os.path.join(tempfile.gettempdir(), file_name)

            if not raw_data:
                raise ValueError(f"No data returned for symbol {symbol}")

            logger.info(f"Validating data for balance_sheet for {symbol}...")
            extraction_date = today.isoformat()

            validated_data = BalanceSheetSchema.model_validate(raw_data)

            if has_extra_fields(validated_data):
                extra_keys = list(validated_data.model_extra.keys())
                logger.warning(
                    f"New fields detected for {symbol} in '{function}': {extra_keys}. Routing payload to quarantine."
                )
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(raw_data, f, ensure_ascii=False)

                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                length = count_real_rows(raw_data)

                quarantine_blob = (
                    f"financial/quarantine/balance_sheet/"
                    f"year={today.year}/month={today.month:02d}/day={today.day:02d}/{file_name}"
                )
                gcp_loader.upload_file(file_path, quarantine_blob)
                os.remove(file_path)

                time_seconds = time.perf_counter() - start_time
                log_extraction(
                    logger=logger,
                    status="QUARANTINE",
                    stage_location_bucket=BUCKET_BRONZE,
                    last_updated=extraction_date,
                    endpoint=function,
                    symbol=symbol,
                    rows=length,
                    size=round(file_size_mb, 6),
                    time_seconds=round(time_seconds, 3),
                    error_message=f"Extra fields detected: {extra_keys}",
                )
                batch.record_failure(symbol, f"Extra fields detected: {extra_keys}")
                continue

            logger.info(f"Validation succeeded for {symbol}.")

            data = validated_data.model_dump(mode="json", by_alias=True, exclude_unset=True)

            if isinstance(data, list):
                for item in data:
                    item["extraction_date"] = extraction_date
            elif isinstance(data, dict):
                data["extraction_date"] = extraction_date

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)

            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            logger.info(f"File created: {file_path} ({file_size_mb:.4f} MB)")

            length = count_real_rows(data)
            logger.info(f"Rows processed for {symbol}: {length}")

            fiscal_date = str(
                validated_data.annualReports[0].fiscalDateEnding
                if validated_data.annualReports
                else (validated_data.quarterlyReports[0].fiscalDateEnding if validated_data.quarterlyReports else "")
            )

            # Skip the upload when the fiscal period is already covered by the watermark.
            if not watermark.should_upload(symbol, fiscal_date):
                logger.info(
                    f"Fiscal period '{fiscal_date}' for {symbol} already exists in the Data Lake. GCS upload skipped."
                )
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                batch.record_success(symbol)
                continue

            destination_blob_name = (
                f"financial/balance_sheet/year={today.year}/month={today.month:02d}/day={today.day:02d}/{file_name}"
            )

            gcp_loader.upload_file(file_path, destination_blob_name)
            os.remove(file_path)
            logger.info(f"Upload completed and local file removed: {file_name}")

            watermark.record_success(symbol, fiscal_date)
            files_generated.append(destination_blob_name)
            batch.record_success(symbol)

            time_seconds = time.perf_counter() - start_time
            logger.info(f"Total time for {symbol}: {time_seconds:.2f}s")

            log_extraction(
                logger=logger,
                status="SUCCESS",
                stage_location_bucket=BUCKET_BRONZE,
                last_updated=extraction_date,
                endpoint=function,
                symbol=symbol,
                rows=length,
                size=round(file_size_mb, 6),
                time_seconds=round(time_seconds, 3),
                error_message=None,
            )

        except AlphaVantageRateLimitError as e:
            time_seconds = time.perf_counter() - start_time
            logger.error(f"Rate limit during extraction for {symbol}: {e}")
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
                error_message=str(e),
            )
            batch.record_failure(symbol, e, stop=True)
            break

        except ValidationError as e:
            time_seconds = time.perf_counter() - start_time
            logger.error(f"Validation error for {symbol}: {e}")
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
                error_message=str(e),
            )
            batch.record_failure(symbol, e)

        except ValueError as e:
            time_seconds = time.perf_counter() - start_time
            logger.error(f"ValueError for {symbol}: {e}")
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
                error_message=str(e),
            )
            batch.record_failure(symbol, e)

        except Exception as e:
            time_seconds = time.perf_counter() - start_time
            logger.error(f"Unexpected error while extracting balance_sheet for {symbol}: {e}")
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
                error_message=str(e),
            )
            batch.record_failure(symbol, e)

        finally:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)

    # Persist updated watermarks in GCS.
    watermark.save()
    log_batch_summary(logger, batch.as_log_entry())

    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    log_destination = (
        f"financial/metadata/balance_sheet/"
        f"year={today.year}/month={today.month:02d}/day={today.day:02d}/balance_sheet_extraction.log"
    )
    upload_and_clean_log(gcp_loader, "extraction.log", log_destination)

    batch.raise_for_incomplete_batch()
    return files_generated


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    extract_balance_sheet()

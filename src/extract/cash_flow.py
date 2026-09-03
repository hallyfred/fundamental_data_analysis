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
from src.extract.api_client import AlphaVantageAPIClient
from src.extract.contract import CashFlowSchema, has_extra_fields
from src.load.loader import GCPSLoader
from src.utils.helpers import count_real_rows
from src.utils.logger import log_extraction, setup_logger, upload_and_clean_log


def extract_cash_flow(symbols: list[str] | None = None):
    logger = setup_logger()
    function = ENDPOINTS_API["cash_flow"]
    today = date.today()

    if symbols is None:
        symbols = get_symbols_for_day(today.weekday())

    logger.info(f"Iniciando extração de cash_flow para {len(symbols)} símbolos: {symbols}")
    files_generated = []

    gcp_loader = GCPSLoader(project_id=PROJECT_ID, bucket_name=BUCKET_BRONZE)
    client = AlphaVantageAPIClient(BASE_URL, ALPHA_VANTAGE_API_KEY)

    for symbol in symbols:
        length = 0
        file_size_mb = 0.0
        file_path = None

        start_time = time.perf_counter()

        try:
            raw_data = client.get(function, symbol)

            file_name = f"cash_flow_{symbol}_{today}.json"
            file_path = os.path.join(tempfile.gettempdir(), file_name)

            if not raw_data:
                raise ValueError(f"Nenhum dado retornado para o símbolo {symbol}")

            logger.info(f"Validando dados de cash_flow para {symbol}...")
            extraction_date = today.isoformat()

            validated_data = CashFlowSchema.model_validate(raw_data)

            if has_extra_fields(validated_data):
                extra_keys = list(validated_data.model_extra.keys())
                logger.warning(
                    f"Campos novos detectados para {symbol} em '{function}': {extra_keys}. Roteando para quarentena."
                )
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(raw_data, f, ensure_ascii=False)

                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                length = count_real_rows(raw_data)

                quarantine_blob = (
                    f"financial/quarantine/cash_flow/"
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
                    error_message=f"Campos extras detectados: {extra_keys}",
                )
                continue

            logger.info(f"Validação bem-sucedida para {symbol}.")

            data = validated_data.model_dump(mode="json", by_alias=True, exclude_unset=True)

            if isinstance(data, list):
                for item in data:
                    item["extraction_date"] = extraction_date
            elif isinstance(data, dict):
                data["extraction_date"] = extraction_date

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)

            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            logger.info(f"Arquivo criado: {file_path} ({file_size_mb:.4f} MB)")

            length = count_real_rows(data)
            logger.info(f"Linhas processadas para {symbol}: {length}")

            destination_blob_name = (
                f"financial/cash_flow/year={today.year}/month={today.month:02d}/day={today.day:02d}/{file_name}"
            )

            gcp_loader.upload_file(file_path, destination_blob_name)
            os.remove(file_path)
            logger.info(f"Upload concluído e arquivo local removido: {file_name}")

            files_generated.append(destination_blob_name)

            time_seconds = time.perf_counter() - start_time
            logger.info(f"Tempo total para {symbol}: {time_seconds:.2f}s")

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

        except ValidationError as e:
            time_seconds = time.perf_counter() - start_time
            logger.error(f"Erro de validação para {symbol}: {e}")
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

        except ValueError as e:
            time_seconds = time.perf_counter() - start_time
            logger.error(f"ValueError para {symbol}: {e}")
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

        except Exception as e:
            time_seconds = time.perf_counter() - start_time
            logger.error(f"Erro inesperado ao extrair cash_flow para {symbol}: {e}")
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

        finally:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)

    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    log_destination = (
        f"financial/metadata/cash_flow/"
        f"year={today.year}/month={today.month:02d}/day={today.day:02d}/cash_flow_extraction.log"
    )
    upload_and_clean_log(gcp_loader, "extraction.log", log_destination)

    return files_generated


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    extract_cash_flow()

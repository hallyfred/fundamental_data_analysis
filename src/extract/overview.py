from datetime import date
import time
import json
import os
import tempfile

from src.extract.api_client import AlphaVantageAPIClient
from src.utils.logger import setup_logger, log_extraction, upload_and_clean_log
from src.utils.helpers import count_real_rows
from src.load.loader import GCPSLoader
from src.extract.contract import OverviewSchema, has_extra_fields
from pydantic import ValidationError
from config.config import BASE_URL, ALPHA_VANTAGE_API_KEY, SYMBOLS, PROJECT_ID, BUCKET_BRONZE, ENDPOINTS_API


def extract_overview():
    logger = setup_logger()
    logger.info("Iniciando extração de overview para todos os símbolos.")
    function = ENDPOINTS_API["overview"]

    today = date.today()
    files_generated = []

    gcp_loader = GCPSLoader(project_id=PROJECT_ID, bucket_name=BUCKET_BRONZE)
    client = AlphaVantageAPIClient(BASE_URL, ALPHA_VANTAGE_API_KEY)

    for symbol in SYMBOLS:

        length = 0
        file_size_mb = 0.0
        file_path = None

        start_time = time.perf_counter()

        try:
            raw_data = client.get(function, symbol)

            file_name = f"overview_{symbol}_{today}.json"
            # Grava em diretório temporário controlado pelo SO — evita colisões em CWD
            file_path = os.path.join(tempfile.gettempdir(), file_name)

            if not raw_data:
                raise ValueError(f"Nenhum dado retornado para o símbolo {symbol}")

            logger.info(f"Validando dados de overview para {symbol}...")
            extraction_date = today.isoformat()

            validated_data = OverviewSchema.model_validate(raw_data)

            # Verifica se a API retornou campos não mapeados no contrato
            if has_extra_fields(validated_data):
                extra_keys = list(validated_data.model_extra.keys())
                logger.warning(
                    f"Campos novos detectados para {symbol} em '{function}': {extra_keys}. "
                    f"Roteando para quarentena."
                )
                # Salva o dado RAW (sem model_dump) para preservar os campos novos
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(raw_data, f, ensure_ascii=False)

                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                length = count_real_rows(raw_data)

                quarantine_blob = (
                    f"financial/quarantine/overview/"
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
                continue  # não adiciona em files_generated (não vai para Bronze)

            logger.info(f"Validação bem-sucedida para {symbol}.")

            data = validated_data.model_dump(mode='json', by_alias=True, exclude_unset=True)

            if isinstance(data, list):
                for item in data:
                    item["extraction_date"] = extraction_date
            elif isinstance(data, dict):
                data["extraction_date"] = extraction_date

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)

            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            logger.info(f"Arquivo criado: {file_path} ({file_size_mb:.4f} MB)")

            length = count_real_rows(data)
            logger.info(f"Linhas processadas para {symbol}: {length}")

            destination_blob_name = (
                f"financial/overview/"
                f"year={today.year}/month={today.month:02d}/day={today.day:02d}/{file_name}"
            )

            # Upload propaga exceção se falhar — o append só ocorre após sucesso
            gcp_loader.upload_file(file_path, destination_blob_name)
            os.remove(file_path)
            logger.info(f"Upload concluído e arquivo local removido: {file_name}")

            files_generated.append(destination_blob_name)  # apenas após upload confirmado

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
            logger.error(f"Erro inesperado ao extrair overview para {symbol}: {e}")
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
            # Garante remoção do arquivo temporário mesmo em caso de falha após criação
            if file_path and os.path.exists(file_path):
                os.remove(file_path)

    # Libera os handlers do logger antes de fazer upload do log
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    log_destination = (
        f"financial/metadata/overview/"
        f"year={today.year}/month={today.month:02d}/day={today.day:02d}/overview_extraction.log"
    )
    upload_and_clean_log(gcp_loader, 'extraction.log', log_destination)

    return files_generated


if __name__ == "__main__":
    extract_overview()
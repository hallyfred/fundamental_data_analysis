import json
import logging
import os
import sys
from datetime import UTC, datetime


def setup_logger(file_name="extraction.log"):
    """
    Configura e retorna um logger formatado para o console (sys.stdout).
    O arquivo de log que sobe para o GCP conterá estritamente as entradas
    JSON geradas por log_extraction(), sem misturar mensagens de texto narrativas.
    """
    logger = logging.getLogger("extraction_logger")
    logger.setLevel(logging.INFO)
    logger.log_file = file_name

    # Evita duplicação de handlers se o logger já foi configurado
    if not logger.handlers:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(stream_handler)

    return logger


def log_extraction(
    logger,
    status,
    stage_location_bucket,
    last_updated,
    endpoint,
    symbol,
    rows=0,
    size=0.0,
    time_seconds=0.0,
    error_message=None,
):
    """
    Registra uma entrada estruturada em JSON no arquivo de log do pipeline.
    Garante que o arquivo de log no GCS seja estritamente um JSON Lines (NDJSON)
    enxuto com apenas os metadados de cada extração.
    """
    log_entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "status": status,
        "stage_location_bucket": stage_location_bucket,
        "last_updated": last_updated,
        "endpoint": endpoint,
        "symbol": symbol,
        "rows_processed": rows,
        "size_mb": size,
        "time_seconds": time_seconds,
        "error_message": str(error_message) if error_message else None,
    }

    # Grava exclusivamente a linha JSON no arquivo que será enviado ao GCS
    log_file = getattr(logger, "log_file", "extraction.log") if logger else "extraction.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")


def upload_and_clean_log(gcp_loader, local_log_file, destination_log_path):
    """
    Faz upload do arquivo de log local para o GCS e remove o arquivo local.
    Se o arquivo não existir ou o upload falhar, loga um aviso sem interromper o pipeline.
    """
    log_uploaded = False  # garante que a variável está sempre inicializada

    if not os.path.exists(local_log_file):
        logging.warning(f"Arquivo de log não encontrado, upload ignorado: {local_log_file}")
        return

    try:
        gcp_loader.upload_file(local_log_file, destination_log_path)
        log_uploaded = True
    except Exception as e:
        # Falha no upload do log não deve derrubar o pipeline principal
        logging.warning(f"Falha ao fazer upload do log para {destination_log_path}: {e}")

    if log_uploaded:
        os.remove(local_log_file)
        logging.info(f"Log enviado para {destination_log_path} e removido localmente.")
    else:
        logging.warning(f"Log NÃO enviado para o GCS. Arquivo local mantido em: {local_log_file}")

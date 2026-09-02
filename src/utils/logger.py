import logging
import json
from datetime import datetime, timezone
import os


def setup_logger(file_name='extraction.log'):
    """Configura e retorna um logger com FileHandler para o arquivo especificado."""
    logger = logging.getLogger('extraction_logger')
    logger.setLevel(logging.INFO)

    # Evita duplicação de handlers se o logger já foi configurado
    if not logger.handlers:
        handler = logging.FileHandler(file_name, encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(handler)

    return logger


def log_extraction(logger, status, stage_location_bucket, last_updated, endpoint, symbol, rows=0, size=0.0, time_seconds=0.0, error_message=None):
    """Registra uma entrada estruturada em JSON no logger."""
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
        "error_message": str(error_message) if error_message else None,
    }
    logger.info(json.dumps(log_entry))


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
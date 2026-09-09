import json
import logging

from src.load.loader import GCPSLoader

logger = logging.getLogger(__name__)


class WatermarkManager:
    """
    Gerencia o watermark de ingestão no GCS por endpoint.
    Armazena e consulta o último exercício fiscal (fiscalDateEnding / fiscal_year_end)
    processado para cada ticker, evitando uploads duplicados no Data Lake.
    """

    def __init__(self, gcp_loader: GCPSLoader, endpoint: str):
        self.gcp_loader = gcp_loader
        self.endpoint = endpoint
        self.watermark_blob = f"financial/metadata/watermarks/{endpoint}_watermark.json"
        self._watermarks: dict[str, str] = self._load()
        self._dirty = False

    def _load(self) -> dict[str, str]:
        """Carrega o mapa de watermarks existente no GCS ou inicializa vazio."""
        try:
            content = self.gcp_loader.download_as_text(self.watermark_blob)
            if content:
                data = json.loads(content)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            logger.warning(f"Erro ao carregar watermark para '{self.endpoint}': {e}. Iniciando novo mapa.")
        return {}

    def get_latest_date(self, symbol: str) -> str | None:
        """Retorna o último exercício fiscal registrado para o símbolo."""
        return self._watermarks.get(symbol.upper())

    def should_upload(self, symbol: str, current_fiscal_date: str | None) -> bool:
        """
        Determina se os dados devem ser enviados para o GCS:
        - Se current_fiscal_date for None/vazio: True (não bloqueia por falta de metadado).
        - Se o símbolo for novo: True.
        - Se current_fiscal_date > última data gravada: True.
        - Se current_fiscal_date <= última data gravada: False (já ingerido).
        """
        if not current_fiscal_date:
            return True

        symbol_key = symbol.upper()
        last_date = self._watermarks.get(symbol_key)
        if not last_date:
            return True

        return str(current_fiscal_date) > str(last_date)

    def record_success(self, symbol: str, current_fiscal_date: str | None) -> None:
        """Registra a nova data de watermark para o símbolo caso seja mais recente."""
        if not current_fiscal_date:
            return

        symbol_key = symbol.upper()
        current_val = str(current_fiscal_date)
        last_val = self._watermarks.get(symbol_key)

        if not last_val or current_val > last_val:
            self._watermarks[symbol_key] = current_val
            self._dirty = True

    def save(self) -> None:
        """Persiste os watermarks atualizados no GCS se houver modificações."""
        if not self._dirty:
            return

        try:
            payload = json.dumps(self._watermarks, indent=2, ensure_ascii=False)
            self.gcp_loader.upload_text(payload, self.watermark_blob)
            self._dirty = False
            logger.info(f"Watermark atualizado com sucesso no GCS: {self.watermark_blob}")
        except Exception as e:
            logger.error(f"Falha ao salvar watermark no GCS ({self.watermark_blob}): {e}")

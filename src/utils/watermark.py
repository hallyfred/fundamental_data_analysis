import json
import logging

from src.load.loader import GCPSLoader

logger = logging.getLogger(__name__)


class WatermarkManager:
    """
    Manage the GCS ingestion watermark for one endpoint.
    Store and retrieve the latest fiscal period (fiscalDateEnding / fiscal_year_end)
    processed for each ticker to avoid duplicate Data Lake uploads.
    """

    def __init__(self, gcp_loader: GCPSLoader, endpoint: str):
        self.gcp_loader = gcp_loader
        self.endpoint = endpoint
        self.watermark_blob = f"financial/metadata/watermarks/{endpoint}_watermark.json"
        self._watermarks: dict[str, str] = self._load()
        self._dirty = False

    def _load(self) -> dict[str, str]:
        """Load the existing GCS watermark map or initialize an empty one."""
        try:
            content = self.gcp_loader.download_as_text(self.watermark_blob)
            if content:
                data = json.loads(content)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            logger.warning(f"Failed to load watermark for '{self.endpoint}': {e}. Starting with an empty map.")
        return {}

    def get_latest_date(self, symbol: str) -> str | None:
        """Return the latest fiscal period recorded for the symbol."""
        return self._watermarks.get(symbol.upper())

    def should_upload(self, symbol: str, current_fiscal_date: str | None) -> bool:
        """
        Determine whether the payload should be uploaded to GCS:
        - Return True when current_fiscal_date is missing; absent metadata must not block ingestion.
        - Return True for a new symbol.
        - Return True when current_fiscal_date is newer than the stored value.
        - Return False when current_fiscal_date is not newer.
        """
        if not current_fiscal_date:
            return True

        symbol_key = symbol.upper()
        last_date = self._watermarks.get(symbol_key)
        if not last_date:
            return True

        return str(current_fiscal_date) > str(last_date)

    def record_success(self, symbol: str, current_fiscal_date: str | None) -> None:
        """Record a newer fiscal date in the symbol watermark."""
        if not current_fiscal_date:
            return

        symbol_key = symbol.upper()
        current_val = str(current_fiscal_date)
        last_val = self._watermarks.get(symbol_key)

        if not last_val or current_val > last_val:
            self._watermarks[symbol_key] = current_val
            self._dirty = True

    def save(self) -> None:
        """Persist modified watermarks in GCS."""
        if not self._dirty:
            return

        try:
            payload = json.dumps(self._watermarks, indent=2, ensure_ascii=False)
            self.gcp_loader.upload_text(payload, self.watermark_blob)
            self._dirty = False
            logger.info(f"Watermark successfully updated in GCS: {self.watermark_blob}")
        except Exception as e:
            logger.error(f"Failed to save watermark in GCS ({self.watermark_blob}): {e}")

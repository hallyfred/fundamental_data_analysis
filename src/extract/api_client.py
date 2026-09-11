import logging
import re
import time

import requests

from config.config import TIMEOUT

_logger = logging.getLogger(__name__)


# =============================================================================
# Alpha Vantage semantic exceptions
# The API returns HTTP 200 even for errors. These exceptions distinguish
# retryable rate limits from permanent request failures.
# =============================================================================


class AlphaVantageRateLimitError(Exception):
    """Raised when Alpha Vantage reports a per-minute or daily rate limit."""


class AlphaVantageAPIError(Exception):
    """Raised for non-retryable semantic, HTTP, or network API failures."""


# =============================================================================
# HTTP client with timeout, retry/backoff, and semantic error detection
# =============================================================================


class AlphaVantageAPIClient:
    MAX_RETRIES = 3
    BACKOFF_BASE_SECONDS = 2  # delays: 2s, 4s, 8s

    def __init__(self, base_url: str, api_key: str, max_retries: int | None = None):
        # Fail immediately when the API key is missing.
        if not api_key:
            raise ValueError(
                "ALPHA_VANTAGE_API_KEY is not configured. Set it in the .env file before running the pipeline."
            )
        self.base_url = base_url
        self.api_key = api_key
        self.max_retries = max_retries if max_retries is not None else self.MAX_RETRIES
        if self.max_retries < 1:
            raise ValueError("max_retries must be at least 1.")

    def _sanitize(self, message: str) -> str:
        """Remove API keys from log and exception text."""
        if not message:
            return ""
        sanitized = message.replace(self.api_key, "***REDACTED_API_KEY***")
        sanitized = re.sub(
            r"(?i)(apikey=)[^&\s]+",
            r"\1***REDACTED_API_KEY***",
            sanitized,
        )
        return re.sub(
            r"(?i)(API key as )([A-Z0-9_-]+)",
            r"\1***REDACTED_API_KEY***",
            sanitized,
        )

    def _check_semantic_errors(self, data: dict, symbol: str, function: str) -> None:
        """Detect and sanitize errors returned inside HTTP 200 responses."""
        if "Note" in data:
            msg = self._sanitize(str(data["Note"]))
            raise AlphaVantageRateLimitError(
                f"Rate limit reached while requesting '{function}' for '{symbol}'. API response: {msg}"
            )
        if "Information" in data:
            raw_info = str(data["Information"])
            msg = self._sanitize(raw_info)
            if "rate limit" in raw_info.lower():
                raise AlphaVantageRateLimitError(
                    f"Daily request limit reached while requesting '{function}' for '{symbol}'. API response: {msg}"
                )
            raise AlphaVantageAPIError(
                f"Access denied while requesting '{function}' for '{symbol}'. API response: {msg}"
            )
        if "Error Message" in data:
            msg = self._sanitize(str(data["Error Message"]))
            raise AlphaVantageAPIError(f"Invalid request for '{function}' and '{symbol}'. API response: {msg}")

    def get(self, function: str, symbol: str) -> dict:
        """Request Alpha Vantage data with timeout, retries, and redaction."""
        params = {
            "function": function,
            "symbol": symbol,
            "apikey": self.api_key,
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.get(self.base_url, params=params, timeout=TIMEOUT)
                response.raise_for_status()
                data = response.json()

                # Detect semantic errors before returning the payload.
                self._check_semantic_errors(data, symbol, function)

                return data

            except AlphaVantageRateLimitError as e:
                # Fail immediately on the daily limit to preserve the request budget.
                err_msg = str(e).lower()
                if "25 requests per day" in err_msg or "daily request limit" in err_msg:
                    _logger.error("[%s/%s] Alpha Vantage daily request limit reached.", symbol, function)
                    raise

                # Retry transient per-minute limits with exponential backoff.
                if attempt < self.max_retries:
                    wait = self.BACKOFF_BASE_SECONDS**attempt
                    _logger.warning(
                        "[%s/%s] Rate limit on attempt %s/%s. Retrying in %ss.",
                        symbol,
                        function,
                        attempt,
                        self.max_retries,
                        wait,
                    )
                    time.sleep(wait)
                else:
                    _logger.error("[%s/%s] Rate limit persisted after %s attempts.", symbol, function, self.max_retries)
                    raise

            except AlphaVantageAPIError:
                # Semantic API failures are not retryable.
                raise

            except requests.exceptions.Timeout as exc:
                safe_error = self._sanitize(str(exc))
                if attempt < self.max_retries:
                    wait = self.BACKOFF_BASE_SECONDS**attempt
                    _logger.warning(
                        "[%s/%s] Timeout on attempt %s/%s: %s. Retrying in %ss.",
                        symbol,
                        function,
                        attempt,
                        self.max_retries,
                        safe_error,
                        wait,
                    )
                    time.sleep(wait)
                else:
                    raise AlphaVantageAPIError(
                        f"[{symbol}/{function}] Request timed out after {self.max_retries} attempt(s): {safe_error}"
                    ) from None

            except requests.exceptions.RequestException as exc:
                # Sanitize errors because Requests may include the full URL and API key.
                safe_error = self._sanitize(str(exc))
                if attempt < self.max_retries:
                    wait = self.BACKOFF_BASE_SECONDS**attempt
                    _logger.warning(
                        "[%s/%s] Network error on attempt %s/%s: %s. Retrying in %ss.",
                        symbol,
                        function,
                        attempt,
                        self.max_retries,
                        safe_error,
                        wait,
                    )
                    time.sleep(wait)
                else:
                    raise AlphaVantageAPIError(
                        f"[{symbol}/{function}] Network request failed after {self.max_retries} attempt(s): {safe_error}"
                    ) from None

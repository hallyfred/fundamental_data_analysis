import logging
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

import requests

from config.config import TIMEOUT

_logger = logging.getLogger(__name__)


@dataclass
class RequestMetrics:
    """Capture real HTTP attempts for one endpoint execution.

    ``actual_requests`` counts attempts made to ``requests.get``. A retry is
    therefore visible in the total instead of being mistaken for one logical
    ticker request.
    """

    run_id: str | None
    endpoint: str
    actual_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limit_requests: int = 0
    retry_requests: int = 0
    events: list[dict] = field(default_factory=list)

    def start_attempt(self, symbol: str, attempt: int) -> dict:
        self.actual_requests += 1
        if attempt > 1:
            self.retry_requests += 1

        event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "run_id": self.run_id,
            "endpoint": self.endpoint,
            "symbol": symbol,
            "attempt": attempt,
            "status": "started",
        }
        self.events.append(event)
        return event

    def finish_attempt(self, event: dict, status: str, error_type: str | None = None) -> None:
        event["finished_at"] = datetime.now(UTC).isoformat()
        event["status"] = status
        if error_type:
            event["error_type"] = error_type

        if status == "success":
            self.successful_requests += 1
        elif status.startswith("rate_limit"):
            self.rate_limit_requests += 1
        else:
            self.failed_requests += 1

    def as_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "endpoint": self.endpoint,
            "actual_requests": self.actual_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "rate_limit_requests": self.rate_limit_requests,
            "retry_requests": self.retry_requests,
            "events": self.events,
        }


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
    # Keep a deliberately conservative gap between actual Alpha Vantage HTTP
    # requests.  The provider can return a generic throttle response, so the
    # pipeline uses 30 seconds instead of relying on the advertised 1 rps.
    REQUEST_INTERVAL_SECONDS = 30

    def __init__(
        self,
        base_url: str,
        api_key: str,
        max_retries: int | None = None,
        request_metrics: RequestMetrics | None = None,
        request_interval_seconds: int | float | None = None,
    ):
        # Fail immediately when the API key is missing.
        if not api_key:
            raise ValueError(
                "ALPHA_VANTAGE_API_KEY is not configured. Set it in the .env file before running the pipeline."
            )
        self.base_url = base_url
        self.api_key = api_key
        self.max_retries = max_retries if max_retries is not None else self.MAX_RETRIES
        self.request_metrics = request_metrics
        self.request_interval_seconds = (
            request_interval_seconds if request_interval_seconds is not None else self.REQUEST_INTERVAL_SECONDS
        )
        if self.max_retries < 1:
            raise ValueError("max_retries must be at least 1.")
        if self.request_interval_seconds < 0:
            raise ValueError("request_interval_seconds must be non-negative.")

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
            event = self.request_metrics.start_attempt(symbol, attempt) if self.request_metrics else None
            request_started = False
            try:
                request_started = True
                response = requests.get(self.base_url, params=params, timeout=TIMEOUT)
                response.raise_for_status()
                data = response.json()

                # Detect semantic errors before returning the payload.
                self._check_semantic_errors(data, symbol, function)

                if event:
                    self.request_metrics.finish_attempt(event, "success")

                return data

            except AlphaVantageRateLimitError as e:
                if event:
                    scope = "daily" if "daily request limit" in str(e).lower() else "transient"
                    self.request_metrics.finish_attempt(event, f"rate_limit_{scope}", "AlphaVantageRateLimitError")
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
                if event:
                    self.request_metrics.finish_attempt(event, "failed", "AlphaVantageAPIError")
                # Semantic API failures are not retryable.
                raise

            except requests.exceptions.Timeout as exc:
                if event:
                    self.request_metrics.finish_attempt(event, "failed", "Timeout")
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
                if event:
                    self.request_metrics.finish_attempt(event, "failed", type(exc).__name__)
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

            finally:
                # This runs after every real HTTP attempt, including the last
                # request of an extractor.  As extraction tasks are serial,
                # it also guarantees the same gap before the next endpoint.
                if request_started and self.request_interval_seconds:
                    _logger.info(
                        "Waiting %ss before the next Alpha Vantage request.",
                        self.request_interval_seconds,
                    )
                    time.sleep(self.request_interval_seconds)

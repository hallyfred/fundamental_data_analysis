from __future__ import annotations

import json
import logging
import os
import re
from typing import Any
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

SENSITIVE_ENVIRONMENT_VARIABLES = (
    "ALPHA_VANTAGE_API_KEY",
    "AIRFLOW__CORE__FERNET_KEY",
    "POSTGRES_PASSWORD",
    "_AIRFLOW_WWW_USER_PASSWORD",
)


def _redact_sensitive_values(message: str) -> str:
    sanitized = message
    for variable_name in SENSITIVE_ENVIRONMENT_VARIABLES:
        value = os.getenv(variable_name, "")
        if value:
            sanitized = sanitized.replace(value, "***REDACTED***")
    return re.sub(
        r"(?i)((?:api[_-]?key|token|password)=)[^&\s]+",
        r"\1***REDACTED***",
        sanitized,
    )


def notify_pipeline_failure(context: dict[str, Any]) -> None:
    """Log task failures and optionally notify an HTTP webhook."""
    task_instance = context.get("task_instance") or context.get("ti")
    exception = context.get("exception")
    error = _redact_sensitive_values(str(exception) if exception else "unknown error")
    normalized_error = error.lower().replace("-", " ")
    payload = {
        "event": "airflow_task_failure",
        "dag_id": getattr(task_instance, "dag_id", None),
        "task_id": getattr(task_instance, "task_id", None),
        "run_id": context.get("run_id"),
        "logical_date": str(context.get("logical_date") or ""),
        "reason": "rate_limit" if "rate limit" in normalized_error else "task_failure",
        "error": error[:1000],
    }
    logger.error("Pipeline failure: %s", json.dumps(payload, ensure_ascii=False))

    webhook_url = os.getenv("ALERT_WEBHOOK_URL", "").strip()
    if not webhook_url:
        return
    parsed_webhook = urlparse(webhook_url)
    if parsed_webhook.scheme != "https" or not parsed_webhook.netloc:
        logger.warning("Failure webhook was not sent because ALERT_WEBHOOK_URL must use HTTPS.")
        return

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Failure webhook could not be delivered (%s).", type(exc).__name__)

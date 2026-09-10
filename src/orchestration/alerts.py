from __future__ import annotations

import json
import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)


def notify_pipeline_failure(context: dict[str, Any]) -> None:
    """Log task failures and optionally notify an HTTP webhook."""
    task_instance = context.get("task_instance") or context.get("ti")
    exception = context.get("exception")
    error = str(exception) if exception else "unknown error"
    payload = {
        "event": "airflow_task_failure",
        "dag_id": getattr(task_instance, "dag_id", None),
        "task_id": getattr(task_instance, "task_id", None),
        "run_id": context.get("run_id"),
        "logical_date": str(context.get("logical_date") or ""),
        "reason": "rate_limit" if "rate limit" in error.lower() else "task_failure",
        "error": error[:1000],
    }
    logger.error("Pipeline failure: %s", json.dumps(payload, ensure_ascii=False))

    webhook_url = os.getenv("ALERT_WEBHOOK_URL", "").strip()
    if not webhook_url:
        return

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Failure webhook could not be delivered: %s", exc)

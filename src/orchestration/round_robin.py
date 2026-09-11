from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from config.config import (
    API_LIMIT_PER_DAY,
    ENDPOINTS_API,
    build_ticker_batches,
    enumerate_ticker_batches,
    get_batch_for_day,
    get_symbols_for_day,
)

PIPELINE_TIMEZONE = ZoneInfo("America/Sao_Paulo")


def get_pipeline_run_date(run_at: date | datetime) -> date:
    """Return the Airflow run date in the pipeline's business timezone."""
    if isinstance(run_at, datetime):
        if run_at.tzinfo is None:
            run_at = run_at.replace(tzinfo=PIPELINE_TIMEZONE)
        else:
            run_at = run_at.astimezone(PIPELINE_TIMEZONE)
        return run_at.date()
    return run_at


def build_round_robin_plan(run_at: date | datetime, run_id: str | None = None) -> dict:
    run_date = get_pipeline_run_date(run_at)
    symbols = get_symbols_for_day(run_date.weekday())
    planned_requests = len(symbols) * len(ENDPOINTS_API)

    if planned_requests > API_LIMIT_PER_DAY:
        raise ValueError(
            f"Round-robin plan requires {planned_requests} requests, above the daily limit of {API_LIMIT_PER_DAY}."
        )

    return {
        "run_id": run_id,
        "run_date": run_date.isoformat(),
        "weekday": run_date.weekday(),
        "symbols": symbols,
        "endpoints": list(ENDPOINTS_API.values()),
        "planned_requests": planned_requests,
        "daily_request_limit": API_LIMIT_PER_DAY,
    }


__all__ = [
    "PIPELINE_TIMEZONE",
    "build_ticker_batches",
    "build_round_robin_plan",
    "enumerate_ticker_batches",
    "get_batch_for_day",
    "get_pipeline_run_date",
]

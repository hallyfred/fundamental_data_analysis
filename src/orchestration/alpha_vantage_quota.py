"""Persistent cooldown guard for Alpha Vantage's daily request budget."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

ALPHA_VANTAGE_LAST_REQUEST_VARIABLE = "alpha_vantage_last_request_at"
ALPHA_VANTAGE_COOLDOWN = timedelta(hours=24)


def utc_now() -> datetime:
    return datetime.now(UTC)


def parse_last_request(value: str | None) -> datetime | None:
    """Parse the stored ISO timestamp, treating malformed legacy values as absent."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def record_alpha_vantage_request() -> None:
    """Record immediately before an HTTP attempt, including failed attempts.

    A failed request can still be counted by the provider, so persisting it is
    intentionally conservative and prevents another run from immediately
    retrying the entire daily budget.
    """
    # Keep the extractor importable in local tools and unit tests that do not
    # run an Airflow metadata database. The DAG container resolves this import.
    from airflow.models import Variable

    Variable.set(ALPHA_VANTAGE_LAST_REQUEST_VARIABLE, utc_now().isoformat())

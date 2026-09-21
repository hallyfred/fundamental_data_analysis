"""Airflow sensor implementation for the Alpha Vantage cooldown."""

from __future__ import annotations

from airflow.models import Variable
from airflow.sensors.base import BaseSensorOperator

from src.orchestration.alpha_vantage_quota import (
    ALPHA_VANTAGE_COOLDOWN,
    ALPHA_VANTAGE_LAST_REQUEST_VARIABLE,
    parse_last_request,
    utc_now,
)


class AlphaVantageQuotaSensor(BaseSensorOperator):
    """Reschedule until 24 hours have elapsed since the last API attempt."""

    def __init__(self, *, cooldown=ALPHA_VANTAGE_COOLDOWN, **kwargs):
        super().__init__(mode="reschedule", **kwargs)
        self.cooldown = cooldown

    def poke(self, context) -> bool:
        last_request = parse_last_request(Variable.get(ALPHA_VANTAGE_LAST_REQUEST_VARIABLE, default_var=None))
        if last_request is None:
            self.log.info("No Alpha Vantage request timestamp found; extraction may start.")
            return True

        available_at = last_request + self.cooldown
        now = utc_now()
        if now >= available_at:
            self.log.info("Alpha Vantage quota cooldown ended at %s; extraction may start.", available_at.isoformat())
            return True

        self.log.info(
            "Alpha Vantage quota is cooling down. Last request: %s; next attempt after: %s.",
            last_request.isoformat(),
            available_at.isoformat(),
        )
        return False

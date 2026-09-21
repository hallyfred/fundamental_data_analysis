import sys
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from src.orchestration.alpha_vantage_quota import (
    ALPHA_VANTAGE_LAST_REQUEST_VARIABLE,
    parse_last_request,
)

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="Airflow sensors require Linux")

if sys.platform != "win32":
    from src.orchestration.alpha_vantage_quota_sensor import AlphaVantageQuotaSensor


def test_parse_last_request_normalizes_to_utc():
    assert parse_last_request("2026-09-19T10:00:00-03:00") == datetime(2026, 9, 19, 13, tzinfo=UTC)
    assert parse_last_request("not-a-date") is None


@patch("src.orchestration.alpha_vantage_quota_sensor.Variable")
@patch("src.orchestration.alpha_vantage_quota_sensor.utc_now")
def test_quota_sensor_waits_until_full_cooldown(mock_now, mock_variable):
    last_request = datetime(2026, 9, 18, 22, tzinfo=UTC)
    mock_variable.get.return_value = last_request.isoformat()
    sensor = AlphaVantageQuotaSensor(task_id="quota_test", poke_interval=60)

    mock_now.return_value = last_request + timedelta(hours=23, minutes=59)
    assert sensor.poke({}) is False

    mock_now.return_value = last_request + timedelta(hours=24)
    assert sensor.poke({}) is True


@patch("src.orchestration.alpha_vantage_quota_sensor.Variable")
def test_quota_sensor_allows_first_run_without_timestamp(mock_variable):
    mock_variable.get.return_value = None
    sensor = AlphaVantageQuotaSensor(task_id="quota_test", poke_interval=60)

    assert sensor.poke({}) is True
    mock_variable.get.assert_called_once_with(ALPHA_VANTAGE_LAST_REQUEST_VARIABLE, default_var=None)

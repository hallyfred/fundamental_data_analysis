from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch

import pytest

from config.config import API_LIMIT_PER_DAY, ENDPOINTS_API, WEEKDAY_SYMBOLS, get_symbols_for_day
from src.extract.balance_sheet import extract_balance_sheet
from src.extract.overview import extract_overview
from src.orchestration.round_robin import build_round_robin_plan, get_pipeline_run_date


def test_round_robin_schedule_structure():
    assert len(WEEKDAY_SYMBOLS) == 7
    assert all(len(WEEKDAY_SYMBOLS[day]) == 5 for day in range(7))
    all_symbols = [sym for day in range(7) for sym in WEEKDAY_SYMBOLS[day]]
    assert len(all_symbols) == 35
    assert len(set(all_symbols)) == len(all_symbols)


def test_get_symbols_for_day_rotation():
    assert get_symbols_for_day(0) == WEEKDAY_SYMBOLS[0]
    assert get_symbols_for_day(6) == WEEKDAY_SYMBOLS[6]
    assert get_symbols_for_day(7) == WEEKDAY_SYMBOLS[0]


def test_seven_run_cycle_covers_every_symbol_and_wraps_on_day_eight():
    monday = date(2026, 9, 7)
    plans = [build_round_robin_plan(monday + timedelta(days=offset)) for offset in range(8)]

    weekly_symbols = [symbol for plan in plans[:7] for symbol in plan["symbols"]]
    assert len(weekly_symbols) == 35
    assert len(set(weekly_symbols)) == 35
    assert plans[7]["symbols"] == plans[0]["symbols"]


def test_rerun_for_same_date_keeps_the_same_batch():
    run_date = date(2026, 9, 9)

    first_plan = build_round_robin_plan(run_date, run_id="scheduled__first")
    rerun_plan = build_round_robin_plan(run_date, run_id="manual__rerun")

    assert rerun_plan["symbols"] == first_plan["symbols"]
    assert rerun_plan["run_date"] == first_plan["run_date"]


def test_plan_uses_pipeline_timezone_and_respects_daily_limit():
    sunday_night_in_sao_paulo = datetime(2026, 9, 7, 2, tzinfo=UTC)
    plan = build_round_robin_plan(sunday_night_in_sao_paulo, run_id="scheduled__2026-09-06")

    assert get_pipeline_run_date(sunday_night_in_sao_paulo) == date(2026, 9, 6)
    assert plan["symbols"] == WEEKDAY_SYMBOLS[6]
    assert plan["planned_requests"] == len(plan["symbols"]) * len(ENDPOINTS_API)
    assert plan["planned_requests"] == API_LIMIT_PER_DAY
    assert plan["run_id"] == "scheduled__2026-09-06"


def test_plan_rejects_a_batch_above_the_daily_limit():
    with patch(
        "src.orchestration.round_robin.get_symbols_for_day",
        return_value=["A", "B", "C", "D", "E", "F"],
    ):
        with pytest.raises(ValueError, match="above the daily limit"):
            build_round_robin_plan(date(2026, 9, 7))


@patch("src.extract.api_client.AlphaVantageAPIClient.get", return_value={"Symbol": "AAPL"})
@patch("src.load.loader.GCPSLoader.upload_file")
def test_extract_overview_custom_symbols(mock_upload, mock_get):
    files = extract_overview(symbols=["AAPL"])
    assert len(files) == 1
    mock_get.assert_called_once_with("OVERVIEW", "AAPL")


@patch(
    "src.extract.api_client.AlphaVantageAPIClient.get",
    return_value={"symbol": "M", "annualReports": [], "quarterlyReports": []},
)
@patch("src.load.loader.GCPSLoader.upload_file")
def test_extract_balance_sheet_default_batch(mock_upload, mock_get):
    files = extract_balance_sheet(symbols=None)
    expected_count = len(get_symbols_for_day(date.today().weekday()))
    assert mock_get.call_count == expected_count
    assert len(files) == expected_count

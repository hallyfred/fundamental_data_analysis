from __future__ import annotations

from contextlib import ExitStack
from datetime import date, timedelta
from unittest.mock import patch

from src.extract.balance_sheet import extract_balance_sheet
from src.extract.cash_flow import extract_cash_flow
from src.extract.earning import extract_earning
from src.extract.income_statement import extract_income_statement
from src.extract.overview import extract_overview
from src.orchestration.round_robin import build_round_robin_plan

EXTRACTORS = {
    "OVERVIEW": extract_overview,
    "INCOME_STATEMENT": extract_income_statement,
    "BALANCE_SHEET": extract_balance_sheet,
    "CASH_FLOW": extract_cash_flow,
    "EARNINGS": extract_earning,
}

SUMMARY_PATCHES = [
    "src.extract.overview.log_batch_summary",
    "src.extract.income_statement.log_batch_summary",
    "src.extract.balance_sheet.log_batch_summary",
    "src.extract.cash_flow.log_batch_summary",
    "src.extract.earning.log_batch_summary",
]


def _api_payload(function: str, symbol: str) -> dict:
    if function == "OVERVIEW":
        return {
            "Symbol": symbol,
            "AssetType": "Common Stock",
            "Name": f"{symbol} Inc",
            "MarketCapitalization": 1,
        }
    if function == "EARNINGS":
        return {
            "symbol": symbol,
            "annualEarnings": [{"fiscalDateEnding": "2025-12-31", "reportedEPS": "1.00"}],
            "quarterlyEarnings": [],
        }
    return {
        "symbol": symbol,
        "annualReports": [{"fiscalDateEnding": "2025-12-31", "reportedCurrency": "USD"}],
        "quarterlyReports": [],
    }


def test_mocked_week_executes_35_unique_tickers_with_25_requests_per_run():
    monday = date(2026, 9, 7)
    summaries: list[dict] = []

    def capture_summary(_logger, summary):
        summaries.append(summary)

    with ExitStack() as stack:
        mock_get = stack.enter_context(
            patch(
                "src.extract.api_client.AlphaVantageAPIClient.get",
                side_effect=_api_payload,
            )
        )
        mock_upload = stack.enter_context(patch("src.load.loader.GCPSLoader.upload_file"))
        for target in SUMMARY_PATCHES:
            stack.enter_context(patch(target, side_effect=capture_summary))

        weekly_symbols: list[str] = []
        for offset in range(7):
            run_date = monday + timedelta(days=offset)
            run_id = f"mocked__{run_date.isoformat()}"
            plan = build_round_robin_plan(run_date, run_id=run_id)
            weekly_symbols.extend(plan["symbols"])

            requests_before_run = mock_get.call_count
            for endpoint in plan["endpoints"]:
                files = EXTRACTORS[endpoint](symbols=plan["symbols"], run_id=run_id)
                assert len(files) == 5

            assert mock_get.call_count - requests_before_run == plan["planned_requests"] == 25

    assert len(weekly_symbols) == 35
    assert len(set(weekly_symbols)) == 35
    assert mock_get.call_count == 175
    assert mock_upload.call_count == 175
    assert len(summaries) == 35
    assert all(summary["status"] == "SUCCESS" for summary in summaries)
    assert all(len(summary["planned_symbols"]) == 5 for summary in summaries)
    assert all(summary["completed_symbols"] == summary["planned_symbols"] for summary in summaries)
    assert all(summary["failed_symbols"] == [] for summary in summaries)
    assert all(summary["pending_symbols"] == [] for summary in summaries)
    assert all(summary["planned_requests"] == 5 for summary in summaries)


def test_day_eight_repeats_the_first_batch_without_changing_the_run_plan():
    monday = date(2026, 9, 7)
    first = build_round_robin_plan(monday)
    eighth = build_round_robin_plan(monday + timedelta(days=7))

    assert eighth["symbols"] == first["symbols"]
    assert eighth["planned_requests"] == first["planned_requests"] == 25

from unittest.mock import patch

import pytest

from src.extract.api_client import AlphaVantageRateLimitError
from src.extract.balance_sheet import extract_balance_sheet
from src.extract.batch import ExtractionBatchError
from src.extract.cash_flow import extract_cash_flow
from src.extract.earning import extract_earning
from src.extract.income_statement import extract_income_statement
from src.extract.overview import extract_overview

EXTRACTORS = [
    (extract_overview, "overview", "overview"),
    (extract_balance_sheet, "balance_sheet", "balance_sheet"),
    (extract_cash_flow, "cash_flow", "cash_flow"),
    (extract_income_statement, "income_statement", "income_statement"),
    (extract_earning, "earnings", "earning"),
]


@pytest.mark.parametrize(("extractor_fn", "payload_key", "endpoint_folder"), EXTRACTORS)
def test_extractors_success(extractor_fn, payload_key, endpoint_folder, sample_payloads):
    """Test the successful flow for every extractor with mocked API and GCS calls."""
    with (
        patch("src.extract.api_client.AlphaVantageAPIClient.get", return_value=sample_payloads[payload_key]),
        patch("src.load.loader.GCPSLoader.upload_file") as mock_upload,
    ):
        files = extractor_fn(symbols=["AAPL"])
        assert len(files) == 1
        assert endpoint_folder in files[0]
        mock_upload.assert_called_once()


def test_extractor_quarantine_routing(sample_payloads):
    """Ensure unexpected fields route the payload to quarantine instead of Bronze."""
    payload_with_extra = dict(sample_payloads["overview"], NewUnknownField="Extra")
    with (
        patch("src.extract.api_client.AlphaVantageAPIClient.get", return_value=payload_with_extra),
        patch("src.load.loader.GCPSLoader.upload_file") as mock_upload,
    ):
        with pytest.raises(ExtractionBatchError, match="did not complete"):
            extract_overview(symbols=["AAPL"])
        assert "quarantine" in mock_upload.call_args[0][1]


def test_extractor_handles_empty_payload():
    """Ensure an empty payload creates no uploads and produces a controlled failure."""
    with (
        patch("src.extract.api_client.AlphaVantageAPIClient.get", return_value={}),
        patch("src.load.loader.GCPSLoader.upload_file") as mock_upload,
    ):
        with pytest.raises(ExtractionBatchError, match="AAPL"):
            extract_overview(symbols=["AAPL"])
        mock_upload.assert_not_called()


def test_extractor_reports_partial_batch_failure(sample_payloads):
    with (
        patch(
            "src.extract.api_client.AlphaVantageAPIClient.get",
            side_effect=[sample_payloads["overview"], {}],
        ) as mock_get,
        patch("src.load.loader.GCPSLoader.upload_file"),
        patch("src.extract.overview.log_batch_summary") as mock_summary,
    ):
        with pytest.raises(ExtractionBatchError, match="MSFT"):
            extract_overview(symbols=["AAPL", "MSFT"], run_id="scheduled__test")

    assert mock_get.call_count == 2
    summary = mock_summary.call_args.args[1]
    assert summary["run_id"] == "scheduled__test"
    assert summary["status"] == "ERROR"
    assert summary["completed_symbols"] == ["AAPL"]
    assert summary["failed_symbols"] == ["MSFT"]
    assert summary["pending_symbols"] == []


def test_daily_rate_limit_stops_remaining_symbols():
    with (
        patch(
            "src.extract.api_client.AlphaVantageAPIClient.get",
            side_effect=AlphaVantageRateLimitError("25 requests per day"),
        ) as mock_get,
        patch("src.load.loader.GCPSLoader.upload_file"),
        patch("src.extract.overview.log_batch_summary") as mock_summary,
    ):
        with pytest.raises(ExtractionBatchError, match="Pending: MSFT"):
            extract_overview(symbols=["AAPL", "MSFT"])

    mock_get.assert_called_once()
    summary = mock_summary.call_args.args[1]
    assert summary["stopped_early"] is True
    assert summary["failed_symbols"] == ["AAPL"]
    assert summary["pending_symbols"] == ["MSFT"]

from unittest.mock import patch

import pytest

from src.extract.balance_sheet import extract_balance_sheet
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
    """Testa fluxo de sucesso para todos os extratores com mock da API e GCS."""
    with (
        patch("src.extract.api_client.AlphaVantageAPIClient.get", return_value=sample_payloads[payload_key]),
        patch("src.load.loader.GCPSLoader.upload_file") as mock_upload,
    ):
        files = extractor_fn(symbols=["AAPL"])
        assert len(files) == 1
        assert endpoint_folder in files[0]
        mock_upload.assert_called_once()


def test_extractor_quarantine_routing(sample_payloads):
    """Garante que campos inesperados desviam o arquivo para quarentena sem subir para Bronze."""
    payload_with_extra = dict(sample_payloads["overview"], NewUnknownField="Extra")
    with (
        patch("src.extract.api_client.AlphaVantageAPIClient.get", return_value=payload_with_extra),
        patch("src.load.loader.GCPSLoader.upload_file") as mock_upload,
    ):
        files = extract_overview(symbols=["AAPL"])
        assert len(files) == 0
        assert "quarantine" in mock_upload.call_args[0][1]


def test_extractor_handles_empty_payload():
    """Garante que payload vazio não gera uploads nem quebra o pipeline."""
    with (
        patch("src.extract.api_client.AlphaVantageAPIClient.get", return_value={}),
        patch("src.load.loader.GCPSLoader.upload_file") as mock_upload,
    ):
        assert extract_overview(symbols=["AAPL"]) == []
        mock_upload.assert_not_called()

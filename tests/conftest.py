from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_loader():
    with patch("src.load.loader.GCPSLoader") as mock_cls:
        instance = MagicMock()
        mock_cls.return_value = instance
        yield instance


@pytest.fixture(autouse=True)
def mock_clean_log():
    with (
        patch("src.extract.overview.upload_and_clean_log"),
        patch("src.extract.balance_sheet.upload_and_clean_log"),
        patch("src.extract.cash_flow.upload_and_clean_log"),
        patch("src.extract.income_statement.upload_and_clean_log"),
        patch("src.extract.earning.upload_and_clean_log"),
    ):
        yield


@pytest.fixture
def sample_payloads():
    statement = {
        "symbol": "AAPL",
        "annualReports": [{"fiscalDateEnding": "2023-09-30", "reportedCurrency": "USD"}],
        "quarterlyReports": [],
    }
    return {
        "overview": {
            "Symbol": "AAPL",
            "AssetType": "Common Stock",
            "Name": "Apple Inc",
            "MarketCapitalization": 3000000000000,
        },
        "balance_sheet": statement,
        "cash_flow": statement,
        "income_statement": statement,
        "earnings": {"symbol": "AAPL", "annualEarnings": [], "quarterlyEarnings": []},
    }

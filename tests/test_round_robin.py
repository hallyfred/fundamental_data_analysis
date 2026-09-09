from datetime import date
from unittest.mock import patch

from config.config import WEEKDAY_SYMBOLS, get_symbols_for_day
from src.extract.balance_sheet import extract_balance_sheet
from src.extract.overview import extract_overview


def test_round_robin_schedule_structure():
    assert len(WEEKDAY_SYMBOLS) == 7
    all_symbols = [sym for day in range(7) for sym in WEEKDAY_SYMBOLS[day]]
    assert len(set(all_symbols)) == len(all_symbols)


def test_get_symbols_for_day_rotation():
    assert get_symbols_for_day(0) == WEEKDAY_SYMBOLS[0]
    assert get_symbols_for_day(6) == WEEKDAY_SYMBOLS[6]
    assert get_symbols_for_day(7) == WEEKDAY_SYMBOLS[0]


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

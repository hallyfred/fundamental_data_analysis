from unittest.mock import MagicMock, patch

import pytest
import requests

from src.extract.api_client import (
    AlphaVantageAPIClient,
    AlphaVantageAPIError,
    AlphaVantageRateLimitError,
)

BASE_URL, API_KEY = "https://www.alphavantage.co/query", "test_key"


@pytest.fixture
def client():
    return AlphaVantageAPIClient(BASE_URL, API_KEY)


@pytest.mark.parametrize("invalid_key", ["", None])
def test_init_validates_api_key(invalid_key):
    with pytest.raises(ValueError):
        AlphaVantageAPIClient(BASE_URL, invalid_key)


@patch("src.extract.api_client.requests.get")
def test_get_success(mock_get, client):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: {"Symbol": "AAPL"})
    assert client.get("OVERVIEW", "AAPL") == {"Symbol": "AAPL"}
    assert mock_get.call_args[1]["timeout"] == 30


@patch("src.extract.api_client.time.sleep")
@patch("src.extract.api_client.requests.get")
def test_rate_limit_retry_and_exhaust(mock_get, mock_sleep, client):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: {"Note": "Rate limit"})
    with pytest.raises(AlphaVantageRateLimitError):
        client.get("OVERVIEW", "AAPL")
    assert mock_get.call_count == client.MAX_RETRIES


@pytest.mark.parametrize("payload", [{"Information": "Demo key"}, {"Error Message": "Invalid call"}])
@patch("src.extract.api_client.requests.get")
def test_non_retryable_semantic_errors(mock_get, payload, client):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: payload)
    with pytest.raises(AlphaVantageAPIError):
        client.get("OVERVIEW", "AAPL")
    assert mock_get.call_count == 1


@patch("src.extract.api_client.time.sleep")
@patch("src.extract.api_client.requests.get")
def test_retry_on_network_failure_then_succeed(mock_get, mock_sleep, client):
    mock_get.side_effect = [
        requests.exceptions.Timeout("Timeout"),
        MagicMock(status_code=200, json=lambda: {"Symbol": "AAPL"}),
    ]
    assert client.get("OVERVIEW", "AAPL") == {"Symbol": "AAPL"}
    assert mock_get.call_count == 2


@patch("src.extract.api_client.requests.get")
def test_api_key_sanitization_in_error_messages(mock_get, client):
    raw_response = {
        "Information": f"We have detected your API key as {API_KEY} and our standard API rate limit is 25 requests per day."
    }
    mock_get.return_value = MagicMock(status_code=200, json=lambda: raw_response)
    with pytest.raises(AlphaVantageRateLimitError) as exc_info:
        client.get("OVERVIEW", "AAPL")

    err_text = str(exc_info.value)
    assert API_KEY not in err_text
    assert "***REDACTED_API_KEY***" in err_text

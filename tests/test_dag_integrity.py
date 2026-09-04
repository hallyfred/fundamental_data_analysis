from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

try:
    from dags.financial_pipeline_dag import run_extractor, select_batch_for_run

    AIRFLOW_LOADED = True
except (ImportError, Exception):
    AIRFLOW_LOADED = False

pytestmark = pytest.mark.skipif(not AIRFLOW_LOADED, reason="Airflow requer ambiente POSIX/Linux")


def test_select_batch_for_run():
    mock_ti = MagicMock()
    batch = select_batch_for_run(data_interval_start=datetime(2026, 9, 7), ti=mock_ti)
    assert isinstance(batch, list)
    mock_ti.xcom_push.assert_called_once_with(key="ticker_batch", value=batch)


@patch("src.extract.overview.extract_overview", return_value=["f1.json"])
def test_run_extractor_overview(mock_extract):
    mock_ti = MagicMock()
    mock_ti.xcom_pull.return_value = ["AAPL"]
    assert run_extractor("overview", ti=mock_ti) == ["f1.json"]
    mock_extract.assert_called_once_with(symbols=["AAPL"])


def test_run_extractor_invalid_raises_error():
    with pytest.raises(ValueError):
        run_extractor("unknown_fn", ti=MagicMock())

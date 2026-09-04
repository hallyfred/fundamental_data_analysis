import json
from unittest.mock import MagicMock

import pytest

from src.utils.helpers import count_real_rows
from src.utils.logger import log_extraction, setup_logger, upload_and_clean_log


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ([1, 2, 3], 3),
        ({"Symbol": "AAPL"}, 1),
        ([], 0),
        (None, 0),
        ({"annual": [1, 2], "quarterly": [3, 4, 5]}, 5),
    ],
)
def test_count_real_rows(payload, expected):
    assert count_real_rows(payload) == expected


def test_logger_and_ndjson_extraction(tmp_path):
    log_file = str(tmp_path / "extraction.log")
    logger = setup_logger(log_file)
    assert logger.log_file == log_file

    log_extraction(logger, "SUCCESS", "bkt", "2026-09-03", "overview", "AAPL", 1, 0.01, 0.1, None)
    with open(log_file, encoding="utf-8") as f:
        lines = f.readlines()

    assert len(lines) == 1
    assert json.loads(lines[0])["symbol"] == "AAPL"


def test_upload_and_clean_log(tmp_path):
    log_file = tmp_path / "test.log"
    log_file.write_text('{"a":1}')

    mock_loader = MagicMock()
    upload_and_clean_log(mock_loader, str(log_file), "dest.log")

    mock_loader.upload_file.assert_called_once_with(str(log_file), "dest.log")
    assert not log_file.exists()


def test_upload_and_clean_log_handles_missing_file():
    mock_loader = MagicMock()
    upload_and_clean_log(mock_loader, "missing.log", "dest.log")
    mock_loader.upload_file.assert_not_called()

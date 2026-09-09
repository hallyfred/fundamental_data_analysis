import json
from unittest.mock import MagicMock

from src.utils.watermark import WatermarkManager


def test_watermark_initial_load_missing_file():
    mock_loader = MagicMock()
    mock_loader.download_as_text.return_value = None

    manager = WatermarkManager(mock_loader, "overview")
    assert manager._watermarks == {}
    assert manager.get_latest_date("AAPL") is None


def test_watermark_loads_existing_state():
    mock_loader = MagicMock()
    mock_loader.download_as_text.return_value = json.dumps({"AAPL": "2023-09-30"})

    manager = WatermarkManager(mock_loader, "overview")
    assert manager.get_latest_date("AAPL") == "2023-09-30"


def test_watermark_should_upload_logic():
    mock_loader = MagicMock()
    mock_loader.download_as_text.return_value = json.dumps({"AAPL": "2023-09-30"})

    manager = WatermarkManager(mock_loader, "overview")

    # Novo símbolo que não existe no watermark: deve enviar
    assert manager.should_upload("MSFT", "2023-06-30") is True

    # Data mais recente que a registrada: deve enviar
    assert manager.should_upload("AAPL", "2024-09-30") is True

    # Data IGUAL à registrada: NÃO deve enviar (duplicado)
    assert manager.should_upload("AAPL", "2023-09-30") is False

    # Data ANTERIOR à registrada: NÃO deve enviar
    assert manager.should_upload("AAPL", "2022-09-30") is False

    # Data ausente/vazia: deve enviar por segurança
    assert manager.should_upload("AAPL", None) is True
    assert manager.should_upload("AAPL", "") is True


def test_watermark_record_and_save():
    mock_loader = MagicMock()
    mock_loader.download_as_text.return_value = None

    manager = WatermarkManager(mock_loader, "balance_sheet")
    manager.record_success("AAPL", "2023-09-30")

    assert manager._dirty is True
    assert manager.get_latest_date("AAPL") == "2023-09-30"

    manager.save()
    mock_loader.upload_text.assert_called_once()
    assert manager._dirty is False

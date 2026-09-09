from unittest.mock import patch

import pytest
from google.cloud.exceptions import GoogleCloudError

from src.load.loader import GCPSLoader


@patch("src.load.loader.storage.Client")
def test_upload_file_success(mock_client_cls):
    mock_client = mock_client_cls.return_value
    mock_blob = mock_client.bucket.return_value.blob.return_value

    GCPSLoader("proj", "bucket").upload_file("local.json", "dest.json")

    mock_client.bucket.assert_called_once_with("bucket")
    mock_blob.upload_from_filename.assert_called_once_with("local.json")


@patch("src.load.loader.storage.Client")
def test_upload_file_propagates_exception(mock_client_cls):
    mock_client_cls.return_value.bucket.return_value.blob.return_value.upload_from_filename.side_effect = (
        GoogleCloudError("Denied")
    )
    with pytest.raises(GoogleCloudError):
        GCPSLoader("proj", "bucket").upload_file("local.json", "dest.json")

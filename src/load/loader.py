import logging

from google.cloud import storage

logger = logging.getLogger(__name__)


class GCPSLoader:
    def __init__(self, project_id, bucket_name):
        self.project_id = project_id
        self.bucket_name = bucket_name
        self.client = storage.Client(project=project_id)
        self.bucket = self.client.bucket(bucket_name)

    def upload_file(self, local_file_path, destination_blob_name):
        """
        Upload a local file to GCS.
        Propagate upload failures so the caller can handle them.
        """
        blob = self.bucket.blob(destination_blob_name)
        blob.upload_from_filename(local_file_path)
        logger.info(f"Upload completed: {local_file_path} → gs://{self.bucket_name}/{destination_blob_name}")

    def download_as_text(self, destination_blob_name: str) -> str | None:
        """Download a blob as text, returning None when it does not exist."""
        try:
            blob = self.bucket.blob(destination_blob_name)
            if not blob.exists():
                return None
            return blob.download_as_text()
        except Exception as e:
            logger.warning(f"Could not read {destination_blob_name} from GCS: {e}")
            return None

    def upload_text(self, text_content: str, destination_blob_name: str, content_type: str = "application/json"):
        """Upload text directly to GCS without a local file."""
        blob = self.bucket.blob(destination_blob_name)
        blob.upload_from_string(text_content, content_type=content_type)
        logger.info(f"Text upload completed → gs://{self.bucket_name}/{destination_blob_name}")

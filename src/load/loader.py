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
        Faz upload de um arquivo local para o GCS.
        Propaga a exceção em caso de falha — é responsabilidade do caller tratar o erro.
        """
        blob = self.bucket.blob(destination_blob_name)
        blob.upload_from_filename(local_file_path)
        logger.info(f"Upload concluído: {local_file_path} → gs://{self.bucket_name}/{destination_blob_name}")

import os
from google.cloud import storage


class GCPSLoader:
    def __init__(self, project_id, bucket_name):
        self.project_id = project_id
        self.bucket_name = bucket_name
        self.client = storage.Client(project=project_id)
        self.bucket = self.client.bucket(bucket_name)


    def upload_file(self, local_file_path, destination_blob_name):
        try:

            blob = self.bucket.blob(destination_blob_name)
            blob.upload_from_filename(local_file_path)
            print(f"File {local_file_path} uploaded to {destination_blob_name}.")
            return True
        except Exception as e:
            print(f"Error occurred while uploading {local_file_path} to GCP: {e}")
            return False

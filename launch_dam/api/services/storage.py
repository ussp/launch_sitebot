"""Storage service for Railway S3-compatible buckets."""

import os
from io import BytesIO
from typing import BinaryIO

import boto3
from botocore.config import Config


class StorageService:
    """Service for interacting with Railway Object Storage (S3-compatible)."""

    def __init__(self):
        self.endpoint = os.getenv("BUCKET_ENDPOINT")
        self.bucket_name = os.getenv("BUCKET_NAME")
        self.access_key = os.getenv("BUCKET_ACCESS_KEY_ID")
        self.secret_key = os.getenv("BUCKET_SECRET_ACCESS_KEY")

        if not all([self.endpoint, self.bucket_name, self.access_key, self.secret_key]):
            raise ValueError("Missing bucket configuration. Set BUCKET_* environment variables.")

        self.client = boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=Config(signature_version="s3v4"),
        )

    def upload_thumbnail(self, asset_id: str, image_data: bytes | BinaryIO) -> str:
        """
        Upload a thumbnail image to the bucket.

        Args:
            asset_id: The asset UUID or source ID
            image_data: Image bytes or file-like object

        Returns:
            The public URL of the uploaded thumbnail
        """
        key = f"thumbnails/{asset_id}.jpg"

        if isinstance(image_data, bytes):
            image_data = BytesIO(image_data)

        self.client.upload_fileobj(
            image_data,
            self.bucket_name,
            key,
            ExtraArgs={"ContentType": "image/jpeg"},
        )

        return self.get_thumbnail_url(asset_id)

    def get_thumbnail_url(self, asset_id: str) -> str:
        """Get the public URL for a thumbnail."""
        key = f"thumbnails/{asset_id}.jpg"
        # Railway buckets provide public URLs
        return f"{self.endpoint}/{self.bucket_name}/{key}"

    def delete_thumbnail(self, asset_id: str) -> None:
        """Delete a thumbnail from the bucket."""
        key = f"thumbnails/{asset_id}.jpg"
        self.client.delete_object(Bucket=self.bucket_name, Key=key)

    def thumbnail_exists(self, asset_id: str) -> bool:
        """Check if a thumbnail exists in the bucket."""
        key = f"thumbnails/{asset_id}.jpg"
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except self.client.exceptions.ClientError:
            return False

    def list_thumbnails(self, prefix: str = "thumbnails/", max_keys: int = 1000) -> list[str]:
        """List thumbnail keys in the bucket."""
        response = self.client.list_objects_v2(
            Bucket=self.bucket_name,
            Prefix=prefix,
            MaxKeys=max_keys,
        )
        return [obj["Key"] for obj in response.get("Contents", [])]


def get_storage_service() -> StorageService | None:
    """Get storage service if configured, None otherwise."""
    try:
        return StorageService()
    except ValueError:
        return None

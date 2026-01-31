#!/usr/bin/env python3
"""
Upload thumbnails from local storage to Railway bucket.

This script reads thumbnails from the local canto_assets/thumbnails directory
and uploads them to the Railway S3-compatible bucket.
"""

import asyncio
import os
import sys
from pathlib import Path

import asyncpg
import boto3
from botocore.config import Config

# Default paths
DEFAULT_THUMBNAILS_DIR = Path(__file__).parent.parent.parent / "canto_assets" / "thumbnails"


def get_s3_client():
    """Create S3 client for Railway bucket."""
    endpoint = os.getenv("BUCKET_ENDPOINT")
    access_key = os.getenv("BUCKET_ACCESS_KEY_ID")
    secret_key = os.getenv("BUCKET_SECRET_ACCESS_KEY")

    if not all([endpoint, access_key, secret_key]):
        raise ValueError(
            "Missing bucket configuration. Set BUCKET_ENDPOINT, "
            "BUCKET_ACCESS_KEY_ID, and BUCKET_SECRET_ACCESS_KEY"
        )

    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4"),
    )


async def upload_thumbnails(
    thumbnails_dir: Path,
    database_url: str,
    bucket_name: str,
    batch_size: int = 100,
    dry_run: bool = False,
):
    """Upload thumbnails to Railway bucket and update database URLs."""

    print(f"Thumbnails directory: {thumbnails_dir}")
    print(f"Bucket: {bucket_name}")
    print(f"Dry run: {dry_run}")

    # Get S3 client
    client = get_s3_client()
    endpoint = os.getenv("BUCKET_ENDPOINT")

    # Connect to database
    print("Connecting to database...")
    conn = await asyncpg.connect(database_url)

    # Get list of thumbnail files
    thumb_files = list(thumbnails_dir.glob("*_thumb.jpg"))
    total = len(thumb_files)
    print(f"Found {total} thumbnail files")

    uploaded = 0
    errors = []

    try:
        for i, thumb_path in enumerate(thumb_files):
            try:
                # Extract source ID from filename (e.g., "abc123_thumb.jpg" -> "abc123")
                filename = thumb_path.name
                source_id_short = filename.replace("_thumb.jpg", "")

                # Upload to bucket
                key = f"thumbnails/{source_id_short}.jpg"
                public_url = f"{endpoint}/{bucket_name}/{key}"

                if not dry_run:
                    with open(thumb_path, "rb") as f:
                        client.upload_fileobj(
                            f,
                            bucket_name,
                            key,
                            ExtraArgs={"ContentType": "image/jpeg"},
                        )

                    # Update database with new URL
                    # Match by source_id containing the short ID
                    await conn.execute(
                        """
                        UPDATE assets
                        SET thumbnail_url = $1, updated_in_db = NOW()
                        WHERE source_id LIKE '%' || $2
                        """,
                        public_url,
                        source_id_short,
                    )

                uploaded += 1

                if (i + 1) % batch_size == 0:
                    print(f"Progress: {i + 1}/{total} ({(i + 1) / total * 100:.1f}%)")

            except Exception as e:
                errors.append({"file": str(thumb_path), "error": str(e)})
                if len(errors) <= 5:
                    print(f"Error uploading {thumb_path.name}: {e}")

    finally:
        await conn.close()

    print(f"\n=== Upload Complete ===")
    print(f"Uploaded: {uploaded}/{total}")
    print(f"Errors: {len(errors)}")

    if errors and len(errors) <= 20:
        print("\nErrors:")
        for err in errors:
            print(f"  - {err['file']}: {err['error']}")

    return {"uploaded": uploaded, "total": total, "errors": len(errors)}


async def main():
    """Main entry point."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)

    bucket_name = os.getenv("BUCKET_NAME")
    if not bucket_name:
        print("ERROR: BUCKET_NAME environment variable not set")
        sys.exit(1)

    thumbnails_dir = Path(os.getenv("THUMBNAILS_DIR", DEFAULT_THUMBNAILS_DIR))
    if not thumbnails_dir.exists():
        print(f"ERROR: Thumbnails directory not found: {thumbnails_dir}")
        sys.exit(1)

    dry_run = os.getenv("DRY_RUN", "").lower() in ("true", "1", "yes")
    batch_size = int(os.getenv("BATCH_SIZE", "100"))

    await upload_thumbnails(
        thumbnails_dir=thumbnails_dir,
        database_url=database_url,
        bucket_name=bucket_name,
        batch_size=batch_size,
        dry_run=dry_run,
    )


if __name__ == "__main__":
    asyncio.run(main())

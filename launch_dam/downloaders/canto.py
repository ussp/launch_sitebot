"""Canto DAM downloader implementation."""

import asyncio
import io
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from PIL import Image

from .base import AssetDownloader


class CantoDownloader(AssetDownloader):
    """
    Downloader for Canto DAM assets.

    Syncs assets from a Canto instance to Launch DAM.
    """

    def __init__(
        self,
        api_base_url: str,
        canto_base_url: str,
        canto_token: str,
    ):
        """
        Initialize the Canto downloader.

        Args:
            api_base_url: Base URL of the Launch DAM API
            canto_base_url: Base URL of the Canto instance (e.g., https://launchtrampolinepark.canto.com)
            canto_token: Canto API token
        """
        super().__init__(api_base_url)
        self.canto_url = canto_base_url.rstrip("/")
        self.canto_token = canto_token

    async def _canto_request(
        self, method: str, endpoint: str, **kwargs
    ) -> dict | list | bytes:
        """Make a request to the Canto API."""
        url = f"{self.canto_url}/api/v1/{endpoint.lstrip('/')}"
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.canto_token}"

        response = await self.client.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        return response.content

    async def get_assets(
        self,
        modified_since: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """
        Get assets from Canto.

        Args:
            modified_since: Only return assets modified after this time
            limit: Maximum number of assets to return
            offset: Pagination offset

        Returns:
            List of asset metadata dictionaries
        """
        params = {
            "limit": limit,
            "start": offset,
            "sortBy": "time",
            "sortDirection": "descending",
        }

        if modified_since:
            # Canto uses Unix timestamp in milliseconds
            params["lastModified"] = int(modified_since.timestamp() * 1000)

        result = await self._canto_request("GET", "/search", params=params)
        return result.get("results", [])

    async def download_preview(self, asset_id: str, size: int = 800) -> bytes:
        """
        Download a preview/thumbnail for an asset.

        Args:
            asset_id: Canto asset ID
            size: Maximum dimension for the preview

        Returns:
            JPEG image bytes
        """
        # Get asset details to find preview URL
        asset = await self._canto_request("GET", f"/image/{asset_id}")
        preview_url = asset.get("url", {}).get("preview")

        if not preview_url:
            raise ValueError(f"No preview URL for asset {asset_id}")

        # Download the preview
        response = await self.client.get(preview_url)
        response.raise_for_status()

        # Resize if needed
        img = Image.open(io.BytesIO(response.content))
        if max(img.size) > size:
            img.thumbnail((size, size), Image.Resampling.LANCZOS)

        # Convert to JPEG
        output = io.BytesIO()
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(output, format="JPEG", quality=85)
        return output.getvalue()

    def _map_canto_to_dam(self, canto_asset: dict) -> dict[str, Any]:
        """
        Map Canto asset metadata to Launch DAM format.

        Args:
            canto_asset: Raw Canto asset data

        Returns:
            Metadata dictionary for Launch DAM ingestion
        """
        data = canto_asset.get("default", {})
        scheme = canto_asset.get("scheme", "image")

        # Parse timestamps
        created = None
        modified = None
        if data.get("Date Created"):
            try:
                created = datetime.fromisoformat(data["Date Created"])
            except ValueError:
                pass
        if data.get("Date Modified"):
            try:
                modified = datetime.fromisoformat(data["Date Modified"])
            except ValueError:
                pass

        # Get album path
        albums = canto_asset.get("album", [])
        album_path = albums[0] if albums else None

        return {
            "source_id": canto_asset.get("id"),
            "filename": canto_asset.get("name", "unknown"),
            "content_type": data.get("Content Type"),
            "file_size": int(data.get("Size", 0)) if data.get("Size") else None,
            "width": int(data.get("Width", 0)) if data.get("Width") else None,
            "height": int(data.get("Height", 0)) if data.get("Height") else None,
            "md5_checksum": data.get("MD5"),
            "album_path": album_path,
            "source_tags": data.get("tag", []),
            "source_keywords": data.get("keyword", []),
            "approval_status": data.get("Approval Status"),
            "owner_name": data.get("Owner"),
            "canto_created_at": created.isoformat() if created else None,
            "canto_modified_at": modified.isoformat() if modified else None,
            "source_url": canto_asset.get("url", {}).get("preview"),
        }

    async def sync(self, since: datetime | None = None) -> dict:
        """
        Sync assets from Canto to Launch DAM.

        Args:
            since: Only sync assets modified after this time

        Returns:
            Sync summary
        """
        synced = 0
        skipped = 0
        failed = 0
        errors = []

        offset = 0
        batch_size = 100

        while True:
            # Get batch of assets
            assets = await self.get_assets(
                modified_since=since,
                limit=batch_size,
                offset=offset,
            )

            if not assets:
                break

            for canto_asset in assets:
                try:
                    source_id = canto_asset.get("id")
                    if not source_id:
                        continue

                    # Check if already exists with same MD5
                    existing = await self.check_existing(source_id)
                    canto_md5 = canto_asset.get("default", {}).get("MD5")

                    if existing and existing.get("md5_checksum") == canto_md5:
                        skipped += 1
                        continue

                    # Map metadata
                    metadata = self._map_canto_to_dam(canto_asset)

                    # Register asset
                    asset_id = await self.register_asset(metadata)

                    # Download and upload thumbnail
                    try:
                        thumb_bytes = await self.download_preview(source_id)
                        await self.upload_thumbnail(asset_id, thumb_bytes)
                    except Exception as e:
                        # Continue even if thumbnail fails
                        print(f"Warning: Thumbnail failed for {source_id}: {e}")

                    # Complete ingestion
                    await self.complete_ingestion(asset_id)

                    synced += 1

                    # Rate limiting
                    await asyncio.sleep(0.1)

                except Exception as e:
                    failed += 1
                    errors.append({
                        "source_id": canto_asset.get("id"),
                        "error": str(e),
                    })

            offset += batch_size

            # Check if we got fewer than requested (last page)
            if len(assets) < batch_size:
                break

        return {
            "synced": synced,
            "skipped": skipped,
            "failed": failed,
            "errors": errors[:20] if errors else [],
        }


class CantoMetadataDownloader(AssetDownloader):
    """
    Downloader that reads from existing canto_metadata.json file.

    Use this for initial migration when you have a pre-downloaded
    metadata file from the Canto sync script.
    """

    def __init__(self, api_base_url: str, metadata_path: str):
        """
        Initialize from metadata file.

        Args:
            api_base_url: Base URL of the Launch DAM API
            metadata_path: Path to canto_metadata.json file
        """
        super().__init__(api_base_url)
        self.metadata_path = Path(metadata_path)

    async def sync(self, since: datetime | None = None) -> dict:
        """
        Sync assets from the metadata file.

        Args:
            since: Ignored for file-based sync

        Returns:
            Sync summary
        """
        # Load metadata
        with open(self.metadata_path) as f:
            metadata = json.load(f)

        assets = metadata.get("assets", [])
        synced = 0
        skipped = 0
        failed = 0
        errors = []

        for asset in assets:
            try:
                data = asset.get("data", {})
                albums = asset.get("albums", [])

                # Parse timestamps
                created = None
                modified = None
                if data.get("created"):
                    try:
                        created = datetime.strptime(data["created"], "%Y-%m-%d %H:%M")
                    except ValueError:
                        pass
                if data.get("modified"):
                    try:
                        modified = datetime.strptime(data["modified"], "%Y-%m-%d %H:%M")
                    except ValueError:
                        pass

                dam_metadata = {
                    "source_id": asset["id"],
                    "filename": asset.get("name", "unknown"),
                    "content_type": data.get("content_type"),
                    "file_size": int(data.get("size", 0)) if data.get("size") else None,
                    "width": int(data.get("width", 0)) if data.get("width") else None,
                    "height": int(data.get("height", 0)) if data.get("height") else None,
                    "md5_checksum": data.get("md5"),
                    "album_path": albums[0] if albums else None,
                    "source_tags": data.get("tag", []),
                    "source_keywords": data.get("keyword", []),
                    "approval_status": data.get("approval"),
                    "owner_name": data.get("owner"),
                    "canto_created_at": created.isoformat() if created else None,
                    "canto_modified_at": modified.isoformat() if modified else None,
                    "source_url": data.get("preview240"),
                }

                # Register and complete
                asset_id = await self.register_asset(dam_metadata)
                await self.complete_ingestion(asset_id)

                synced += 1

            except Exception as e:
                failed += 1
                errors.append({
                    "source_id": asset.get("id"),
                    "error": str(e),
                })

        return {
            "synced": synced,
            "skipped": skipped,
            "failed": failed,
            "total_in_file": len(assets),
            "errors": errors[:20] if errors else [],
        }

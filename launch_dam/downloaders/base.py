"""Base class for asset downloaders."""

import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import httpx


class AssetDownloader(ABC):
    """
    Base class for asset downloaders.

    Any downloader (Canto, manual upload, other integrations) should
    inherit from this class and implement the sync() method.
    """

    def __init__(self, api_base_url: str):
        """
        Initialize the downloader.

        Args:
            api_base_url: Base URL of the Launch DAM API
        """
        self.api_url = api_base_url.rstrip("/")
        self._spec: dict | None = None
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=60.0)
        await self._load_spec()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get the HTTP client."""
        if not self._client:
            raise RuntimeError("Downloader not initialized. Use 'async with' context manager.")
        return self._client

    @property
    def spec(self) -> dict:
        """Get the ingestion specification."""
        if not self._spec:
            raise RuntimeError("Spec not loaded. Use 'async with' context manager.")
        return self._spec

    async def _load_spec(self) -> None:
        """Load the ingestion specification from the API."""
        response = await self.client.get(f"{self.api_url}/api/ingest/spec")
        response.raise_for_status()
        self._spec = response.json()

    def sanitize_filename(self, name: str) -> str:
        """
        Sanitize a filename according to the spec rules.

        Args:
            name: Original filename

        Returns:
            Sanitized filename
        """
        rules = self.spec["naming"]["sanitize_rules"]

        # Replace spaces
        if rules.get("replace_spaces"):
            name = name.replace(" ", rules["replace_spaces"])

        # Remove special characters
        if rules.get("remove_special"):
            allowed = rules.get("allowed_chars", "a-zA-Z0-9_-.")
            name = re.sub(f"[^{allowed}]", "", name)

        # Enforce max length
        if rules.get("max_length"):
            name = name[: rules["max_length"]]

        # Lowercase if specified
        if rules.get("lowercase"):
            name = name.lower()

        return name

    def generate_filename(self, source_id: str, original_name: str, ext: str) -> str:
        """
        Generate a filename according to the spec pattern.

        Args:
            source_id: Unique source identifier
            original_name: Original filename (without extension)
            ext: File extension

        Returns:
            Generated filename
        """
        pattern = self.spec["naming"]["pattern"]
        sanitized = self.sanitize_filename(original_name)

        return pattern.format(
            source_id=source_id[:32],  # Limit source_id length
            sanitized_name=sanitized,
            ext=ext.lstrip("."),
        )

    async def register_asset(self, metadata: dict[str, Any]) -> str:
        """
        Register an asset with the API.

        Args:
            metadata: Asset metadata conforming to ingestion spec

        Returns:
            Assigned asset UUID

        Raises:
            ValueError: If required fields are missing
            httpx.HTTPError: If API request fails
        """
        # Validate required fields
        required = self.spec.get("required_metadata", [])
        missing = [f for f in required if f not in metadata]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        response = await self.client.post(
            f"{self.api_url}/api/ingest/register",
            json=metadata,
        )
        response.raise_for_status()
        return response.json()["id"]

    async def upload_thumbnail(self, asset_id: str, image_bytes: bytes) -> dict:
        """
        Upload a thumbnail for an asset.

        Args:
            asset_id: Asset UUID
            image_bytes: JPEG image bytes

        Returns:
            Upload response
        """
        response = await self.client.put(
            f"{self.api_url}/api/ingest/thumbnail/{asset_id}",
            content=image_bytes,
            headers={"Content-Type": "image/jpeg"},
        )
        response.raise_for_status()
        return response.json()

    async def complete_ingestion(self, asset_id: str) -> dict:
        """
        Mark ingestion as complete for an asset.

        This triggers classification and search text generation.

        Args:
            asset_id: Asset UUID

        Returns:
            Completion response
        """
        response = await self.client.post(
            f"{self.api_url}/api/ingest/complete/{asset_id}"
        )
        response.raise_for_status()
        return response.json()

    async def check_existing(self, source_id: str) -> dict | None:
        """
        Check if an asset already exists by source ID.

        Args:
            source_id: Source system identifier

        Returns:
            Existing asset data or None
        """
        try:
            response = await self.client.get(
                f"{self.api_url}/api/assets",
                params={"source_id": source_id},
            )
            response.raise_for_status()
            assets = response.json()
            return assets[0] if assets else None
        except httpx.HTTPStatusError:
            return None

    async def batch_register(self, assets: list[dict[str, Any]]) -> dict:
        """
        Register multiple assets in a batch.

        Args:
            assets: List of asset metadata dictionaries

        Returns:
            Batch registration response with results and errors
        """
        response = await self.client.post(
            f"{self.api_url}/api/ingest/batch-register",
            json=assets,
        )
        response.raise_for_status()
        return response.json()

    @abstractmethod
    async def sync(self, since: datetime | None = None) -> dict:
        """
        Sync assets from the source system.

        This is the main entry point that subclasses must implement.

        Args:
            since: Optional datetime to sync only assets modified after this time

        Returns:
            Sync summary with counts of synced/skipped/failed assets
        """
        raise NotImplementedError

    async def full_sync(self) -> dict:
        """
        Perform a full sync of all assets.

        Returns:
            Sync summary
        """
        return await self.sync(since=None)

    async def incremental_sync(self, since: datetime) -> dict:
        """
        Sync only assets modified since the given datetime.

        Args:
            since: Only sync assets modified after this time

        Returns:
            Sync summary
        """
        return await self.sync(since=since)

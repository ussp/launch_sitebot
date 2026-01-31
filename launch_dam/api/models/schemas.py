"""Pydantic schemas for the DAM API."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    """Filters for search queries."""

    asset_type: str | None = Field(None, description="Filter by asset type: template or inspiration")
    album: str | None = Field(None, description="Filter by album name")
    media_type: str | None = Field(None, description="Filter by media type: image, video, document")
    content_type: str | None = Field(None, description="Filter by MIME type")
    min_reusability: int | None = Field(None, ge=1, le=5, description="Minimum reusability score")
    has_text_overlay_space: bool | None = Field(None, description="Filter for assets with text overlay space")
    min_energy: int | None = Field(None, ge=1, le=10, description="Minimum energy level")
    no_hardcoded_date: bool | None = Field(None, description="Exclude assets with hardcoded dates")
    no_hardcoded_location: bool | None = Field(None, description="Exclude assets with hardcoded locations")


class SearchRequest(BaseModel):
    """Request body for search endpoint."""

    query: str = Field(..., description="Natural language search query")
    filters: SearchFilters | None = Field(None, description="Optional filters")
    limit: int = Field(20, ge=1, le=100, description="Maximum number of results")
    include_reasoning: bool = Field(False, description="Include match reasoning in results")


class SearchResult(BaseModel):
    """Single search result."""

    id: UUID
    filename: str
    thumbnail_url: str | None
    full_url: str | None
    asset_type: str | None
    album_name: str | None
    media_type: str | None
    content_type: str | None
    width: int | None
    height: int | None
    score: float
    reasoning: str | None = None
    semantic_description: str | None = None


class SearchResponse(BaseModel):
    """Response from search endpoint."""

    results: list[SearchResult]
    total: int
    query: str
    filters_applied: dict[str, Any] | None = None


class AssetSummary(BaseModel):
    """Summarized asset for list views."""

    id: UUID
    filename: str
    thumbnail_url: str | None
    asset_type: str | None
    album_name: str | None
    media_type: str | None
    processing_status: str | None


class Asset(BaseModel):
    """Full asset details."""

    id: UUID
    source_id: str
    source_type: str | None
    source_scheme: str | None

    filename: str
    content_type: str | None
    media_type: str | None
    file_size: int | None
    width: int | None
    height: int | None
    resolution: float | None
    orientation: str | None
    md5_checksum: str | None

    album_path: str | None
    album_name: str | None

    source_tags: list[str] | None
    source_keywords: list[str] | None
    approval_status: str | None
    owner_name: str | None

    canto_created_at: datetime | None
    canto_modified_at: datetime | None

    thumbnail_url: str | None
    full_url: str | None
    canto_preview_240: str | None

    asset_type: str | None
    reusability_score: int | None

    scene: dict | None
    people: dict | None
    objects: dict | None
    text_content: dict | None
    hardcoded_elements: dict | None
    composition: dict | None
    framing: dict | None
    edges: dict | None
    colors: dict | None
    style: dict | None
    quality: dict | None
    brand: dict | None
    sub_brand: str | None
    mood: dict | None
    tone: dict | None
    editorial: dict | None
    editing_notes: dict | None
    video_metadata: dict | None

    auto_tags: list[str] | None
    semantic_description: str | None

    processing_status: str | None
    synced_at: datetime | None
    analyzed_at: datetime | None
    indexed_at: datetime | None

    class Config:
        from_attributes = True


class AssetCreate(BaseModel):
    """Asset creation request (for manual upload)."""

    filename: str
    content_type: str | None = None
    file_size: int | None = None
    width: int | None = None
    height: int | None = None
    album_path: str | None = None
    tags: list[str] | None = None


class Album(BaseModel):
    """Album information."""

    name: str
    path: str | None
    asset_count: int
    has_templates: bool = False


class IngestRegister(BaseModel):
    """Request to register a new asset for ingestion."""

    source_id: str
    filename: str
    content_type: str | None = None
    media_type: str | None = None
    file_size: int | None = None
    width: int | None = None
    height: int | None = None
    md5_checksum: str | None = None
    album_path: str | None = None
    album_name: str | None = None
    source_tags: list[str] | None = None
    source_keywords: list[str] | None = None
    source_url: str | None = None
    approval_status: str | None = None
    owner_name: str | None = None
    canto_created_at: datetime | None = None
    canto_modified_at: datetime | None = None


class IngestComplete(BaseModel):
    """Response after completing ingestion."""

    id: UUID
    status: str
    asset_type: str | None
    message: str


class ProcessingStats(BaseModel):
    """Processing pipeline statistics."""

    pending: int = 0
    classified: int = 0
    enriched: int = 0
    indexed: int = 0
    failed: int = 0


class SyncStatus(BaseModel):
    """Overall sync status."""

    total_assets: int
    by_status: ProcessingStats
    last_processed: datetime | None
    embedding_version: int = 1

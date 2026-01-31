"""Ingestion routes for the DAM system."""

import json
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..db import execute, fetch, fetchrow, fetchval
from ..db.queries import INSERT_ASSET
from ..models.schemas import IngestComplete, IngestRegister
from ..services.classifier import classify_asset, extract_album_name, infer_media_type

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.get("/spec")
async def get_ingestion_spec():
    """Return the ingestion specification for downloaders."""
    return {
        "version": "1.0",
        "storage": {
            "thumbnails": {
                "base_path": "thumbnails/",
                "max_dimension": 800,
                "format": "jpg",
                "quality": 85,
            },
            "full": {
                "base_path": "full/",
                "preserve_format": True,
            },
        },
        "naming": {
            "pattern": "{source_id}_{sanitized_name}.{ext}",
            "sanitize_rules": {
                "replace_spaces": "_",
                "remove_special": True,
                "max_length": 100,
                "lowercase": False,
            },
        },
        "required_metadata": [
            "source_id",
            "filename",
        ],
        "optional_metadata": [
            "content_type",
            "media_type",
            "file_size",
            "width",
            "height",
            "md5_checksum",
            "album_path",
            "album_name",
            "source_tags",
            "source_keywords",
            "approval_status",
            "owner_name",
            "canto_created_at",
            "canto_modified_at",
        ],
        "classification": {
            "location_patterns": [
                "brooklyn", "annarbor", "westhouston", "warwick",
                "lewisville", "clearwater", "northattleboro",
            ],
            "date_patterns": ["\\d{4}", "(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\\d{4}"],
            "event_patterns": ["grandopening", "mlkday", "presidentsday", "stpatricks", "blackfriday"],
            "reusable_albums": ["Brand Kit", "Templates", "Social Media Templates"],
            "reusable_patterns": ["template", "flyer", "generic", "base"],
        },
    }


@router.post("/register", response_model=IngestComplete)
async def register_asset(request: IngestRegister) -> IngestComplete:
    """
    Register a new asset for ingestion.

    This creates the asset record and classifies it.
    """
    # Infer media type if not provided
    media_type = request.media_type or infer_media_type(
        request.content_type, request.filename
    )

    # Extract album name if not provided
    album_name = request.album_name or extract_album_name(request.album_path)

    # Classify the asset
    asset_type = classify_asset(request.filename, request.album_path)

    # Insert or update the asset
    try:
        asset_id = await fetchval(
            INSERT_ASSET,
            request.source_id,
            "canto",  # source_type
            None,  # source_scheme
            request.filename,
            request.content_type,
            media_type,
            request.file_size,
            request.width,
            request.height,
            None,  # resolution
            None,  # orientation
            request.md5_checksum,
            request.album_path,
            album_name,
            request.source_tags,
            request.source_keywords,
            request.approval_status,
            request.owner_name,
            request.canto_created_at,
            request.canto_modified_at,
            None,  # canto_time
            None,  # thumbnail_url (set later)
            None,  # full_url
            request.source_url,  # canto_preview_240
            None,  # canto_preview_uri
            asset_type,
            "pending",  # processing_status
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to register asset: {e}")

    return IngestComplete(
        id=asset_id,
        status="registered",
        asset_type=asset_type,
        message=f"Asset registered successfully as {asset_type}",
    )


@router.put("/thumbnail/{asset_id}")
async def upload_thumbnail(
    asset_id: UUID,
    file: UploadFile = File(...),
):
    """Upload a thumbnail for an asset."""
    from ..services.storage import get_storage_service

    # Verify asset exists
    row = await fetchrow("SELECT id, filename, source_id FROM assets WHERE id = $1", asset_id)
    if not row:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Try to use Railway bucket storage
    storage = get_storage_service()
    if storage:
        # Upload to Railway bucket
        contents = await file.read()
        thumbnail_url = storage.upload_thumbnail(str(asset_id), contents)
    else:
        # Fallback to local path placeholder
        thumbnail_url = f"/storage/thumbnails/{asset_id}.jpg"

    await execute(
        "UPDATE assets SET thumbnail_url = $2, updated_in_db = NOW() WHERE id = $1",
        asset_id,
        thumbnail_url,
    )

    return {"id": str(asset_id), "thumbnail_url": thumbnail_url, "status": "uploaded"}


@router.post("/complete/{asset_id}", response_model=IngestComplete)
async def complete_ingestion(asset_id: UUID) -> IngestComplete:
    """
    Mark ingestion as complete and trigger processing.

    This will:
    1. Generate search_text from available metadata
    2. Queue the asset for embedding generation
    """
    from ..services.openai_client import build_search_text

    # Get the asset
    row = await fetchrow("SELECT * FROM assets WHERE id = $1", asset_id)
    if not row:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Build search text from current metadata
    search_text = build_search_text(dict(row))

    # Update asset with search text and mark as classified
    await execute(
        """
        UPDATE assets
        SET search_text = $2, processing_status = 'classified', updated_in_db = NOW()
        WHERE id = $1
        """,
        asset_id,
        search_text,
    )

    return IngestComplete(
        id=asset_id,
        status="completed",
        asset_type=row.get("asset_type"),
        message="Ingestion complete, asset queued for embedding generation",
    )


@router.post("/batch-register")
async def batch_register_assets(assets: list[IngestRegister]) -> dict:
    """Register multiple assets in a batch."""
    results = []
    errors = []

    for i, asset in enumerate(assets):
        try:
            result = await register_asset(asset)
            results.append({"index": i, "id": str(result.id), "status": "success"})
        except Exception as e:
            errors.append({"index": i, "source_id": asset.source_id, "error": str(e)})

    return {
        "registered": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
    }

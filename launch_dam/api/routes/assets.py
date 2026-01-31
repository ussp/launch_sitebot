"""Asset routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from ..db import fetch, fetchrow
from ..db.queries import GET_ASSET_BY_ID
from ..models.schemas import Asset, AssetSummary
from ..services.openai_client import OpenAIService
from ..services.search import SearchService

router = APIRouter(prefix="/assets", tags=["assets"])


def get_search_service() -> SearchService:
    """Dependency to get search service."""
    try:
        openai = OpenAIService()
    except ValueError:
        openai = None
    return SearchService(openai)


@router.get("/{asset_id}", response_model=Asset)
async def get_asset(asset_id: UUID) -> Asset:
    """Get full details for a specific asset."""
    row = await fetchrow(GET_ASSET_BY_ID, asset_id)
    if not row:
        raise HTTPException(status_code=404, detail="Asset not found")
    return Asset(**row)


@router.get("", response_model=list[AssetSummary])
async def list_assets(
    album: str | None = None,
    asset_type: str | None = None,
    media_type: str | None = None,
    processing_status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[AssetSummary]:
    """List assets with optional filters."""
    conditions = []
    params = []
    param_idx = 1

    if album:
        conditions.append(f"album_name = ${param_idx}")
        params.append(album)
        param_idx += 1

    if asset_type:
        conditions.append(f"asset_type = ${param_idx}")
        params.append(asset_type)
        param_idx += 1

    if media_type:
        conditions.append(f"media_type = ${param_idx}")
        params.append(media_type)
        param_idx += 1

    if processing_status:
        conditions.append(f"processing_status = ${param_idx}")
        params.append(processing_status)
        param_idx += 1

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.extend([limit, offset])

    sql = f"""
        SELECT id, filename, thumbnail_url, asset_type, album_name, media_type, processing_status
        FROM assets
        {where_clause}
        ORDER BY created_in_db DESC
        LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """

    rows = await fetch(sql, *params)
    return [AssetSummary(**row) for row in rows]


@router.post("/{asset_id}/analyze")
async def analyze_asset(
    asset_id: UUID,
    service: SearchService = Depends(get_search_service),
) -> dict:
    """
    Trigger vision analysis for a specific asset.

    This will run GPT-4o Vision analysis and update the asset metadata.
    """
    if not service.openai:
        raise HTTPException(
            status_code=503, detail="OpenAI service not configured"
        )

    # Get the asset
    row = await fetchrow(GET_ASSET_BY_ID, asset_id)
    if not row:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Check if we have a thumbnail URL to analyze
    thumbnail_url = row.get("thumbnail_url") or row.get("canto_preview_240")
    if not thumbnail_url:
        raise HTTPException(
            status_code=400, detail="Asset has no thumbnail URL for analysis"
        )

    # Run vision analysis
    try:
        is_video = row.get("media_type") == "video"
        analysis = await service.openai.analyze_image(thumbnail_url, is_video)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vision analysis failed: {e}")

    # Update the asset with vision results
    from ..db import execute
    from ..services.openai_client import build_search_text
    import json

    # Build search text from analysis
    merged = {**row, **analysis}
    search_text = build_search_text(merged)

    # Update asset
    await execute(
        """
        UPDATE assets SET
            scene = $2, people = $3, objects = $4, text_content = $5,
            hardcoded_elements = $6, composition = $7, framing = $8, edges = $9,
            colors = $10, style = $11, quality = $12, brand = $13, sub_brand = $14,
            mood = $15, tone = $16, editorial = $17, editing_notes = $18,
            auto_tags = $19, semantic_description = $20, search_queries = $21,
            reusability_score = $22, search_text = $23,
            analyzed_at = NOW(), processing_status = 'enriched', updated_in_db = NOW()
        WHERE id = $1
        """,
        asset_id,
        json.dumps(analysis.get("scene")),
        json.dumps(analysis.get("people")),
        json.dumps(analysis.get("objects")),
        json.dumps(analysis.get("text_content")),
        json.dumps(analysis.get("hardcoded_elements")),
        json.dumps(analysis.get("composition")),
        json.dumps(analysis.get("framing")),
        json.dumps(analysis.get("edges")),
        json.dumps(analysis.get("colors")),
        json.dumps(analysis.get("style")),
        json.dumps(analysis.get("quality")),
        json.dumps(analysis.get("brand")),
        analysis.get("sub_brand"),
        json.dumps(analysis.get("mood")),
        json.dumps(analysis.get("tone")),
        json.dumps(analysis.get("editorial")),
        json.dumps(analysis.get("editing_notes")),
        analysis.get("auto_tags"),
        analysis.get("semantic_description"),
        analysis.get("search_queries"),
        analysis.get("hardcoded_elements", {}).get("reusability_score"),
        search_text,
    )

    return {
        "id": str(asset_id),
        "status": "analyzed",
        "semantic_description": analysis.get("semantic_description"),
        "auto_tags": analysis.get("auto_tags"),
        "reusability_score": analysis.get("hardcoded_elements", {}).get("reusability_score"),
    }

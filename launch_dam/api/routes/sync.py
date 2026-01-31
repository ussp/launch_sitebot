"""Sync and processing status routes."""

from fastapi import APIRouter

from ..db import execute, fetch, fetchval
from ..db.queries import GET_ASSET_COUNT, GET_PENDING_ASSETS, GET_PROCESSING_STATS
from ..models.schemas import ProcessingStats, SyncStatus

router = APIRouter(prefix="/sync", tags=["sync"])


@router.get("/status", response_model=SyncStatus)
async def get_sync_status() -> SyncStatus:
    """Get overall sync and processing status."""
    # Get total count
    total = await fetchval(GET_ASSET_COUNT)

    # Get counts by status
    rows = await fetch(GET_PROCESSING_STATS)
    stats = ProcessingStats()
    for row in rows:
        status = row["processing_status"]
        count = row["count"]
        if status == "pending":
            stats.pending = count
        elif status == "classified":
            stats.classified = count
        elif status == "enriched":
            stats.enriched = count
        elif status == "indexed":
            stats.indexed = count
        elif status == "failed":
            stats.failed = count

    # Get last processed timestamp
    last_processed = await fetchval(
        "SELECT MAX(indexed_at) FROM assets WHERE indexed_at IS NOT NULL"
    )

    # Get current embedding version
    embedding_version = await fetchval(
        "SELECT MAX(embedding_version) FROM assets"
    ) or 1

    return SyncStatus(
        total_assets=total or 0,
        by_status=stats,
        last_processed=last_processed,
        embedding_version=embedding_version,
    )


@router.get("/pending")
async def get_pending_assets(limit: int = 50):
    """Get assets pending processing."""
    rows = await fetch(GET_PENDING_ASSETS, limit)
    return {"pending": rows, "count": len(rows)}


@router.post("/retry-failed")
async def retry_failed_assets():
    """Reset failed assets to pending for retry."""
    result = await execute(
        """
        UPDATE assets
        SET processing_status = 'pending', processing_error = NULL, updated_in_db = NOW()
        WHERE processing_status = 'failed'
        """
    )

    # Extract count from result string (e.g., "UPDATE 5")
    count = 0
    if result and result.startswith("UPDATE"):
        try:
            count = int(result.split()[1])
        except (IndexError, ValueError):
            pass

    return {"reset_count": count, "message": f"Reset {count} failed assets to pending"}


@router.post("/reindex-all")
async def reindex_all_assets():
    """Mark all indexed assets for re-embedding (version bump)."""
    # Get current max version
    current_version = await fetchval("SELECT MAX(embedding_version) FROM assets") or 1
    new_version = current_version + 1

    # Reset all indexed assets to enriched so they get re-embedded
    result = await execute(
        """
        UPDATE assets
        SET processing_status = 'enriched', updated_in_db = NOW()
        WHERE processing_status = 'indexed'
        """
    )

    count = 0
    if result and result.startswith("UPDATE"):
        try:
            count = int(result.split()[1])
        except (IndexError, ValueError):
            pass

    return {
        "reindex_count": count,
        "new_version": new_version,
        "message": f"Marked {count} assets for re-indexing",
    }


@router.get("/stats")
async def get_detailed_stats():
    """Get detailed statistics about the asset library."""
    # Processing stats
    processing_stats = await fetch(GET_PROCESSING_STATS)

    # Asset type distribution
    type_stats = await fetch(
        """
        SELECT asset_type, COUNT(*) as count
        FROM assets
        GROUP BY asset_type
        ORDER BY count DESC
        """
    )

    # Media type distribution
    media_stats = await fetch(
        """
        SELECT media_type, COUNT(*) as count
        FROM assets
        WHERE media_type IS NOT NULL
        GROUP BY media_type
        ORDER BY count DESC
        """
    )

    # Top albums
    album_stats = await fetch(
        """
        SELECT album_name, COUNT(*) as count
        FROM assets
        WHERE album_name IS NOT NULL
        GROUP BY album_name
        ORDER BY count DESC
        LIMIT 20
        """
    )

    # Embedding coverage
    embedding_stats = await fetchval(
        """
        SELECT COUNT(*) FROM assets WHERE embedding IS NOT NULL
        """
    )
    total = await fetchval(GET_ASSET_COUNT)

    return {
        "total_assets": total,
        "processing_status": {row["processing_status"]: row["count"] for row in processing_stats},
        "by_asset_type": {row["asset_type"]: row["count"] for row in type_stats},
        "by_media_type": {row["media_type"]: row["count"] for row in media_stats},
        "top_albums": album_stats,
        "embedding_coverage": {
            "with_embedding": embedding_stats or 0,
            "total": total or 0,
            "percentage": round((embedding_stats or 0) / (total or 1) * 100, 2),
        },
    }

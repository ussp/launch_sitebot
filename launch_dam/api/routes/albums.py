"""Album routes."""

from fastapi import APIRouter

from ..db import fetch
from ..db.queries import GET_ALBUMS
from ..models.schemas import Album

router = APIRouter(prefix="/albums", tags=["albums"])


@router.get("", response_model=list[Album])
async def list_albums() -> list[Album]:
    """List all albums with asset counts."""
    rows = await fetch(GET_ALBUMS)
    return [
        Album(
            name=row["name"],
            path=row["path"],
            asset_count=row["asset_count"],
            has_templates=row.get("has_templates", False),
        )
        for row in rows
    ]


@router.get("/{album_name}/assets")
async def list_album_assets(
    album_name: str,
    limit: int = 50,
    offset: int = 0,
):
    """List assets in a specific album."""
    rows = await fetch(
        """
        SELECT id, filename, thumbnail_url, asset_type, media_type, processing_status
        FROM assets
        WHERE album_name = $1
        ORDER BY filename
        LIMIT $2 OFFSET $3
        """,
        album_name,
        limit,
        offset,
    )
    return {"album": album_name, "assets": rows, "count": len(rows)}

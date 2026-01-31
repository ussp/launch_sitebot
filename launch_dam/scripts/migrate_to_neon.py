#!/usr/bin/env python3
"""
Migrate assets from canto_metadata.json to Neon PostgreSQL.

This script reads the existing Canto metadata and inserts it into the Neon database.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import asyncpg

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.classifier import classify_asset, extract_album_name, infer_media_type
from api.services.openai_client import build_search_text


def parse_canto_datetime(dt_str: str | None) -> datetime | None:
    """Parse Canto datetime string to datetime object."""
    if not dt_str:
        return None
    try:
        # Format: "2026-01-26 19:51"
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def extract_short_id(full_id: str) -> str:
    """Extract the short asset ID from the full Canto ID.

    Example: '7cfb62c0_0fc4_4f42_9464_09ffe5e92d9c_image_8468c2dbd53247b9b80c9c151970ca15'
    Returns: '8468c2dbd53247b9b80c9c151970ca15'
    """
    parts = full_id.split("_")
    if len(parts) >= 6:
        return parts[-1]
    return full_id


async def migrate_assets(database_url: str, metadata_path: str, batch_size: int = 100):
    """Migrate assets from metadata JSON to Neon PostgreSQL."""

    # Load metadata
    print(f"Loading metadata from {metadata_path}...")
    with open(metadata_path) as f:
        metadata = json.load(f)

    assets = metadata.get("assets", [])
    total_assets = len(assets)
    print(f"Found {total_assets} assets to migrate")

    # Connect to database
    print(f"Connecting to database...")
    conn = await asyncpg.connect(database_url)

    # Prepare insert statement
    insert_sql = """
    INSERT INTO assets (
        source_id, source_type, source_scheme,
        filename, content_type, media_type, file_size,
        width, height, resolution, orientation, md5_checksum,
        album_path, album_name,
        source_tags, source_keywords, approval_status, owner_name,
        canto_created_at, canto_modified_at, canto_time,
        thumbnail_url, canto_preview_240, canto_preview_uri,
        asset_type, search_text, processing_status
    ) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
        $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27
    )
    ON CONFLICT (source_id) DO UPDATE SET
        filename = EXCLUDED.filename,
        content_type = EXCLUDED.content_type,
        media_type = EXCLUDED.media_type,
        file_size = EXCLUDED.file_size,
        width = EXCLUDED.width,
        height = EXCLUDED.height,
        md5_checksum = EXCLUDED.md5_checksum,
        album_path = EXCLUDED.album_path,
        album_name = EXCLUDED.album_name,
        source_tags = EXCLUDED.source_tags,
        source_keywords = EXCLUDED.source_keywords,
        canto_modified_at = EXCLUDED.canto_modified_at,
        canto_preview_240 = EXCLUDED.canto_preview_240,
        search_text = EXCLUDED.search_text,
        updated_in_db = NOW()
    RETURNING id
    """

    migrated = 0
    errors = []

    try:
        for i, asset in enumerate(assets):
            try:
                # Extract data
                data = asset.get("data", {})
                albums = asset.get("albums", [])
                album_path = albums[0] if albums else None
                album_name = extract_album_name(album_path)

                # Parse dimensions
                width = int(data.get("width", 0)) if data.get("width") else None
                height = int(data.get("height", 0)) if data.get("height") else None
                file_size = int(data.get("size", 0)) if data.get("size") else None
                resolution = float(data.get("resolution", 0)) if data.get("resolution") else None

                # Get content type and infer media type
                content_type = data.get("content_type")
                filename = asset.get("name", "unknown")
                media_type = infer_media_type(content_type, filename)

                # Classify asset
                asset_type = classify_asset(filename, album_path)

                # Build local thumbnail path
                short_id = extract_short_id(asset["id"])
                thumbnail_url = f"/storage/thumbnails/{short_id}_thumb.jpg"

                # Build search text from available data
                asset_dict = {
                    "filename": filename,
                    "album_name": album_name,
                    "album_path": album_path,
                    "source_tags": data.get("tag", []),
                    "source_keywords": data.get("keyword", []),
                }
                search_text = build_search_text(asset_dict)

                # Parse timestamps
                created = parse_canto_datetime(data.get("created"))
                modified = parse_canto_datetime(data.get("modified"))
                canto_time = asset.get("time")

                # Insert
                await conn.execute(
                    insert_sql,
                    asset["id"],                      # source_id
                    "canto",                          # source_type
                    asset.get("scheme"),              # source_scheme
                    filename,                         # filename
                    content_type,                     # content_type
                    media_type,                       # media_type
                    file_size,                        # file_size
                    width,                            # width
                    height,                           # height
                    resolution,                       # resolution
                    data.get("orientation"),          # orientation
                    data.get("md5"),                  # md5_checksum
                    album_path,                       # album_path
                    album_name,                       # album_name
                    data.get("tag", []),              # source_tags
                    data.get("keyword", []),          # source_keywords
                    data.get("approval"),             # approval_status
                    data.get("owner"),                # owner_name
                    created,                          # canto_created_at
                    modified,                         # canto_modified_at
                    canto_time,                       # canto_time
                    thumbnail_url,                    # thumbnail_url (local path)
                    data.get("preview240"),           # canto_preview_240
                    data.get("uri"),                  # canto_preview_uri
                    asset_type,                       # asset_type
                    search_text,                      # search_text
                    "classified",                     # processing_status
                )

                migrated += 1

                # Progress update
                if (i + 1) % batch_size == 0:
                    print(f"Progress: {i + 1}/{total_assets} ({(i + 1) / total_assets * 100:.1f}%)")

            except Exception as e:
                errors.append({"index": i, "id": asset.get("id"), "error": str(e)})
                if len(errors) <= 10:
                    print(f"Error migrating asset {i}: {e}")

    finally:
        await conn.close()

    print(f"\n=== Migration Complete ===")
    print(f"Migrated: {migrated}/{total_assets}")
    print(f"Errors: {len(errors)}")

    if errors and len(errors) <= 20:
        print("\nError details:")
        for err in errors:
            print(f"  - {err['id']}: {err['error']}")
    elif errors:
        print(f"\nFirst 10 errors:")
        for err in errors[:10]:
            print(f"  - {err['id']}: {err['error']}")


async def update_album_counts(database_url: str):
    """Update album table with counts from assets."""
    print("Updating album counts...")
    conn = await asyncpg.connect(database_url)

    try:
        # Get album stats
        albums = await conn.fetch("""
            SELECT
                album_path as path,
                album_name as name,
                COUNT(*) as count,
                BOOL_OR(asset_type = 'template') as is_reusable
            FROM assets
            WHERE album_path IS NOT NULL
            GROUP BY album_path, album_name
        """)

        # Upsert albums
        for album in albums:
            await conn.execute("""
                INSERT INTO albums (path, name, asset_count, is_reusable)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (path) DO UPDATE SET
                    asset_count = EXCLUDED.asset_count,
                    is_reusable = EXCLUDED.is_reusable
            """, album["path"], album["name"], album["count"], album["is_reusable"])

        print(f"Updated {len(albums)} albums")

    finally:
        await conn.close()


async def main():
    """Main migration entry point."""
    # Get database URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        print("Example: postgresql://user:pass@host/dbname")
        sys.exit(1)

    # Default metadata path
    metadata_path = os.getenv(
        "METADATA_PATH",
        str(Path(__file__).parent.parent.parent / "canto_assets" / "canto_metadata.json")
    )

    if not Path(metadata_path).exists():
        print(f"ERROR: Metadata file not found: {metadata_path}")
        sys.exit(1)

    # Run migration
    await migrate_assets(database_url, metadata_path)
    await update_album_counts(database_url)

    print("\nMigration complete!")


if __name__ == "__main__":
    asyncio.run(main())

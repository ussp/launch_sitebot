#!/usr/bin/env python3
"""
Run vision analysis on assets to extract rich metadata.

This script processes template assets (or specified assets) through
GPT-4o Vision to extract detailed visual metadata for search.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import asyncpg

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.openai_client import OpenAIService, build_search_text


async def run_vision_analysis(
    database_url: str,
    openai_api_key: str,
    asset_type_filter: str | None = "template",
    album_filter: str | None = None,
    max_assets: int | None = None,
    analyze_unanalyzed_only: bool = True,
):
    """Run vision analysis on qualifying assets."""

    print("Initializing OpenAI client...")
    os.environ["OPENAI_API_KEY"] = openai_api_key
    openai = OpenAIService()

    print("Connecting to database...")
    conn = await asyncpg.connect(database_url)

    try:
        # Build query for assets to analyze
        conditions = ["media_type IN ('image', 'video')"]
        params = []
        param_idx = 1

        if analyze_unanalyzed_only:
            conditions.append("analyzed_at IS NULL")

        if asset_type_filter:
            conditions.append(f"asset_type = ${param_idx}")
            params.append(asset_type_filter)
            param_idx += 1

        if album_filter:
            conditions.append(f"album_name ILIKE ${param_idx}")
            params.append(f"%{album_filter}%")
            param_idx += 1

        # Need a URL to analyze
        conditions.append("(canto_preview_240 IS NOT NULL OR thumbnail_url IS NOT NULL)")

        where_clause = " AND ".join(conditions)
        query = f"""
            SELECT id, filename, media_type, canto_preview_240, thumbnail_url,
                   album_name, album_path, source_tags, source_keywords
            FROM assets
            WHERE {where_clause}
            ORDER BY created_in_db ASC
        """

        if max_assets:
            query += f" LIMIT {max_assets}"

        rows = await conn.fetch(query, *params)
        total = len(rows)
        print(f"Found {total} assets to analyze")

        if total == 0:
            print("No assets to process")
            return

        processed = 0
        errors = []

        for i, row in enumerate(rows):
            try:
                # Get image URL (prefer Canto CDN, fall back to local thumbnail)
                image_url = row["canto_preview_240"] or row["thumbnail_url"]
                if not image_url:
                    continue

                # For local thumbnails, we'd need to serve them or upload
                # For now, skip if no Canto URL (migration will handle later)
                if image_url.startswith("/storage"):
                    print(f"  Skipping {row['filename']} - local thumbnail only")
                    continue

                is_video = row["media_type"] == "video"

                print(f"  [{i + 1}/{total}] Analyzing: {row['filename']}")

                # Run vision analysis
                analysis = await openai.analyze_image(image_url, is_video)

                # Build updated search text
                merged = {**dict(row), **analysis}
                search_text = build_search_text(merged)

                # Update asset
                await conn.execute(
                    """
                    UPDATE assets SET
                        scene = $2::jsonb,
                        people = $3::jsonb,
                        objects = $4::jsonb,
                        text_content = $5::jsonb,
                        hardcoded_elements = $6::jsonb,
                        composition = $7::jsonb,
                        framing = $8::jsonb,
                        edges = $9::jsonb,
                        colors = $10::jsonb,
                        style = $11::jsonb,
                        quality = $12::jsonb,
                        brand = $13::jsonb,
                        sub_brand = $14,
                        mood = $15::jsonb,
                        tone = $16::jsonb,
                        editorial = $17::jsonb,
                        editing_notes = $18::jsonb,
                        auto_tags = $19,
                        semantic_description = $20,
                        search_queries = $21,
                        reusability_score = $22,
                        search_text = $23,
                        analyzed_at = NOW(),
                        processing_status = 'enriched',
                        updated_in_db = NOW()
                    WHERE id = $1
                    """,
                    row["id"],
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

                processed += 1

                # Rate limiting - GPT-4o vision has limits
                await asyncio.sleep(1)

            except Exception as e:
                errors.append({"id": str(row["id"]), "filename": row["filename"], "error": str(e)})
                print(f"    Error: {e}")

                # Mark as failed
                await conn.execute(
                    """
                    UPDATE assets
                    SET processing_error = $2, updated_in_db = NOW()
                    WHERE id = $1
                    """,
                    row["id"],
                    str(e),
                )

    finally:
        await conn.close()

    print(f"\n=== Vision Analysis Complete ===")
    print(f"Processed: {processed}/{total}")
    print(f"Errors: {len(errors)}")

    if errors:
        print("\nErrors:")
        for err in errors[:20]:
            print(f"  - {err['filename']}: {err['error']}")


async def main():
    """Main entry point."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set")
        sys.exit(1)

    # Options from environment
    asset_type = os.getenv("ASSET_TYPE", "template")  # 'template', 'inspiration', or None for all
    album_filter = os.getenv("ALBUM_FILTER")
    max_assets = os.getenv("MAX_ASSETS")
    max_assets = int(max_assets) if max_assets else None

    await run_vision_analysis(
        database_url,
        openai_api_key,
        asset_type_filter=asset_type if asset_type else None,
        album_filter=album_filter,
        max_assets=max_assets,
    )


if __name__ == "__main__":
    asyncio.run(main())

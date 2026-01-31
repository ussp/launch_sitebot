#!/usr/bin/env python3
"""
Generate embeddings for assets that have search_text but no embedding.

This script processes assets in batches and generates OpenAI embeddings
for semantic search.
"""

import asyncio
import os
import sys
from pathlib import Path

import asyncpg

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


async def generate_embeddings(
    database_url: str,
    openai_api_key: str,
    batch_size: int = 50,
    max_assets: int | None = None,
):
    """Generate embeddings for assets without them."""
    from openai import AsyncOpenAI

    print("Initializing OpenAI client...")
    client = AsyncOpenAI(api_key=openai_api_key)

    print("Connecting to database...")
    conn = await asyncpg.connect(database_url)

    try:
        # Get assets that need embeddings
        query = """
            SELECT id, search_text
            FROM assets
            WHERE search_text IS NOT NULL
              AND search_text != ''
              AND embedding IS NULL
              AND processing_status IN ('classified', 'enriched')
            ORDER BY created_in_db ASC
        """
        if max_assets:
            query += f" LIMIT {max_assets}"

        rows = await conn.fetch(query)
        total = len(rows)
        print(f"Found {total} assets needing embeddings")

        if total == 0:
            print("No assets to process")
            return

        processed = 0
        errors = []

        # Process in batches
        for i in range(0, total, batch_size):
            batch = rows[i : i + batch_size]
            texts = [row["search_text"][:8000] for row in batch]  # Limit text length

            try:
                # Generate embeddings in batch
                response = await client.embeddings.create(
                    model="text-embedding-3-small",
                    input=texts,
                    dimensions=1536,
                )

                # Update each asset
                for j, embedding_data in enumerate(response.data):
                    row = batch[j]
                    embedding = embedding_data.embedding
                    embedding_str = f"[{','.join(map(str, embedding))}]"

                    await conn.execute(
                        """
                        UPDATE assets
                        SET embedding = $2::vector,
                            embedding_version = 1,
                            processing_status = 'indexed',
                            indexed_at = NOW(),
                            updated_in_db = NOW()
                        WHERE id = $1
                        """,
                        row["id"],
                        embedding_str,
                    )

                processed += len(batch)
                print(f"Progress: {processed}/{total} ({processed / total * 100:.1f}%)")

            except Exception as e:
                errors.append({"batch_start": i, "error": str(e)})
                print(f"Error processing batch starting at {i}: {e}")

                # Mark these as failed
                for row in batch:
                    await conn.execute(
                        """
                        UPDATE assets
                        SET processing_status = 'failed',
                            processing_error = $2,
                            updated_in_db = NOW()
                        WHERE id = $1
                        """,
                        row["id"],
                        str(e),
                    )

            # Small delay to avoid rate limits
            await asyncio.sleep(0.1)

    finally:
        await conn.close()

    print(f"\n=== Embedding Generation Complete ===")
    print(f"Processed: {processed}/{total}")
    print(f"Errors: {len(errors)}")


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

    batch_size = int(os.getenv("BATCH_SIZE", "50"))
    max_assets = os.getenv("MAX_ASSETS")
    max_assets = int(max_assets) if max_assets else None

    await generate_embeddings(database_url, openai_api_key, batch_size, max_assets)


if __name__ == "__main__":
    asyncio.run(main())

"""Search service for the DAM system."""

import re
from uuid import UUID

from ..db import fetch, fetchval
from ..db.queries import (
    FILTERED_HYBRID_SEARCH,
    GET_ASSET_BY_ID,
    HYBRID_SEARCH,
    KEYWORD_SEARCH,
    SEMANTIC_SEARCH,
)
from ..models.schemas import SearchFilters, SearchResult
from .openai_client import OpenAIService
from .storage import get_storage_service


class SearchService:
    """Service for searching assets."""

    def __init__(self, openai_service: OpenAIService | None = None):
        self.openai = openai_service
        self.storage = get_storage_service()

    def _get_presigned_thumbnail(self, thumbnail_url: str | None) -> str | None:
        """Convert a stored thumbnail URL to a presigned URL."""
        if not thumbnail_url or not self.storage:
            return thumbnail_url

        # Extract the key from various URL formats
        # Format: https://storage.railway.app/bucket-name/thumbnails/xxx.jpg
        # Or: /storage/thumbnails/xxx.jpg
        match = re.search(r"thumbnails/([^/]+\.jpg)", thumbnail_url)
        if match:
            key = f"thumbnails/{match.group(1)}"
            try:
                return self.storage.get_presigned_url(key, expires_in=3600)
            except Exception:
                return thumbnail_url
        return thumbnail_url

    async def search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        limit: int = 20,
        include_reasoning: bool = False,
    ) -> tuple[list[SearchResult], int]:
        """
        Search for assets using hybrid semantic + keyword search.

        Args:
            query: Natural language search query
            filters: Optional filters to apply
            limit: Maximum number of results
            include_reasoning: Whether to include match reasoning

        Returns:
            Tuple of (results list, total count)
        """
        # Generate embedding for semantic search
        if self.openai:
            try:
                query_embedding = await self.openai.generate_embedding(query)
            except Exception:
                # Fall back to keyword-only search if embedding fails
                query_embedding = None
        else:
            query_embedding = None

        # Execute search query
        if filters and self._has_active_filters(filters):
            rows = await self._filtered_search(query, query_embedding, filters, limit)
        elif query_embedding:
            rows = await self._hybrid_search(query, query_embedding, limit)
        else:
            rows = await self._keyword_search(query, limit)

        # Convert to SearchResult objects
        results = []
        for row in rows:
            reasoning = None
            if include_reasoning:
                reasoning = self._generate_reasoning(row, query)

            results.append(
                SearchResult(
                    id=row["id"],
                    filename=row["filename"],
                    thumbnail_url=self._get_presigned_thumbnail(row.get("thumbnail_url")),
                    full_url=row.get("full_url"),
                    asset_type=row.get("asset_type"),
                    album_name=row.get("album_name"),
                    media_type=row.get("media_type"),
                    content_type=row.get("content_type"),
                    width=row.get("width"),
                    height=row.get("height"),
                    score=float(row.get("score") or row.get("combined_score") or 0),
                    reasoning=reasoning,
                    semantic_description=row.get("semantic_description"),
                )
            )

        # Get total count (approximate for now)
        total = len(results)

        return results, total

    async def _hybrid_search(
        self, query: str, embedding: list[float], limit: int
    ) -> list[dict]:
        """Execute hybrid semantic + keyword search."""
        embedding_str = f"[{','.join(map(str, embedding))}]"
        return await fetch(HYBRID_SEARCH, embedding_str, query, limit)

    async def _keyword_search(self, query: str, limit: int) -> list[dict]:
        """Execute keyword-only search with ILIKE fallback."""
        # First try trigram similarity
        rows = await fetch(KEYWORD_SEARCH, query, limit)
        if rows:
            return rows

        # Fall back to ILIKE search for better recall
        ilike_query = """
            SELECT *, 0.5 as score
            FROM assets
            WHERE search_text IS NOT NULL
              AND (search_text ILIKE $1 OR filename ILIKE $1)
            ORDER BY
                CASE WHEN filename ILIKE $1 THEN 0 ELSE 1 END,
                created_in_db DESC
            LIMIT $2
        """
        pattern = f"%{query}%"
        return await fetch(ilike_query, pattern, limit)

    async def _filtered_search(
        self,
        query: str,
        embedding: list[float] | None,
        filters: SearchFilters,
        limit: int,
    ) -> list[dict]:
        """Execute filtered hybrid search."""
        if embedding:
            embedding_str = f"[{','.join(map(str, embedding))}]"
            return await fetch(
                FILTERED_HYBRID_SEARCH,
                embedding_str,
                query,
                limit,
                filters.asset_type,
                filters.album,
                filters.media_type,
            )
        else:
            # Build dynamic query for keyword + filters
            return await self._filtered_keyword_search(query, filters, limit)

    async def _filtered_keyword_search(
        self, query: str, filters: SearchFilters, limit: int
    ) -> list[dict]:
        """Execute filtered keyword search with dynamic WHERE clauses."""
        # Build filter conditions (start from index 2, index 1 is for query pattern)
        filter_conditions = []
        params = [f"%{query}%"]  # $1 is the ILIKE pattern
        param_idx = 2

        if filters.asset_type:
            filter_conditions.append(f"asset_type = ${param_idx}")
            params.append(filters.asset_type)
            param_idx += 1

        if filters.album:
            filter_conditions.append(f"album_name = ${param_idx}")
            params.append(filters.album)
            param_idx += 1

        if filters.media_type:
            filter_conditions.append(f"media_type = ${param_idx}")
            params.append(filters.media_type)
            param_idx += 1

        if filters.content_type:
            filter_conditions.append(f"content_type = ${param_idx}")
            params.append(filters.content_type)
            param_idx += 1

        if filters.min_reusability:
            filter_conditions.append(f"reusability_score >= ${param_idx}")
            params.append(filters.min_reusability)
            param_idx += 1

        if filters.has_text_overlay_space:
            filter_conditions.append(
                "(composition->'negative_space'->>'suitable_for_text_overlay')::boolean = true"
            )

        if filters.min_energy:
            filter_conditions.append(f"(mood->>'energy_level')::int >= ${param_idx}")
            params.append(filters.min_energy)
            param_idx += 1

        if filters.no_hardcoded_date:
            filter_conditions.append(
                "(hardcoded_elements->>'has_date')::boolean IS NOT TRUE"
            )

        if filters.no_hardcoded_location:
            filter_conditions.append(
                "(hardcoded_elements->>'has_location')::boolean IS NOT TRUE"
            )

        params.append(limit)

        # Build WHERE clause
        where_parts = ["search_text IS NOT NULL", "(search_text ILIKE $1 OR filename ILIKE $1)"]
        where_parts.extend(filter_conditions)

        sql = f"""
            SELECT *, 0.5 as score
            FROM assets
            WHERE {' AND '.join(where_parts)}
            ORDER BY
                CASE WHEN filename ILIKE $1 THEN 0 ELSE 1 END,
                created_in_db DESC
            LIMIT ${param_idx}
        """

        return await fetch(sql, *params)

    def _has_active_filters(self, filters: SearchFilters) -> bool:
        """Check if any filters are actually set."""
        return any(
            [
                filters.asset_type,
                filters.album,
                filters.media_type,
                filters.content_type,
                filters.min_reusability,
                filters.has_text_overlay_space,
                filters.min_energy,
                filters.no_hardcoded_date,
                filters.no_hardcoded_location,
            ]
        )

    def _generate_reasoning(self, row: dict, query: str) -> str:
        """Generate a simple explanation of why this result matched."""
        parts = []

        # Check query terms in filename
        query_terms = query.lower().split()
        filename_lower = row.get("filename", "").lower()
        matched_terms = [t for t in query_terms if t in filename_lower]
        if matched_terms:
            parts.append(f"Filename contains: {', '.join(matched_terms)}")

        # Check asset type
        if row.get("asset_type") == "template":
            parts.append("Classified as reusable template")

        # Check album
        album = row.get("album_name")
        if album and any(t in album.lower() for t in query_terms):
            parts.append(f"In album: {album}")

        # Check semantic description
        desc = row.get("semantic_description", "")
        if desc:
            matched_desc = [t for t in query_terms if t in desc.lower()]
            if matched_desc:
                parts.append(f"Description matches: {', '.join(matched_desc)}")

        if not parts:
            parts.append("Matched via semantic similarity")

        return "; ".join(parts)

    async def get_asset(self, asset_id: UUID) -> dict | None:
        """Get a single asset by ID."""
        rows = await fetch(GET_ASSET_BY_ID, asset_id)
        return rows[0] if rows else None

    async def semantic_search_only(
        self, query: str, limit: int = 20
    ) -> list[SearchResult]:
        """Execute semantic-only search (for testing)."""
        if not self.openai:
            return []

        embedding = await self.openai.generate_embedding(query)
        embedding_str = f"[{','.join(map(str, embedding))}]"
        rows = await fetch(SEMANTIC_SEARCH, embedding_str, limit)

        return [
            SearchResult(
                id=row["id"],
                filename=row["filename"],
                thumbnail_url=self._get_presigned_thumbnail(row.get("thumbnail_url")),
                full_url=row.get("full_url"),
                asset_type=row.get("asset_type"),
                album_name=row.get("album_name"),
                media_type=row.get("media_type"),
                content_type=row.get("content_type"),
                width=row.get("width"),
                height=row.get("height"),
                score=float(row.get("score", 0)),
                semantic_description=row.get("semantic_description"),
            )
            for row in rows
        ]

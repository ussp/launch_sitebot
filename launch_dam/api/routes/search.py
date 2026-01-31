"""Search routes."""

from fastapi import APIRouter, Depends, HTTPException

from ..models.schemas import SearchRequest, SearchResponse
from ..services.openai_client import OpenAIService
from ..services.search import SearchService

router = APIRouter(prefix="/search", tags=["search"])


def get_search_service() -> SearchService:
    """Dependency to get search service."""
    try:
        openai = OpenAIService()
    except ValueError:
        # OpenAI not configured, use keyword-only search
        openai = None
    return SearchService(openai)


@router.post("", response_model=SearchResponse)
async def search_assets(
    request: SearchRequest,
    service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    """
    Search for assets using natural language query.

    Supports hybrid semantic + keyword search with optional filters.
    """
    try:
        results, total = await service.search(
            query=request.query,
            filters=request.filters,
            limit=request.limit,
            include_reasoning=request.include_reasoning,
        )

        filters_applied = None
        if request.filters:
            filters_applied = {
                k: v for k, v in request.filters.model_dump().items() if v is not None
            }

        return SearchResponse(
            results=results,
            total=total,
            query=request.query,
            filters_applied=filters_applied,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/semantic")
async def semantic_search(
    query: str,
    limit: int = 20,
    service: SearchService = Depends(get_search_service),
):
    """
    Semantic-only search (for testing/debugging).
    """
    if not service.openai:
        raise HTTPException(
            status_code=503, detail="OpenAI service not configured"
        )

    results = await service.semantic_search_only(query, limit)
    return {"results": results, "query": query}

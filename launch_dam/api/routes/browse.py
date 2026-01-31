"""Browse routes - internal endpoints for the asset browser SPA (no auth required)."""

from fastapi import APIRouter, Depends, HTTPException

from ..models.schemas import SearchFilters, SearchRequest, SearchResponse
from ..services.openai_client import OpenAIService
from ..services.search import SearchService

router = APIRouter(prefix="/browse", tags=["browse"])


def get_search_service() -> SearchService:
    """Dependency to get search service."""
    try:
        openai = OpenAIService()
    except ValueError:
        openai = None
    return SearchService(openai)


@router.post("/search", response_model=SearchResponse)
async def browse_search(
    request: SearchRequest,
    service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    """
    Internal search endpoint for the browse SPA.

    This endpoint does not require API key authentication as it's
    intended for first-party use by the asset browser interface.
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

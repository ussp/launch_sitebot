"""API routes."""

from .albums import router as albums_router
from .assets import router as assets_router
from .ingest import router as ingest_router
from .search import router as search_router
from .sync import router as sync_router

__all__ = [
    "search_router",
    "assets_router",
    "albums_router",
    "ingest_router",
    "sync_router",
]

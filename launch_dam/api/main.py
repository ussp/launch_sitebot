"""Launch DAM - Digital Asset Management API for Launch Family Entertainment."""

import os
import secrets
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader

from .db import close_pool, init_pool
from .routes import albums_router, assets_router, ingest_router, search_router, sync_router

# API Key Security
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_api_key() -> str | None:
    """Get API key from environment."""
    return os.getenv("API_KEY")


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """Verify API key from request header."""
    expected_key = get_api_key()

    # If no API key is configured, allow all requests (dev mode)
    if not expected_key:
        return "dev-mode"

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Provide X-API-Key header.",
        )

    # Use constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(api_key, expected_key):
        raise HTTPException(
            status_code=403,
            detail="Invalid API key",
        )

    return api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup: Initialize database pool
    await init_pool()
    yield
    # Shutdown: Close database pool
    await close_pool()


app = FastAPI(
    title="Launch DAM API",
    description="Digital Asset Management system for Launch Family Entertainment marketing assets",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with API key protection
app.include_router(search_router, prefix="/api", dependencies=[Depends(verify_api_key)])
app.include_router(assets_router, prefix="/api", dependencies=[Depends(verify_api_key)])
app.include_router(albums_router, prefix="/api", dependencies=[Depends(verify_api_key)])
app.include_router(ingest_router, prefix="/api", dependencies=[Depends(verify_api_key)])
app.include_router(sync_router, prefix="/api", dependencies=[Depends(verify_api_key)])


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Launch DAM API",
        "version": "1.0.0",
        "description": "Digital Asset Management for Launch Family Entertainment",
        "endpoints": {
            "search": "/api/search",
            "assets": "/api/assets",
            "albums": "/api/albums",
            "ingest": "/api/ingest",
            "sync": "/api/sync",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    from .db import fetchval

    try:
        # Test database connection
        result = await fetchval("SELECT 1")
        db_status = "healthy" if result == 1 else "unhealthy"
    except Exception as e:
        db_status = f"unhealthy: {e}"

    # Check OpenAI configuration
    openai_configured = bool(os.getenv("OPENAI_API_KEY"))

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "openai_configured": openai_configured,
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)

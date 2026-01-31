"""Launch DAM - Digital Asset Management API for Launch Family Entertainment."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import close_pool, init_pool
from .routes import albums_router, assets_router, ingest_router, search_router, sync_router


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

# Include routers
app.include_router(search_router, prefix="/api")
app.include_router(assets_router, prefix="/api")
app.include_router(albums_router, prefix="/api")
app.include_router(ingest_router, prefix="/api")
app.include_router(sync_router, prefix="/api")


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

"""
main.py
=======

FastAPI application entry point for the Agentic Lending Platform.

Responsibilities
----------------
- Instantiate the FastAPI app with metadata (title, version, description).
- Configure CORS middleware for cross-origin frontend access.
- Register lifespan events (startup / shutdown) for resource management.
- Mount API routers from the orchestration, intelligence, and service layers.
- Expose a health-check endpoint at ``GET /health``.

Usage
-----
Run with Uvicorn::

    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialise shared resources on startup, clean up on shutdown."""
    logger.info("🚀 Starting Agentic Lending Platform v%s", settings.APP_VERSION)
    # TODO: initialise DB connection pool, cache clients, etc.
    yield
    logger.info("🛑 Shutting down Agentic Lending Platform")
    # TODO: close DB connections, flush logs, etc.


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Agentic AI-powered lending platform with multi-agent orchestration.",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["system"])
async def health_check():
    """Return basic health status for load-balancer probes."""
    return {"status": "healthy", "version": settings.APP_VERSION}


# ---------------------------------------------------------------------------
# Router registration
# ---------------------------------------------------------------------------
# TODO: Import and include routers as modules are implemented:
# from backend.orchestration.master_agent import router as orchestration_router
# app.include_router(orchestration_router, prefix="/api/v1")

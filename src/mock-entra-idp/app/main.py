"""Main FastAPI application for Mock Entra ID."""

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config.settings import get_settings
from app.endpoints import authorize, discovery, token


def setup_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """Configure structured logging."""
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    settings = get_settings()

    # Setup logging
    setup_logging(settings.LOG_LEVEL, settings.LOG_FORMAT)

    logger = structlog.get_logger(__name__)

    logger.info(
        "mock_entra_idp_starting",
        version="0.1.0",
        tenant_id=settings.MOCK_TENANT_ID,
        port=settings.MOCK_IDP_PORT,
    )

    # Initialize key manager (generates initial RSA key pair)
    from app.crypto.key_manager import get_key_manager

    key_manager = get_key_manager()
    logger.info(
        "key_manager_initialized",
        current_kid=key_manager.current_kid,
        total_keys=len(key_manager.keys),
    )

    # Initialize storage (seeds clients, users, service principals)
    from app.storage.memory import get_storage

    storage = get_storage(settings)
    logger.info(
        "storage_initialized",
        backend=settings.STORAGE_BACKEND,
    )

    yield

    logger.info("mock_entra_idp_shutting_down")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Mock Entra ID Token Issuer",
        description=(
            "OAuth 2.0/OIDC token issuer that emulates Microsoft Entra ID "
            "for testing and demos."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.LOG_LEVEL == "DEBUG" else None,
        redoc_url="/redoc" if settings.LOG_LEVEL == "DEBUG" else None,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins for demo purposes
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static files
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    # Include routers
    app.include_router(authorize.router, tags=["Authorization"])
    app.include_router(token.router, tags=["Token"])
    app.include_router(discovery.router, tags=["Discovery"])

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    uvicorn.run(
        "app.main:app",
        host=settings.MOCK_IDP_HOST,
        port=settings.MOCK_IDP_PORT,
        reload=settings.LOG_LEVEL == "DEBUG",
        log_level=settings.LOG_LEVEL.lower(),
    )

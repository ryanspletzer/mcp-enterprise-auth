"""Main FastAPI application for MCP server."""

import sys
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.auth.middleware import get_auth_context
from app.config import Settings, get_settings
from app.dcr import dcr_router
from app.utils.exceptions import MCPError
from app.utils.logging import get_logger, setup_logging

# Initialize logger (will be configured in lifespan)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Handles startup and shutdown events.

    Args:
        app: FastAPI application

    Yields:
        None
    """
    # Startup
    settings = get_settings()

    # Set up logging
    setup_logging(settings)

    logger.info(
        "mcp_server_starting",
        version="0.1.0",
        deployment_mode=settings.DEPLOYMENT_MODE,
        port=settings.MCP_SERVER_PORT,
    )

    # Log configuration (sanitized)
    logger.info(
        "configuration_loaded",
        tenant_id=settings.ENTRA_TENANT_ID,
        server_app_id=settings.MCP_SERVER_APP_ID,
        deployment_mode=settings.DEPLOYMENT_MODE,
        debug_mode=settings.DEBUG_MODE,
        enable_dcr=settings.ENABLE_DCR_ENDPOINT,
        enable_swagger=settings.ENABLE_SWAGGER,
        log_level=settings.LOG_LEVEL,
    )

    yield

    # Shutdown
    logger.info("mcp_server_shutting_down")


# Create FastAPI app
def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI application
    """
    settings = get_settings()

    app = FastAPI(
        title="MCP Server with Proper Enterprise Authentication",
        description=(
            "Model Context Protocol (MCP) server with comprehensive OAuth 2.0 / "
            "OpenID Connect authentication via Microsoft Entra ID."
        ),
        version="0.1.0",
        docs_url=settings.SWAGGER_UI_PATH if settings.ENABLE_SWAGGER else None,
        redoc_url="/redoc" if settings.ENABLE_SWAGGER else None,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins(),
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.get_cors_methods(),
        allow_headers=settings.CORS_ALLOWED_HEADERS.split(","),
    )

    # Rate limiting
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore
    app.add_middleware(SlowAPIMiddleware)

    # Exception handlers
    @app.exception_handler(MCPError)
    async def mcp_error_handler(request: Request, exc: MCPError) -> JSONResponse:
        """Handle MCP errors.

        Args:
            request: Request
            exc: MCP error

        Returns:
            JSON error response
        """
        logger.error(
            "mcp_error",
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details,
            path=request.url.path,
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "error_description": exc.message,
                "details": exc.details if settings.DEBUG_MODE else {},
            },
        )

    # Include routers
    if settings.ENABLE_DCR_ENDPOINT:
        app.include_router(dcr_router)
        logger.info("dcr_router_registered")

    # Health check endpoints
    @app.get(
        settings.HEALTH_CHECK_PATH if settings.ENABLE_HEALTH_CHECK else "/health",
        tags=["Health"],
        summary="Health check",
        description="Simple health check endpoint for load balancers and monitoring",
    )
    async def health_check() -> dict[str, str]:
        """Health check endpoint.

        Returns:
            Health status
        """
        return {"status": "healthy"}

    @app.get(
        settings.READINESS_CHECK_PATH if settings.ENABLE_HEALTH_CHECK else "/ready",
        tags=["Health"],
        summary="Readiness check",
        description="Readiness check endpoint for Kubernetes, ECS, etc.",
    )
    async def readiness_check() -> dict[str, Any]:
        """Readiness check endpoint.

        Verifies that the application is ready to accept requests.

        Returns:
            Readiness status
        """
        settings = get_settings()

        checks = {
            "jwks_url_configured": bool(settings.ENTRA_JWKS_URL),
            "tenant_configured": bool(settings.ENTRA_TENANT_ID),
            "app_id_configured": bool(settings.MCP_SERVER_APP_ID),
        }

        all_ready = all(checks.values())

        return {
            "status": "ready" if all_ready else "not_ready",
            "checks": checks if settings.DEBUG_MODE else {},
        }

    @app.get(
        "/",
        tags=["Info"],
        summary="API information",
        description="Basic API information and links",
    )
    async def root() -> dict[str, Any]:
        """Root endpoint with API information.

        Returns:
            API information
        """
        settings = get_settings()

        return {
            "name": "MCP Server with Proper Enterprise Authentication",
            "version": "0.1.0",
            "deployment_mode": settings.DEPLOYMENT_MODE,
            "docs_url": settings.SWAGGER_UI_PATH if settings.ENABLE_SWAGGER else None,
            "dcr_enabled": settings.ENABLE_DCR_ENDPOINT,
            "authentication": "OAuth 2.0 / OpenID Connect (Entra ID)",
        }

    # Protected example endpoint (requires authentication)
    @app.get(
        "/api/me",
        tags=["API"],
        summary="Get current user/app information",
        description="Returns information about the authenticated user or service principal",
    )
    async def get_me(auth=get_auth_context) -> dict[str, Any]:
        """Get current user/app information.

        Args:
            auth: Auth context from dependency

        Returns:
            User or service principal information
        """
        auth_context = await auth

        return {
            "token_type": auth_context.token_type.value,
            "identity": auth_context.identity,
            "permissions": {
                k: v for k, v in auth_context.permissions.items() if k != "token_type"
            },
        }

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    uvicorn.run(
        "app.main:app",
        host=settings.MCP_SERVER_HOST,
        port=settings.MCP_SERVER_PORT,
        reload=settings.DEBUG_MODE,
        log_level=settings.LOG_LEVEL.lower(),
    )

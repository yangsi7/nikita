"""FastAPI application entrypoint for Nikita."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nikita.config.settings import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    print("Starting Nikita API server...")
    # TODO: Initialize database connections
    # TODO: Initialize Graphiti client
    # TODO: Set up Telegram webhook
    yield
    # Shutdown
    print("Shutting down Nikita API server...")
    # TODO: Close database connections
    # TODO: Close Graphiti client


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Nikita: Don't Get Dumped",
        description="AI Girlfriend Game API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    # TODO: Add route imports once implemented
    # from nikita.api.routes import telegram, voice, portal, admin
    # app.include_router(telegram.router, prefix="/telegram", tags=["Telegram"])
    # app.include_router(voice.router, prefix="/voice", tags=["Voice"])
    # app.include_router(portal.router, prefix="/portal", tags=["Portal"])
    # app.include_router(admin.router, prefix="/admin", tags=["Admin"])

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "name": "Nikita: Don't Get Dumped",
            "version": "0.1.0",
            "status": "online",
        }

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy"}

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "nikita.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )

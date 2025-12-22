"""FastAPI application entrypoint for Nikita."""

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nikita.config.settings import get_settings

# Configure logging to output to stdout for Cloud Run
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
# Ensure our app loggers are at INFO level
logging.getLogger("nikita").setLevel(logging.INFO)

settings = get_settings()


# Note: Stub classes removed in Sprint 3 (T3.3)
# Real dependencies are now injected via FastAPI Depends in routes


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler with proper DB initialization."""
    from sqlalchemy import text

    from nikita.db.database import get_async_engine, get_supabase_client

    print("Starting Nikita API server...")

    # 1. Validate database connection
    engine = get_async_engine()
    app.state.db_engine = engine
    app.state.db_healthy = False

    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        app.state.db_healthy = True
        print("✓ Database connection validated")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        # Continue anyway - health endpoint will show unhealthy

    # 2. Initialize Supabase client (singleton)
    try:
        supabase = await get_supabase_client()
        app.state.supabase = supabase
        print("✓ Supabase client initialized")
    except Exception as e:
        print(f"✗ Supabase client failed: {e}")
        app.state.supabase = None

    yield

    # Shutdown
    print("Shutting down Nikita API server...")

    # Close Telegram bot client
    if hasattr(app.state, "telegram_bot"):
        await app.state.telegram_bot.close()

    # Dispose engine connections
    if hasattr(app.state, "db_engine"):
        await app.state.db_engine.dispose()
        print("✓ Database connections closed")


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

    # Initialize Telegram bot (stateless, shared across requests)
    from nikita.platforms.telegram.bot import TelegramBot

    bot = TelegramBot()
    app.state.telegram_bot = bot

    # Telegram router - dependencies injected per-request via FastAPI Depends
    from nikita.api.routes import create_telegram_router

    telegram_router = create_telegram_router(bot=bot)
    app.include_router(
        telegram_router,
        prefix="/api/v1/telegram",
        tags=["Telegram"],
    )

    # Task routes for pg_cron background jobs
    from nikita.api.routes import tasks_router

    app.include_router(
        tasks_router,
        prefix="/api/v1/tasks",
        tags=["Tasks"],
    )

    # Portal routes for user dashboard
    from nikita.api.routes import portal

    app.include_router(
        portal.router,
        prefix="/api/v1/portal",
        tags=["Portal"],
    )

    # Admin routes for system management
    from nikita.api.routes import admin

    app.include_router(
        admin.router,
        prefix="/api/v1/admin",
        tags=["Admin"],
    )

    # Admin debug portal routes (@silent-agents.com only)
    from nikita.api.routes import admin_debug

    app.include_router(
        admin_debug.router,
        prefix="/admin/debug",
        tags=["Admin Debug"],
    )

    # TODO: Add remaining routes once implemented
    # app.include_router(voice.router, prefix="/api/v1/voice", tags=["Voice"])

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
        """Health check endpoint with database status."""
        db_healthy = getattr(app.state, "db_healthy", False)
        supabase_ok = getattr(app.state, "supabase", None) is not None

        status = "healthy" if db_healthy else "degraded"
        return {
            "status": status,
            "database": "connected" if db_healthy else "disconnected",
            "supabase": "connected" if supabase_ok else "disconnected",
        }

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

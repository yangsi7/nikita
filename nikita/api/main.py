"""FastAPI application entrypoint for Nikita."""

import logging
import sys
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

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

# Spec 036 T3.1: Threshold for slow request logging (seconds)
SLOW_REQUEST_THRESHOLD_SECONDS = 45.0


class SlowRequestMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware to log slow requests for observability (Spec 036 T3.1).

    Logs a warning for any request taking longer than SLOW_REQUEST_THRESHOLD_SECONDS.
    Includes request path, method, and duration.
    """

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Process the request
        response = await call_next(request)

        # Calculate duration
        duration_seconds = time.time() - start_time

        # Log slow requests
        if duration_seconds > SLOW_REQUEST_THRESHOLD_SECONDS:
            logger = logging.getLogger("nikita.api.slow_request")
            logger.warning(
                f"[SLOW-REQUEST] {request.method} {request.url.path} "
                f"took {duration_seconds:.2f}s (threshold: {SLOW_REQUEST_THRESHOLD_SECONDS}s)",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_seconds": duration_seconds,
                    "threshold_seconds": SLOW_REQUEST_THRESHOLD_SECONDS,
                },
            )

        return response


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

    # 3. Validate ElevenLabs configuration
    try:
        from nikita.agents.voice.validation import validate_elevenlabs_config

        warnings = await validate_elevenlabs_config(settings)
        for warning in warnings:
            print(f"⚠ {warning}")
        if not warnings:
            print("✓ ElevenLabs configuration validated")
    except Exception as e:
        print(f"⚠ ElevenLabs validation failed: {e}")

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

    # Spec 036 T3.1: Add slow request monitoring middleware
    app.add_middleware(SlowRequestMonitoringMiddleware)

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

    # Voice routes for ElevenLabs Conversational AI (Spec 007)
    from nikita.api.routes import voice

    app.include_router(
        voice.router,
        prefix="/api/v1/voice",
        tags=["Voice"],
    )

    # Onboarding routes for Meta-Nikita voice onboarding (Spec 028)
    from nikita.api.routes import onboarding

    app.include_router(
        onboarding.router,
        prefix="/api/v1/onboarding",
        tags=["Onboarding"],
    )

    # Global exception handler - logs errors to database for admin dashboard (P0-3)
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Log unhandled exceptions to error_logs table for admin monitoring."""
        logger = logging.getLogger("nikita.api.error_handler")

        # Log to console immediately
        logger.exception(f"Unhandled exception on {request.method} {request.url.path}")

        # Log to database asynchronously (best-effort, don't fail request)
        try:
            from nikita.api.dependencies.error_logging import log_error
            from nikita.db.database import get_session_maker
            from nikita.db.models.error_log import ErrorLevel

            session_maker = get_session_maker()
            async with session_maker() as session:
                await log_error(
                    session=session,
                    message=str(exc),
                    source=f"nikita.api:{request.url.path}",
                    level=ErrorLevel.ERROR,
                    exception=exc,
                    context={
                        "method": request.method,
                        "path": request.url.path,
                        "query": str(request.query_params),
                    },
                )
        except Exception as log_exc:
            # Don't let logging failure affect user response
            logger.warning(f"Failed to log error to database: {log_exc}")

        # Return generic error response
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

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
        """Basic health check endpoint (fast, no DB query).

        Returns cached startup state. Use /health/deep for live DB check.
        """
        db_healthy = getattr(app.state, "db_healthy", False)
        supabase_ok = getattr(app.state, "supabase", None) is not None

        status = "healthy" if db_healthy else "degraded"
        return {
            "status": status,
            "service": "nikita-api",
            "database": "connected" if db_healthy else "disconnected",
            "supabase": "connected" if supabase_ok else "disconnected",
        }

    @app.get("/health/deep")
    async def health_deep():
        """Deep health check with live database query.

        Actually queries the database to verify connectivity.
        Use for post-deployment verification.
        """
        from sqlalchemy import text

        from nikita.db.database import get_session_maker

        db_status = "disconnected"
        db_error = None

        try:
            session_maker = get_session_maker()
            async with session_maker() as session:
                result = await session.execute(text("SELECT 1"))
                if result.scalar() == 1:
                    db_status = "connected"
        except Exception as e:
            db_error = str(e)

        supabase_ok = getattr(app.state, "supabase", None) is not None

        status = "healthy" if db_status == "connected" else "degraded"
        response = {
            "status": status,
            "service": "nikita-api",
            "database": db_status,
            "supabase": "connected" if supabase_ok else "disconnected",
        }

        if db_error:
            response["database_error"] = db_error

        return response

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

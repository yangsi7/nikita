"""API route definitions."""

from nikita.api.routes.tasks import router as tasks_router
from nikita.api.routes.telegram import create_telegram_router

__all__ = ["create_telegram_router", "tasks_router"]

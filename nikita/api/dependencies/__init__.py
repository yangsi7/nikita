"""FastAPI dependencies for the Nikita API."""

from nikita.api.dependencies.audit import audit_admin_action
from nikita.api.dependencies.auth import get_current_user_id
from nikita.api.dependencies.logging import PiiSafeFormatter, get_pii_safe_logger

__all__ = [
    "audit_admin_action",
    "get_current_user_id",
    "get_pii_safe_logger",
    "PiiSafeFormatter",
]

"""Internal webhook endpoints.

These endpoints are called by Supabase webhooks and other backend
services. Authentication uses the shared TASK_AUTH_SECRET Bearer token
(same pattern as pg_cron endpoints in `tasks.py`), never a Supabase
user JWT.

Note: the POST /auth/password-reset-hook endpoint (Spec 214 FR-11c T1.4,
AC-11c.12) was removed in GH #610. It revoked portal_bridge_tokens rows,
but that table's writer (nikita/onboarding/bridge_tokens.py) was deleted
as part of consolidating to the live auth_bridge_tokens flow. The endpoint
had no rows to revoke and was vestigial.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Internal"])

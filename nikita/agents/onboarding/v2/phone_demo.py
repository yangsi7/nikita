"""
Phone-demo consent + outbound call dispatch for Spec 218 FR-009/FR-010/FR-011.

Responsibilities:
- Record server-side consent (TCPA compliance, FR-009)
- Dispatch outbound ElevenLabs call via VoiceService.make_outbound_call
- Enforce lifetime single-fire per user via DB UNIQUE constraint on user_id
- Idempotency: ON CONFLICT (user_id) DO NOTHING; caller raises HTTP 409

Schema source: spec §Entity 2 (GATE-2 passed audit)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def record_consent_and_dispatch(
    *,
    session: Any,
    user_id: UUID,
    phone_e164: str,
    client_ip: str | None,
    user_agent: str | None,
) -> dict[str, Any]:
    """
    Insert a phone_demo_calls row and dispatch the outbound call.

    Returns:
        dict with keys: inserted (bool), provider_call_id (str | None),
        status (str)

    Raises:
        NotImplementedError: GREEN phase replaces this stub.
    """
    raise NotImplementedError("phone_demo.record_consent_and_dispatch — GREEN phase")


async def end_call(
    *,
    session: Any,
    user_id: UUID,
) -> dict[str, Any]:
    """
    Abort an in-flight phone-demo call gracefully (FR-010 "End early").

    Terminates the ElevenLabs call if provider_call_id is set and the
    status is not already terminal. Updates status to 'ended_error'
    (user-initiated abort).

    Returns:
        dict with keys: success (bool), message (str)

    Raises:
        NotImplementedError: GREEN phase replaces this stub.
    """
    raise NotImplementedError("phone_demo.end_call — GREEN phase")

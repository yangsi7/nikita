"""
Phone-demo consent + outbound call dispatch for Spec 218 FR-009/FR-010/FR-011.

Responsibilities:
- Record server-side consent (TCPA compliance, FR-009)
- Dispatch outbound ElevenLabs call via VoiceService.make_outbound_call
- Enforce lifetime single-fire per user via DB UNIQUE constraint on user_id
- Idempotency: ON CONFLICT (user_id) DO NOTHING; caller raises HTTP 409

Schema source: spec §Entity 2 (GATE-2 passed audit)

Column mapping (spec §Entity 2 authoritative):
  consent_recorded_at  — timestamptz, server-side consent timestamp
  provider_call_id     — text, ElevenLabs conversation_id post-dispatch
  status               — CHECK enum (pending|ringing|in_progress|ended_*)
  ended_at             — timestamptz, set by webhook piggyback
  cost_usd             — numeric(8,4), set by webhook piggyback
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text

logger = logging.getLogger(__name__)

# Status values (spec §Entity 2 CHECK constraint)
STATUS_PENDING = "pending"
STATUS_RINGING = "ringing"
STATUS_IN_PROGRESS = "in_progress"
STATUS_ENDED_SUCCESS = "ended_success"
STATUS_ENDED_BUSY = "ended_busy"
STATUS_ENDED_NO_ANSWER = "ended_no_answer"
STATUS_ENDED_ERROR = "ended_error"
STATUS_CEILING_TIMEOUT = "ceiling_timeout"

# ElevenLabs phone-demo conversation config override (brief ~10s demo call)
_PHONE_DEMO_FIRST_MESSAGE = (
    "Hey, it's Nikita. Just wanted to hear your voice for a second. "
    "This is only a demo — I'll see you inside the app."
)
_PHONE_DEMO_SYSTEM_PROMPT = (
    "You are Nikita. This is a 10-second phone demo. "
    "Say the first_message warmly, pause briefly, then say goodbye naturally. "
    "Keep the entire call under 15 seconds."
)


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

    Uses ON CONFLICT (user_id) DO NOTHING for idempotency (FR-011 lifetime cap).
    If the row was not inserted (duplicate), returns inserted=False.
    Caller is responsible for returning HTTP 409.

    The consent row is inserted with status='pending' BEFORE the call is
    dispatched (FR-009: record first, call second; if record fails, no call).

    Returns:
        dict with keys:
          inserted (bool): True if new row was created, False if duplicate
          provider_call_id (str | None): ElevenLabs conversation_id
          status (str): 'pending' on success
    """
    now = datetime.now(UTC)

    # Insert consent row (ON CONFLICT DO NOTHING for idempotency)
    insert_sql = text("""
        INSERT INTO phone_demo_calls
            (user_id, phone_e164, consent_recorded_at, consent_source,
             client_ip, user_agent, status)
        VALUES
            (:user_id, :phone_e164, :consent_recorded_at, 'phone_demo_optin',
             :client_ip, :user_agent, 'pending')
        ON CONFLICT (user_id) DO NOTHING
    """)

    result = await session.execute(
        insert_sql,
        {
            "user_id": str(user_id),
            "phone_e164": phone_e164,
            "consent_recorded_at": now,
            "client_ip": client_ip,
            "user_agent": user_agent,
        },
    )
    await session.commit()

    inserted = result.rowcount == 1

    if not inserted:
        logger.info(
            "[PHONE_DEMO] Duplicate consent for user_id=%s (FR-011 lifetime cap)",
            user_id,
        )
        return {"inserted": False, "provider_call_id": None, "status": STATUS_PENDING}

    # Dispatch outbound call via VoiceService (FR-009: call AFTER record)
    provider_call_id: str | None = None
    try:
        from nikita.agents.voice.service import VoiceService

        service = VoiceService()
        call_result = await service.make_outbound_call(
            to_number=phone_e164,
            user_id=user_id,
            conversation_config_override={
                "agent": {
                    "prompt": {"prompt": _PHONE_DEMO_SYSTEM_PROMPT},
                    "first_message": _PHONE_DEMO_FIRST_MESSAGE,
                }
            },
            dynamic_variables={"secret__user_id": str(user_id)},
            is_onboarding=True,
        )
        if call_result.get("success"):
            provider_call_id = call_result.get("conversation_id")
            logger.info(
                "[PHONE_DEMO] Call dispatched: user_id=%s conversation_id=%s",
                user_id,
                provider_call_id,
            )
        else:
            logger.warning(
                "[PHONE_DEMO] Call dispatch failed: user_id=%s message=%s",
                user_id,
                call_result.get("message"),
            )
    except Exception as exc:
        # Non-fatal: consent row already persisted. Log and continue.
        # FE will see status='pending' and Realtime will update when webhook fires.
        logger.exception(
            "[PHONE_DEMO] Exception during call dispatch: user_id=%s error=%s",
            user_id,
            exc,
        )

    # Update provider_call_id on the consent row if we got one
    if provider_call_id:
        update_sql = text("""
            UPDATE phone_demo_calls
            SET provider_call_id = :provider_call_id
            WHERE user_id = :user_id
        """)
        await session.execute(
            update_sql,
            {"provider_call_id": provider_call_id, "user_id": str(user_id)},
        )
        await session.commit()

    return {
        "inserted": True,
        "provider_call_id": provider_call_id,
        "status": STATUS_PENDING,
    }


async def end_call(
    *,
    session: Any,
    user_id: UUID,
) -> dict[str, Any]:
    """
    Abort an in-flight phone-demo call gracefully (FR-010 "End early").

    Looks up the user's phone_demo_calls row. If provider_call_id is set
    and status is not already terminal, attempts to end the ElevenLabs
    conversation. Updates status to 'ended_error' (user-initiated abort)
    regardless of whether the API call succeeds (best-effort).

    Returns:
        dict with keys: success (bool), message (str)
    """
    # Look up the call record
    select_sql = text("""
        SELECT id, provider_call_id, status
        FROM phone_demo_calls
        WHERE user_id = :user_id
        LIMIT 1
    """)
    row_result = await session.execute(select_sql, {"user_id": str(user_id)})
    row = row_result.fetchone()

    if row is None:
        return {"success": False, "message": "No phone demo call found for this account"}

    _row_id, provider_call_id, status = row

    # Terminal statuses — nothing to abort
    terminal_statuses = {
        STATUS_ENDED_SUCCESS,
        STATUS_ENDED_BUSY,
        STATUS_ENDED_NO_ANSWER,
        STATUS_ENDED_ERROR,
        STATUS_CEILING_TIMEOUT,
    }
    if status in terminal_statuses:
        return {"success": True, "message": f"Call already completed (status={status})"}

    # Attempt to terminate via ElevenLabs if we have a conversation_id
    if provider_call_id:
        try:
            from nikita.agents.voice.service import VoiceService

            service = VoiceService()
            client = service._get_elevenlabs_client()
            # ElevenLabs SDK: end_conversation(conversation_id)
            await client.end_conversation(provider_call_id)
            logger.info(
                "[PHONE_DEMO] Terminated call via API: user_id=%s conversation_id=%s",
                user_id,
                provider_call_id,
            )
        except Exception as exc:
            logger.warning(
                "[PHONE_DEMO] Failed to terminate call via API (best-effort): %s",
                exc,
            )

    # Update status to ended_error (user-initiated abort) + ended_at
    now = datetime.now(UTC)
    update_sql = text("""
        UPDATE phone_demo_calls
        SET status = 'ended_error', ended_at = :ended_at
        WHERE user_id = :user_id
          AND status NOT IN (
            'ended_success', 'ended_busy', 'ended_no_answer',
            'ended_error', 'ceiling_timeout'
          )
    """)
    await session.execute(update_sql, {"ended_at": now, "user_id": str(user_id)})
    await session.commit()

    return {"success": True, "message": "Call ended"}


async def handle_webhook_update(
    *,
    session: Any,
    provider_call_id: str,
    status: str,
    cost_usd: float | None = None,
) -> bool:
    """
    Update phone_demo_calls row from voice webhook (post_call_transcription piggyback).

    Called at the top of the post_call_transcription handler.
    Returns True if a row was found + updated (caller should return early).
    Returns False if no matching row (normal voice call — caller continues normally).
    """
    now = datetime.now(UTC)

    update_sql = text("""
        UPDATE phone_demo_calls
        SET status = :status,
            ended_at = :ended_at,
            cost_usd = :cost_usd
        WHERE provider_call_id = :provider_call_id
        RETURNING id
    """)
    result = await session.execute(
        update_sql,
        {
            "status": status,
            "ended_at": now,
            "cost_usd": cost_usd,
            "provider_call_id": provider_call_id,
        },
    )
    row = result.fetchone()
    await session.commit()

    if row is not None:
        logger.info(
            "[PHONE_DEMO] Webhook updated phone_demo_calls: "
            "provider_call_id=%s status=%s",
            provider_call_id,
            status,
        )
        return True

    return False

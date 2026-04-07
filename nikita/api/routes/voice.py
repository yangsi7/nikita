"""Voice API routes for call initiation and server tools.

Implements:
- T007: Call initiation endpoint (POST /api/v1/voice/initiate)
- T013: Server tool endpoint (POST /api/v1/voice/server-tool)

Part of Spec 007: Voice Agent (ElevenLabs Conversational AI 2.0).
"""

import json
import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError

from nikita.agents.voice.availability import get_availability_service
from nikita.agents.voice.models import ServerToolName, ServerToolRequest
from nikita.agents.voice.server_tools import get_server_tool_handler
from nikita.agents.voice.service import get_voice_service
from nikita.config.settings import get_settings
from nikita.utils.masking import mask_phone

logger = logging.getLogger(__name__)
router = APIRouter(tags=["voice"])


# === Request/Response Models ===


class InitiateCallRequest(BaseModel):
    """Request to initiate a voice call."""

    user_id: UUID = Field(..., description="User UUID")


class InitiateCallResponse(BaseModel):
    """Response with connection parameters for voice call."""

    agent_id: str = Field(..., description="ElevenLabs agent ID")
    signed_token: str = Field(..., description="Signed auth token for server tools")
    session_id: str = Field(..., description="Unique session identifier")
    context: dict = Field(default_factory=dict, description="User context")
    dynamic_variables: dict = Field(
        default_factory=dict, description="Variables for prompt interpolation"
    )
    tts_settings: dict | None = Field(
        default=None, description="TTS parameters (stability, similarity, speed)"
    )
    conversation_config_override: dict | None = Field(
        default=None,
        description="Override for agent config (prompt, first_message, TTS) - "
        "if provided, overrides ElevenLabs dashboard defaults",
    )


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str


class AvailabilityResponse(BaseModel):
    """Response for voice call availability check."""

    available: bool = Field(..., description="Whether Nikita is available for a call")
    reason: str = Field(..., description="Human-readable reason")
    chapter: int = Field(..., description="User's current chapter")
    availability_rate: float = Field(
        ..., description="Base availability rate for chapter (0.0-1.0)"
    )


# === Endpoints ===


@router.get(
    "/availability/{user_id}",
    response_model=AvailabilityResponse,
    responses={
        404: {"model": ErrorResponse, "description": "User not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Check Voice Call Availability",
    description="""
    Check if Nikita is available for a voice call with this user.

    Availability depends on:
    - Chapter: Higher chapters = higher availability (10% → 95%)
    - Game status: Boss fight = always available, game_over/won = never available
    - Randomness: Each check has a probability based on chapter

    **T034**: GET /api/v1/voice/availability/{user_id}
    """,
)
async def check_availability(user_id: UUID) -> AvailabilityResponse:
    """
    Check voice call availability (T034).

    AC-T034.1: Returns availability status with reason
    AC-T034.2: Checks chapter-based availability rate
    AC-T034.3: Checks game status (boss_fight, game_over, won)
    """
    logger.info(f"[VOICE API] Availability check for user {user_id}")

    try:
        from nikita.db.database import get_session_maker
        from nikita.db.repositories.user_repository import UserRepository

        session_maker = get_session_maker()
        async with session_maker() as session:
            repo = UserRepository(session)
            user = await repo.get(user_id)

            if user is None:
                raise HTTPException(status_code=404, detail="User not found")

            availability = get_availability_service()
            is_available, reason = availability.is_available(user)
            rate = availability.get_availability_rate(user)

            logger.info(
                f"[VOICE API] Availability result: "
                f"available={is_available}, chapter={user.chapter}"
            )

            return AvailabilityResponse(
                available=is_available,
                reason=reason,
                chapter=user.chapter,
                availability_rate=rate,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[VOICE API] Availability check error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {type(e).__name__}",
        )


@router.get(
    "/signed-url/{user_id}",
    responses={
        403: {"model": ErrorResponse, "description": "Voice not available"},
        404: {"model": ErrorResponse, "description": "User not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Get Signed URL for Voice Widget",
    description="""
    Generate an ElevenLabs signed URL for the frontend voice widget.

    This endpoint:
    1. Calls VoiceService.initiate_call() to get personalized prompt + context
    2. Calls ElevenLabs API to generate a signed WebSocket URL
    3. Returns URL + all personalization data for frontend

    **Returns**:
    - signed_url: ElevenLabs WebSocket URL for connection
    - signed_token: Auth token for server tools (pass as secret__signed_token)
    - session_id: Session identifier
    - dynamic_variables: Variables for prompt interpolation
    - conversation_config_override: Override for agent (prompt, first_message, TTS)

    **Frontend Usage**:
    ```javascript
    const conversation = await Conversation.startSession({
      signedUrl: response.signed_url,
      overrides: response.conversation_config_override,
      dynamicVariables: {
        ...response.dynamic_variables,
        secret__signed_token: response.signed_token,
      }
    });
    ```

    **Use for**: Portal voice test page, mobile app voice integration
    """,
)
async def get_signed_url(user_id: UUID) -> dict:
    """Generate ElevenLabs signed URL for frontend widget with full personalization."""
    import httpx

    logger.info(f"[VOICE API] Signed URL request for user {user_id}")

    settings = get_settings()

    try:
        # Call initiate_call to get all personalization data
        service = get_voice_service()
        try:
            init_result = await service.initiate_call(user_id)
        except ValueError as e:
            error_msg = str(e).lower()
            if "not found" in error_msg:
                raise HTTPException(status_code=404, detail=str(e))
            elif "not available" in error_msg:
                raise HTTPException(status_code=403, detail=str(e))
            else:
                raise HTTPException(status_code=400, detail=str(e))

        # Call ElevenLabs API for signed URL
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.elevenlabs.io/v1/convai/conversation/get-signed-url",
                params={"agent_id": settings.elevenlabs_default_agent_id},
                headers={"xi-api-key": settings.elevenlabs_api_key},
                timeout=10.0,
            )

            if response.status_code != 200:
                logger.error(f"[VOICE API] ElevenLabs API error: {response.text}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to get signed URL from ElevenLabs",
                )

            data = response.json()

        logger.info(
            f"[VOICE API] Signed URL generated for user {user_id}, "
            f"session={init_result['session_id']}, "
            f"has_override={init_result.get('conversation_config_override') is not None}"
        )

        return {
            "signed_url": data["signed_url"],
            "user_id": str(user_id),
            "agent_id": settings.elevenlabs_default_agent_id,
            "signed_token": init_result["signed_token"],
            "session_id": init_result["session_id"],
            "dynamic_variables": init_result.get("dynamic_variables", {}),
            "conversation_config_override": init_result.get("conversation_config_override"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[VOICE API] Signed URL error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {type(e).__name__}",
        )


@router.post(
    "/initiate",
    response_model=InitiateCallResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Voice call not available"},
        404: {"model": ErrorResponse, "description": "User not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Initiate Voice Call",
    description="""
    Initiate a voice call for a user.

    Returns connection parameters for ElevenLabs Conversational AI:
    - agent_id: The ElevenLabs agent to connect to
    - signed_token: Authentication token for server tools
    - session_id: Session identifier for tracking
    - context: User context for personalization
    - dynamic_variables: Variables for prompt interpolation
    - tts_settings: Voice synthesis parameters

    **Errors**:
    - 403: User cannot make voice calls (game over, wrong chapter, etc.)
    - 404: User not found
    - 500: Unexpected server error
    """,
)
async def initiate_call(request: InitiateCallRequest) -> InitiateCallResponse:
    """
    Initiate a voice call (T007).

    AC-T007.1: Returns signed ElevenLabs connection params
    AC-T007.2: Validates user authentication (user_id)
    AC-T007.3: Returns 403 if call not available
    """
    logger.info(f"[VOICE API] Initiate call request for user {request.user_id}")

    try:
        service = get_voice_service()
        result = await service.initiate_call(request.user_id)

        logger.info(f"[VOICE API] Call initiated: session={result['session_id']}")

        return InitiateCallResponse(
            agent_id=result["agent_id"],
            signed_token=result["signed_token"],
            session_id=result["session_id"],
            context=result.get("context", {}),
            dynamic_variables=result.get("dynamic_variables", {}),
            tts_settings=result.get("tts_settings"),
            conversation_config_override=result.get("conversation_config_override"),
        )

    except ValueError as e:
        error_msg = str(e)
        logger.warning(f"[VOICE API] Call initiation failed: {error_msg}")

        # Determine error type from message
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        elif "not available" in error_msg.lower():
            raise HTTPException(status_code=403, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)

    except Exception as e:
        logger.error(f"[VOICE API] Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {type(e).__name__}",
        )


# === Server Tool Models ===


class ServerToolAPIRequest(BaseModel):
    """Request from ElevenLabs server tool webhook."""

    tool_name: str = Field(..., description="Tool to execute")
    signed_token: str = Field(..., description="Signed authentication token")
    data: dict = Field(default_factory=dict, description="Tool parameters")


class ServerToolAPIResponse(BaseModel):
    """Response to ElevenLabs server tool."""

    success: bool = Field(..., description="Whether tool succeeded")
    data: dict | None = Field(default=None, description="Tool response data")
    error: str | None = Field(default=None, description="Error message if failed")


# === Server Tool Endpoint ===


# Shared auth: validate_signed_token imported from nikita.api.utils.webhook_auth
from nikita.api.utils.webhook_auth import validate_signed_token as _validate_signed_token


@router.post(
    "/server-tool",
    response_model=ServerToolAPIResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid authentication"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Handle Server Tool Call",
    description="""
    Handle server tool calls from ElevenLabs during voice conversations.

    ElevenLabs calls this endpoint when the LLM needs to:
    - get_context: Load user context (chapter, vices, engagement)
    - get_memory: Query SupabaseMemory (pgVector) system
    - score_turn: Analyze conversation exchange
    - update_memory: Store new facts

    AC-T013.1: Handles tool calls
    AC-T013.2: Validates signed token
    AC-T013.3: Returns JSON response
    """,
)
async def handle_server_tool(request: ServerToolAPIRequest) -> ServerToolAPIResponse:
    """
    Handle server tool request from ElevenLabs (T013).

    AC-T013.1: POST /api/v1/voice/server-tool handles tool calls
    AC-T013.2: Validates ElevenLabs webhook signature (via signed_token)
    AC-T013.3: Returns JSON response for tool result
    """
    logger.info(f"[VOICE API] Server tool request: {request.tool_name}")

    # Validate signed token (AC-T013.2)
    try:
        user_id, session_id = _validate_signed_token(request.signed_token)
    except ValueError as e:
        logger.warning(f"[VOICE API] Token validation failed: {e}")
        raise HTTPException(status_code=401, detail=str(e))

    # Map string tool name to enum
    try:
        tool_name_enum = ServerToolName(request.tool_name)
    except ValueError:
        logger.warning(f"[VOICE API] Unknown tool: {request.tool_name}")
        return ServerToolAPIResponse(
            success=False,
            error=f"Unknown tool: {request.tool_name}",
        )

    # Create internal request
    internal_request = ServerToolRequest(
        tool_name=tool_name_enum,
        user_id=user_id,
        session_id=session_id,
        data=request.data or {},
    )

    # Handle tool call
    try:
        handler = get_server_tool_handler()
        response = await handler.handle(internal_request)

        logger.info(
            f"[VOICE API] Tool {request.tool_name} "
            f"{'succeeded' if response.success else 'failed'}"
        )

        return ServerToolAPIResponse(
            success=response.success,
            data=response.data,
            error=response.error,
        )

    except Exception as e:
        logger.error(f"[VOICE API] Server tool error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Tool execution failed: {type(e).__name__}",
        )


# === Webhook Models (T053) ===


class WebhookResponse(BaseModel):
    """Response for webhook processing."""

    status: str = Field(..., description="Processing status")
    message: str | None = Field(default=None, description="Status message")


# === Webhook HMAC Validation (T054) ===

# Shared auth: verify_elevenlabs_signature imported from nikita.api.utils.webhook_auth
from nikita.api.utils.webhook_auth import verify_elevenlabs_signature


async def _process_webhook_event(event_data: dict) -> dict:
    """
    Process webhook event from ElevenLabs.

    Handles event types:
    - post_call_transcription: Store transcript, trigger post-processing
    - call_initiation_failure: Log error
    - call_ended: Log call completion
    """
    # ElevenLabs uses "type" not "event_type" (Issue #12 fix)
    event_type = event_data.get("type")

    # Debug: log raw payload structure
    logger.info(f"[WEBHOOK] Raw payload keys: {list(event_data.keys())}")

    if event_type == "post_call_transcription":
        # ElevenLabs nests everything under "data" (Issue #12 fix)
        data = event_data.get("data", {})
        session_id = data.get("conversation_id")
        transcript_data = data.get("transcript", [])

        # user_id comes from our dynamic_variables (set in pre-call response)
        # Structure: data.conversation_initiation_client_data.dynamic_variables.secret__user_id
        client_data = data.get("conversation_initiation_client_data", {})
        dynamic_vars = client_data.get("dynamic_variables", {})
        user_id_str = dynamic_vars.get("secret__user_id")

        logger.info(
            f"[WEBHOOK] Post-call transcription received: "
            f"session_id={session_id}, user_id={user_id_str}, "
            f"transcript_entries={len(transcript_data) if isinstance(transcript_data, list) else 'raw'}"
        )

        if not user_id_str:
            logger.warning("[WEBHOOK] No user_id in metadata - cannot process transcript")
            return {
                "status": "skipped",
                "reason": "missing_user_id",
                "conversation_id": session_id,
            }

        try:
            # A1: Parse ElevenLabs transcript format
            from datetime import UTC, datetime
            from uuid import UUID

            user_id = UUID(user_id_str)

            # Parse transcript - can be list of turns or raw string
            if isinstance(transcript_data, list):
                # ElevenLabs format: [{"role": "user"|"agent", "message": "...", ...}]
                messages = []
                transcript_lines = []
                for turn in transcript_data:
                    role = turn.get("role", "unknown")
                    # Normalize role names (ElevenLabs uses "agent" for AI)
                    if role == "agent":
                        role = "nikita"
                    message = turn.get("message", turn.get("text", ""))

                    messages.append({
                        "role": role,
                        "content": message,
                        "timestamp": turn.get("time_in_call_secs", datetime.now(UTC).isoformat()),
                    })
                    transcript_lines.append(f"{role}: {message}")

                transcript_raw = "\n".join(transcript_lines)
            else:
                # Raw string format - parse it
                transcript_raw = str(transcript_data)
                messages = [{"role": "system", "content": transcript_raw, "timestamp": datetime.now(UTC).isoformat()}]

            # A2: Create conversation record with platform='voice'
            from nikita.db.database import get_session_maker
            from nikita.db.models.conversation import Conversation
            from nikita.db.repositories.user_repository import UserRepository

            session_maker = get_session_maker()
            async with session_maker() as session:
                # Load user to get chapter
                user_repo = UserRepository(session)
                user = await user_repo.get(user_id)

                if user is None:
                    logger.warning(f"[WEBHOOK] User {user_id} not found - skipping transcript")
                    return {
                        "status": "skipped",
                        "reason": "user_not_found",
                        "conversation_id": session_id,
                    }

                # Create conversation record
                conversation = Conversation(
                    user_id=user_id,
                    platform="voice",
                    messages=messages,
                    started_at=datetime.now(UTC),
                    chapter_at_time=user.chapter,
                    elevenlabs_session_id=session_id,
                    transcript_raw=transcript_raw,
                    status="active",  # Will be processed by PostProcessor
                    last_message_at=datetime.now(UTC),  # Trigger post-processing
                )
                session.add(conversation)
                await session.flush()
                await session.commit()  # CRITICAL: Persist conversation BEFORE scoring (P0 bug fix)
                await session.refresh(conversation)
                conversation_db_id = conversation.id

                logger.info(
                    f"[WEBHOOK] Created voice conversation: "
                    f"id={conversation_db_id}, user={user_id}, session={session_id}, "
                    f"messages={len(messages)}"
                )

                # DEBT-002: Track call end time and duration
                try:
                    from nikita.db.repositories.voice_call_repository import (
                        VoiceCallRepository,
                    )

                    voice_call_repo = VoiceCallRepository(session)
                    call_duration = data.get("call_duration_secs")
                    if (
                        call_duration is None
                        and isinstance(transcript_data, list)
                        and transcript_data
                    ):
                        last_turn = transcript_data[-1]
                        call_duration = int(
                            last_turn.get("time_in_call_secs", 0)
                        )
                    await voice_call_repo.update_call_end(
                        session_id=session_id,
                        ended_at=datetime.now(UTC),
                        duration_seconds=int(call_duration or 0),
                    )
                    await session.commit()
                except Exception as call_end_err:
                    logger.warning(
                        "[WEBHOOK] Failed to update call end (non-fatal): %s",
                        call_end_err,
                    )

                # P3: Score the voice conversation (Issue #17 fix)
                # Parse transcript into (user, nikita) exchange tuples
                score_delta = Decimal("0")
                try:
                    from nikita.agents.voice.scoring import VoiceCallScorer
                    from nikita.engine.scoring.models import ConversationContext

                    # Build transcript as (user_msg, nikita_response) tuples
                    # Filter out pairs where either message has None content (tool calls, interruptions)
                    transcript_pairs = []
                    i = 0
                    while i < len(messages) - 1:
                        if messages[i]["role"] == "user" and messages[i + 1]["role"] == "nikita":
                            user_content = messages[i].get("content")
                            nikita_content = messages[i + 1].get("content")
                            # Only add pair if both have valid string content
                            if (
                                user_content is not None
                                and nikita_content is not None
                                and isinstance(user_content, str)
                                and isinstance(nikita_content, str)
                            ):
                                transcript_pairs.append((user_content, nikita_content))
                            i += 2
                        else:
                            i += 1

                    if transcript_pairs:
                        # Build context for scoring
                        context = ConversationContext(
                            chapter=user.chapter,
                            relationship_score=user.relationship_score,
                            # Filter out None content (tool calls, interruptions, system events)
                            recent_messages=[
                                (msg["role"], msg["content"])
                                for msg in messages
                                if msg.get("content") is not None and isinstance(msg.get("content"), str)
                            ],
                            engagement_state="in_zone",  # Default for voice
                        )

                        scorer = VoiceCallScorer()
                        call_score = await scorer.score_call(
                            user_id=user_id,
                            session_id=session_id,
                            transcript=transcript_pairs,
                            context=context,
                            duration_seconds=0,  # Not available in webhook
                        )

                        # Apply score to user metrics
                        await scorer.apply_score(user_id, call_score)

                        # Calculate total delta for storage
                        score_delta = (
                            call_score.deltas.intimacy +
                            call_score.deltas.passion +
                            call_score.deltas.trust +
                            call_score.deltas.secureness
                        )

                        # Store score_delta on conversation
                        conversation.score_delta = score_delta
                        session.add(conversation)

                        logger.info(
                            f"[WEBHOOK] Scored voice call: user={user_id}, "
                            f"delta={score_delta}, explanation={call_score.explanation[:50]}..."
                        )

                        # Spec 113 FR-001: Boss threshold check after voice scoring (non-fatal).
                        # IMPORTANT: apply_score() commits in its own independent session.
                        # Must re-fetch user via repo.get() — session.refresh() returns stale data.
                        # user_repo is already instantiated above (line 614); reuse it (DD-7).
                        try:
                            from nikita.engine.chapters.boss import BossStateMachine
                            fresh_user = await user_repo.get(user_id)
                            if fresh_user:
                                boss_sm = BossStateMachine()
                                if boss_sm.should_trigger_boss(
                                    relationship_score=fresh_user.relationship_score,
                                    chapter=fresh_user.chapter,
                                    game_status=fresh_user.game_status,
                                    cool_down_until=fresh_user.cool_down_until,
                                ):
                                    await user_repo.set_boss_fight_status(user_id)
                                    logger.info(
                                        "[VOICE-BOSS] Boss triggered: user=%s chapter=%d",
                                        user_id,
                                        fresh_user.chapter,
                                    )
                        except Exception as boss_err:
                            logger.warning("[VOICE-BOSS] Boss check failed (non-fatal): %s", boss_err)

                        # Spec 113 FR-002: Consecutive crises after voice scoring (non-fatal).
                        # Uses details.zone == "critical" (temperature-based), consistent with
                        # text path at scoring/service.py:316. Not a raw relationship_score threshold.
                        try:
                            from nikita.conflicts.persistence import (
                                load_conflict_details,
                                save_conflict_details,
                            )
                            from nikita.conflicts.models import ConflictDetails

                            raw_details = await load_conflict_details(user_id, session)
                            details = ConflictDetails.from_jsonb(raw_details) if raw_details else ConflictDetails()

                            if score_delta < 0 and details.zone == "critical":
                                details.consecutive_crises += 1
                                logger.info(
                                    "[VOICE-CRISIS] crisis #%d user=%s",
                                    details.consecutive_crises,
                                    user_id,
                                )
                            elif score_delta > 0 and details.consecutive_crises > 0:
                                details.consecutive_crises = 0
                                logger.info("[VOICE-CRISIS] crises reset user=%s", user_id)

                            await save_conflict_details(user_id, details.to_jsonb(), session)
                        except Exception as crisis_err:
                            logger.warning("[VOICE-CRISIS] Crisis update failed (non-fatal): %s", crisis_err)

                except Exception as e:
                    # Non-fatal - log but continue with post-processing
                    logger.warning(f"[WEBHOOK] Failed to score voice call: {e}")

                # A3: Trigger post-processing pipeline (AC-FR015-002)
                # NOTE: PostProcessor deprecated (Spec 042), only use unified pipeline
                settings = get_settings()
                pipeline_result = None
                if settings.unified_pipeline_enabled:
                    try:
                        from nikita.pipeline.orchestrator import PipelineOrchestrator

                        orchestrator = PipelineOrchestrator(session)

                        # Spec 051: Run pipeline async to avoid webhook timeout
                        # Voice pipeline can take 30-60s (memory queries, LLM calls)
                        # ElevenLabs webhooks timeout at 30s
                        import asyncio

                        async def run_pipeline():
                            """Run pipeline in background without blocking webhook response."""
                            try:
                                result = await orchestrator.process(
                                    conversation_id=conversation_db_id,
                                    user_id=user_id,
                                    platform="voice",
                                    conversation=conversation,
                                    user=user,
                                )
                                logger.info(
                                    f"[WEBHOOK] Pipeline completed async: "
                                    f"success={result.success}, stages={len(result.stage_timings)}"
                                )
                            except Exception as e:
                                logger.error(f"[WEBHOOK] Async pipeline error: {e}", exc_info=True)

                        # Create task without awaiting (non-blocking)
                        asyncio.create_task(run_pipeline())

                        logger.info(
                            f"[WEBHOOK] Pipeline scheduled async for conversation {conversation_db_id}"
                        )

                    except Exception as e:
                        logger.warning(f"[WEBHOOK] Pipeline scheduling failed (non-fatal): {e}")

                await session.commit()

                # Build response (pipeline runs async, no result available yet)
                return {
                    "status": "processed",
                    "transcript_stored": True,
                    "conversation_id": session_id,
                    "db_conversation_id": str(conversation_db_id),
                    "post_processing": {
                        "scheduled": settings.unified_pipeline_enabled,
                        "pipeline": "unified" if settings.unified_pipeline_enabled else "legacy",
                        "note": "Pipeline runs async, check logs for completion status",
                    },
                }

        except Exception as e:
            logger.error(f"[WEBHOOK] Failed to process transcript: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "conversation_id": session_id,
            }

    elif event_type == "call_initiation_failure":
        # Log failure (AC-T053.4)
        # ElevenLabs structure: data.failure_reason (Issue #12 fix)
        data = event_data.get("data", {})
        reason = data.get("failure_reason", "unknown")
        conversation_id = data.get("conversation_id", "unknown")
        logger.warning(
            f"[WEBHOOK] Call initiation failed: reason={reason}, "
            f"conversation_id={conversation_id}"
        )

        return {"status": "logged", "event_type": "call_initiation_failure"}

    elif event_type == "post_call_audio":
        # Log audio webhook (just acknowledge, we don't process audio)
        data = event_data.get("data", {})
        conversation_id = data.get("conversation_id", "unknown")
        logger.info(f"[WEBHOOK] Post-call audio received: conversation_id={conversation_id}")

        return {"status": "acknowledged", "event_type": "post_call_audio"}

    else:
        # Unknown event type
        logger.info(f"[WEBHOOK] Unknown event type: {event_type}")
        return {"status": "ignored", "reason": "unknown_event_type"}


# === Webhook Endpoint (T053) ===


@router.post(
    "/webhook",
    response_model=WebhookResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid signature"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="ElevenLabs Webhook",
    description="""
    Handle webhooks from ElevenLabs Conversational AI.

    Events handled:
    - post_call_transcription: Voice call transcript for post-processing
    - call_initiation_failure: Log failures
    - call_ended: Log call completion

    **Security**: Validates HMAC signature in elevenlabs-signature header.

    AC-T053.1: Handles post_call_transcription
    AC-T053.2: Validates HMAC signature
    AC-T053.3: Extracts transcript and metadata
    AC-T053.4: Logs call_initiation_failure events
    """,
)
async def handle_webhook(
    request: Request,
    elevenlabs_signature: str | None = Header(default=None, alias="elevenlabs-signature"),
) -> WebhookResponse:
    """
    Handle ElevenLabs webhook (T053).

    AC-FR015-001: Store transcript when post_call_transcription received
    AC-FR015-005: Validate HMAC signature
    """
    # Read raw body for signature validation
    body = await request.body()
    payload = body.decode("utf-8")

    # Validate signature (AC-T054.4)
    if not elevenlabs_signature:
        logger.warning("[WEBHOOK] Missing elevenlabs-signature header")
        raise HTTPException(
            status_code=401,
            detail="Missing signature header",
        )

    settings = get_settings()
    if not settings.elevenlabs_webhook_secret:
        logger.error("[WEBHOOK] ELEVENLABS_WEBHOOK_SECRET not configured")
        raise HTTPException(status_code=500, detail="Voice webhook secret not configured")
    secret = settings.elevenlabs_webhook_secret

    try:
        if not verify_elevenlabs_signature(payload, elevenlabs_signature, secret):
            logger.warning("[WEBHOOK] Invalid signature")
            raise HTTPException(
                status_code=401,
                detail="Invalid signature",
            )
    except ValueError as e:
        logger.warning(f"[WEBHOOK] Signature validation failed: {e}")
        raise HTTPException(
            status_code=401,
            detail=str(e),
        )

    # Parse event data
    try:
        import json
        event_data = json.loads(payload)
    except json.JSONDecodeError as e:
        logger.error(f"[WEBHOOK] Invalid JSON payload: {e}")
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload",
        )

    # Process event
    try:
        result = await _process_webhook_event(event_data)
        return WebhookResponse(
            status=result.get("status", "processed"),
            message=result.get("reason"),
        )
    except Exception as e:
        logger.error(f"[WEBHOOK] Processing error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Webhook processing failed: {type(e).__name__}",
        )


# === Pre-Call Webhook (T078) ===


class PreCallRequest(BaseModel):
    """Request from Twilio/ElevenLabs pre-call webhook.

    ElevenLabs sends these fields when a call comes in via Twilio.
    See: https://elevenlabs.io/docs/agents-platform/twilio#pre-call-webhook
    """

    caller_id: str = Field(..., description="Caller's phone number (E.164)")
    agent_id: str = Field(..., description="ElevenLabs agent ID")
    called_number: str = Field(..., description="Number that was called")
    call_sid: str = Field(..., description="Unique Twilio call identifier")


class PreCallResponse(BaseModel):
    """Response for pre-call webhook.

    ElevenLabs expects a conversation_initiation_client_data event format.
    See: https://elevenlabs.io/docs/agents-platform/twilio#personalization
    """

    type: str = Field(
        default="conversation_initiation_client_data",
        description="Event type (must be conversation_initiation_client_data)",
    )
    dynamic_variables: dict | None = Field(
        default=None, description="Variables for prompt interpolation"
    )
    conversation_config_override: dict | None = Field(
        default=None, description="TTS, prompt, and first message overrides"
    )


@router.post(
    "/pre-call",
    response_model=PreCallResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid signature"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Handle Pre-Call Webhook",
    description="""
    Handle pre-call webhooks from Twilio/ElevenLabs for inbound calls.

    This endpoint is called before accepting an inbound voice call:
    - Receives caller_id, agent_id, called_number, call_sid from ElevenLabs
    - Looks up user by phone number (caller_id)
    - Checks if Nikita is available (chapter-based)
    - Returns conversation_initiation_client_data event

    **Returns** (conversation_initiation_client_data format):
    - type: "conversation_initiation_client_data"
    - dynamic_variables: User context for prompt interpolation
    - conversation_config_override: TTS, prompt, and first message overrides

    AC-T078.1: POST /api/v1/voice/pre-call handles Twilio-ElevenLabs pre-call
    AC-T078.2: Returns dynamic_variables and conversation_config_override
    AC-T078.3: Returns empty dynamic_variables for unknown callers (call still accepted)
    AC-T078.4: Validates HMAC signature
    """,
)
async def handle_pre_call(
    request: Request,
    elevenlabs_signature: str | None = Header(default=None, alias="elevenlabs-signature"),
) -> PreCallResponse:
    """
    Handle pre-call webhook (T078).

    AC-T078.1: Handles Twilio-ElevenLabs pre-call
    AC-T078.2: Returns dynamic_variables and conversation_config_override
    AC-T078.3: Returns empty dynamic_variables for unknown callers
    AC-T078.4: Validates HMAC signature (SEC-006)
    """
    # Read raw body once (needed for both HMAC verification and parsing)
    body = await request.body()
    payload = body.decode("utf-8")

    # SEC-006: Validate HMAC signature (same pattern as post-call webhook)
    settings = get_settings()
    if settings.elevenlabs_webhook_secret:
        if not elevenlabs_signature:
            logger.warning("[PRE-CALL] Missing elevenlabs-signature header")
            raise HTTPException(status_code=401, detail="Missing signature header")

        try:
            if not verify_elevenlabs_signature(
                payload, elevenlabs_signature, settings.elevenlabs_webhook_secret
            ):
                logger.warning("[PRE-CALL] Invalid HMAC signature")
                raise HTTPException(status_code=401, detail="Invalid signature")
        except ValueError as e:
            logger.warning(f"[PRE-CALL] Signature validation failed: {e}")
            raise HTTPException(status_code=401, detail=str(e))

    # Parse body into PreCallRequest model
    try:
        body_data = json.loads(payload)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    try:
        pre_call = PreCallRequest(**body_data)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    # SEC-005/SEC-009: Log with masked PII, keys-only for dynamic_variables
    logger.info(
        f"[PRE-CALL] Incoming request: "
        f"caller_id={mask_phone(pre_call.caller_id)}, "
        f"agent_id={pre_call.agent_id}, "
        f"called_number={mask_phone(pre_call.called_number)}, "
        f"call_sid={pre_call.call_sid}"
    )

    try:
        from nikita.agents.voice.inbound import get_inbound_handler

        handler = get_inbound_handler()
        result = await handler.handle_incoming_call(pre_call.caller_id)

        # Log handler result with keys only (SEC-009: no dynamic_variables values)
        dv_keys = list(result.get("dynamic_variables", {}).keys()) if result.get("dynamic_variables") else None
        logger.info(
            f"[PRE-CALL] Handler result: "
            f"accept_call={result.get('accept_call')}, "
            f"dynamic_variables_keys={dv_keys}, "
            f"has_config_override={result.get('conversation_config_override') is not None}"
        )

        # Build response
        response = PreCallResponse(
            type="conversation_initiation_client_data",
            dynamic_variables=result.get("dynamic_variables"),
            conversation_config_override=result.get("conversation_config_override"),
        )

        # SEC-009: Log only keys, not full dynamic_variables values
        logger.info(
            f"[PRE-CALL] Sending response: "
            f"type={response.type}, "
            f"dynamic_variables_keys={list(response.dynamic_variables.keys()) if response.dynamic_variables else None}, "
            f"conversation_config_override_keys={list(response.conversation_config_override.keys()) if response.conversation_config_override else None}"
        )

        return response

    except Exception as e:
        logger.error(f"[PRE-CALL] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Pre-call processing failed: {type(e).__name__}",
        )

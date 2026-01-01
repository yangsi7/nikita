"""Voice API routes for call initiation and server tools.

Implements:
- T007: Call initiation endpoint (POST /api/v1/voice/initiate)
- T013: Server tool endpoint (POST /api/v1/voice/server-tool)

Part of Spec 007: Voice Agent (ElevenLabs Conversational AI 2.0).
"""

import hashlib
import hmac
import logging
import time
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from nikita.agents.voice.availability import get_availability_service
from nikita.agents.voice.models import ServerToolName, ServerToolRequest
from nikita.agents.voice.server_tools import get_server_tool_handler
from nikita.agents.voice.service import get_voice_service
from nikita.config.settings import get_settings

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


def _validate_signed_token(token: str) -> tuple[str, str]:
    """
    Validate signed token and extract user_id and session_id.

    Token format: {user_id}:{session_id}:{timestamp}:{signature}

    AC-T013.2: Validates ElevenLabs webhook signature
    """
    parts = token.split(":")
    if len(parts) != 4:
        raise ValueError("Invalid token format")

    user_id, session_id, timestamp_str, signature = parts

    # Validate timestamp
    try:
        timestamp = int(timestamp_str)
    except ValueError:
        raise ValueError("Invalid timestamp")

    # Check if token is expired (5 minute window)
    current_time = int(time.time())
    if current_time - timestamp > 300:
        raise ValueError("Token expired")

    # Verify signature
    settings = get_settings()
    secret = settings.elevenlabs_webhook_secret or "default_voice_secret"
    payload = f"{user_id}:{session_id}:{timestamp_str}"
    expected_signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        raise ValueError("Invalid signature")

    return user_id, session_id


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
    - get_memory: Query Graphiti memory system
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

WEBHOOK_TIMESTAMP_TOLERANCE = 300  # 5 minutes


def verify_elevenlabs_signature(
    payload: str, signature_header: str, secret: str
) -> bool:
    """
    Verify ElevenLabs webhook signature (T054).

    Signature format: t={timestamp},v1={signature}

    AC-T054.1: Validates "timestamp.payload" format
    AC-T054.2: Rejects timestamps older than 5 minutes
    AC-T054.3: Uses constant-time comparison
    """
    if not signature_header:
        return False

    # Parse signature header
    parts = {}
    for part in signature_header.split(","):
        if "=" in part:
            key, value = part.split("=", 1)
            parts[key] = value

    timestamp_str = parts.get("t")
    signature = parts.get("v1")

    if not timestamp_str or not signature:
        return False

    # Validate timestamp
    try:
        timestamp = int(timestamp_str)
    except ValueError:
        return False

    current_time = int(time.time())
    if current_time - timestamp > WEBHOOK_TIMESTAMP_TOLERANCE:
        raise ValueError("Webhook timestamp expired")

    # Verify signature using constant-time comparison
    message = f"{timestamp}.{payload}"
    expected_signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)


async def _process_webhook_event(event_data: dict) -> dict:
    """
    Process webhook event from ElevenLabs.

    Handles event types:
    - post_call_transcription: Store transcript, trigger post-processing
    - call_initiation_failure: Log error
    - call_ended: Log call completion
    """
    event_type = event_data.get("event_type")

    if event_type == "post_call_transcription":
        # Store transcript and trigger post-processing (AC-FR015-001)
        conversation_id = event_data.get("conversation_id")
        transcript = event_data.get("transcript", "")

        logger.info(
            f"[WEBHOOK] Post-call transcription received: "
            f"conversation_id={conversation_id}, len={len(transcript)}"
        )

        # TODO: Store transcript in conversation table
        # TODO: Trigger voice post-processing pipeline (AC-FR015-002)

        return {
            "status": "processed",
            "transcript_stored": True,
            "conversation_id": conversation_id,
        }

    elif event_type == "call_initiation_failure":
        # Log failure (AC-T053.4)
        reason = event_data.get("reason", "unknown")
        logger.warning(f"[WEBHOOK] Call initiation failed: {reason}")

        return {"status": "logged", "event_type": "call_initiation_failure"}

    elif event_type == "call_ended":
        # Log call completion
        conversation_id = event_data.get("conversation_id")
        duration = event_data.get("call_duration_seconds", 0)
        logger.info(
            f"[WEBHOOK] Call ended: conversation_id={conversation_id}, "
            f"duration={duration}s"
        )

        return {"status": "logged", "event_type": "call_ended"}

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
    secret = settings.elevenlabs_webhook_secret or "default_voice_secret"

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

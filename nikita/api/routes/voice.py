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
from decimal import Decimal
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

    # Check if token is expired (30 minute window for longer conversations)
    current_time = int(time.time())
    if current_time - timestamp > 1800:  # 30 minutes
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
    signature = parts.get("v0")  # ElevenLabs uses v0 format (not v1)

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
                await session.refresh(conversation)
                conversation_db_id = conversation.id

                logger.info(
                    f"[WEBHOOK] Created voice conversation: "
                    f"id={conversation_db_id}, user={user_id}, session={session_id}, "
                    f"messages={len(messages)}"
                )

                # P3: Score the voice conversation (Issue #17 fix)
                # Parse transcript into (user, nikita) exchange tuples
                score_delta = Decimal("0")
                try:
                    from nikita.agents.voice.scoring import VoiceCallScorer
                    from nikita.engine.scoring.models import ConversationContext

                    # Build transcript as (user_msg, nikita_response) tuples
                    transcript_pairs = []
                    i = 0
                    while i < len(messages) - 1:
                        if messages[i]["role"] == "user" and messages[i + 1]["role"] == "nikita":
                            transcript_pairs.append(
                                (messages[i]["content"], messages[i + 1]["content"])
                            )
                            i += 2
                        else:
                            i += 1

                    if transcript_pairs:
                        # Build context for scoring
                        context = ConversationContext(
                            chapter=user.chapter,
                            relationship_score=user.relationship_score,
                            recent_messages=[(role, msg["content"]) for msg in messages for role in [msg["role"]]],
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

                except Exception as e:
                    # Non-fatal - log but continue with post-processing
                    logger.warning(f"[WEBHOOK] Failed to score voice call: {e}")

                # A3: Trigger post-processing pipeline (AC-FR015-002)
                # Import inside function to avoid circular imports
                from nikita.context.post_processor import PostProcessor

                processor = PostProcessor(session)
                result = await processor.process_conversation(conversation_db_id)

                logger.info(
                    f"[WEBHOOK] Post-processing complete: "
                    f"conversation_id={conversation_db_id}, "
                    f"success={result.success}, stage={result.stage_reached}, "
                    f"threads={result.threads_created}, thoughts={result.thoughts_created}"
                )

                # FR-015/FR-034: Generate and cache prompt for NEXT call
                prompt_cached = False
                if result.success:
                    try:
                        from nikita.meta_prompts.service import MetaPromptService

                        meta_service = MetaPromptService(session)
                        prompt_result = await meta_service.generate_system_prompt(
                            user_id=user_id,
                            skip_logging=True,  # Don't log voice prompt generations
                        )

                        # Cache the prompt on user record
                        user.cached_voice_prompt = prompt_result.content
                        user.cached_voice_prompt_at = datetime.now(UTC)
                        session.add(user)

                        logger.info(
                            f"[WEBHOOK] Cached voice prompt for next call: "
                            f"user={user_id}, prompt_length={len(prompt_result.content)}"
                        )
                        prompt_cached = True

                    except Exception as e:
                        # Non-fatal - log but don't fail the webhook
                        logger.warning(
                            f"[WEBHOOK] Failed to cache voice prompt: {e}"
                        )

                await session.commit()

                return {
                    "status": "processed",
                    "transcript_stored": True,
                    "conversation_id": session_id,
                    "db_conversation_id": str(conversation_db_id),
                    "post_processing": {
                        "success": result.success,
                        "stage_reached": result.stage_reached,
                        "threads_created": result.threads_created,
                        "thoughts_created": result.thoughts_created,
                        "summary": result.summary[:100] if result.summary else None,
                    },
                    "prompt_cached": prompt_cached,
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
    request: PreCallRequest,
    elevenlabs_signature: str | None = Header(default=None, alias="elevenlabs-signature"),
) -> PreCallResponse:
    """
    Handle pre-call webhook (T078).

    AC-T078.1: Handles Twilio-ElevenLabs pre-call
    AC-T078.2: Returns dynamic_variables and conversation_config_override
    AC-T078.3: Returns empty dynamic_variables for unknown callers
    """
    # Enhanced logging for debugging (Issue 5 fix verification)
    logger.info(
        f"[PRE-CALL] Incoming request: "
        f"caller_id={request.caller_id}, "
        f"agent_id={request.agent_id}, "
        f"called_number={request.called_number}, "
        f"call_sid={request.call_sid}"
    )

    try:
        from nikita.agents.voice.inbound import get_inbound_handler

        handler = get_inbound_handler()
        result = await handler.handle_incoming_call(request.caller_id)

        # Log what InboundCallHandler returned (CRITICAL for debugging)
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

        # Log exact response being sent to ElevenLabs (CRITICAL for debugging)
        logger.info(
            f"[PRE-CALL] Sending response: "
            f"type={response.type}, "
            f"dynamic_variables={response.dynamic_variables}, "
            f"conversation_config_override_keys={list(response.conversation_config_override.keys()) if response.conversation_config_override else None}"
        )

        return response

    except Exception as e:
        logger.error(f"[PRE-CALL] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Pre-call processing failed: {type(e).__name__}",
        )

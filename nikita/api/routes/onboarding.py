"""Onboarding API routes for Meta-Nikita voice onboarding (Spec 028).

Implements:
- T012: Initiate onboarding call endpoint
- T013: Onboarding server tool endpoint
- T014: Onboarding webhook endpoint

Part of Spec 028: Voice Onboarding.
"""

import hashlib
import hmac
import logging
import time
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.config.elevenlabs import get_agent_id
from nikita.config.settings import get_settings
from nikita.db.database import get_session_maker
from nikita.db.repositories.user_repository import UserRepository
from nikita.onboarding import (
    OnboardingServerToolHandler,
    OnboardingToolRequest,
    OnboardingToolResponse,
    VoiceOnboardingFlow,
)
from nikita.onboarding.meta_nikita import META_NIKITA_FIRST_MESSAGE

logger = logging.getLogger(__name__)
router = APIRouter(tags=["onboarding"])


# === Request/Response Models ===


class InitiateOnboardingRequest(BaseModel):
    """Request to initiate an onboarding call."""

    user_name: str | None = Field(default=None, description="User's display name")


class InitiateOnboardingResponse(BaseModel):
    """Response with connection parameters for onboarding call."""

    agent_id: str = Field(..., description="Meta-Nikita agent ID")
    signed_token: str = Field(..., description="Signed auth token")
    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User UUID")
    dynamic_variables: dict = Field(
        default_factory=dict, description="Variables for prompt interpolation"
    )


class OnboardingStatusResponse(BaseModel):
    """Response with user's onboarding status."""

    user_id: str = Field(..., description="User UUID")
    status: str = Field(..., description="Onboarding status")
    onboarded_at: str | None = Field(default=None, description="Completion timestamp")
    profile: dict | None = Field(default=None, description="Collected profile data")


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str


# === Dependency Injection ===


async def get_db_session() -> AsyncSession:
    """Get database session."""
    session_maker = get_session_maker()
    async with session_maker() as session:
        yield session


async def get_user_repo(session: AsyncSession = Depends(get_db_session)) -> UserRepository:
    """Get user repository."""
    return UserRepository(session)


# Singleton handler instance
_onboarding_handler: OnboardingServerToolHandler | None = None


def get_onboarding_handler() -> OnboardingServerToolHandler:
    """Get or create the onboarding server tool handler."""
    global _onboarding_handler
    if _onboarding_handler is None:
        _onboarding_handler = OnboardingServerToolHandler()
    return _onboarding_handler


# === Endpoints ===


@router.get(
    "/status/{user_id}",
    response_model=OnboardingStatusResponse,
    responses={
        404: {"model": ErrorResponse, "description": "User not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Check Onboarding Status",
    description="""
    Get the onboarding status for a user.

    Returns:
    - status: pending, in_progress, completed, or skipped
    - onboarded_at: Timestamp when onboarding completed
    - profile: Collected profile data (if completed)
    """,
)
async def get_onboarding_status(
    user_id: UUID,
    user_repo: UserRepository = Depends(get_user_repo),
) -> OnboardingStatusResponse:
    """Get user's onboarding status."""
    try:
        user = await user_repo.get(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return OnboardingStatusResponse(
            user_id=str(user_id),
            status=user.onboarding_status,
            onboarded_at=user.onboarded_at.isoformat() if user.onboarded_at else None,
            profile=user.onboarding_profile,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting onboarding status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/initiate/{user_id}",
    response_model=InitiateOnboardingResponse,
    responses={
        400: {"model": ErrorResponse, "description": "User already onboarded"},
        404: {"model": ErrorResponse, "description": "User not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Initiate Onboarding Call",
    description="""
    Initiate a Meta-Nikita voice onboarding call.

    Returns connection parameters needed to start the ElevenLabs
    Conversational AI session with Meta-Nikita.

    **T012**: POST /api/v1/onboarding/initiate/{user_id}
    """,
)
async def initiate_onboarding(
    user_id: UUID,
    request: InitiateOnboardingRequest | None = None,
    user_repo: UserRepository = Depends(get_user_repo),
) -> InitiateOnboardingResponse:
    """Initiate an onboarding voice call."""
    try:
        user = await user_repo.get(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Check if already onboarded
        if user.onboarding_status in ("completed", "skipped"):
            raise HTTPException(
                status_code=400,
                detail=f"User already onboarded (status: {user.onboarding_status})",
            )

        # Update status to in_progress
        await user_repo.update_onboarding_status(user_id, "in_progress")

        # Generate session ID and signed token
        settings = get_settings()
        session_id = f"onboarding_{user_id}_{int(time.time())}"

        # Create signed token for server tool authentication
        token_data = f"{user_id}:{session_id}:{int(time.time())}"
        if not settings.elevenlabs_webhook_secret:
            raise ValueError("ELEVENLABS_WEBHOOK_SECRET must be configured")
        secret = settings.elevenlabs_webhook_secret
        signed_token = hmac.new(
            secret.encode(),
            token_data.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Get Meta-Nikita agent ID
        agent_id = get_agent_id(is_onboarding=True)

        # Build dynamic variables for Meta-Nikita
        user_name = request.user_name if request else None
        dynamic_variables = {
            "user_name": user_name or "there",
            "user_id": str(user_id),
        }

        logger.info(f"Initiated onboarding call for user {user_id}, session {session_id}")

        return InitiateOnboardingResponse(
            agent_id=agent_id,
            signed_token=signed_token,
            session_id=session_id,
            user_id=str(user_id),
            dynamic_variables=dynamic_variables,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating onboarding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/server-tool",
    response_model=OnboardingToolResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Handle Onboarding Server Tool",
    description="""
    Handle server tool calls from ElevenLabs during Meta-Nikita onboarding.

    Supported tools:
    - collect_profile: Store profile fields (timezone, occupation, etc.)
    - configure_preferences: Set darkness_level, pacing, conversation_style
    - complete_onboarding: Mark onboarding complete and trigger handoff

    **T013**: POST /api/v1/onboarding/server-tool
    """,
)
async def handle_server_tool(
    request: OnboardingToolRequest,
    handler: OnboardingServerToolHandler = Depends(get_onboarding_handler),
) -> OnboardingToolResponse:
    """Handle an onboarding server tool request."""
    try:
        logger.info(
            f"Onboarding server tool request: {request.tool_name} for user {request.user_id}"
        )
        result = await handler.handle_request(request)
        logger.info(f"Onboarding server tool result: success={result.success}")
        return result
    except Exception as e:
        logger.error(f"Error handling onboarding server tool: {e}")
        return OnboardingToolResponse(
            success=False,
            error=str(e),
        )


@router.post(
    "/webhook",
    responses={
        200: {"description": "Webhook processed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid signature"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Handle Onboarding Webhook",
    description="""
    Handle webhook events from ElevenLabs for onboarding calls.

    Events:
    - call_started: Onboarding call started
    - call_ended: Onboarding call ended

    **T014**: POST /api/v1/onboarding/webhook
    """,
)
async def handle_webhook(
    request: Request,
    elevenlabs_signature: str | None = Header(None, alias="X-ElevenLabs-Signature"),
    user_repo: UserRepository = Depends(get_user_repo),
) -> dict[str, Any]:
    """Handle ElevenLabs webhook for onboarding calls."""
    try:
        # Get raw body for signature verification
        body = await request.body()
        body_str = body.decode("utf-8")

        # Parse payload
        import json
        payload = json.loads(body_str)

        # Verify signature (optional in dev)
        settings = get_settings()
        if settings.elevenlabs_webhook_secret and elevenlabs_signature:
            # ElevenLabs uses t=timestamp,v0=hash format
            try:
                parts = dict(p.split("=", 1) for p in elevenlabs_signature.split(","))
                timestamp = parts.get("t", "")
                received_sig = parts.get("v0", "")

                # Compute expected signature
                message = f"{timestamp}.{body_str}"
                expected_sig = hmac.new(
                    settings.elevenlabs_webhook_secret.encode(),
                    message.encode(),
                    hashlib.sha256,
                ).hexdigest()

                if not hmac.compare_digest(received_sig, expected_sig):
                    logger.warning("Invalid webhook signature")
                    # Don't reject in production - log and continue
            except Exception as e:
                logger.warning(f"Signature verification failed: {e}")

        # Extract event data
        event_type = payload.get("type")
        data = payload.get("data", {})

        logger.info(f"Onboarding webhook: {event_type}")

        if event_type == "call_started":
            # Extract user_id from session metadata
            conversation_id = data.get("conversation_id")
            logger.info(f"Onboarding call started: {conversation_id}")

        elif event_type == "call_ended":
            conversation_id = data.get("conversation_id")
            call_duration = data.get("call_duration_seconds", 0)
            logger.info(
                f"Onboarding call ended: {conversation_id}, duration: {call_duration}s"
            )

            # If call ended without completion, we may need to handle this
            # (user hung up early, call dropped, etc.)

        return {"status": "ok", "event": event_type}

    except Exception as e:
        logger.error(f"Error handling onboarding webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/pre-call",
    responses={
        200: {"description": "Pre-call data returned successfully"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Handle Pre-Call Webhook",
    description="""
    Handle ElevenLabs pre-call webhook for onboarding calls.

    ElevenLabs calls this BEFORE starting an outbound conversation to get
    dynamic variables including user_id for server tool authentication.

    Returns:
    - dynamic_variables: user_id and user_name for server tools
    - conversation_config_override: Personalized first message
    """,
)
async def handle_onboarding_pre_call(
    request: Request,
    user_repo: UserRepository = Depends(get_user_repo),
) -> dict[str, Any]:
    """Handle ElevenLabs pre-call webhook for onboarding calls.

    ElevenLabs calls this BEFORE starting a conversation to get dynamic variables.
    Returns user_id so server tools can store data to the correct user.
    """
    try:
        body = await request.json()
        caller_id = body.get("caller_id", "")
        called_number = body.get("called_number", "")

        logger.info(f"Onboarding pre-call webhook: caller_id={caller_id}, called_number={called_number}")

        # Look up user by phone number
        # For INBOUND calls: caller_id = user's phone, called_number = Meta-Nikita's phone
        # For OUTBOUND calls: caller_id = Meta-Nikita's phone, called_number = user's phone
        user = await user_repo.get_by_phone_number(caller_id)
        phone_used = caller_id

        # If not found by caller_id, try called_number (outbound call case)
        if not user and called_number:
            logger.info(f"Pre-call: No user for caller_id, trying called_number: {called_number}")
            user = await user_repo.get_by_phone_number(called_number)
            phone_used = called_number

        if not user:
            logger.warning(f"Pre-call: No user found for caller_id={caller_id} or called_number={called_number}")
            return {
                "type": "conversation_initiation_client_data",
                "dynamic_variables": {
                    "user_id": "",
                    "user_name": "there",
                },
            }

        logger.info(f"Pre-call: Found user {user.id} for phone {phone_used}")

        # Try to get user name from onboarding_profile if available
        user_name = "there"
        if user.onboarding_profile and isinstance(user.onboarding_profile, dict):
            # Name might be stored from previous partial onboarding
            user_name = user.onboarding_profile.get("user_name", "there")

        # Personalize first message if we have user's name
        first_message = META_NIKITA_FIRST_MESSAGE
        if user_name != "there":
            first_message = (
                f"Mmm, {user_name}... finally someone new. "
                "I'm the one who decides if you're worth meeting Nikita. "
                "The rules are simple - keep her interested, or get dumped. "
                "Real consequences. Real feelings. You ready to see what you're made of?"
            )

        return {
            "type": "conversation_initiation_client_data",
            "dynamic_variables": {
                "user_id": str(user.id),
                "user_name": user_name,
            },
            "conversation_config_override": {
                "agent": {
                    "first_message": first_message,
                }
            },
        }

    except Exception as e:
        logger.error(f"Error handling onboarding pre-call: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/call/{user_id}",
    responses={
        200: {"description": "Outbound call initiated successfully"},
        400: {"model": ErrorResponse, "description": "User already onboarded or invalid state"},
        404: {"model": ErrorResponse, "description": "User not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Initiate Onboarding Voice Call",
    description="""
    Initiate an outbound Meta-Nikita onboarding call to a user.

    This endpoint uses the unified phone number architecture (Spec 033):
    - Uses the default Nikita agent with conversation_config_override
    - Meta-Nikita persona is applied via the override
    - After onboarding completes, Nikita calls back without override

    **Prerequisites**:
    - User must have a phone_number set
    - User must not be already onboarded
    - ELEVENLABS_PHONE_NUMBER_ID must be configured

    **Returns**:
    - success: Whether the call was initiated
    - conversation_id: ElevenLabs conversation ID
    - call_sid: Twilio call SID
    """,
)
async def initiate_onboarding_call(
    user_id: UUID,
    user_repo: UserRepository = Depends(get_user_repo),
) -> dict:
    """Initiate an outbound onboarding call with Meta-Nikita persona override."""
    try:
        from nikita.agents.voice.service import get_voice_service
        from nikita.onboarding.meta_nikita import build_meta_nikita_config_override

        user = await user_repo.get(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Check if already onboarded
        if user.onboarding_status in ("completed", "skipped"):
            raise HTTPException(
                status_code=400,
                detail=f"User already onboarded (status: {user.onboarding_status})",
            )

        # Check if user has a phone number
        if not user.phone_number:
            raise HTTPException(
                status_code=400,
                detail="User does not have a phone number set",
            )

        # Update status to in_progress
        await user_repo.update_onboarding_status(user_id, "in_progress")

        # Get user name for personalization
        user_name = "there"
        if user.onboarding_profile and isinstance(user.onboarding_profile, dict):
            user_name = user.onboarding_profile.get("user_name", "there")

        # Build Meta-Nikita config override
        config = build_meta_nikita_config_override(user_id, user_name)

        # Make outbound call with config override
        voice_service = get_voice_service()
        result = await voice_service.make_outbound_call(
            to_number=user.phone_number,
            user_id=user_id,
            conversation_config_override=config["conversation_config_override"],
            dynamic_variables=config["dynamic_variables"],
            is_onboarding=True,
        )

        if result.get("success"):
            logger.info(
                f"Onboarding call initiated for user {user_id}: "
                f"conversation_id={result.get('conversation_id')}"
            )
        else:
            logger.error(f"Onboarding call failed for user {user_id}: {result.get('error')}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating onboarding call: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/skip/{user_id}",
    response_model=OnboardingStatusResponse,
    responses={
        404: {"model": ErrorResponse, "description": "User not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Skip Onboarding",
    description="""
    Allow a user to skip voice onboarding.

    Sets default profile values and marks onboarding as skipped.
    User can still update preferences later via settings.
    """,
)
async def skip_onboarding(
    user_id: UUID,
    user_repo: UserRepository = Depends(get_user_repo),
) -> OnboardingStatusResponse:
    """Skip onboarding for a user."""
    try:
        user = await user_repo.get(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Set default profile
        default_profile = {
            "darkness_level": 3,
            "pacing_weeks": 4,
            "conversation_style": "balanced",
            "skipped": True,
        }

        await user_repo.update_onboarding_profile(user_id, default_profile)
        await user_repo.update_onboarding_status(user_id, "skipped")

        logger.info(f"User {user_id} skipped onboarding")

        return OnboardingStatusResponse(
            user_id=str(user_id),
            status="skipped",
            onboarded_at=None,
            profile=default_profile,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error skipping onboarding: {e}")
        raise HTTPException(status_code=500, detail=str(e))

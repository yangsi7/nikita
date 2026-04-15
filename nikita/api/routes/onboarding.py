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

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.api.dependencies.auth import get_current_user_id
from nikita.api.utils.webhook_auth import validate_signed_token, verify_elevenlabs_signature
from nikita.onboarding.meta_nikita import DEFAULT_META_NIKITA_AGENT_ID
from nikita.config.settings import get_settings
from nikita.db.database import get_async_session, get_session_maker
from nikita.db.repositories.profile_repository import ProfileRepository
from nikita.db.repositories.user_repository import UserRepository
from nikita.db.repositories.vice_repository import VicePreferenceRepository
from nikita.onboarding.handoff import HandoffManager
from nikita.services.portal_onboarding import PortalOnboardingFacade
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


async def get_user_repo(session: AsyncSession = Depends(get_async_session)) -> UserRepository:
    """Get user repository."""
    return UserRepository(session)


async def get_profile_repo(session: AsyncSession = Depends(get_async_session)) -> ProfileRepository:
    """Get profile repository."""
    return ProfileRepository(session)


async def get_vice_repo(session: AsyncSession = Depends(get_async_session)) -> VicePreferenceRepository:
    """Get vice preference repository."""
    return VicePreferenceRepository(session)


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
    current_user_id: UUID = Depends(get_current_user_id),
    user_repo: UserRepository = Depends(get_user_repo),
) -> OnboardingStatusResponse:
    """Get user's onboarding status."""
    try:
        if current_user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
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
    except Exception:
        # FR-7: no PII in exception echo — use logger.exception with user_id only
        logger.exception(
            "Error getting onboarding status",
            extra={"user_id": str(user_id)},
        )
        raise HTTPException(status_code=500, detail="Server error")


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
    current_user_id: UUID = Depends(get_current_user_id),
    user_repo: UserRepository = Depends(get_user_repo),
) -> InitiateOnboardingResponse:
    """Initiate an onboarding voice call."""
    try:
        if current_user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
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
        signature = hmac.new(
            secret.encode(),
            token_data.encode(),
            hashlib.sha256,
        ).hexdigest()
        signed_token = f"{token_data}:{signature}"

        # Get Meta-Nikita agent ID
        agent_id = DEFAULT_META_NIKITA_AGENT_ID

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
    except Exception:
        # FR-7: no PII in exception echo — use logger.exception with user_id only
        logger.exception(
            "Error initiating onboarding",
            extra={"user_id": str(user_id)},
        )
        raise HTTPException(status_code=500, detail="Server error")


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
    # SEC-001: Validate signed token (Closes #220)
    if not request.signed_token:
        raise HTTPException(status_code=401, detail="Missing signed token")
    try:
        validated_user_id, _ = validate_signed_token(request.signed_token)
    except ValueError as e:
        logger.warning(f"[ONBOARDING] Token validation failed: {e}")
        raise HTTPException(status_code=401, detail=str(e))

    # Override user_id with validated value from token
    request.user_id = validated_user_id

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
    elevenlabs_signature: str | None = Header(default=None, alias="elevenlabs-signature"),
    user_repo: UserRepository = Depends(get_user_repo),
) -> dict[str, Any]:
    """Handle ElevenLabs webhook for onboarding calls."""
    # Read raw body BEFORE parsing JSON (needed for signature verification)
    body = await request.body()
    body_str = body.decode("utf-8")

    # SEC-003: Hard reject on missing or invalid signature (Closes #225)
    if not elevenlabs_signature:
        logger.warning("[ONBOARDING WEBHOOK] Missing elevenlabs-signature header")
        raise HTTPException(status_code=401, detail="Missing signature header")

    settings = get_settings()
    if not settings.elevenlabs_webhook_secret:
        logger.error("[ONBOARDING WEBHOOK] ELEVENLABS_WEBHOOK_SECRET not configured")
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    secret = settings.elevenlabs_webhook_secret

    try:
        if not verify_elevenlabs_signature(body_str, elevenlabs_signature, secret):
            logger.warning("[ONBOARDING WEBHOOK] Invalid signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
    except ValueError as e:
        logger.warning(f"[ONBOARDING WEBHOOK] Signature validation failed: {e}")
        raise HTTPException(status_code=401, detail=str(e))

    # Parse payload after signature verified
    try:
        import json
        payload = json.loads(body_str)
    except Exception as e:
        logger.error(f"[ONBOARDING WEBHOOK] Invalid JSON payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Extract event data
    event_type = payload.get("type")
    data = payload.get("data", {})

    logger.info(f"Onboarding webhook: {event_type}")

    try:
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
    elevenlabs_signature: str | None = Header(default=None, alias="elevenlabs-signature"),
    user_repo: UserRepository = Depends(get_user_repo),
) -> dict[str, Any]:
    """Handle ElevenLabs pre-call webhook for onboarding calls.

    ElevenLabs calls this BEFORE starting a conversation to get dynamic variables.
    Returns user_id so server tools can store data to the correct user.
    """
    # SEC-003: Validate HMAC signature when secret is configured
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8")

    settings = get_settings()
    if settings.elevenlabs_webhook_secret:
        if not elevenlabs_signature:
            logger.warning("[ONBOARDING PRE-CALL] Missing elevenlabs-signature header")
            raise HTTPException(status_code=401, detail="Missing signature header")
        secret = settings.elevenlabs_webhook_secret
        try:
            if not verify_elevenlabs_signature(body_str, elevenlabs_signature, secret):
                logger.warning("[ONBOARDING PRE-CALL] Invalid signature")
                raise HTTPException(status_code=401, detail="Invalid signature")
        except ValueError as e:
            logger.warning(f"[ONBOARDING PRE-CALL] Signature validation failed: {e}")
            raise HTTPException(status_code=401, detail=str(e))

    try:
        import json
        body = json.loads(body_str)
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

    except HTTPException:
        raise
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
    current_user_id: UUID = Depends(get_current_user_id),
    user_repo: UserRepository = Depends(get_user_repo),
) -> dict:
    """Initiate an outbound onboarding call with Meta-Nikita persona override."""
    try:
        if current_user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

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
        if not user.phone:
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
            to_number=user.phone,
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
    current_user_id: UUID = Depends(get_current_user_id),
    user_repo: UserRepository = Depends(get_user_repo),
) -> OnboardingStatusResponse:
    """Skip onboarding for a user."""
    try:
        if current_user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
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


# === Portal Profile Endpoint (Spec 081) ===


class PortalProfileRequest(BaseModel):
    """Profile data submitted from portal onboarding (Spec 081 FR-003).

    Replaces Telegram-based profile collection with portal visual forms.
    """

    location_city: str = Field(
        ..., min_length=2, max_length=100, description="Player's city"
    )
    social_scene: Literal["techno", "art", "food", "cocktails", "nature"] = Field(
        ..., description="Social scene preference"
    )
    drug_tolerance: int = Field(
        ..., ge=1, le=5, description="Content intensity 1-5"
    )
    life_stage: Literal[
        "tech", "finance", "creative", "student", "entrepreneur", "other"
    ] | None = Field(default=None, description="Career phase (optional)")
    interest: str | None = Field(
        default=None, max_length=200, description="Primary interest (optional)"
    )
    phone: str | None = Field(
        default=None,
        min_length=8,
        max_length=20,
        description="Player's phone number in E.164 format (optional, Spec 212)",
    )

    @field_validator("location_city")
    @classmethod
    def location_not_blank(cls, v: str) -> str:
        """Validate city via the shared onboarding validator (GH #198).

        Pydantic v2 converts any ``ValueError`` raised here into a
        ``ValidationError`` (HTTP 422). ``validate_city`` also strips and
        normalizes internal whitespace.
        """
        from nikita.onboarding.validation import validate_city

        return validate_city(v)

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone_field(cls, v: str | None) -> str | None:
        """Validate and normalize phone via the shared validation module (Spec 212 PR B).

        Runs before Pydantic's own length checks (mode="before") so that
        raw user input with formatting characters (spaces, dashes) is stripped
        first. Returns None to signal "no phone" when input is blank or None —
        this short-circuits Pydantic's min_length check intentionally.

        Pydantic v2 converts any ``ValueError`` raised here into a
        ``ValidationError`` (HTTP 422).
        """
        from nikita.onboarding.validation import validate_phone

        if not v or not str(v).strip():
            return None
        return validate_phone(v)


class PortalProfileResponse(BaseModel):
    """Response from portal profile save."""

    status: str = "ok"
    message: str = "Profile saved, game starting..."


@router.post(
    "/profile",
    response_model=PortalProfileResponse,
    summary="Save profile from portal onboarding (Spec 081, GH #183)",
    description="""
    Accepts profile data from the portal cinematic onboarding experience.
    Creates user_profiles row, updates onboarding_status to 'completed',
    activates game state, seeds vice preferences, and triggers handoff
    (first Nikita message via Telegram) in background.
    """,
)
async def save_portal_profile(
    body: PortalProfileRequest,
    background_tasks: BackgroundTasks,
    user_id: UUID = Depends(get_current_user_id),
    profile_repo: ProfileRepository = Depends(get_profile_repo),
    user_repo: UserRepository = Depends(get_user_repo),
    vice_repo: VicePreferenceRepository = Depends(get_vice_repo),
) -> PortalProfileResponse:
    """Save player profile submitted from portal onboarding."""
    # Spec 212 PR B: Write phone BEFORE idempotency guard so that users who
    # have already completed onboarding can still correct/add their phone number
    # by resubmitting the profile form (phone-correction use case).
    # IntegrityError must be caught HERE — before any broad except — to return
    # a clean 409 instead of a 500, and to prevent _trigger_portal_handoff from
    # being enqueued when the phone is already registered.
    if body.phone:
        try:
            await user_repo.update_phone(user_id, body.phone)
        except IntegrityError:
            logger.warning(
                "Phone already registered for user_id=%s (duplicate key)", user_id
            )
            raise HTTPException(status_code=409, detail="Phone already registered")

    try:
        # REL-004: Idempotency guard -- check onboarding_status first
        user = await user_repo.get(user_id)
        if user and user.onboarding_status == "completed":
            logger.info(
                "Onboarding already completed for user_id=%s, skipping", user_id
            )
            return PortalProfileResponse(
                status="ok",
                message="Profile already exists",
            )

        # Check if profile already exists (idempotent)
        existing = await profile_repo.get_by_user_id(user_id)
        if existing:
            logger.info("Profile already exists for user_id=%s, skipping create", user_id)
            return PortalProfileResponse(
                status="ok",
                message="Profile already exists",
            )

        # Create profile
        await profile_repo.create_profile(
            user_id=user_id,
            location_city=body.location_city,
            social_scene=body.social_scene,
            drug_tolerance=body.drug_tolerance,
            life_stage=body.life_stage,
            primary_interest=body.interest,
        )

        # Persist profile to users.onboarding_profile JSONB so handoff can read it.
        # Portal path stores structured data in user_profiles table, but handoff
        # reads from this JSONB. Without this, portal users get empty JSONB and
        # the first message falls back to generic templates.
        # (GH onboarding-pipeline-bootstrap: fixes Bug 2 data gap)
        await user_repo.update_onboarding_profile(user_id, {
            "location_city": body.location_city,
            "social_scene": body.social_scene,
            "darkness_level": body.drug_tolerance,
            "life_stage": body.life_stage,
            "interest": body.interest,
        })

        # Update onboarding status to completed
        await user_repo.update_onboarding_status(user_id, "completed")

        # GH #183: Activate game state (game_status='active', score=50, days=0)
        await user_repo.activate_game(user_id)

        # GH #183: Seed vice preferences from drug_tolerance (maps to darkness_level)
        try:
            from nikita.engine.vice.seeder import seed_vices_from_profile
            await seed_vices_from_profile(
                user_id=user_id,
                profile={"darkness_level": body.drug_tolerance},
                vice_repo=vice_repo,
            )
        except Exception as vice_err:
            logger.warning(
                "Vice seeding failed for user_id=%s: %s", user_id, vice_err
            )

        # (get_async_session auto-commits on success)

        logger.info(
            "Portal profile saved for user_id=%s city=%s scene=%s",
            user_id, body.location_city.replace("\n", " "), body.social_scene
        )

        # GH #183: Trigger handoff in background (first Nikita message via Telegram)
        background_tasks.add_task(
            _trigger_portal_handoff,
            user_id=user_id,
            user_repo=user_repo,
            drug_tolerance=body.drug_tolerance,
        )

        return PortalProfileResponse()

    except Exception as e:
        logger.error("Error saving portal profile for user_id=%s: %s", user_id, e)
        raise HTTPException(status_code=500, detail="Failed to save profile")


async def _trigger_portal_handoff(
    user_id: UUID,
    user_repo: UserRepository,
    drug_tolerance: int,
) -> None:
    """Trigger handoff from portal onboarding to Nikita (GH #183).

    Runs as a background task after the profile save response is sent.
    Sends the first Nikita message via Telegram and bootstraps the pipeline.

    Args:
        user_id: User's UUID.
        user_repo: UserRepository for fetching user data.
        drug_tolerance: Maps to darkness_level for message personalization.
    """
    try:
        user = await user_repo.get(user_id)
        if not user:
            logger.error("User %s not found for portal handoff", user_id)
            return

        telegram_id = user.telegram_id
        if not telegram_id:
            # Spec 212 PR C: structured log for pending branch (no raw phone digits).
            logger.warning(
                "User %s has no telegram_id, deferring handoff (pending_handoff=True)",
                user_id,
                extra={
                    "event": "portal_handoff.branch",
                    "branch": "pending",
                    "user_id": str(user_id),
                    "phone_present": user.phone is not None,
                    "telegram_present": False,
                },
            )
            # PR-2 (GH #198-linked): persist deferred-handoff intent so the
            # MessageHandler fires HandoffManager on the user's first message.
            try:
                await user_repo.set_pending_handoff(user_id, True)
            except Exception as flag_err:
                logger.error(
                    "Failed to set pending_handoff for user %s: %s",
                    user_id,
                    flag_err,
                )
            return

        # Build full onboarding profile from JSONB for message personalization.
        # Previously only darkness_level was passed, stripping all other fields
        # (GH onboarding-pipeline-bootstrap: fixes Bug 2).
        from nikita.onboarding.models import build_profile_from_jsonb
        profile = build_profile_from_jsonb(
            user.onboarding_profile or {},
            fallback_darkness=drug_tolerance,
        )

        # Spec 213 PR 213-3: run portal facade to generate + cache backstory
        # scenarios BEFORE first message, using a FRESH session (not request-scoped).
        # Session safety: background task opens own session — never share with request.
        # Facade errors are non-blocking; handoff proceeds regardless of outcome.
        try:
            session_maker = get_session_maker()
            async with session_maker() as facade_session:
                facade = PortalOnboardingFacade()
                await facade.process(user_id, profile, facade_session)
        except Exception as facade_err:
            logger.warning(
                "Portal facade failed for user_id=%s (non-blocking): %s",
                user_id,
                type(facade_err).__name__,
            )

        # Spec 212 PR C (T022): phone-conditional handoff routing.
        # phone_present: bool only — never log raw phone digits.
        logger.info(
            "Portal handoff routing for user_id=%s branch=%s",
            user_id,
            "voice" if user.phone else "telegram",
            extra={
                "event": "portal_handoff.branch",
                "branch": "voice" if user.phone else "telegram",
                "user_id": str(user_id),
                "phone_present": user.phone is not None,
                "telegram_present": True,
            },
        )

        handoff = HandoffManager()
        if user.phone:
            # Voice callback path: Nikita calls the user back after onboarding.
            # execute_handoff_with_voice_callback already handles:
            #   - Success: voice call initiated
            #   - API returns failure: Telegram text fallback
            #   - Exception: Telegram text fallback (Spec 212 PR C T023)
            result = await handoff.execute_handoff_with_voice_callback(
                user_id=user_id,
                telegram_id=telegram_id,
                phone_number=user.phone,
                profile=profile,
                user_name="friend",
            )
        else:
            result = await handoff.execute_handoff(
                user_id=user_id,
                telegram_id=telegram_id,
                profile=profile,
                user_name="friend",
            )

        if result.success:
            logger.info("Portal handoff completed for user_id=%s", user_id)
        else:
            logger.error(
                "Portal handoff failed for user_id=%s: %s",
                user_id, result.error
            )

    except Exception:
        logger.exception(
            "Portal handoff error for user_id=%s",
            user_id,
            extra={"user_id": str(user_id)},
        )

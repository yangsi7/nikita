"""Telegram webhook API routes with FastAPI dependency injection.

Handles incoming Telegram updates via webhook:
- POST /webhook: Receives updates from Telegram
- POST /set-webhook: Configures webhook URL

AC Coverage: AC-FR001-001, AC-FR002-001, AC-T006.1-4

Sprint 3 Refactor: Full dependency injection via FastAPI Depends.
"""

from typing import Annotated

import hmac
import html

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, field_validator

import logging
from uuid import UUID

from nikita.config.settings import get_settings

from nikita.agents.text.handler import MessageHandler as TextAgentMessageHandler
from nikita.db.database import get_async_session, get_session_maker, get_supabase_client
from nikita.db.dependencies import (
    BackstoryRepoDep,
    ConversationRepoDep,
    OnboardingStateRepoDep,
    PendingRegistrationRepoDep,
    ProfileRepoDep,
    UserRepoDep,
    ViceRepoDep,
)
from nikita.db.models.profile import OnboardingStep
from nikita.db.repositories.pending_registration_repository import (
    PendingRegistrationRepository,
)
from nikita.db.repositories.user_repository import UserRepository
from nikita.db.repositories.conversation_repository import ConversationRepository
from nikita.db.repositories.profile_repository import (
    BackstoryRepository,
    ProfileRepository,
    VenueCacheRepository,
)

logger = logging.getLogger(__name__)
from nikita.platforms.telegram.auth import TelegramAuth
from nikita.platforms.telegram.bot import TelegramBot
from nikita.platforms.telegram.commands import CommandHandler
from nikita.platforms.telegram.delivery import ResponseDelivery
from nikita.platforms.telegram.message_handler import MessageHandler
from nikita.platforms.telegram.models import TelegramUpdate
from nikita.platforms.telegram.onboarding.handler import OnboardingHandler
from nikita.platforms.telegram.rate_limiter import RateLimiter, get_shared_cache
from nikita.platforms.telegram.registration_handler import RegistrationHandler
from nikita.platforms.telegram.otp_handler import OTPVerificationHandler
from nikita.services.venue_research import VenueResearchService
from nikita.services.backstory_generator import BackstoryGeneratorService
from nikita.services.persona_adaptation import PersonaAdaptationService


class WebhookResponse(BaseModel):
    """Response model for webhook endpoint."""

    status: str = "ok"


class SetWebhookRequest(BaseModel):
    """Request model for set-webhook endpoint."""

    url: str

    @field_validator("url")
    @classmethod
    def validate_https(cls, v: str) -> str:
        """Validate that URL uses HTTPS."""
        if not v.startswith("https://"):
            raise ValueError("Webhook URL must use HTTPS")
        return v


# =============================================================================
# Dependency Functions
# =============================================================================


def _get_bot_from_state(request: Request) -> TelegramBot:
    """Get TelegramBot from app.state.

    Args:
        request: FastAPI request with app reference.

    Returns:
        TelegramBot instance from app.state.

    Raises:
        HTTPException: If bot not configured.
    """
    bot = getattr(request.app.state, "telegram_bot", None)
    if bot is None:
        raise HTTPException(
            status_code=500,
            detail="Telegram bot not configured",
        )
    return bot


BotDep = Annotated[TelegramBot, Depends(_get_bot_from_state)]


async def get_telegram_auth(
    user_repo: UserRepoDep,
    pending_repo: PendingRegistrationRepoDep,
) -> TelegramAuth:
    """Get TelegramAuth with injected dependencies.

    Args:
        user_repo: Injected UserRepository.
        pending_repo: Injected PendingRegistrationRepository.

    Returns:
        Configured TelegramAuth instance.
    """
    supabase = await get_supabase_client()
    return TelegramAuth(
        supabase_client=supabase,
        user_repository=user_repo,
        pending_registration_repository=pending_repo,
    )


TelegramAuthDep = Annotated[TelegramAuth, Depends(get_telegram_auth)]


async def get_command_handler(
    user_repo: UserRepoDep,
    telegram_auth: TelegramAuthDep,
    bot: BotDep,
    profile_repo: ProfileRepoDep,
    onboarding_repo: OnboardingStateRepoDep,
) -> CommandHandler:
    """Get CommandHandler with injected dependencies.

    Issue #7 Fix: Added profile_repo and onboarding_repo for limbo state detection.
    When a user exists but has no profile (due to Bug #2), we detect this and
    create a fresh onboarding state to restart the flow.

    Args:
        user_repo: Injected UserRepository.
        telegram_auth: Injected TelegramAuth.
        bot: Injected TelegramBot from app.state.
        profile_repo: Injected ProfileRepository for limbo state detection.
        onboarding_repo: Injected OnboardingStateRepository for limbo state fix.

    Returns:
        Configured CommandHandler instance.
    """
    return CommandHandler(
        user_repository=user_repo,
        telegram_auth=telegram_auth,
        bot=bot,
        profile_repository=profile_repo,
        onboarding_repository=onboarding_repo,
    )


CommandHandlerDep = Annotated[CommandHandler, Depends(get_command_handler)]


async def get_message_handler(
    user_repo: UserRepoDep,
    conversation_repo: ConversationRepoDep,
    profile_repo: ProfileRepoDep,
    backstory_repo: BackstoryRepoDep,
    bot: BotDep,
) -> MessageHandler:
    """Get MessageHandler with injected dependencies.

    Phase 2: Added profile_repo and backstory_repo for profile gate check.
    The onboarding_handler is set to None here to avoid circular dependency.
    If user needs onboarding, MessageHandler sends a message and returns early.

    Args:
        user_repo: Injected UserRepository.
        conversation_repo: Injected ConversationRepository for tracking messages.
        profile_repo: Injected ProfileRepository for profile gate check.
        backstory_repo: Injected BackstoryRepository for profile gate check.
        bot: Injected TelegramBot from app.state.

    Returns:
        Configured MessageHandler instance.
    """
    rate_limiter = RateLimiter(cache=get_shared_cache())  # In-memory for MVP
    response_delivery = ResponseDelivery(bot=bot)

    # Create text agent handler (uses defaults for timer, skip, fact extractor)
    text_agent_handler = TextAgentMessageHandler()

    return MessageHandler(
        user_repository=user_repo,
        conversation_repository=conversation_repo,
        text_agent_handler=text_agent_handler,
        response_delivery=response_delivery,
        bot=bot,
        rate_limiter=rate_limiter,
        profile_repository=profile_repo,
        backstory_repository=backstory_repo,
        # Note: onboarding_handler is None to avoid circular dependency.
        # MessageHandler's profile gate just sends a redirect message.
    )


MessageHandlerDep = Annotated[MessageHandler, Depends(get_message_handler)]


async def get_registration_handler(
    telegram_auth: TelegramAuthDep,
    bot: BotDep,
) -> RegistrationHandler:
    """Get RegistrationHandler with injected dependencies.

    Args:
        telegram_auth: Injected TelegramAuth.
        bot: Injected TelegramBot from app.state.

    Returns:
        Configured RegistrationHandler instance.
    """
    return RegistrationHandler(
        telegram_auth=telegram_auth,
        bot=bot,
    )


RegistrationHandlerDep = Annotated[RegistrationHandler, Depends(get_registration_handler)]


async def get_venue_cache_repo(
    session=Depends(get_async_session),
) -> VenueCacheRepository:
    """Get VenueCacheRepository with session dependency.

    BUG-005 Fix: Correct dependency chain for VenueResearchService.
    """
    return VenueCacheRepository(session)


async def get_venue_research_service(
    venue_cache_repo: VenueCacheRepository = Depends(get_venue_cache_repo),
) -> VenueResearchService:
    """Get VenueResearchService with venue cache repository dependency.

    BUG-002 Fix: Inject VenueResearchService for Firecrawl venue search.
    BUG-005 Fix: Corrected to use VenueCacheRepository instead of session.

    Args:
        venue_cache_repo: Injected venue cache repository.

    Returns:
        Configured VenueResearchService instance.
    """
    return VenueResearchService(venue_cache_repo)


async def get_backstory_generator() -> BackstoryGeneratorService:
    """Get BackstoryGeneratorService (no dependencies).

    BUG-002 Fix: Inject BackstoryGeneratorService for AI-generated backstories.
    BUG-005 Fix: Removed incorrect session parameter (service has no __init__ args).

    Returns:
        BackstoryGeneratorService instance.
    """
    return BackstoryGeneratorService()


async def get_persona_adaptation() -> PersonaAdaptationService:
    """Get PersonaAdaptationService (no dependencies).

    BUG-002 Fix: Inject PersonaAdaptationService for Nikita persona customization.
    BUG-005 Fix: Removed incorrect session parameter (service has no __init__ args).

    Returns:
        PersonaAdaptationService instance.
    """
    return PersonaAdaptationService()


async def get_onboarding_handler(
    bot: BotDep,
    onboarding_repo: OnboardingStateRepoDep,
    profile_repo: ProfileRepoDep,
    user_repo: UserRepoDep,
    backstory_repo: BackstoryRepoDep,
    vice_repo: ViceRepoDep,
    venue_research: VenueResearchService = Depends(get_venue_research_service),
    backstory_gen: BackstoryGeneratorService = Depends(get_backstory_generator),
    persona_adapt: PersonaAdaptationService = Depends(get_persona_adaptation),
) -> OnboardingHandler:
    """Get OnboardingHandler with injected dependencies.

    Phase 4: Added user_repo, backstory_repo, vice_repo for profile persistence
    and vice initialization during onboarding.

    BUG-002 Fix: Added venue_research, backstory_gen, persona_adapt services
    to enable Firecrawl venue search (PRIMARY path, not fallback).

    Args:
        bot: Injected TelegramBot from app.state.
        onboarding_repo: Injected OnboardingStateRepository.
        profile_repo: Injected ProfileRepository.
        user_repo: Injected UserRepository (to lookup user_id from telegram_id).
        backstory_repo: Injected BackstoryRepository for backstory persistence.
        vice_repo: Injected VicePreferenceRepository for vice initialization.
        venue_research: Injected VenueResearchService for Firecrawl venue search.
        backstory_gen: Injected BackstoryGeneratorService for AI backstories.
        persona_adapt: Injected PersonaAdaptationService for Nikita customization.

    Returns:
        Configured OnboardingHandler instance.
    """
    return OnboardingHandler(
        bot=bot,
        onboarding_repository=onboarding_repo,
        profile_repository=profile_repo,
        user_repository=user_repo,
        backstory_repository=backstory_repo,
        vice_repository=vice_repo,
        venue_research_service=venue_research,
        backstory_generator=backstory_gen,
        persona_adaptation=persona_adapt,
    )


OnboardingHandlerDep = Annotated[OnboardingHandler, Depends(get_onboarding_handler)]


async def get_otp_handler(
    telegram_auth: TelegramAuthDep,
    bot: BotDep,
    pending_repo: PendingRegistrationRepoDep,
    onboarding_handler: OnboardingHandlerDep,
    profile_repo: ProfileRepoDep,
    user_repo: UserRepoDep,
) -> OTPVerificationHandler:
    """Get OTPVerificationHandler with injected dependencies.

    AC-T2.2: Includes onboarding handler and profile repository for new user routing.
    Dec 2025: Added pending_repo for OTP retry limit tracking.
    Spec 028: Added user_repo for onboarding_status check.

    Args:
        telegram_auth: Injected TelegramAuth.
        bot: Injected TelegramBot from app.state.
        pending_repo: Injected PendingRegistrationRepository for retry tracking.
        onboarding_handler: Injected OnboardingHandler for new user onboarding.
        profile_repo: Injected ProfileRepository for profile existence check.
        user_repo: Injected UserRepository for onboarding_status check (028).

    Returns:
        Configured OTPVerificationHandler instance.
    """
    return OTPVerificationHandler(
        telegram_auth=telegram_auth,
        bot=bot,
        pending_repo=pending_repo,
        onboarding_handler=onboarding_handler,
        profile_repository=profile_repo,
        user_repository=user_repo,
    )


OTPHandlerDep = Annotated[OTPVerificationHandler, Depends(get_otp_handler)]


# =============================================================================
# Router Factory
# =============================================================================


def create_telegram_router(bot: TelegramBot) -> APIRouter:
    """Create Telegram webhook router.

    Args:
        bot: TelegramBot instance (stored on app.state).

    Returns:
        Configured APIRouter with /webhook and /set-webhook endpoints.

    Note:
        CommandHandler and MessageHandler are injected per-request via
        FastAPI Depends, not passed as arguments here.
    """
    router = APIRouter()

    async def _handle_message_with_fresh_session(
        bot_instance: TelegramBot,
        message: "TelegramMessage",
    ) -> None:
        """Run MessageHandler.handle with a fresh DB session.

        Background tasks run AFTER the request session is closed, so we must
        create our own session to avoid DBAPI errors on stale connections.
        This wrapper:
        1. Creates a fresh AsyncSession via get_session_maker()
        2. Instantiates repos with the fresh session
        3. Runs MessageHandler.handle(message)
        4. Commits on success, rolls back on failure
        5. Sends error message to user if handle() crashes
        """
        from nikita.platforms.telegram.models import TelegramMessage as _TM

        session_maker = get_session_maker()
        async with session_maker() as session:
            try:
                user_repo = UserRepository(session)
                conversation_repo = ConversationRepository(session)
                profile_repo = ProfileRepository(session)
                backstory_repo = BackstoryRepository(session)

                rate_limiter = RateLimiter(cache=get_shared_cache())
                response_delivery = ResponseDelivery(bot=bot_instance)
                text_agent_handler = TextAgentMessageHandler()

                handler = MessageHandler(
                    user_repository=user_repo,
                    conversation_repository=conversation_repo,
                    text_agent_handler=text_agent_handler,
                    response_delivery=response_delivery,
                    bot=bot_instance,
                    rate_limiter=rate_limiter,
                    profile_repository=profile_repo,
                    backstory_repository=backstory_repo,
                )

                await handler.handle(message)
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(
                    f"[BG-TASK] MessageHandler crashed: {e}",
                    exc_info=True,
                )
                # Best-effort error notification to user
                try:
                    chat_id = message.chat.id if message.chat else None
                    if chat_id:
                        await bot_instance.send_message(
                            chat_id=chat_id,
                            text="Something went wrong processing your message. Please try again.",
                        )
                except Exception as notify_err:
                    logger.error(f"[BG-TASK] Failed to notify user of error: {notify_err}")

    @router.post("/webhook", response_model=WebhookResponse)
    async def receive_webhook(
        update: TelegramUpdate,
        background_tasks: BackgroundTasks,
        command_handler: CommandHandlerDep,
        message_handler: MessageHandlerDep,
        registration_handler: RegistrationHandlerDep,
        otp_handler: OTPHandlerDep,
        onboarding_handler: OnboardingHandlerDep,
        pending_repo: PendingRegistrationRepoDep,
        user_repo: UserRepoDep,
        bot_instance: BotDep,
        profile_repo: ProfileRepoDep,
        onboarding_repo: OnboardingStateRepoDep,
        x_telegram_bot_api_secret_token: Annotated[
            str | None, Header(alias="X-Telegram-Bot-Api-Secret-Token")
        ] = None,
    ) -> WebhookResponse:
        """Receive Telegram webhook update.

        AC-FR001-001: Receives updates from Telegram
        AC-T006.1-4: Routes commands vs messages appropriately
        AC-FR004-001: Routes email input to registration handler
        AC-T2.5: OTP state detection for code verification
        AC-T2.2-004: Ongoing onboarding state detection
        SEC-01: Validates webhook signature via X-Telegram-Bot-Api-Secret-Token

        Returns 200 immediately, processes asynchronously.

        Args:
            update: Telegram update object.
            background_tasks: FastAPI background task manager.
            command_handler: Injected CommandHandler.
            message_handler: Injected MessageHandler.
            registration_handler: Injected RegistrationHandler.
            otp_handler: Injected OTPVerificationHandler for code verification.
            onboarding_handler: Injected OnboardingHandler for profile collection.
            pending_repo: Injected PendingRegistrationRepository for OTP state.
            user_repo: Injected UserRepository for checking registration.
            bot_instance: Injected TelegramBot.
            x_telegram_bot_api_secret_token: Telegram's secret token header.

        Returns:
            WebhookResponse with status: ok.

        Raises:
            HTTPException: 403 if signature validation fails.
        """
        # SEC-01: Verify webhook signature (CRITICAL)
        settings = get_settings()
        expected_secret = settings.telegram_webhook_secret
        if expected_secret:
            if not x_telegram_bot_api_secret_token or not hmac.compare_digest(
                x_telegram_bot_api_secret_token, expected_secret
            ):
                raise HTTPException(status_code=403, detail="Invalid webhook signature")

        # Spec 028: Handle callback_query for onboarding choice buttons
        if update.callback_query is not None:
            callback = update.callback_query
            callback_id = callback.id
            telegram_id = callback.from_.id if callback.from_ else None
            chat_id = callback.message.chat.id if callback.message and callback.message.chat else None
            data = callback.data

            logger.info(
                f"[LLM-DEBUG] Callback query: callback_id={callback_id}, "
                f"telegram_id={telegram_id}, data={data}"
            )

            if telegram_id and chat_id and data:
                # Route onboarding callbacks to OTP handler
                if data.startswith("onboarding_"):
                    background_tasks.add_task(
                        otp_handler.handle_callback,
                        callback_id,
                        telegram_id,
                        chat_id,
                        data,
                    )

            return WebhookResponse()

        # AC-T006.3: Handle empty updates gracefully
        if update.message is None:
            # Ignore edited_message, etc. for MVP
            logger.info("[LLM-DEBUG] Webhook received: no message, ignoring")
            return WebhookResponse()

        message = update.message
        telegram_id = message.from_.id if message.from_ else None
        chat_id = message.chat.id if message.chat else None
        text = message.text

        logger.info(
            f"[LLM-DEBUG] Webhook received: telegram_id={telegram_id}, "
            f"chat_id={chat_id}, text_len={len(text) if text else 0}"
        )

        # Check if this is a command
        is_command = message.text is not None and message.text.startswith("/")

        if is_command:
            # AC-T006.1: Route commands to CommandHandler
            # Convert Pydantic model to dict for handler compatibility
            logger.info(f"[LLM-DEBUG] Routing to CommandHandler: {text}")
            background_tasks.add_task(
                command_handler.handle,
                message.model_dump(by_alias=True),
            )
        elif message.text is not None:
            telegram_id = message.from_.id
            chat_id = message.chat.id
            text = message.text.strip()

            # AC-T2.5: Check if user is awaiting OTP code
            pending = await pending_repo.get(telegram_id)
            logger.info(
                f"[LLM-DEBUG] Pending check: has_pending={pending is not None}, "
                f"otp_state={pending.otp_state if pending else 'N/A'}"
            )
            if pending and pending.otp_state == "code_sent":
                # User is in OTP verification state
                if OTPVerificationHandler.is_otp_code(text):
                    # AC-T2.5.2: OTP code (6-8 digits) - verify it
                    background_tasks.add_task(
                        otp_handler.handle,
                        telegram_id,
                        chat_id,
                        text,
                    )
                else:
                    # AC-T2.5.3: Not a code - remind user with helpful error
                    background_tasks.add_task(
                        bot_instance.send_message,
                        chat_id=chat_id,
                        text="That doesn't look like an OTP code. Enter the numeric code from your email! 📧",
                    )
                return WebhookResponse()

            # AC-FR004-001: Check if user needs to register
            user = await user_repo.get_by_telegram_id(telegram_id)
            logger.info(
                f"[LLM-DEBUG] User check: found={user is not None}, "
                f"user_id={user.id if user else 'None'}"
            )

            if user is None:
                # Unregistered user - check if this looks like email
                if registration_handler.is_valid_email(text):
                    # Email input during registration flow
                    logger.info(f"[LLM-DEBUG] Routing to RegistrationHandler (email input)")
                    background_tasks.add_task(
                        registration_handler.handle_email_input,
                        telegram_id,
                        chat_id,
                        text,
                    )
                else:
                    # Not an email, prompt to register
                    logger.info(f"[LLM-DEBUG] Unregistered user, sending prompt to register")
                    background_tasks.add_task(
                        bot_instance.send_message,
                        chat_id=chat_id,
                        text="You need to register first. Send /start to begin.",
                    )
            else:
                # FIX: Check if user already completed onboarding (voice or text)
                # Voice onboarding sets user.onboarding_status = "completed" but doesn't
                # create user_profiles entry. Must check status BEFORE LIMBO-FIX.
                user_onboarding_status = getattr(user, "onboarding_status", None)
                if user_onboarding_status in ("completed", "skipped"):
                    # User completed onboarding (voice or text) - route to MessageHandler
                    logger.info(
                        f"[ROUTING] User {user.id} has onboarding_status={user_onboarding_status}, "
                        f"routing directly to MessageHandler"
                    )
                    background_tasks.add_task(
                        _handle_message_with_fresh_session,
                        bot_instance,
                        message,
                    )
                else:
                    # AC-T2.2-004: Check for ongoing onboarding state
                    onboarding_state = await onboarding_handler.has_incomplete_onboarding(
                        telegram_id
                    )

                    # Issue #9 Fix: Synchronous limbo state detection and fix
                    # If no onboarding state OR complete state with no profile, reset to LOCATION
                    # This MUST happen synchronously, not in background task
                    profile = await profile_repo.get(user.id)
                    if profile is None:
                        # LIMBO STATE: User exists but no profile
                        # Need to start/restart onboarding
                        if onboarding_state is None:
                            logger.warning(
                                f"[LIMBO-FIX-SYNC] User {user.id} has no profile and no onboarding state - "
                                f"creating fresh state SYNCHRONOUSLY"
                            )
                            onboarding_state = await onboarding_repo.get_or_create(telegram_id)
                        elif onboarding_state.is_complete():
                            # State marked complete but profile missing - reset to LOCATION
                            logger.warning(
                                f"[LIMBO-FIX-SYNC] User {user.id} has complete onboarding but no profile - "
                                f"resetting to LOCATION step"
                            )
                            onboarding_state = await onboarding_repo.update_step(
                                telegram_id=telegram_id,
                                step=OnboardingStep.LOCATION,
                                collected_answers={},  # Clear old answers
                            )
                        # Explicit commit to ensure visibility for routing
                        await onboarding_repo.session.commit()
                        logger.info(
                            f"[LIMBO-FIX-SYNC] Onboarding state ready: "
                            f"telegram_id={telegram_id}, step={onboarding_state.current_step}"
                        )

                    if onboarding_state is not None:
                        # User is in onboarding flow - route to OnboardingHandler
                        logger.info(
                            f"[LLM-DEBUG] Routing to OnboardingHandler: "
                            f"telegram_id={telegram_id}, step={onboarding_state.current_step}"
                        )
                        background_tasks.add_task(
                            onboarding_handler.handle,
                            telegram_id,
                            chat_id,
                            text,
                        )
                    else:
                        # AC-T006.2: Registered user - route to MessageHandler
                        logger.info(
                            f"[LLM-DEBUG] ROUTING TO MESSAGE HANDLER for user_id={user.id} "
                            f"- THIS SHOULD TRIGGER LLM"
                        )
                        background_tasks.add_task(
                            _handle_message_with_fresh_session,
                            bot_instance,
                            message,
                        )
        # Ignore non-text messages (photos, voice, etc.) for MVP

        # AC-T006.4: Return 200 immediately
        return WebhookResponse()

    @router.get("/auth/confirm", response_class=HTMLResponse)
    async def auth_confirm(
        code: str | None = None,
        access_token: str | None = None,
        error: str | None = None,
        error_code: str | None = None,
        error_description: str | None = None,
    ) -> str:
        """DEPRECATED: Complete Telegram registration via magic link verification.

        This endpoint is deprecated in favor of OTP code entry in Telegram chat.
        Kept for backward compatibility with existing magic links in users' emails.
        New registrations should use OTP flow via send_otp_code/verify_otp_code.

        AC-015-002: Exchange PKCE code with Supabase, or verify implicit flow token.

        Flow:
        1. Receive code from Supabase PKCE redirect
        2. Exchange code for session with Supabase
        3. Extract email from Supabase response
        4. Look up pending registration by email → get telegram_id
        5. Create user with telegram_id
        6. Delete pending registration
        7. Show success/error HTML page

        Args:
            code: PKCE authorization code from Supabase redirect
            error: Error type from Supabase (e.g., "access_denied")
            error_code: Specific error code (e.g., "otp_expired")
            error_description: Human-readable error message

        Returns:
            HTML page with confirmation or error message.
        """
        # DEPRECATED: Log usage of deprecated endpoint
        logger.warning(
            "DEPRECATED: auth_confirm endpoint called. "
            "This flow is deprecated in favor of OTP code entry in Telegram chat."
        )

        def render_error_page(error_msg: str, error_reason: str = "") -> str:
            """Render HTML error page with Nikita dark theme."""
            # SEC-4: Escape user-provided content to prevent XSS
            error_msg = html.escape(error_msg)
            error_reason = html.escape(error_reason) if error_reason else ""
            return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Authentication Error - Nikita</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --background: #0a0a0a;
            --card: #141414;
            --foreground: #fafafa;
            --muted: #a1a1a1;
            --destructive: #ef4444;
            --primary: #dc2626;
            --border: rgba(255,255,255,0.08);
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--background);
            color: var(--foreground);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1rem;
        }}
        .card {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 2.5rem;
            max-width: 420px;
            text-align: center;
        }}
        .icon {{ font-size: 4rem; margin-bottom: 1.5rem; }}
        h1 {{
            color: var(--destructive);
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }}
        .subtitle {{
            color: var(--muted);
            font-size: 0.9rem;
            line-height: 1.5;
            margin-bottom: 1.5rem;
        }}
        .error-box {{
            background: rgba(239,68,68,0.1);
            border-left: 3px solid var(--destructive);
            padding: 1rem;
            text-align: left;
            border-radius: 0 8px 8px 0;
            margin-bottom: 1.5rem;
        }}
        .error-box strong {{
            color: var(--destructive);
            display: block;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.25rem;
        }}
        .error-box span {{ color: var(--muted); font-size: 0.875rem; }}
        .steps {{
            text-align: left;
            color: var(--muted);
            font-size: 0.875rem;
            margin-bottom: 1.5rem;
            padding-left: 1.25rem;
        }}
        .steps li {{ margin-bottom: 0.5rem; }}
        .steps code {{
            background: var(--border);
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 0.8rem;
        }}
        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: var(--primary);
            color: white;
            padding: 0.875rem 1.75rem;
            border-radius: 10px;
            text-decoration: none;
            font-weight: 600;
            font-size: 0.9rem;
            transition: opacity 0.2s, transform 0.1s;
        }}
        .btn:hover {{ opacity: 0.9; }}
        .btn:active {{ transform: scale(0.98); }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">⚠️</div>
        <h1>Authentication Failed</h1>
        <p class="subtitle">{error_msg}</p>
        {f'<div class="error-box"><strong>Reason</strong><span>{error_reason}</span></div>' if error_reason else ''}
        <ol class="steps">
            <li>Return to Telegram</li>
            <li>Send <code>/start</code> for a new magic link</li>
            <li>Click the link promptly</li>
        </ol>
        <a href="https://t.me/Nikita_my_bot" class="btn">💬 Open Telegram</a>
    </div>
    <script>
        // Handle Supabase implicit flow - tokens or errors in URL fragment
        const hash = window.location.hash.substring(1);
        if (hash) {{
            const params = new URLSearchParams(hash);
            // Check for access_token (success - implicit flow)
            if (params.get('access_token') && !window.location.search.includes('access_token=')) {{
                const newUrl = window.location.pathname +
                    '?access_token=' + encodeURIComponent(params.get('access_token'));
                window.location.replace(newUrl);
            }}
            // Check for error
            else if (params.get('error') && !window.location.search.includes('error=')) {{
                const err = params.get('error');
                const errCode = params.get('error_code');
                const errDesc = params.get('error_description');
                const newUrl = window.location.pathname +
                    '?error=' + encodeURIComponent(err) +
                    (errCode ? '&error_code=' + encodeURIComponent(errCode) : '') +
                    (errDesc ? '&error_description=' + encodeURIComponent(errDesc) : '');
                window.location.replace(newUrl);
            }}
        }}
    </script>
</body>
</html>"""

        def render_success_page() -> str:
            """Render HTML success page with Nikita dark theme."""
            return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Registration Complete - Nikita</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --background: #0a0a0a;
            --card: #141414;
            --foreground: #fafafa;
            --muted: #a1a1a1;
            --success: #22c55e;
            --primary: #dc2626;
            --border: rgba(255,255,255,0.08);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--background);
            color: var(--foreground);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1rem;
        }
        .card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 2.5rem;
            max-width: 420px;
            text-align: center;
        }
        .icon { font-size: 4rem; margin-bottom: 1.5rem; }
        h1 {
            color: var(--foreground);
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        .subtitle {
            color: var(--muted);
            font-size: 0.9rem;
            line-height: 1.6;
            margin-bottom: 1.5rem;
        }
        .success-box {
            background: rgba(34,197,94,0.1);
            border: 1px solid rgba(34,197,94,0.2);
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1.5rem;
        }
        .success-box p {
            color: var(--success);
            font-size: 0.875rem;
            font-weight: 500;
        }
        .btn {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: var(--primary);
            color: white;
            padding: 0.875rem 1.75rem;
            border-radius: 10px;
            text-decoration: none;
            font-weight: 600;
            font-size: 0.9rem;
            transition: opacity 0.2s, transform 0.1s;
        }
        .btn:hover { opacity: 0.9; }
        .btn:active { transform: scale(0.98); }
    </style>
    <script>
        // Check for errors in URL fragment (Supabase sends errors this way)
        const hash = window.location.hash.substring(1);
        if (hash && hash.includes('error=')) {
            const params = new URLSearchParams(hash);
            const error = params.get('error');
            const errorCode = params.get('error_code');
            const errorDesc = params.get('error_description');
            const newUrl = window.location.pathname +
                '?error=' + encodeURIComponent(error) +
                (errorCode ? '&error_code=' + encodeURIComponent(errorCode) : '') +
                (errorDesc ? '&error_description=' + encodeURIComponent(errorDesc) : '');
            window.location.replace(newUrl);
        }
    </script>
</head>
<body>
    <div class="card">
        <div class="icon">💝</div>
        <h1>You're In!</h1>
        <div class="success-box">
            <p>Account linked successfully</p>
        </div>
        <p class="subtitle">Return to Telegram and start chatting with Nikita. She's been waiting for you...</p>
        <a href="https://t.me/Nikita_my_bot" class="btn">💬 Open Telegram</a>
    </div>
</body>
</html>"""

        # Handle Supabase errors from query params
        if error or error_code:
            error_msg = error_description or error or "Unknown error"
            error_reason = ""
            if error_code == "otp_expired":
                error_reason = "Magic link has expired. Request a new one."
            elif error_code == "otp_disabled":
                error_reason = "This magic link has already been used."
            elif error == "access_denied":
                error_reason = "Authentication link is invalid or expired."
            return render_error_page(error_msg, error_reason)

        # Must have either access_token (implicit flow) or code (PKCE flow)
        if not access_token and not code:
            return render_error_page(
                "No authorization code provided",
                "The magic link URL is missing required parameters"
            )

        # AC-015-002: Extract user info from token or exchange code
        try:
            email: str | None = None
            supabase_user_id: UUID | None = None

            if access_token:
                # SEC-3: Verify JWT signature using Supabase JWT secret
                import jwt as pyjwt

                try:
                    settings = get_settings()
                    jwt_secret = settings.supabase_jwt_secret

                    if not jwt_secret:
                        logger.error("SUPABASE_JWT_SECRET not configured - cannot verify JWT")
                        return render_error_page(
                            "Server configuration error",
                            "JWT verification is not configured. Please contact support."
                        )

                    # Decode AND verify signature with Supabase JWT secret
                    payload = pyjwt.decode(
                        access_token,
                        jwt_secret,
                        algorithms=["HS256"],
                        audience="authenticated",
                    )

                    email = payload.get('email')
                    user_id_str = payload.get('sub')

                    if not email or not user_id_str:
                        raise ValueError("JWT missing email or sub claim")

                    supabase_user_id = UUID(user_id_str)
                    logger.info(f"Implicit flow: verified JWT for email: {email}")

                except pyjwt.ExpiredSignatureError:
                    logger.warning("JWT has expired")
                    return render_error_page(
                        "Authentication expired",
                        "Your magic link has expired. Please request a new one."
                    )
                except pyjwt.InvalidSignatureError:
                    logger.warning("JWT signature verification failed")
                    return render_error_page(
                        "Invalid authentication token",
                        "The token signature could not be verified."
                    )
                except pyjwt.InvalidTokenError as jwt_err:
                    logger.error(f"Invalid JWT: {jwt_err}")
                    return render_error_page(
                        "Invalid authentication token",
                        "The access token is invalid. Please try again."
                    )
                except Exception as jwt_err:
                    logger.error(f"Failed to verify access_token JWT: {jwt_err}")
                    return render_error_page(
                        "Invalid authentication token",
                        "The access token could not be verified. Please try again."
                    )

            elif code:
                # PKCE flow: exchange code for session
                supabase = await get_supabase_client()
                logger.info(f"Exchanging auth code for session")
                response = await supabase.auth.exchange_code_for_session(
                    {"auth_code": code}
                )

                if not response.user:
                    logger.error("Supabase returned no user after code exchange")
                    return render_error_page(
                        "Authentication failed",
                        "Unable to verify your identity. Please try again."
                    )

                email = response.user.email
                supabase_user_id = UUID(response.user.id)
                logger.info(f"Auth code exchanged successfully for email: {email}")

            # Get database session and repositories
            session_maker = get_session_maker()
            async with session_maker() as session:
                pending_repo = PendingRegistrationRepository(session)
                user_repo = UserRepository(session)

                # Look up pending registration by email to get telegram_id
                # Use get_by_email_any since Supabase has already verified the email
                # (our 10-min expiration shouldn't block if Supabase accepted the link)
                pending = await pending_repo.get_by_email_any(email)

                if pending is None:
                    # No pending registration - check if user already exists (double-click)
                    existing = await user_repo.get(supabase_user_id)
                    if existing:
                        logger.info(f"User {supabase_user_id} already exists (double-click)")
                        return render_success_page()

                    # Also check by email in case user registered via portal
                    logger.warning(f"No pending registration for email: {email}")
                    return render_error_page(
                        "No pending registration found",
                        "Please return to Telegram and send /start to begin registration."
                    )

                telegram_id = pending.telegram_id
                logger.info(f"Found pending registration: telegram_id={telegram_id}")

                # Check if user already exists by supabase_user_id (portal registration)
                existing_user = await user_repo.get(supabase_user_id)
                if existing_user:
                    # User exists - link telegram_id if not already set
                    if existing_user.telegram_id is None:
                        logger.info(f"Linking telegram_id {telegram_id} to existing user {supabase_user_id}")
                        existing_user.telegram_id = telegram_id
                        await user_repo.update(existing_user)
                    else:
                        logger.info(f"User {supabase_user_id} already has telegram_id={existing_user.telegram_id}")
                    await pending_repo.delete(telegram_id)
                    await session.commit()
                    return render_success_page()

                # Check if user already exists by telegram_id (race condition protection)
                existing_by_telegram = await user_repo.get_by_telegram_id(telegram_id)
                if existing_by_telegram:
                    logger.info(f"User already exists for telegram_id={telegram_id}")
                    await pending_repo.delete(telegram_id)
                    await session.commit()
                    return render_success_page()

                # Create new user with telegram_id
                logger.info(f"Creating user: supabase_id={supabase_user_id}, telegram_id={telegram_id}")
                await user_repo.create_with_metrics(
                    user_id=supabase_user_id,
                    telegram_id=telegram_id,
                )

                # Clean up pending registration
                await pending_repo.delete(telegram_id)

                # Commit transaction
                await session.commit()
                logger.info(f"User created successfully: {supabase_user_id}")

            return render_success_page()

        except Exception as e:
            logger.error(f"Auth confirm failed: {e}", exc_info=True)
            return render_error_page(
                "Verification failed",
                f"An error occurred during registration. Please try again. ({type(e).__name__})"
            )

    @router.post("/set-webhook", response_model=WebhookResponse)
    async def set_webhook(
        request: SetWebhookRequest,
        bot_instance: BotDep,
    ) -> WebhookResponse:
        """Configure Telegram webhook URL.

        SEC-01: Automatically includes secret_token from settings.

        Args:
            request: Request with HTTPS webhook URL.
            bot_instance: Injected TelegramBot.

        Returns:
            WebhookResponse with status: ok.

        Raises:
            HTTPException: If API call fails.
        """
        try:
            settings = get_settings()
            await bot_instance.set_webhook(
                url=request.url,
                secret_token=settings.telegram_webhook_secret,
            )
            return WebhookResponse()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to set webhook: {str(e)}",
            )

    return router

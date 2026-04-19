"""Telegram webhook API routes with FastAPI dependency injection.

Handles incoming Telegram updates via webhook:
- POST /webhook: Receives updates from Telegram
- POST /set-webhook: Configures webhook URL

AC Coverage: AC-FR001-001, AC-FR002-001, AC-T006.1-4

Sprint 3 Refactor: Full dependency injection via FastAPI Depends.
"""

import hmac
import logging
import time
import threading
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.config.settings import get_settings

from nikita.agents.text.handler import MessageHandler as TextAgentMessageHandler
from nikita.db.database import get_async_session, get_session_maker, get_supabase_client
from nikita.db.dependencies import (
    ConversationRepoDep,
    MetricsRepoDep,
    OnboardingStateRepoDep,
    PendingRegistrationRepoDep,
    ProfileRepoDep,
    TelegramLinkRepoDep,
    UserRepoDep,
)
from nikita.db.repositories.pending_registration_repository import (
    PendingRegistrationRepository,
)
from nikita.db.repositories.user_repository import UserRepository
from nikita.db.repositories.conversation_repository import ConversationRepository
from nikita.db.repositories.metrics_repository import UserMetricsRepository
from nikita.db.repositories.profile_repository import (
    BackstoryRepository,
    ProfileRepository,
)

logger = logging.getLogger(__name__)

# --- Telegram update_id deduplication cache ---
# TTL=600s (10 min) — Telegram retries for ~60s, generous buffer.
# In-process LRU dict: O(1) lookup, no DB round-trip.
# BKD-007: Per-process limitation — Cloud Run can spin up multiple instances.
# Duplicate updates are possible across instances (Telegram retries during cold start).
# Acceptable tradeoff: dedup is best-effort; pipeline is idempotent for re-processed convs.
_UPDATE_ID_CACHE: dict[int, float] = {}
_CACHE_LOCK = threading.Lock()
_CACHE_TTL = 600  # seconds
_CACHE_MAX_SIZE = 10_000


def _is_duplicate_update(update_id: int) -> bool:
    """Check if this update_id was already processed. Thread-safe with TTL."""
    now = time.monotonic()
    with _CACHE_LOCK:
        # Lazy cleanup: remove expired entries when cache is large
        if len(_UPDATE_ID_CACHE) > _CACHE_MAX_SIZE:
            expired = [k for k, t in _UPDATE_ID_CACHE.items() if now - t > _CACHE_TTL]
            for k in expired:
                del _UPDATE_ID_CACHE[k]

        # Check if already seen
        if update_id in _UPDATE_ID_CACHE:
            stored_time = _UPDATE_ID_CACHE[update_id]
            if now - stored_time < _CACHE_TTL:
                return True  # Duplicate
            # Expired — treat as new

        # Mark as seen
        _UPDATE_ID_CACHE[update_id] = now
        return False


from nikita.platforms.telegram.auth import TelegramAuth
from nikita.platforms.telegram.bot import TelegramBot
from nikita.platforms.telegram.commands import CommandHandler
from nikita.platforms.telegram.delivery import ResponseDelivery
from nikita.platforms.telegram.message_handler import MessageHandler
from nikita.platforms.telegram.models import TelegramUpdate
from nikita.platforms.telegram.rate_limiter import DatabaseRateLimiter
from nikita.platforms.telegram.registration_handler import RegistrationHandler
from nikita.platforms.telegram.otp_handler import OTPVerificationHandler

# Spec 214 FR-11c T1.6: legacy `OnboardingHandler` (8-step Telegram Q&A)
# was deleted. Portal wizard owns onboarding. Venue/backstory/persona
# services are no longer wired into the Telegram router — they're called
# by the portal backend in `nikita/services/portal_onboarding.py`.


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
    telegram_link_repo: TelegramLinkRepoDep,
) -> CommandHandler:
    """Get CommandHandler with injected dependencies.

    Issue #7 Fix: Added profile_repo and onboarding_repo for limbo state detection.
    When a user exists but has no profile (due to Bug #2), we detect this and
    create a fresh onboarding state to restart the flow.

    GH #321: Added telegram_link_repo so `/start <payload>` from portal
    deep-links can consume the code and atomically bind users.telegram_id.

    Args:
        user_repo: Injected UserRepository.
        telegram_auth: Injected TelegramAuth.
        bot: Injected TelegramBot from app.state.
        profile_repo: Injected ProfileRepository for limbo state detection.
        onboarding_repo: Injected OnboardingStateRepository for limbo state fix.
        telegram_link_repo: Injected TelegramLinkRepository for deep-link
            code verification (GH #321).

    Returns:
        Configured CommandHandler instance.
    """
    return CommandHandler(
        user_repository=user_repo,
        telegram_auth=telegram_auth,
        bot=bot,
        profile_repository=profile_repo,
        onboarding_repository=onboarding_repo,
        telegram_link_repository=telegram_link_repo,
    )


CommandHandlerDep = Annotated[CommandHandler, Depends(get_command_handler)]


async def build_message_handler(
    session: AsyncSession,
    bot: TelegramBot,
) -> MessageHandler:
    """Build MessageHandler with all dependencies.

    Single source of truth for MessageHandler construction.
    Used by both FastAPI DI (get_message_handler) and background tasks.

    The onboarding_handler is intentionally omitted to avoid a circular
    dependency. MessageHandler's profile gate sends a redirect message instead.

    Args:
        session: Database session.
        bot: Telegram bot client.

    Returns:
        Fully initialized MessageHandler.
    """
    user_repo = UserRepository(session)
    conversation_repo = ConversationRepository(session)
    profile_repo = ProfileRepository(session)
    backstory_repo = BackstoryRepository(session)
    metrics_repo = UserMetricsRepository(session)

    rate_limiter = DatabaseRateLimiter(session=session)
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
        metrics_repository=metrics_repo,
        # Note: onboarding_handler is None to avoid circular dependency.
        # MessageHandler's profile gate just sends a redirect message.
    )


async def get_message_handler(
    bot: BotDep,
    session: AsyncSession = Depends(get_async_session),
) -> MessageHandler:
    """Get MessageHandler with injected dependencies.

    Delegates to build_message_handler — single source of truth for
    MessageHandler construction. Called by FastAPI DI for the webhook endpoint.

    Args:
        bot: Injected TelegramBot from app.state.
        session: Raw AsyncSession for repository construction.

    Returns:
        Configured MessageHandler instance.
    """
    return await build_message_handler(session=session, bot=bot)


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


async def get_otp_handler(
    telegram_auth: TelegramAuthDep,
    bot: BotDep,
    pending_repo: PendingRegistrationRepoDep,
    profile_repo: ProfileRepoDep,
    user_repo: UserRepoDep,
) -> OTPVerificationHandler:
    """Get OTPVerificationHandler with injected dependencies.

    Spec 214 FR-11c T1.6: removed `onboarding_handler` dep. The legacy
    8-step Q&A handler is deleted; OTP success now defers new-user
    onboarding to the portal wizard via the redirect path in
    `message_handler` and `commands._handle_start`.

    Args:
        telegram_auth: Injected TelegramAuth.
        bot: Injected TelegramBot from app.state.
        pending_repo: Injected PendingRegistrationRepository for retry tracking.
        profile_repo: Injected ProfileRepository for profile existence check.
        user_repo: Injected UserRepository for onboarding_status check (028).

    Returns:
        Configured OTPVerificationHandler instance.
    """
    return OTPVerificationHandler(
        telegram_auth=telegram_auth,
        bot=bot,
        pending_repo=pending_repo,
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
        session_maker = get_session_maker()
        async with session_maker() as session:
            try:
                handler = await build_message_handler(session=session, bot=bot_instance)

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
        pending_repo: PendingRegistrationRepoDep,
        user_repo: UserRepoDep,
        bot_instance: BotDep,
        profile_repo: ProfileRepoDep,
        rate_limit_session: AsyncSession = Depends(get_async_session),
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

        # DEDUP: Reject duplicate Telegram updates (retries during slow processing)
        if _is_duplicate_update(update.update_id):
            logger.info(f"[DEDUP] Ignoring duplicate update_id={update.update_id}")
            return WebhookResponse()

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
                # Spec 081: onboarding_text callback removed (single-button pattern)
                # No callback routing needed — all onboarding buttons are URL-based
                logger.debug(
                    f"Unhandled callback data={data}, telegram_id={telegram_id}"
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

        # Spec 115 FR-001/FR-003: Per-user rate limit — commands are exempt.
        # Checked here (after dedup, before pipeline dispatch) to prevent a
        # single user from exhausting MAX_CONCURRENT_PIPELINES=10.
        # GH #134: DatabaseRateLimiter persists across Cloud Run instances.
        if telegram_id and not is_command:
            webhook_rate_limiter = DatabaseRateLimiter(session=rate_limit_session)
            rate_result = await webhook_rate_limiter.check_by_telegram_id(telegram_id=telegram_id)
            if not rate_result.allowed:
                logger.warning(
                    "[RATE_LIMIT] telegram_id=%d reason=%s retry_after=%d",
                    telegram_id,
                    rate_result.reason,
                    rate_result.retry_after_seconds or 60,
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limit_exceeded",
                        "retry_after": rate_result.retry_after_seconds or 60,
                    },
                )

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
                # Spec 214 FR-11c T1.6: known user → MessageHandler.
                # MessageHandler's pre-onboard gate (T1.5) inspects
                # user_profiles and sends a portal redirect if the
                # wizard is incomplete; the legacy 8-step Telegram Q&A
                # flow was deleted together with OnboardingHandler.
                logger.info(
                    f"[LLM-DEBUG] Routing to MessageHandler for user_id={user.id} "
                    f"(FR-11c: portal owns onboarding)"
                )
                background_tasks.add_task(
                    _handle_message_with_fresh_session,
                    bot_instance,
                    message,
                )
        # Ignore non-text messages (photos, voice, etc.) for MVP

        # AC-T006.4: Return 200 immediately
        return WebhookResponse()

    @router.get("/auth/confirm")
    async def auth_confirm(
        code: str | None = None,
        access_token: str | None = None,
        error: str | None = None,
        error_code: str | None = None,
        error_description: str | None = None,
    ) -> JSONResponse:
        """DEPRECATED: This endpoint has been removed.

        Returns 410 Gone. Voice onboarding via OTP replaced magic link flow.
        """
        return JSONResponse(
            status_code=410,
            content={
                "status": "gone",
                "message": "This authentication method has been deprecated. Please use OTP code entry in Telegram chat.",
            },
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

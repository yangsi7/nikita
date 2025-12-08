"""Telegram webhook API routes with FastAPI dependency injection.

Handles incoming Telegram updates via webhook:
- POST /webhook: Receives updates from Telegram
- POST /set-webhook: Configures webhook URL

AC Coverage: AC-FR001-001, AC-FR002-001, AC-T006.1-4

Sprint 3 Refactor: Full dependency injection via FastAPI Depends.
"""

from typing import Annotated

import hmac

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, field_validator

from nikita.config.settings import get_settings

from nikita.agents.text.handler import MessageHandler as TextAgentMessageHandler
from nikita.db.database import get_supabase_client
from nikita.db.dependencies import PendingRegistrationRepoDep, UserRepoDep
from nikita.platforms.telegram.auth import TelegramAuth
from nikita.platforms.telegram.bot import TelegramBot
from nikita.platforms.telegram.commands import CommandHandler
from nikita.platforms.telegram.delivery import ResponseDelivery
from nikita.platforms.telegram.message_handler import MessageHandler
from nikita.platforms.telegram.models import TelegramUpdate
from nikita.platforms.telegram.rate_limiter import RateLimiter, get_shared_cache
from nikita.platforms.telegram.registration_handler import RegistrationHandler


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
) -> CommandHandler:
    """Get CommandHandler with injected dependencies.

    Args:
        user_repo: Injected UserRepository.
        telegram_auth: Injected TelegramAuth.
        bot: Injected TelegramBot from app.state.

    Returns:
        Configured CommandHandler instance.
    """
    return CommandHandler(
        user_repository=user_repo,
        telegram_auth=telegram_auth,
        bot=bot,
    )


CommandHandlerDep = Annotated[CommandHandler, Depends(get_command_handler)]


async def get_message_handler(
    user_repo: UserRepoDep,
    bot: BotDep,
) -> MessageHandler:
    """Get MessageHandler with injected dependencies.

    Args:
        user_repo: Injected UserRepository.
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
        text_agent_handler=text_agent_handler,
        response_delivery=response_delivery,
        bot=bot,
        rate_limiter=rate_limiter,
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

    @router.post("/webhook", response_model=WebhookResponse)
    async def receive_webhook(
        update: TelegramUpdate,
        background_tasks: BackgroundTasks,
        command_handler: CommandHandlerDep,
        message_handler: MessageHandlerDep,
        registration_handler: RegistrationHandlerDep,
        user_repo: UserRepoDep,
        bot_instance: BotDep,
        x_telegram_bot_api_secret_token: Annotated[
            str | None, Header(alias="X-Telegram-Bot-Api-Secret-Token")
        ] = None,
    ) -> WebhookResponse:
        """Receive Telegram webhook update.

        AC-FR001-001: Receives updates from Telegram
        AC-T006.1-4: Routes commands vs messages appropriately
        AC-FR004-001: Routes email input to registration handler
        SEC-01: Validates webhook signature via X-Telegram-Bot-Api-Secret-Token

        Returns 200 immediately, processes asynchronously.

        Args:
            update: Telegram update object.
            background_tasks: FastAPI background task manager.
            command_handler: Injected CommandHandler.
            message_handler: Injected MessageHandler.
            registration_handler: Injected RegistrationHandler.
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

        # AC-T006.3: Handle empty updates gracefully
        if update.message is None:
            # Ignore edited_message, callback_query, etc. for MVP
            return WebhookResponse()

        message = update.message

        # Check if this is a command
        is_command = message.text is not None and message.text.startswith("/")

        if is_command:
            # AC-T006.1: Route commands to CommandHandler
            # Convert Pydantic model to dict for handler compatibility
            background_tasks.add_task(
                command_handler.handle,
                message.model_dump(by_alias=True),
            )
        elif message.text is not None:
            # AC-FR004-001: Check if user needs to register
            telegram_id = message.from_.id
            chat_id = message.chat.id
            user = await user_repo.get_by_telegram_id(telegram_id)

            if user is None:
                # Unregistered user - check if this looks like email
                if registration_handler.is_valid_email(message.text):
                    # Email input during registration flow
                    background_tasks.add_task(
                        registration_handler.handle_email_input,
                        telegram_id,
                        chat_id,
                        message.text,
                    )
                else:
                    # Not an email, prompt to register
                    background_tasks.add_task(
                        bot_instance.send_message,
                        chat_id=chat_id,
                        text="You need to register first. Send /start to begin.",
                    )
            else:
                # AC-T006.2: Registered user - route to MessageHandler
                background_tasks.add_task(
                    message_handler.handle,
                    message,
                )
        # Ignore non-text messages (photos, voice, etc.) for MVP

        # AC-T006.4: Return 200 immediately
        return WebhookResponse()

    @router.get("/auth/confirm", response_class=HTMLResponse)
    async def auth_confirm(
        error: str | None = None,
        error_code: str | None = None,
        error_description: str | None = None,
    ) -> str:
        """Email verification confirmation page with error handling.

        Displayed after user clicks magic link from email.
        Handles both success and error cases (expired links, invalid tokens, etc.).

        Args:
            error: Error type from Supabase (e.g., "access_denied")
            error_code: Specific error code (e.g., "otp_expired")
            error_description: Human-readable error message

        Returns:
            HTML page with confirmation or error message.

        Note:
            Supabase sends errors in URL fragment (#error=...) which requires
            JavaScript to extract. This endpoint also checks query params.
        """
        # Check if there's an error in query params
        if error or error_code:
            error_msg = error_description or error or "Unknown error"
            error_reason = ""

            if error_code == "otp_expired":
                error_reason = "Magic link expired (60 second timeout)"
            elif error_code == "otp_disabled":
                error_reason = "Magic link has already been used"
            elif error == "access_denied":
                error_reason = "Invalid or expired authentication link"

            return f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Authentication Error - Nikita</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                        margin: 0;
                        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                    }}
                    .container {{
                        background: white;
                        padding: 2.5rem;
                        border-radius: 12px;
                        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
                        max-width: 450px;
                        text-align: center;
                    }}
                    h1 {{
                        color: #dc2626;
                        margin-bottom: 1rem;
                        font-size: 1.8rem;
                    }}
                    .error-icon {{
                        font-size: 4rem;
                        margin-bottom: 1rem;
                    }}
                    p {{
                        color: #666;
                        line-height: 1.6;
                        margin-bottom: 1rem;
                    }}
                    .error-detail {{
                        background: #fee2e2;
                        border-left: 4px solid #dc2626;
                        padding: 1rem;
                        margin: 1.5rem 0;
                        text-align: left;
                    }}
                    .error-detail strong {{
                        color: #991b1b;
                        display: block;
                        margin-bottom: 0.5rem;
                    }}
                    .telegram-link {{
                        display: inline-block;
                        background: #0088cc;
                        color: white;
                        padding: 0.75rem 1.5rem;
                        border-radius: 6px;
                        text-decoration: none;
                        font-weight: 600;
                        transition: background 0.3s;
                        margin-top: 1rem;
                    }}
                    .telegram-link:hover {{
                        background: #006699;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="error-icon">⚠️</div>
                    <h1>Authentication Failed</h1>
                    <p>{error_msg}</p>
                    {f'<div class="error-detail"><strong>Reason:</strong> {error_reason}</div>' if error_reason else ''}
                    <p><strong>What to do:</strong></p>
                    <p>1. Return to Telegram<br>2. Send <code>/start</code> to request a new magic link<br>3. Click the new link within 60 seconds</p>
                    <a href="https://telegram.me" class="telegram-link">Open Telegram</a>
                </div>
                <script>
                    // Supabase sends errors in URL fragment (#error=...)
                    // Check fragment and reload page with query params if error found
                    const hash = window.location.hash.substring(1);
                    if (hash && hash.includes('error=')) {{
                        const params = new URLSearchParams(hash);
                        const error = params.get('error');
                        const errorCode = params.get('error_code');
                        const errorDesc = params.get('error_description');

                        if (error && !window.location.search.includes('error=')) {{
                            // Reload with error in query params
                            const newUrl = window.location.pathname +
                                '?error=' + encodeURIComponent(error) +
                                (errorCode ? '&error_code=' + encodeURIComponent(errorCode) : '') +
                                (errorDesc ? '&error_description=' + encodeURIComponent(errorDesc) : '');
                            window.location.replace(newUrl);
                        }}
                    }}
                </script>
            </body>
            </html>
            """

        # Success case - no errors
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Email Verified - Nikita</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }
                .container {
                    background: white;
                    padding: 2.5rem;
                    border-radius: 12px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    max-width: 400px;
                    text-align: center;
                }
                h1 {
                    color: #333;
                    margin-bottom: 1rem;
                    font-size: 1.8rem;
                }
                .checkmark {
                    font-size: 4rem;
                    color: #10b981;
                    margin-bottom: 1rem;
                }
                p {
                    color: #666;
                    line-height: 1.6;
                    margin-bottom: 1.5rem;
                }
                .telegram-link {
                    display: inline-block;
                    background: #0088cc;
                    color: white;
                    padding: 0.75rem 1.5rem;
                    border-radius: 6px;
                    text-decoration: none;
                    font-weight: 600;
                    transition: background 0.3s;
                }
                .telegram-link:hover {
                    background: #006699;
                }
            </style>
            <script>
                // Check for errors in URL fragment (Supabase sends errors this way)
                const hash = window.location.hash.substring(1);
                if (hash && hash.includes('error=')) {
                    const params = new URLSearchParams(hash);
                    const error = params.get('error');
                    const errorCode = params.get('error_code');
                    const errorDesc = params.get('error_description');

                    // Reload with error in query params for server-side handling
                    const newUrl = window.location.pathname +
                        '?error=' + encodeURIComponent(error) +
                        (errorCode ? '&error_code=' + encodeURIComponent(errorCode) : '') +
                        (errorDesc ? '&error_description=' + encodeURIComponent(errorDesc) : '');
                    window.location.replace(newUrl);
                }
            </script>
        </head>
        <body>
            <div class="container">
                <div class="checkmark">✓</div>
                <h1>Email Verified!</h1>
                <p>Your email has been successfully verified.</p>
                <p>Return to Telegram to complete your registration and start chatting with Nikita.</p>
                <a href="https://telegram.me" class="telegram-link">Open Telegram</a>
            </div>
        </body>
        </html>
        """

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

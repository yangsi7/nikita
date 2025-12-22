"""Telegram user authentication via Supabase OTP codes.

Handles user registration flow (v2.0 - OTP):
1. User provides email → send OTP code (6-8 digits) via email
2. User enters code in Telegram chat → verify OTP
3. Create user account + link telegram_id

OTP State Machine:
- pending: Initial state (email received, OTP not yet sent)
- code_sent: OTP code sent, awaiting user input in chat
- verified: Successfully verified (transient, record deleted)
- expired: Code expired (for audit trail before cleanup)

Note: Magic link flow (v1.0) is deprecated but kept for backward compatibility.
"""

import logging
import re
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from supabase import AsyncClient
from supabase_auth.errors import AuthApiError

from nikita.db.repositories.pending_registration_repository import (
    PendingRegistrationRepository,
)
from nikita.db.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class TelegramAuth:
    """Handle Telegram user authentication via Supabase.

    Manages the registration flow where users provide email addresses
    to receive magic links, then link their Telegram accounts after verification.
    """

    # Email validation regex (basic validation)
    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

    def __init__(
        self,
        supabase_client: AsyncClient,
        user_repository: UserRepository,
        pending_registration_repository: PendingRegistrationRepository,
    ):
        """Initialize TelegramAuth.

        Args:
            supabase_client: Supabase client for auth operations.
            user_repository: Repository for user database operations.
            pending_registration_repository: Repository for pending registrations.
        """
        self.supabase = supabase_client
        self.user_repository = user_repository
        self.pending_repo = pending_registration_repository

    async def register_user(
        self,
        telegram_id: int,
        email: str,
        registration_source: str = "telegram",  # "telegram" or "portal"
    ) -> dict[str, Any]:
        """DEPRECATED: Initiate user registration with magic link.

        This method is deprecated in favor of send_otp_code() for Telegram flow.
        Kept for backward compatibility with portal flow and existing magic links.

        AC-T008.1: Creates pending registration
        AC-T008.2: Sends magic link email via Supabase
        AC-FR004-001: Valid email triggers magic link

        Supports dual registration flows:
        - "telegram": DEPRECATED - use send_otp_code() instead
        - "portal": Redirect to portal /auth/callback (Web portal flow)

        Args:
            telegram_id: User's Telegram ID.
            email: Email address for magic link delivery.
            registration_source: Where registration initiated ("telegram" or "portal").

        Returns:
            dict with status and details:
            - status="magic_link_sent": Magic link sent successfully
            - status="already_registered": telegram_id already linked
            - status="error": Failed to send

        Raises:
            ValueError: If email format is invalid.
        """
        # Validate email format
        if not self.EMAIL_REGEX.match(email):
            raise ValueError(f"Invalid email format: {email}")

        # Check if telegram_id already registered
        existing_user = await self.user_repository.get_by_telegram_id(telegram_id)
        if existing_user is not None:
            return {
                "status": "already_registered",
                "user": existing_user,
            }

        # Send magic link via Supabase with redirect URL
        # Choose redirect based on registration source
        from nikita.config.settings import get_settings

        settings = get_settings()

        if registration_source == "portal" and settings.portal_url:
            # Portal flow: redirect to portal's /auth/callback for session exchange
            redirect_url = f"{settings.portal_url}/auth/callback"
        else:
            # Telegram flow: redirect to backend /auth/confirm for instructions
            webhook_url = settings.telegram_webhook_url or "http://localhost:8000"
            # Extract base URL (scheme + host only) - ignore any path in webhook URL
            # This avoids path duplication when webhook URL contains /api/v1/...
            parsed = urlparse(webhook_url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            redirect_url = f"{base_url}/api/v1/telegram/auth/confirm"

        response = await self.supabase.auth.sign_in_with_otp({
            "email": email,
            "options": {
                "email_redirect_to": redirect_url,
            }
        })

        # Store pending registration in database (replaces in-memory dict)
        # Uses upsert so re-requesting magic link updates existing record
        await self.pending_repo.store(telegram_id, email)

        return {
            "status": "magic_link_sent",
            "email": email,
            "telegram_id": telegram_id,
        }

    async def verify_magic_link(
        self,
        telegram_id: int,
        otp_token: str,
    ) -> Any:  # Returns User
        """DEPRECATED: Verify magic link OTP and complete registration.

        This method is deprecated in favor of verify_otp_code() for Telegram flow.
        Kept for backward compatibility with auth_confirm endpoint (existing magic links).

        AC-T008.3: Completes registration flow
        AC-FR004-002: Valid link creates account + confirms

        Args:
            telegram_id: User's Telegram ID.
            otp_token: OTP token from magic link (OTP code).

        Returns:
            Created User object with telegram_id linked.

        Raises:
            ValueError: If no pending registration found.
            Exception: If OTP verification fails.
        """
        # Check for pending registration in database
        email = await self.pending_repo.get_email(telegram_id)
        if email is None:
            raise ValueError(
                f"No pending registration found for telegram_id {telegram_id}. "
                "User must call register_user() first, or registration may have expired."
            )

        # Verify OTP with Supabase
        # This validates the magic link token and creates the auth user
        try:
            response = await self.supabase.auth.verify_otp(
                {
                    "email": email,
                    "token": otp_token,
                    "type": "magiclink",  # Explicitly specify magic link type
                }
            )

            # Extract user_id from Supabase auth response
            supabase_user_id = UUID(response.user.id)

            # Create user in our database with telegram_id linked
            user = await self.user_repository.create_with_metrics(
                user_id=supabase_user_id,
                telegram_id=telegram_id,
            )

            # Clear pending registration from database
            await self.pending_repo.delete(telegram_id)

            return user

        except Exception as e:
            # Re-raise with context
            raise Exception(f"Failed to verify OTP: {str(e)}") from e

    async def link_telegram(
        self,
        user_id: UUID,
        telegram_id: int,
    ) -> None:
        """Link Telegram ID to existing user account.

        AC-T008.4: Updates user record with telegram_id

        Used when a user already has an account (via web/other platform)
        and wants to link their Telegram account.

        Args:
            user_id: Existing user's UUID.
            telegram_id: Telegram ID to link.

        Raises:
            ValueError: If user not found.
        """
        # Get existing user
        user = await self.user_repository.get(user_id)
        if user is None:
            raise ValueError(f"User not found: {user_id}")

        # Update telegram_id
        user.telegram_id = telegram_id

        # Persist changes
        await self.user_repository.update(user)

    async def get_pending_email(self, telegram_id: int) -> str | None:
        """Get pending email for telegram_id (for debugging/testing).

        Args:
            telegram_id: Telegram ID to check.

        Returns:
            Pending email if exists and not expired, None otherwise.
        """
        return await self.pending_repo.get_email(telegram_id)

    # =========================================================================
    # OTP Flow Methods (v2.0 - Preferred)
    # =========================================================================

    async def send_otp_code(
        self,
        telegram_id: int,
        chat_id: int,
        email: str,
    ) -> dict[str, Any]:
        """Send OTP code to email (no magic link redirect).

        This is the v2.0 OTP flow that keeps users in Telegram throughout.

        AC-T2.2.1: send_otp_code method exists
        AC-T2.2.2: Calls Supabase sign_in_with_otp WITHOUT emailRedirectTo
        AC-T2.2.3: Stores pending registration with chat_id and otp_state="code_sent"
        AC-T2.2.4: Returns {"status": "code_sent", "email": email}
        AC-T2.2.5: Validates email format before sending

        Args:
            telegram_id: User's Telegram ID.
            chat_id: Telegram chat ID for sending messages back.
            email: Email address for OTP code delivery.

        Returns:
            dict with status:
            - status="code_sent": OTP code sent successfully
            - status="already_registered": telegram_id already linked

        Raises:
            ValueError: If email format is invalid.
        """
        # AC-T2.2.5: Validate email format
        if not self.EMAIL_REGEX.match(email):
            raise ValueError(f"Invalid email format: {email}")

        # Check if telegram_id already registered
        existing_user = await self.user_repository.get_by_telegram_id(telegram_id)
        if existing_user is not None:
            return {
                "status": "already_registered",
                "user": existing_user,
            }

        # AC-T2.2.2: Send OTP code via Supabase
        # CRITICAL: email_redirect_to is REQUIRED for email template to render.
        # Without it, {{ .ConfirmationURL }} in the template is empty and email silently fails.
        # Users will use the OTP code from the email, not the magic link.
        from nikita.config.settings import get_settings
        settings = get_settings()
        # Use backend_url (Cloud Run URL) for email redirects
        # Fallback chain: backend_url > telegram_webhook_url > localhost
        base_url = settings.backend_url
        if not base_url:
            webhook_url = settings.telegram_webhook_url or "http://localhost:8000"
            parsed = urlparse(webhook_url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
        redirect_url = f"{base_url}/api/v1/telegram/auth/confirm"

        await self.supabase.auth.sign_in_with_otp({
            "email": email,
            "options": {
                "should_create_user": True,
                "email_redirect_to": redirect_url,  # Required for email template to render
            }
        })

        # AC-T2.2.3: Store pending registration with chat_id and otp_state
        await self.pending_repo.store(
            telegram_id=telegram_id,
            email=email,
            chat_id=chat_id,
            otp_state="code_sent",
        )

        # AC-T2.2.4: Return success status
        return {
            "status": "code_sent",
            "email": email,
            "telegram_id": telegram_id,
        }

    async def verify_otp_code(
        self,
        telegram_id: int,
        code: str,
    ) -> Any:  # Returns User
        """Verify OTP code (6-8 digits) and complete registration.

        This is the v2.0 OTP verification that uses type="email" (not "magiclink").

        AC-T2.3.1: verify_otp_code method exists
        AC-T2.3.2: Retrieves pending registration by telegram_id
        AC-T2.3.3: Calls Supabase verify_otp with type="email"
        AC-T2.3.4: Creates user record with telegram_id on success
        AC-T2.3.5: Deletes pending registration after successful verification
        AC-T2.3.6: Raises ValueError on invalid/expired code

        Args:
            telegram_id: User's Telegram ID.
            code: OTP code (6-8 digits) from email.

        Returns:
            Created User object with telegram_id linked.

        Raises:
            ValueError: If no pending registration found or code is invalid/expired.
        """
        # AC-T2.3.2: Get pending registration
        pending = await self.pending_repo.get(telegram_id)
        if pending is None:
            raise ValueError(
                f"No pending registration found for telegram_id {telegram_id}. "
                "User must send email first."
            )

        if pending.otp_state != "code_sent":
            logger.error(
                f"[OTP-DEBUG] Wrong OTP state: telegram_id={telegram_id}, "
                f"state={pending.otp_state}, expected='code_sent'"
            )
            raise ValueError(
                f"Invalid OTP state: {pending.otp_state}. Expected 'code_sent'."
            )

        # AC-T2.3.3: Verify OTP with Supabase using type="email" (NOT "magiclink")
        logger.info(
            f"[OTP-DEBUG] Calling Supabase verify_otp: email={pending.email}, "
            f"code_length={len(code)}, type='email'"
        )
        try:
            response = await self.supabase.auth.verify_otp({
                "email": pending.email,
                "token": code,
                "type": "email",  # CRITICAL: "email" for OTP, not "magiclink"
            })
            logger.info(
                f"[OTP-DEBUG] Supabase verify_otp SUCCESS: user_id={response.user.id}"
            )

            supabase_user_id = UUID(response.user.id)

            # AC-T2.3.5: Clear pending registration IMMEDIATELY after Supabase verify
            # IMPORTANT: Delete BEFORE user creation to prevent limbo state.
            # If user creation fails, user can restart with /start.
            # Supabase auth is already verified, so re-sending OTP will work.
            await self.pending_repo.delete(telegram_id)
            logger.info(
                f"[OTP-DEBUG] Deleted pending registration: telegram_id={telegram_id}"
            )

            # AC-T2.3.4: Create or link user in database
            existing_user = await self.user_repository.get(supabase_user_id)
            if existing_user is not None:
                # User exists (portal-first flow) - link telegram_id if not set
                if existing_user.telegram_id is None:
                    existing_user.telegram_id = telegram_id
                    await self.user_repository.update(existing_user)
                user = existing_user
            else:
                # New user - create with metrics
                user = await self.user_repository.create_with_metrics(
                    user_id=supabase_user_id,
                    telegram_id=telegram_id,
                )

            return user

        except AuthApiError as e:
            # Use error.code (not string matching) per Supabase best practices
            # See: https://supabase.com/docs/guides/auth/debugging/error-codes
            logger.error(
                f"[OTP-DEBUG] Supabase verify_otp FAILED: telegram_id={telegram_id}, "
                f"error_type={type(e).__name__}, code={e.code}, status={e.status}, "
                f"message={e.message}"
            )
            # AC-T2.3.6: Provide clear error messages based on error code
            if e.code == "otp_expired":
                raise ValueError(
                    "OTP code has expired. Please send your email again to get a new code."
                ) from e
            elif e.code == "invalid_credentials":
                raise ValueError("Invalid OTP code. Please check and try again.") from e
            else:
                # Log unexpected error codes for debugging
                logger.warning(
                    f"[OTP-DEBUG] Unexpected error code: {e.code}, status={e.status}"
                )
                raise ValueError(f"OTP verification failed: {e.message}") from e

        except Exception as e:
            # Non-API errors (network issues, etc.)
            logger.error(
                f"[OTP-DEBUG] Unexpected error during OTP verification: "
                f"telegram_id={telegram_id}, error_type={type(e).__name__}, error={e}"
            )
            raise ValueError(f"OTP verification failed: {str(e)}") from e

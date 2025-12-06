"""Telegram user authentication via Supabase magic links.

Handles user registration flow:
1. User provides email → send magic link
2. User clicks link → verify OTP
3. Create user account + link telegram_id
"""

import re
from typing import Any
from uuid import UUID

from supabase import AsyncClient

from nikita.db.repositories.pending_registration_repository import (
    PendingRegistrationRepository,
)
from nikita.db.repositories.user_repository import UserRepository


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
    ) -> dict[str, Any]:
        """Initiate user registration with magic link.

        AC-T008.1: Creates pending registration
        AC-T008.2: Sends magic link email via Supabase
        AC-FR004-001: Valid email triggers magic link

        Args:
            telegram_id: User's Telegram ID.
            email: Email address for magic link delivery.

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
        # Redirect to Cloud Run /auth/confirm endpoint after email verification
        from nikita.config.settings import get_settings

        settings = get_settings()
        webhook_url = settings.telegram_webhook_url or "http://localhost:8000"

        # Construct redirect URL: base_url + /api/v1/telegram/auth/confirm
        # Remove /telegram/webhook if present in webhook_url
        base_url = webhook_url.replace("/telegram/webhook", "").replace("/webhook", "")
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
        """Verify magic link OTP and complete registration.

        AC-T008.3: Completes registration flow
        AC-FR004-002: Valid link creates account + confirms

        Args:
            telegram_id: User's Telegram ID.
            otp_token: OTP token from magic link (6-digit code).

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

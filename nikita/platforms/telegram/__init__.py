"""Telegram platform integration for Nikita.

This module provides Telegram bot functionality for the Nikita text agent,
handling webhook updates, message routing, authentication, and response delivery.
"""

from nikita.platforms.telegram.auth import TelegramAuth
from nikita.platforms.telegram.bot import TelegramBot
from nikita.platforms.telegram.commands import CommandHandler
from nikita.platforms.telegram.delivery import ResponseDelivery
from nikita.platforms.telegram.message_handler import MessageHandler
from nikita.platforms.telegram.models import TelegramUpdate, TelegramMessage, TelegramUser

__all__ = [
    "TelegramAuth",
    "TelegramBot",
    "CommandHandler",
    "ResponseDelivery",
    "MessageHandler",
    "TelegramUpdate",
    "TelegramMessage",
    "TelegramUser",
]

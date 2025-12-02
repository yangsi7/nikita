"""Pydantic models for Telegram webhook updates.

These models define the structure of incoming Telegram updates
and messages for type-safe handling.
"""

from pydantic import BaseModel, ConfigDict, Field


class TelegramUser(BaseModel):
    """Telegram user information.

    AC-T005.3: Model with id, first_name, username fields.
    """

    id: int
    first_name: str
    username: str | None = None
    last_name: str | None = None
    language_code: str | None = None


class TelegramChat(BaseModel):
    """Telegram chat information."""

    id: int
    type: str
    first_name: str | None = None
    username: str | None = None


class TelegramMessage(BaseModel):
    """Telegram message object.

    AC-T005.2: Model with from, chat, text, photo, voice fields.
    """

    model_config = ConfigDict(populate_by_name=True)

    message_id: int
    date: int = 0  # Unix timestamp
    from_: TelegramUser | None = Field(default=None, alias="from")
    chat: TelegramChat
    text: str | None = None
    photo: list[dict] | None = None
    voice: dict | None = None
    document: dict | None = None
    sticker: dict | None = None


class TelegramUpdate(BaseModel):
    """Telegram webhook update.

    AC-T005.1: Model with update_id, message, callback_query.
    """

    update_id: int
    message: TelegramMessage | None = None
    callback_query: dict | None = None
    edited_message: TelegramMessage | None = None

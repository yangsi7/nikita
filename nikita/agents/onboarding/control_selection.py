"""ControlSelection discriminated-union body schema for /converse.

Portal-side ``user_input`` can be either a raw string (free-text turn)
or a structured control selection (chip / slider / toggle / cards / text
— per tech-spec §5.2 / decision D4). The server accepts both shapes
and normalizes at the boundary.

Each variant carries ``kind`` as a Literal discriminator for Pydantic's
discriminated-union decoder. Unknown ``kind`` → 422 at request-parse
time (Pydantic's default behavior for invalid discriminators).
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field


class _BaseControl(BaseModel):
    """Shared config: forbid extra fields so rogue ``user_id`` cannot ride
    in on a nested control selection.
    """

    model_config = ConfigDict(extra="forbid")


class TextControl(_BaseControl):
    """User typed free-text into the chat input."""

    kind: Literal["text"] = "text"
    value: str = Field(min_length=1)


class ChipControl(_BaseControl):
    """User tapped a chip from the current-prompt options grid."""

    kind: Literal["chips"] = "chips"
    value: str = Field(min_length=1, max_length=64)


class SliderControl(_BaseControl):
    """User moved the 1-5 darkness slider."""

    kind: Literal["slider"] = "slider"
    value: int = Field(ge=1, le=5)


class ToggleControl(_BaseControl):
    """User tapped the voice / text toggle."""

    kind: Literal["toggle"] = "toggle"
    value: Literal["voice", "text"]


class CardsControl(_BaseControl):
    """User selected a backstory card.

    ``value`` carries the 12-char hex option_id; the cache_key travels on
    the card payload (not here) to avoid duplication.
    """

    kind: Literal["cards"] = "cards"
    value: str = Field(pattern=r"^[a-f0-9]{12}$")


# Discriminated union — Pydantic validates ``kind`` first, then narrows
# to the matching model. Unknown ``kind`` → 422 automatically.
ControlSelection = Annotated[
    Union[TextControl, ChipControl, SliderControl, ToggleControl, CardsControl],
    Field(discriminator="kind"),
]


__all__ = [
    "CardsControl",
    "ChipControl",
    "ControlSelection",
    "SliderControl",
    "TextControl",
    "ToggleControl",
]

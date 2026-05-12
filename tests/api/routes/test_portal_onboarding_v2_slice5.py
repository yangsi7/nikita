"""Spec 218 Slice 218-5 — persist for slider (saturday_morning, darkness_level)
and text_long (geek_out_on) slots.

Per ``specs/218-onboarding-wizard-v2-agent-driven/subspecs/5/slice.md``.

New slot persistence in slice 218-5:
  saturday_morning  -> int 0-10 (slider value)
  darkness_level    -> int 0-10 (slider value)
  geek_out_on       -> str stripped, max 1000 chars

FR-007 DAG: no new edges from these 3 slots (no dependents).

RED phase: tests fail until PR-218-5 implementation lands.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _reset_retry_counts():
    """Clear ``_retry_counts`` between tests — defense-in-depth per slice-218-3 pattern."""
    from nikita.api.routes import portal_onboarding_v2  # noqa: PLC0415

    portal_onboarding_v2._retry_counts.clear()
    yield
    portal_onboarding_v2._retry_counts.clear()


# ---------------------------------------------------------------------------
# saturday_morning persistence (_slot_payload unit tests)
# ---------------------------------------------------------------------------


class TestSlotPayloadSaturdayMorning:
    """_slot_payload correctly converts saturday_morning slider values."""

    def test_valid_int_persisted(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        result = _slot_payload("saturday_morning", 7)
        assert result == {"saturday_morning": 7}

    def test_zero_persisted(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        result = _slot_payload("saturday_morning", 0)
        assert result == {"saturday_morning": 0}

    def test_ten_persisted(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        result = _slot_payload("saturday_morning", 10)
        assert result == {"saturday_morning": 10}

    def test_negative_int_returns_none(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        assert _slot_payload("saturday_morning", -1) is None

    def test_above_ten_returns_none(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        assert _slot_payload("saturday_morning", 11) is None

    def test_string_value_returns_none(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        assert _slot_payload("saturday_morning", "7") is None

    def test_float_value_returns_none(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        assert _slot_payload("saturday_morning", 7.5) is None


# ---------------------------------------------------------------------------
# darkness_level persistence (_slot_payload unit tests)
# ---------------------------------------------------------------------------


class TestSlotPayloadDarknessLevel:
    """_slot_payload correctly converts darkness_level slider values."""

    def test_valid_int_persisted(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        result = _slot_payload("darkness_level", 5)
        assert result == {"darkness_level": 5}

    def test_zero_persisted(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        result = _slot_payload("darkness_level", 0)
        assert result == {"darkness_level": 0}

    def test_negative_returns_none(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        assert _slot_payload("darkness_level", -1) is None

    def test_above_ten_returns_none(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        assert _slot_payload("darkness_level", 11) is None


# ---------------------------------------------------------------------------
# geek_out_on persistence (_slot_payload unit tests)
# ---------------------------------------------------------------------------


class TestSlotPayloadGeekOutOn:
    """_slot_payload correctly converts geek_out_on text_long values."""

    def test_valid_string_stripped(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        result = _slot_payload("geek_out_on", "  vintage synthesizers  ")
        assert result == {"geek_out_on": "vintage synthesizers"}

    def test_empty_string_returns_none(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        assert _slot_payload("geek_out_on", "   ") is None

    def test_exactly_1000_chars_persisted(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        value = "x" * 1000
        result = _slot_payload("geek_out_on", value)
        assert result == {"geek_out_on": value}

    def test_over_1000_chars_returns_none(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        value = "x" * 1001
        assert _slot_payload("geek_out_on", value) is None

    def test_non_string_returns_none(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        assert _slot_payload("geek_out_on", 42) is None


# ---------------------------------------------------------------------------
# PERSISTABLE set coverage
# ---------------------------------------------------------------------------


class TestPersistableSlotNamesCoversSlice5:
    """_PERSISTABLE_SLOT_NAMES must include all 3 new slice-5 slots."""

    def test_saturday_morning_in_persistable(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            _PERSISTABLE_SLOT_NAMES,
        )

        assert "saturday_morning" in _PERSISTABLE_SLOT_NAMES

    def test_darkness_level_in_persistable(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            _PERSISTABLE_SLOT_NAMES,
        )

        assert "darkness_level" in _PERSISTABLE_SLOT_NAMES

    def test_geek_out_on_in_persistable(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            _PERSISTABLE_SLOT_NAMES,
        )

        assert "geek_out_on" in _PERSISTABLE_SLOT_NAMES

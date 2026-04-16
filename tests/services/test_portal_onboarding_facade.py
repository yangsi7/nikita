"""Unit tests for PortalOnboardingFacade.set_chosen_option — Spec 214 PR 214-D (T010).

TDD RED phase: all tests FAIL until set_chosen_option is implemented in
nikita/services/portal_onboarding.py.

Covers:
- AC-10.1: cache_key mismatch → 403
- AC-10.2: missing cache row → 404
- AC-10.4: unknown option_id → 409
- AC-10.5: success writes full BackstoryOption snapshot
- AC-10.6: emits onboarding.backstory_chosen structured event
- AC-10.4 (idempotent): same choice_id → same snapshot

Per .claude/rules/testing.md:
- Every test_ has at least one assert
- Non-empty repo fixtures
- No zero-assertion shells
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

USER_ID = UUID("550e8400-e29b-41d4-a716-446655440000")
CACHE_KEY = "berlin|techno|3|tech|unknown|twenties|tech"
OPTION_ID_A = "aabbccdd1122"  # 12-char hex (sha256[:12] format)
OPTION_ID_B = "bbccddee2233"


def _make_option_dict(option_id: str = OPTION_ID_A) -> dict[str, Any]:
    """Build a BackstoryOption-shaped dict as stored in backstory_cache."""
    return {
        "id": option_id,
        "venue": "Tresor",
        "context": "Dark basement, peak hour.",
        "the_moment": "She handed back my lighter.",
        "unresolved_hook": "She knew my name before I told her.",
        "tone": "chaotic",
    }


def _make_user(profile: dict | None = None) -> MagicMock:
    """Build a mock User ORM with onboarding_profile JSONB."""
    user = MagicMock()
    user.id = USER_ID
    # Default profile yields a cache_key matching CACHE_KEY when bridge is applied
    default_profile: dict[str, Any] = {
        "location_city": "berlin",
        "drug_tolerance": 3,
        "social_scene": "techno",
        "life_stage": "tech",
        "interest": None,
        "age": 28,
        "occupation": "engineer",
    }
    user.onboarding_profile = profile if profile is not None else default_profile
    return user


# ---------------------------------------------------------------------------
# T010-A: cache_key mismatch → 403
# ---------------------------------------------------------------------------


class TestSetChosenOptionCacheKeyMismatch:
    """AC-10.1: supplied cache_key does not match recomputed key → 403."""

    @pytest.mark.asyncio
    async def test_set_chosen_option_cache_key_mismatch_raises_403(self):
        """cache_key mismatch → HTTPException 403 'Clearance mismatch. Start over.'"""
        from nikita.services.portal_onboarding import PortalOnboardingFacade

        # User profile that would compute a DIFFERENT cache_key than what we supply
        user = _make_user(profile={
            "location_city": "paris",  # different city
            "drug_tolerance": 3,
            "social_scene": "art",
            "life_stage": "creative",
            "interest": None,
            "age": 30,
            "occupation": "artist",
        })

        mock_session = AsyncMock(spec=AsyncSession)

        with patch("nikita.db.repositories.user_repository.UserRepository") as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=user)

            facade = PortalOnboardingFacade()
            with pytest.raises(HTTPException) as exc_info:
                await facade.set_chosen_option(
                    user_id=USER_ID,
                    chosen_option_id=OPTION_ID_A,
                    cache_key=CACHE_KEY,  # stale/mismatched key
                    session=mock_session,
                )

        assert exc_info.value.status_code == 403
        assert "mismatch" in exc_info.value.detail.lower() or "clearance" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# T010-B: missing cache row → 404
# ---------------------------------------------------------------------------


class TestSetChosenOptionMissingCacheRow:
    """AC-10.2: backstory_cache row missing for the given cache_key → 404."""

    @pytest.mark.asyncio
    async def test_set_chosen_option_missing_cache_row_raises_404(self):
        """BackstoryCacheRepository.get returns None → HTTPException 404."""
        from nikita.services.portal_onboarding import PortalOnboardingFacade
        from nikita.onboarding.tuning import compute_backstory_cache_key

        # Profile that computes EXACTLY the same cache_key we supply
        user = _make_user()
        pseudo = SimpleNamespace(
            city=user.onboarding_profile.get("location_city"),
            darkness_level=user.onboarding_profile.get("drug_tolerance"),
            social_scene=user.onboarding_profile.get("social_scene"),
            life_stage=user.onboarding_profile.get("life_stage"),
            interest=user.onboarding_profile.get("interest"),
            age=user.onboarding_profile.get("age"),
            occupation=user.onboarding_profile.get("occupation"),
        )
        real_cache_key = compute_backstory_cache_key(pseudo)

        mock_session = AsyncMock(spec=AsyncSession)

        with (
            patch("nikita.db.repositories.user_repository.UserRepository") as MockRepo,
            patch("nikita.db.repositories.backstory_cache_repository.BackstoryCacheRepository") as MockCacheRepo,
        ):
            MockRepo.return_value.get = AsyncMock(return_value=user)
            MockCacheRepo.return_value.get = AsyncMock(return_value=None)  # cache miss

            facade = PortalOnboardingFacade()
            with pytest.raises(HTTPException) as exc_info:
                await facade.set_chosen_option(
                    user_id=USER_ID,
                    chosen_option_id=OPTION_ID_A,
                    cache_key=real_cache_key,
                    session=mock_session,
                )

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# T010-C: unknown option_id → 409
# ---------------------------------------------------------------------------


class TestSetChosenOptionUnknownOptionId:
    """AC-10.2 (spec 409): chosen_option_id not in cache row's scenarios → 409."""

    @pytest.mark.asyncio
    async def test_set_chosen_option_unknown_option_id_raises_409(self):
        """chosen_option_id not present in cache → HTTPException 409 Conflict."""
        from nikita.services.portal_onboarding import PortalOnboardingFacade
        from nikita.onboarding.tuning import compute_backstory_cache_key

        user = _make_user()
        pseudo = SimpleNamespace(
            city=user.onboarding_profile.get("location_city"),
            darkness_level=user.onboarding_profile.get("drug_tolerance"),
            social_scene=user.onboarding_profile.get("social_scene"),
            life_stage=user.onboarding_profile.get("life_stage"),
            interest=user.onboarding_profile.get("interest"),
            age=user.onboarding_profile.get("age"),
            occupation=user.onboarding_profile.get("occupation"),
        )
        real_cache_key = compute_backstory_cache_key(pseudo)
        cached_scenarios = [_make_option_dict(OPTION_ID_A)]  # only A in cache

        mock_session = AsyncMock(spec=AsyncSession)

        with (
            patch("nikita.db.repositories.user_repository.UserRepository") as MockRepo,
            patch("nikita.db.repositories.backstory_cache_repository.BackstoryCacheRepository") as MockCacheRepo,
        ):
            MockRepo.return_value.get = AsyncMock(return_value=user)
            MockCacheRepo.return_value.get = AsyncMock(return_value=cached_scenarios)

            facade = PortalOnboardingFacade()
            with pytest.raises(HTTPException) as exc_info:
                await facade.set_chosen_option(
                    user_id=USER_ID,
                    chosen_option_id="nonexistentid99",  # NOT in scenarios
                    cache_key=real_cache_key,
                    session=mock_session,
                )

        assert exc_info.value.status_code == 409
        assert "generated" in exc_info.value.detail.lower() or "exist" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# T010-D: success — writes full BackstoryOption snapshot
# ---------------------------------------------------------------------------


class TestSetChosenOptionSuccess:
    """AC-10.5: successful put writes all 6 BackstoryOption fields to JSONB."""

    @pytest.mark.asyncio
    async def test_set_chosen_option_success_writes_full_snapshot(self):
        """Happy path: returns BackstoryOption with all 6 required fields."""
        from nikita.services.portal_onboarding import PortalOnboardingFacade
        from nikita.onboarding.contracts import BackstoryOption
        from nikita.onboarding.tuning import compute_backstory_cache_key

        user = _make_user()
        pseudo = SimpleNamespace(
            city=user.onboarding_profile.get("location_city"),
            darkness_level=user.onboarding_profile.get("drug_tolerance"),
            social_scene=user.onboarding_profile.get("social_scene"),
            life_stage=user.onboarding_profile.get("life_stage"),
            interest=user.onboarding_profile.get("interest"),
            age=user.onboarding_profile.get("age"),
            occupation=user.onboarding_profile.get("occupation"),
        )
        real_cache_key = compute_backstory_cache_key(pseudo)
        option_dict = _make_option_dict(OPTION_ID_A)
        cached_scenarios = [option_dict]

        mock_session = AsyncMock(spec=AsyncSession)
        mock_repo_instance = MagicMock()
        mock_repo_instance.get = AsyncMock(return_value=user)
        mock_repo_instance.update_onboarding_profile_key = AsyncMock()

        mock_cache_repo_instance = MagicMock()
        mock_cache_repo_instance.get = AsyncMock(return_value=cached_scenarios)

        with (
            patch("nikita.db.repositories.user_repository.UserRepository") as MockRepo,
            patch("nikita.db.repositories.backstory_cache_repository.BackstoryCacheRepository") as MockCacheRepo,
        ):
            MockRepo.return_value = mock_repo_instance
            MockCacheRepo.return_value = mock_cache_repo_instance

            facade = PortalOnboardingFacade()
            result = await facade.set_chosen_option(
                user_id=USER_ID,
                chosen_option_id=OPTION_ID_A,
                cache_key=real_cache_key,
                session=mock_session,
            )

        # Must return a BackstoryOption with all 6 fields populated
        assert isinstance(result, BackstoryOption)
        assert result.id == OPTION_ID_A
        assert result.venue == option_dict["venue"]
        assert result.context == option_dict["context"]
        assert result.the_moment == option_dict["the_moment"]
        assert result.unresolved_hook == option_dict["unresolved_hook"]
        assert result.tone == option_dict["tone"]

        # Verify JSONB write was called with the full option dict
        mock_repo_instance.update_onboarding_profile_key.assert_awaited()
        write_calls = mock_repo_instance.update_onboarding_profile_key.await_args_list
        # Find the chosen_option write call
        written_keys = [call[0][1] for call in write_calls]  # second positional arg is key
        assert "chosen_option" in written_keys

        # Atomicity guarantee — facade MUST commit after JSONB write so the
        # row is durable before the structured event is emitted. Regression
        # guard against silent commit-removal (QA review nitpick #1).
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_set_chosen_option_idempotent_same_choice(self):
        """AC-10.4: calling twice with same chosen_option_id → same result."""
        from nikita.services.portal_onboarding import PortalOnboardingFacade
        from nikita.onboarding.tuning import compute_backstory_cache_key

        user = _make_user()
        pseudo = SimpleNamespace(
            city=user.onboarding_profile.get("location_city"),
            darkness_level=user.onboarding_profile.get("drug_tolerance"),
            social_scene=user.onboarding_profile.get("social_scene"),
            life_stage=user.onboarding_profile.get("life_stage"),
            interest=user.onboarding_profile.get("interest"),
            age=user.onboarding_profile.get("age"),
            occupation=user.onboarding_profile.get("occupation"),
        )
        real_cache_key = compute_backstory_cache_key(pseudo)
        option_dict = _make_option_dict(OPTION_ID_A)
        cached_scenarios = [option_dict]

        mock_session = AsyncMock(spec=AsyncSession)
        mock_repo_instance = MagicMock()
        mock_repo_instance.get = AsyncMock(return_value=user)
        mock_repo_instance.update_onboarding_profile_key = AsyncMock()

        mock_cache_repo_instance = MagicMock()
        mock_cache_repo_instance.get = AsyncMock(return_value=cached_scenarios)

        with (
            patch("nikita.db.repositories.user_repository.UserRepository") as MockRepo,
            patch("nikita.db.repositories.backstory_cache_repository.BackstoryCacheRepository") as MockCacheRepo,
        ):
            MockRepo.return_value = mock_repo_instance
            MockCacheRepo.return_value = mock_cache_repo_instance

            facade = PortalOnboardingFacade()
            result1 = await facade.set_chosen_option(
                user_id=USER_ID,
                chosen_option_id=OPTION_ID_A,
                cache_key=real_cache_key,
                session=mock_session,
            )
            result2 = await facade.set_chosen_option(
                user_id=USER_ID,
                chosen_option_id=OPTION_ID_A,
                cache_key=real_cache_key,
                session=mock_session,
            )

        # Both calls produce the same result
        assert result1.id == result2.id
        assert result1.venue == result2.venue
        assert result1.tone == result2.tone

        # Both calls commit (idempotency does not skip the commit; jsonb_set
        # writes the same final state). Two await_count guards against a
        # future "skip-if-unchanged" optimization silently breaking durability.
        assert mock_session.commit.await_count == 2


# ---------------------------------------------------------------------------
# T010-E: structured event emitted
# ---------------------------------------------------------------------------


class TestSetChosenOptionEventEmission:
    """AC-10.6: onboarding.backstory_chosen structured log event emitted."""

    @pytest.mark.asyncio
    async def test_set_chosen_option_emits_backstory_chosen_event(self, caplog):
        """Successful set_chosen_option emits 'onboarding.backstory_chosen' log."""
        import logging

        from nikita.services.portal_onboarding import PortalOnboardingFacade
        from nikita.onboarding.tuning import compute_backstory_cache_key

        user = _make_user()
        pseudo = SimpleNamespace(
            city=user.onboarding_profile.get("location_city"),
            darkness_level=user.onboarding_profile.get("drug_tolerance"),
            social_scene=user.onboarding_profile.get("social_scene"),
            life_stage=user.onboarding_profile.get("life_stage"),
            interest=user.onboarding_profile.get("interest"),
            age=user.onboarding_profile.get("age"),
            occupation=user.onboarding_profile.get("occupation"),
        )
        real_cache_key = compute_backstory_cache_key(pseudo)
        option_dict = _make_option_dict(OPTION_ID_A)
        cached_scenarios = [option_dict]

        mock_session = AsyncMock(spec=AsyncSession)
        mock_repo_instance = MagicMock()
        mock_repo_instance.get = AsyncMock(return_value=user)
        mock_repo_instance.update_onboarding_profile_key = AsyncMock()

        mock_cache_repo_instance = MagicMock()
        mock_cache_repo_instance.get = AsyncMock(return_value=cached_scenarios)

        with (
            patch("nikita.db.repositories.user_repository.UserRepository") as MockRepo,
            patch("nikita.db.repositories.backstory_cache_repository.BackstoryCacheRepository") as MockCacheRepo,
            caplog.at_level(logging.INFO, logger="nikita.services.portal_onboarding"),
        ):
            MockRepo.return_value = mock_repo_instance
            MockCacheRepo.return_value = mock_cache_repo_instance

            facade = PortalOnboardingFacade()
            await facade.set_chosen_option(
                user_id=USER_ID,
                chosen_option_id=OPTION_ID_A,
                cache_key=real_cache_key,
                session=mock_session,
            )

        # Event must include the structured tag
        log_text = " ".join(r.message for r in caplog.records)
        assert "onboarding.backstory_chosen" in log_text
        # Must include tone and venue (no PII — not name/age/occupation/phone/city)
        assert "tone" in log_text or "chaotic" in log_text
        assert "venue" in log_text or "tresor" in log_text.lower()
        # Must NOT include PII fields in log
        assert "name" not in log_text
        assert "age" not in log_text
        assert "occupation" not in log_text
        assert "phone" not in log_text

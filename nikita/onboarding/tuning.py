"""Tuning constants for Spec 213 onboarding backend (FR-4).

Domain-specific timeouts, cache TTLs, rate limits, and bucket mappings for
the portal onboarding handoff path.

CONSTRAINT (FR-4 isolation): This module MUST NOT import from
nikita.engine.constants, nikita.onboarding.models, or nikita.db.*. It is a
pure constants + pure-function module. `compute_backstory_cache_key` is
duck-typed — any object exposing the right attributes works at runtime.

Per .claude/rules/tuning-constants.md, every constant has:
  - Current value
  - Prior values with driving PR/GH issue
  - One-line rationale for *this* value

Regression guards in tests/onboarding/test_tuning_constants.py.
"""

from __future__ import annotations

from typing import Final

# ---------------------------------------------------------------------------
# Service call timeouts
# ---------------------------------------------------------------------------

VENUE_RESEARCH_TIMEOUT_S: Final[float] = 15.0
"""Per-call timeout for VenueResearchService.research_venues.

Prior values: none (new in Spec 213, GH #213).
Rationale: Firecrawl typical p95 ~8s; 15s budget covers cold cache + 1 retry.
"""

BACKSTORY_GEN_TIMEOUT_S: Final[float] = 20.0
"""Per-call timeout for BackstoryGeneratorService.generate_scenarios.

Prior values: none (new in Spec 213, GH #213).
Rationale: Claude Haiku typical p95 ~12s; 20s covers tail latency + 1 retry.
"""

# ---------------------------------------------------------------------------
# Pipeline-ready gate
# ---------------------------------------------------------------------------

PIPELINE_GATE_POLL_INTERVAL_S: Final[float] = 2.0
"""Portal poll interval for /pipeline-ready endpoint.

Prior values: none (new in Spec 213, GH #213).
Rationale: balances perceived responsiveness vs Cloud Run cold-start churn.
"""

PIPELINE_GATE_MAX_WAIT_S: Final[float] = 20.0
"""Maximum portal wait for pipeline readiness before unblocking.

Prior values: none (new in Spec 213, GH #213).
Rationale: VenueResearch (15s) and BackstoryGenerator (20s) run in parallel
fanout, so the dominant bound is BACKSTORY_GEN_TIMEOUT_S (20s). Cloud Run
cold-start (~5s) is absorbed by the parallel fanout. If either service
exceeds 20s, the portal unblocks with 'degraded' state per FR-2a and the
backend continues its pipeline independently. Invariant guarded by tests
in test_tuning_constants.py::TestTimeoutRelationalInvariants.
"""

# ---------------------------------------------------------------------------
# Cache + generation tuning
# ---------------------------------------------------------------------------

BACKSTORY_CACHE_TTL_DAYS: Final[int] = 30
"""Backstory cache TTL for unique (city, scene, ...) profile shape.

Prior values: none (new in Spec 213, GH #213).
Rationale: matches existing VenueCache TTL; balances cost vs scenario freshness.
"""

BACKSTORY_HOOK_PROBABILITY: Final[float] = 0.50
"""Probability that FirstMessageGenerator includes a backstory hook in the first message.

Prior values: none (new in Spec 213, GH #213).
Rationale: 50% creates variety; testable via patched value (1.0 always-include, 0.0 never-include).
"""

# ---------------------------------------------------------------------------
# Rate limits
# ---------------------------------------------------------------------------

PREVIEW_RATE_LIMIT_PER_MIN: Final[int] = 5
"""Per-user rate limit for POST /onboarding/preview-backstory (FR-4a.1).

Prior values: none (new in Spec 213, iter-7 amendment).
Rationale: each call triggers Claude + Firecrawl; 5/min covers wizard navigation and
legitimate retries but prevents abuse/DoS. Voice rate limit is 20/min — different surface
with different cost profile. Separate counter key prefix 'preview:' avoids sharing quota
with the voice rate limiter.
"""

CHOICE_RATE_LIMIT_PER_MIN: Final[int] = 10
"""Per-user rate limit for PUT /onboarding/profile/chosen-option (Spec 214 FR-10.1).

Prior values: none (new in Spec 214 PR 214-D, GH issue tracked in Spec 214).
Rationale: selecting a backstory is a one-shot user action — no external service call
incurred, unlike preview (5/min). 10/min is generous; allows legitimate retries
(endpoint is idempotent) without enabling abuse. Separate 'choice:' key prefix
isolates counters from voice (SEC-010) and preview (Spec 213 'preview:' prefix).
Used by _ChoiceRateLimiter in nikita/api/middleware/rate_limit.py.
"""

PIPELINE_POLL_RATE_LIMIT_PER_MIN: Final[int] = 30
"""Per-user rate limit for GET /onboarding/pipeline-ready/{user_id} (Spec 214 AC-5.6).

Prior values: none (endpoint was previously unlimited; new rate limit in Spec 214 PR 214-D).
Rationale: portal polls at PIPELINE_GATE_POLL_INTERVAL_S=2.0s → ~30 calls over the
20s PIPELINE_GATE_MAX_WAIT_S window. 30/min matches exactly one full poll cycle without
false-positive 429s. 'poll:' key prefix isolates from voice/preview/choice counters.
Used by _PipelineReadyRateLimiter in nikita/api/middleware/rate_limit.py.
"""

# ---------------------------------------------------------------------------
# Cache-key bucketing
# ---------------------------------------------------------------------------

AGE_BUCKETS: Final[tuple[tuple[int, int, str], ...]] = (
    (18, 24, "young_adult"),
    (25, 34, "twenties"),
    (35, 49, "midlife"),
    (50, 99, "experienced"),
)
"""Age bucketing for backstory cache key. Inclusive boundaries.

Prior values: none (new in Spec 213).
Rationale: 4 buckets balance cache hit ratio vs personalization granularity.
"""

OCCUPATION_CATEGORIES: Final[dict[str, str]] = {
    # mapping: lowercase substring → coarse category for cache key
    "engineer": "tech",
    "developer": "tech",
    "designer": "tech",
    "artist": "arts",
    "musician": "arts",
    "writer": "arts",
    "banker": "finance",
    "trader": "finance",
    "analyst": "finance",
    "nurse": "healthcare",
    "doctor": "healthcare",
    "student": "student",
    "barista": "service",
    "server": "service",
    "retail": "service",
}
"""Coarse occupation categorization for backstory cache key.

Original full string preserved in profile.occupation; this is for cache bucketing only.
Prior values: none (new in Spec 213).
Rationale: 6 categories balance cache hit ratio vs persona variety. Default: 'other'.
"""


# ---------------------------------------------------------------------------
# Spec 214 FR-11d — /converse endpoint tuning constants
# ---------------------------------------------------------------------------

ONBOARDING_INPUT_MAX_CHARS: Final[int] = 500
"""Max `user_input` length accepted by POST /onboarding/converse.

Prior values: none (new in Spec 214 FR-11d, GH #351).
Rationale: longer inputs are almost always prompt-injection; 500 covers
verbose genuine answers while rejecting novel-length jailbreak payloads.
"""

NIKITA_REPLY_MAX_CHARS: Final[int] = 280
"""Server-enforced business cap on Nikita's reply text.

Prior values:
  140 (Spec 214 FR-11d initial) — raised by GH #389 (2026-04-22):
    Walk S observed 100% fallback at wizard turn 4+ because the model
    generates contextually-rich replies (>140 chars) when conversation
    history is ≥6 messages. 140 = one tweet; too tight for natural
    onboarding dialogue.
  280 (current, GH #389) — two "tweet segments". Still short/texting-
    style; aligns with modern SMS segment (160 chars) × 1.75 headroom.
    Wire-level Pydantic `ConverseResponse.nikita_reply` permits up to
    500 chars (schema ceiling); server validator downgrades >280 to a
    fallback.
"""

CONVERSE_PER_USER_RPM: Final[int] = 20
"""Per-user rate limit for POST /onboarding/converse (req / minute).

Prior values: none (new in Spec 214 FR-11d, GH #353).
Rationale: 15-turn wizard with retry headroom. Dedicated 'converse:' key
prefix isolates this bucket from voice/preview/choice/poll limiters.
"""

CONVERSE_PER_IP_RPM: Final[int] = 30
"""Per-IP rate limit for POST /onboarding/converse (req / minute).

Prior values: none (new in Spec 214 FR-11d, GH #353).
Rationale: NAT-friendly (university / cafe / corporate) while blunting
distributed abuse. IP derived from X-Forwarded-For per proxy-header config.
"""

CONVERSE_DAILY_LLM_CAP_USD: Final[float] = 2.00
"""Per-user daily LLM spend cap (USD) for /converse.

Prior values: none (new in Spec 214 FR-11d, GH #353).
Rationale: 200 turns × $0.01/turn ceiling. Backed by llm_spend_ledger
(tech-spec §4.3b). Breach → 429 in-character body + Retry-After: 30.
"""

CONVERSE_TIMEOUT_MS_WARM: Final[int] = 8000
"""Agent run timeout (milliseconds) for WARM Cloud Run instances.

Prior values: 2500 (per tech-spec §11 SLO; empirically too tight — Walk P
2026-04-21 observed real LLM calls taking ~6s on warm instance, the 2.5s
ceiling caused 100% wizard failure on prod. GH #378.)
Rationale: p95 LLM (claude-sonnet-4-6) + auth + DB + sanitize + serialize
chain ~5s warm; 8s gives 60% headroom for the long tail. Aligns with
`llm_retry_call_timeout = 60.0` (settings.py) which is the inner LLM
ceiling — we never need to exceed that.
"""

CONVERSE_TIMEOUT_MS_COLD: Final[int] = 30000
"""Agent run timeout (milliseconds) for COLD Cloud Run instances.

Cloud Run scale-to-zero adds 5-15s startup latency on the first request
after idle. Process-startup also pulls model warmup if `llm_warmup_enabled`
(settings default True). The first ~30s of process lifetime gets this
larger budget so a cold start does NOT manifest as a wizard timeout for
the user.

Threshold: `CONVERSE_COLD_WARMUP_WINDOW_SEC` (below) gates which value to
use.
"""

CONVERSE_COLD_WARMUP_WINDOW_SEC: Final[float] = 30.0
"""Process-uptime threshold (seconds) below which a request is treated
as cold and gets `CONVERSE_TIMEOUT_MS_COLD` instead of `_WARM`.

Rationale: Cloud Run cold starts + LLM warmup typically complete within
30s. After that the instance is fully warm and the tighter 8s ceiling
applies.
"""

# Legacy alias kept for backward compat with code that still imports the
# old single-value constant. New code should call the helper at
# `nikita/api/routes/portal_onboarding.py:get_converse_timeout_ms()`.
CONVERSE_TIMEOUT_MS: Final[int] = CONVERSE_TIMEOUT_MS_WARM
"""DEPRECATED alias of CONVERSE_TIMEOUT_MS_WARM. Use the cold/warm split.

Retained so existing imports do not break. Will be removed in a follow-up
once all call sites migrate to the helper.
"""

CONVERSE_429_RETRY_AFTER_SEC: Final[int] = 30
"""Retry-After header (seconds) on /converse 429 responses.

Prior values: none (new in Spec 214 FR-11d).
Rationale: gentle backoff matches typing cadence; short enough that a
legitimate typist doesn't feel locked out.
"""

CONFIDENCE_CONFIRMATION_THRESHOLD: Final[float] = 0.85
"""Minimum extraction confidence to auto-commit without user confirmation.

Prior values: none (new in Spec 214 FR-11d).
Rationale: below this threshold, `confirmation_required=true` surfaces an
inline Yes/Fix that control in the portal.
"""

MIN_USER_AGE: Final[int] = 18
"""Legal minimum age for onboarding; age<18 → in-character rejection.

Prior values: none (unchanged across specs).
Rationale: legal floor. Server-enforced at extraction time regardless of
what the model reports.
"""

STRICTMODE_GUARD_MS: Final[int] = 50
"""React StrictMode double-mount dedup window (milliseconds).

Prior values: none (new in Spec 214 FR-11d, GH #355 / M3).
Rationale: StrictMode fires useEffect twice in dev; 50ms dedup window on
hydrate action prevents duplicate reducer dispatch.
"""

HANDOFF_GREETING_BACKSTOP_INTERVAL_SEC: Final[int] = 60
"""pg_cron cadence for nikita_handoff_greeting_backstop job.

Prior values: none (new in Spec 214 FR-11e, GH B1 backstop).
Rationale: matches Telegram 5xx retry window + headroom; stranded
pending_handoff rows re-dispatched every 60s.
"""

HANDOFF_GREETING_STALE_AFTER_SEC: Final[int] = 30
"""Seconds before an in-flight handoff greeting is considered stranded.

Prior values: none (new in Spec 214 FR-11e).
Rationale: the primary BackgroundTasks dispatch finishes within 30s on a
healthy path; anything older gets picked up by the pg_cron backstop.
"""

PERSONA_DRIFT_FEATURE_TOLERANCE: Final[float] = 0.15
"""Feature-level tolerance for persona-drift test (±15%).

Prior values: none (new in Spec 214 FR-11d, GH #356 / M1).
Rationale: per AC-11d.11, mean sentence length + lowercase-ratio +
canonical-phrase-count must stay within ±15% of the baseline CSV.
"""

PERSONA_DRIFT_COSINE_MIN: Final[float] = 0.70
"""Minimum TF-IDF cosine similarity vs persona baseline CSV.

Prior values: none (new in Spec 214 FR-11d, GH #356).
Rationale: below 0.70 the conversation agent has drifted from Nikita's
established voice enough to warrant a baseline regeneration ADR bump.
"""

PERSONA_DRIFT_SEED_SAMPLES: Final[int] = 20
"""Samples per seed used by persona_baseline_generate.py.

Prior values: none (new in Spec 214 FR-11d).
Rationale: 3 seeds × 20 samples = 60 rows per baseline; enough for a
stable TF-IDF vectorizer without bloating the CSV.
"""

LLM_SOURCE_RATE_GATE_N: Final[int] = 100
"""Simulated-turn sample size for /converse source=llm rollout gate.

Prior values: none (new in Spec 214 FR-11d, AC-11d.9).
Rationale: 100 turns is enough to distinguish 90% from 85% at a reasonable
confidence level in the preview env dry-run.
"""

LLM_SOURCE_RATE_GATE_MIN: Final[float] = 0.90
"""Minimum observed `source=\"llm\"` rate gating PR 3 ship (resolves S2).

Prior values: none (new in Spec 214 FR-11d).
Rationale: below 90% implies fallback-dominant behavior in production; S2
is blocked on this rate being sustained in preview.
"""

CHAT_COMPLETION_RATE_TOLERANCE_PP: Final[int] = 5
"""Tolerance (percentage points) for chat-wizard completion rate vs legacy.

Prior values: none (new in Spec 214 FR-11d, AC-11d.13c / S4).
Rationale: PR 5 legacy drop is blocked until chat-wizard completion is
within ±5pp of form-wizard baseline.
"""

CHAT_COMPLETION_RATE_GATE_N: Final[int] = 50
"""Sample size for Phase C completion-rate gate (AC-11d.13c).

Prior values: none (new in Spec 214 FR-11d).
Rationale: 50 users post-Phase-A provides a reasonable directional signal
without blocking PR 5 indefinitely.
"""

# FR-11d onboarding-tone filter — forbidden phrases (resolves S3, AC-T2.1.2).
# Server-side reply filter catches obvious jailbreak echoes + off-brand
# therapist-speak that should never leave the agent. ≥12 entries required
# by AC-T2.1.2.
ONBOARDING_FORBIDDEN_PHRASES: Final[tuple[str, ...]] = (
    "As an AI",
    "as an AI",
    "As a language model",
    "I am an AI",
    "I'm an AI",
    "I cannot",
    "I'm sorry, but",
    "I apologize, but",
    "Let me help you with that",
    "I'm happy to help",
    "How can I assist",
    "As an assistant",
    "safety guidelines",
    "content policy",
    "OpenAI",
    "Anthropic",
    "I don't have access",
    "I can't provide",
)
"""Case-sensitive substrings that trigger server-side fallback if present
in Nikita's reply. Covers (a) AI-disclosure leaks, (b) customer-support
register, (c) model/vendor names. ≥12 entries per AC-T2.1.2.

Prior values: none (new in Spec 214 FR-11d, GH #351 / S3).
Rationale: these phrases are never in-character for Nikita. A direct
substring match is cheap and deterministic; the LLM-as-judge tone filter
(AC-T2.5.8) handles subtler drift.
"""


# ---------------------------------------------------------------------------
# Bucket helpers (module-private per spec FR-3 step 3)
# ---------------------------------------------------------------------------


def _age_bucket(age: int | None) -> str:
    """Map age to bucket label per AGE_BUCKETS.

    Returns 'unknown' for ``None`` input and for any age outside the
    AGE_BUCKETS range (18–99 inclusive).

    Invariant: in the production path, ``age`` is validated upstream by
    ``OnboardingV2ProfileRequest`` / ``BackstoryPreviewRequest`` (both
    constrain ``Field(ge=18, le=99)``), so out-of-range inputs only occur
    via duck-typed test stubs. Tests verify both below-range (17) and
    above-range (100) both bucket to 'unknown'.
    """
    if age is None:
        return "unknown"
    for low, high, label in AGE_BUCKETS:
        if low <= age <= high:
            return label
    return "unknown"  # outside any bucket


def _occupation_bucket(occupation: str | None) -> str:
    """Map occupation string to coarse category per OCCUPATION_CATEGORIES.

    Substring match (lowercased). Returns 'other' if no match, 'unknown' if None.
    """
    if occupation is None:
        return "unknown"
    occ_lower = occupation.lower()
    for substring, category in OCCUPATION_CATEGORIES.items():
        if substring in occ_lower:
            return category
    return "other"


# ---------------------------------------------------------------------------
# Cache-key computation (public — used by facade + preview endpoint)
# ---------------------------------------------------------------------------


def compute_backstory_cache_key(profile: object) -> str:
    """Deterministic cache key for backstory generation.

    Format: 'city|scene|darkness|life_stage|interest|age_bucket|occupation_bucket'
    with 'unknown' substituted for None values. City normalized to lowercase.

    ``profile`` is duck-typed: any object exposing ``city``, ``social_scene``,
    ``darkness_level``, ``life_stage``, ``interest``, ``age``, ``occupation``
    satisfies the contract. This keeps ``tuning.py`` import-free and lets the
    function be reused by the facade (FR-3), the preview endpoint (FR-4a),
    and tests without a Pydantic dependency.

    Both call sites (facade + preview endpoint) compute the same key for the
    same logical profile; cache coherence depends on it.
    """
    city = (getattr(profile, "city", None) or "unknown").lower()
    scene = getattr(profile, "social_scene", None) or "unknown"
    # None darkness → "unknown" (matches docstring promise and keeps the key
    # from ever containing the literal string "None").
    darkness_raw = getattr(profile, "darkness_level", None)
    darkness = str(darkness_raw) if darkness_raw is not None else "unknown"
    life_stage = getattr(profile, "life_stage", None) or "unknown"
    interest = (getattr(profile, "interest", None) or "unknown").lower()
    age_bkt = _age_bucket(getattr(profile, "age", None))
    occ_bkt = _occupation_bucket(getattr(profile, "occupation", None))
    return f"{city}|{scene}|{darkness}|{life_stage}|{interest}|{age_bkt}|{occ_bkt}"

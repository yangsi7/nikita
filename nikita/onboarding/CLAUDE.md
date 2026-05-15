# nikita/onboarding/ Module

## Purpose

Voice onboarding flow using Meta-Nikita ElevenLabs agent (Spec 028).

Collects user profile, sets experience preferences, and hands off to Nikita for the main game experience.

## Module Structure

| File | Purpose |
|------|---------|
| `__init__.py` | Module exports |
| `meta_nikita.py` | Agent config, persona, TTS settings |
| `server_tools.py` | collect_profile, configure_preferences, complete_onboarding |
| `handoff.py` | HandoffManager - sends first Nikita message via Telegram |
| `models.py` | OnboardingState, ProfileData, PreferenceData |
| `infrastructure.py` | Database persistence utilities |
| `telegram_flow.py` | Telegram integration (ready check, initiation) |
| `voice_flow.py` | ElevenLabs call management |

## Key Configuration

| Setting | Value |
|---------|-------|
| Agent ID | `agent_4801kewekhxgekzap1bqdr62dxvc` |
| Persona | Underground Game Hostess (seductive, playful provocateur) |
| TTS Stability | 0.40 (dynamic, emotional) |
| TTS Similarity | 0.70 |
| TTS Speed | 0.95 (seductive pacing) |

## Server Tools

```python
# collect_profile(field_name, value)
# Fields: timezone, occupation, hobbies, personality_type, hangout_spots

# configure_preferences(darkness_level, pacing_weeks, conversation_style)
# darkness_level: 1-5 (vanilla → full noir)
# pacing_weeks: 4 (intense) or 8 (relaxed)
# conversation_style: listener, balanced, sharer

# complete_onboarding(call_id, notes)
# Triggers handoff to Nikita via Telegram
```

## Database Fields

Added to `users` table (Migration 0009):

| Column | Type | Purpose |
|--------|------|---------|
| `onboarding_status` | VARCHAR(20) | pending/in_progress/completed/skipped |
| `onboarding_profile` | JSONB | Collected profile data |
| `onboarded_at` | TIMESTAMPTZ | Completion timestamp |
| `onboarding_call_id` | VARCHAR(100) | ElevenLabs conversation ID |

## API Routes

5 endpoints at `/api/v1/onboarding/`:
- `POST /status` - Check onboarding status
- `POST /initiate` - Start voice call
- `POST /server-tool` - Handle ElevenLabs tool calls
- `POST /webhook` - Receive call events
- `POST /skip` - Skip voice onboarding

## Tests

231 tests across 8 test files in `tests/onboarding/`:
- `test_infrastructure.py` - 71 tests
- `test_models.py` - 20 tests
- `test_server_tools.py` - 27 tests
- `test_handoff.py` - 19 tests
- `test_telegram_flow.py` - 28 tests
- `test_voice_flow.py` - 45 tests
- `test_e2e.py` - 20 tests
- `test_meta_nikita.py` - 36 tests

## Related

- [Spec 028](../../specs/028-voice-onboarding/spec.md)
- [memory/integrations.md](../../memory/integrations.md#meta-nikita-onboarding-agent)
- [memory/user-journeys.md](../../memory/user-journeys.md#journey-7-voice-onboarding)

## Callers

- `nikita/agents/onboarding/conversation_agent.py:263` — Pydantic AI agent (text wizard); discriminated-union output, 4 firecrawl `fetch_*` tools (firecrawl-only post Spec 218 PR-218-PREREQ-A), callable instructions, output_validator.
- `nikita/onboarding/handoff.py:705` — onboarding-to-main pipeline handoff; one of 5 PipelineOrchestrator invocation sites.
- `nikita/api/routes/portal_onboarding.py` — portal wizard backend (Spec 214/216).
- `portal/src/app/login/page-client.tsx:94` — frontend `signInWithOtp` magic-link step (post-216-G; portal-first `/onboarding/auth` surface deleted).

## Gotchas

- **Telegram-first signup is canonical**, not "voice-preferred" as KT claimed (per auto-memory `feedback_telegram_first_signup_pattern.md`). Voice onboarding is an alt path, not the default.
- **`nikita/platforms/telegram/registration_handler.py:14` handles email-OTP only** — NOT profile collection. Profile questions live in `meta_nikita.py` / `voice_flow.py` / `profile_collector.py`.
- **Onboarding agent flow has known design issues** (Spec 216 redesign): completion gate via `_compute_progress(latest_kind)` is per-turn snapshot, not cumulative-state Pydantic validation. See `.claude/rules/agentic-design-patterns.md` Hard Rules.
- **4 narrow `fetch_*` tools** (firecrawl) at `agents/onboarding/conversation_agent.py:284-287` — borderline against fan-out anti-pattern in `.claude/rules/agentic-design-patterns.md` §3.
- **Profile collection state**: `pending_registration` table holds in-flight registration; expires on completion or `cleanup_expired_registrations` task.
- **Backstory cache**: Spec 213 `backstory_cache` table, populated post-onboarding by Spec 216-E firecrawl tools (WebSearchTool removed in Spec 218 PR-218-PREREQ-A — firecrawl-only). RLS-protected.

Last verified: 2026-05-05

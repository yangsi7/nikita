# W4 KT Migration — USER JOURNEYS Verification

**Date**: 2026-05-05
**Wave**: W4 (KT migration with code-verification gate)
**Source**: `docs/knowledge-transfer/USER_JOURNEY.md` (486 lines)
**Verifier**: `pr-codebase-intel` subagent (HARD CAP 15, read-only)
**Method**: Every claim grep-confirmed against `nikita/api/routes/`, `nikita/platforms/telegram/`, `nikita/agents/voice/`, `nikita/onboarding/`, `portal/src/app/`, `supabase/migrations/`. KT NOT trusted.

## Verdict: PARTIAL MIGRATION — high-level metric values verified; entry-point file/class names and pipeline-invocation framing are wrong

## Verification Table

| # | KT Claim | KT line | Verification target | Code file:line | Status | Migrate? | Replaced by (if STALE) |
|---|---|---|---|---|---|---|---|
| 1 | Telegram entry: `/start` at `commands.py:CommandHandler:45-80` | 57,83 | commands.py | CommandHandler at `commands.py:185`; real entry is `nikita/api/routes/telegram.py:501` POST /webhook | STALE | YES | webhook → `_handle_message_with_fresh_session` at `telegram.py:462`; CommandHandler at `commands.py:185` |
| 2 | Voice entry: `nikita/agents/voice/inbound.py:handle_inbound_call` | 58 | inbound.py | `:223 handle_incoming_call`; real ElevenLabs entry is `nikita/api/routes/voice.py:350` POST /server-tool | STALE | YES | `handle_incoming_call`; ElevenLabs callback `voice.py:350` |
| 3 | Portal entry: `portal/src/app/page.tsx` web app first contact | 59 | page.tsx | `page.tsx:1-25` is now a marketing landing (HeroSection, PitchSection); real onboarding chain is `onboarding/auth/page.tsx:21` → `onboarding/page.tsx:41` → `dashboard/page.tsx` | STALE | YES | Marketing landing; auth chain via `/onboarding/auth` |
| 4 | `nikita/platforms/telegram/webhook.py:30-60` Signature validation | 84 | webhook.py | FILE MISSING | STALE | YES | Sig validation in `nikita/api/routes/telegram.py` (HMAC header) + `nikita/platforms/telegram/auth.py` |
| 5 | `nikita/api/routes/telegram.py:20-50` Webhook endpoint | 85 | telegram.py | endpoint at `:501` (`@router.post("/webhook")`); 20-50 is module imports/docstring | STALE | YES | Endpoint at `:501`; `:447` `create_telegram_router` |
| 6 | "Voice path is preferred, text is fallback" for onboarding | 104-105 | onboarding | per project memory `feedback_telegram_first_signup_pattern.md`, signup is Telegram-first | STALE | NO | Telegram-first |
| 7 | `nikita/onboarding/meta_nikita.py:1-150` Meta-Nikita agent config | 140 | meta_nikita.py | exists 16.4KB | VERIFIED | NO | — |
| 8 | `nikita/onboarding/server_tools.py:30-80` Profile storage tool | 141 | server_tools.py | actual methods at `:107 handle_request`, `:149 collect_profile`, `:226 configure_preferences`, `:303`, `:389` | STALE | YES | Lines 30-80 don't host the storage tool |
| 9 | `nikita/onboarding/handoff.py:1-100` Agent handoff logic | 142 | handoff.py | exists 42.7KB | VERIFIED | NO | — |
| 10 | Text onboarding asks: name, work, hobbies, goals via `registration_handler.py` | 146-150 | registration_handler.py | `:14` handles email OTP only, NOT profile questions | STALE | YES | Profile questions in `meta_nikita.py` / `voice_flow.py` / `profile_collector.py`; registration_handler = email→OTP only |
| 11 | `pending_registration.py` registration state | 156 | nikita/db/models/pending_registration.py | exists | VERIFIED | NO | — |
| 12 | `MessageHandler.handle_message() @ message_handler.py:50-150` (rate limit, profile gate, game-over) | 187 | message_handler.py | file is 84.9KB; method is `handle()` per `telegram.py:486 handler.handle(message)` | STALE | YES | Method `handle()`; 50-150 wrong scope |
| 13 | `ContextEngine.collect() @ engine.py:80-150` with 8 collectors, 45s timeout, 115+ field ContextPackage | 196-199 | nikita/context/ | `nikita/context/package.py:95` defines `ContextPackage`; NO `ContextEngine` class | STALE | YES | No ContextEngine; assembly via 11-stage `PipelineOrchestrator` (`orchestrator.py:47-59`); ContextPackage is Pydantic cache surface |
| 14 | `PromptGenerator.generate() @ generator.py:100-200` | 203-206 | nikita/ | NO `PromptGenerator` class | STALE | YES | `prompt_builder` stage at `orchestrator.py:58` (`PromptBuilderStage`) |
| 15 | `PostProcessor.process_conversation() @ post_processor.py:100-250` — 11 async stages, updates Neo4j | 211-214 | nikita/ | NO `PostProcessor` class; `process_conversation` only on `vice/service.py:142`; pipeline is `PipelineOrchestrator.process()` invoked from `tasks.py:789` | STALE | YES | `PipelineOrchestrator` 11 stages; Neo4j removed (Spec 042) |
| 16 | "Updates Neo4j graphs" in pipeline | 213 | n/a | Neo4j removed | STALE | YES | SupabaseMemory pgVector |
| 17 | Scoring weights Intimacy 30 / Passion 25 / Trust 25 / Secureness 20 | 240-243 | constants.py | `:166-170` METRIC_WEIGHTS exact match | VERIFIED | NO | — |
| 18 | `nikita/engine/scoring/calculator.py:30-100` score delta | 248 | calculator.py | exists, lines plausible | VERIFIED | NO | — |
| 19 | `nikita/engine/scoring/analyzer.py:1-80` response analysis | 249 | analyzer.py | exists 13.5KB | VERIFIED | NO | — |
| 20 | `nikita/engine/constants.py:20-50` metric weights | 250 | constants.py | METRIC_WEIGHTS at `:166`, BOSS_THRESHOLDS at `:132` | STALE | YES | Constants at `:132-170` |
| 21 | Engagement states 6 names (CALIBRATING…OUT_OF_ZONE) | 261-281 | state_machine.py | `:8-13` exact match | VERIFIED | NO | — |
| 22 | `engagement/state_machine.py:1-150` and `engagement/calculator.py:1-100` | 292-293 | files | both exist | VERIFIED | NO | — |
| 23 | `nikita/db/models/user.py:100-150` engagement state storage | 294 | user.py | exists | VERIFIED (file) | NO | — |
| 24 | Boss thresholds Ch1=55%…Ch5=75% | 304-308 | constants.py | `:132-138` exact match | VERIFIED | NO | — |
| 25 | `nikita/engine/chapters/boss_encounter.py:1-150` | 353 | file | MISSING | STALE | YES | `chapters/boss.py` |
| 26 | `nikita/engine/chapters/boss_judgment.py:1-100` | 354 | file | MISSING | STALE | YES | `chapters/judgment.py` |
| 27 | `nikita/engine/chapters/state_machine.py:1-150` | 355 | file | MISSING | STALE | YES | `chapters/phase_manager.py` |
| 28 | Decay rates Ch1=0.8/h…Ch5=0.2/h | 366-371 | constants.py | `:141-147` exact match | VERIFIED | NO | — |
| 29 | Grace periods Ch1=8h…Ch5=72h (yaml) | 366-371 | yaml | yaml matches; `constants.py` GRACE_PERIODS inverted + deprecated | VERIFIED (yaml) | NO | — |
| 30 | pg_cron POST /tasks/decay hourly | 380-381 | tasks.py | `:192` `@router.post("/decay")` | VERIFIED | NO | — |
| 31 | `DecayProcessor.process_all() @ decay_processor.py:30-80` | 386 | path | actual `nikita/engine/decay/processor.py`; `decay_processor.py` is wrong | STALE | YES | `nikita/engine/decay/processor.py` |
| 32 | Decay endpoint at tasks.py:100-150 | 404-406 | tasks.py | actual `:192` | STALE | YES | `tasks.py:192` |
| 33 | Game-over check at message_handler.py:80-100 + db/models/user.py:50-80 | 458-459 | files | both exist; line ranges unverified at 84.9KB scale | UNVERIFIABLE | YES | likely stale ranges |
| 34 | Voice timeout 2s; Voice bypasses ContextEngine | 471, 476 | voice.py | `voice.py:372 handle_server_tool` exists; ContextEngine doesn't exist anyway | UNVERIFIABLE | YES | "ContextEngine bypass" framing moot |
| 35 | "MessageHandler invokes ContextEngine → PromptGenerator → PostProcessor" inline | 187-215 | code | message_handler responds inline; pipeline runs async via cron task endpoints (`tasks.py:771-789` + `:933-963`) | STALE | YES | Pipeline runs via cron, not inline |

## Net Summary

- **Total claims**: 35
- **Verified**: 12
- **Stale**: 21
- **Unverifiable**: 2

## Top facts MISSING from `memory/user-journeys.md` (per code)

- `nikita/api/routes/telegram.py:501` — POST /webhook is the Telegram entry (NOT commands.py); dispatches to `_handle_message_with_fresh_session` at `:462` which builds MessageHandler with a fresh session for background processing.
- `nikita/api/routes/tasks.py:771-789` and `:933-963` — Pipeline runs via cron-task endpoints invoking `PipelineOrchestrator.process()`, NOT inline from message_handler. This is the actual async post-processing path.
- `nikita/pipeline/orchestrator.py:47-59` — 11 named stages: extraction, persistence, memory_update, life_sim, emotional, vice, game_state, conflict, touchpoint, summary, prompt_builder. Replaces KT's "PostProcessor 11 async stages" + "PromptGenerator" + "ContextEngine" trio.
- `nikita/engine/chapters/{boss.py, judgment.py, phase_manager.py}` — current boss/chapter file names. Replaces KT's boss_encounter / boss_judgment / state_machine.
- `nikita/onboarding/voice_flow.py` (23.7KB) and `profile_collector.py` (12.9KB) — voice onboarding plumbing. Per project memory `feedback_telegram_first_signup_pattern.md`, canonical signup is Telegram-first.
- `nikita/agents/voice/inbound.py:223 handle_incoming_call` — actual function name. Real ElevenLabs entry is `nikita/api/routes/voice.py:350` POST /server-tool.
- Portal entry: `portal/src/app/page.tsx` is now a marketing landing. Auth chain: `/onboarding/auth/page.tsx:21` → `/onboarding/page.tsx:41` → `/dashboard/page.tsx`. `E2E_AUTH_BYPASS` shortcut at `onboarding/page.tsx:42-50`. Magic-link `signInWithOtp` exists on dual surfaces (`onboarding/auth/page-client.tsx:50,101` AND `login/page-client.tsx:24,94`) — code smell.
- 3 user-row creation sites in `portal.py:126/477/513` — drift risk; should consolidate.
- Neo4j fully replaced by SupabaseMemory (pgVector, Spec 042).

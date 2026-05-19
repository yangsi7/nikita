# Spec 115 — Telegram Webhook Per-User Rate Limiting

**Status**: Draft
**Domain**: Infrastructure (Domain 6)
**Finding**: DA-005 (P1)
**Complexity**: 2

## Problem

`POST /telegram/webhook` has no per-user rate check at the handler level. The existing
`RateLimiter` is instantiated and passed to `MessageHandler`, but only consulted inside
the message processing flow — after a background task has already been scheduled and
pipeline slots potentially allocated.

A flood of messages from one registered user exhausts `MAX_CONCURRENT_PIPELINES=10`,
starving all other users. Telegram retries failed webhooks, compounding the effect.

## Solution

Check the existing `RateLimiter` at the **top** of the webhook handler, immediately after
deduplication, using `telegram_id` as the rate-limit key. Return HTTP 429 before any
background task is scheduled.

The `RateLimiter` already supports in-memory `InMemoryCache` (20/min, 500/day). The
per-minute limit (20/min) is the primary defence against pipeline starvation.

## Acceptance Criteria

### FR-001 — Pre-pipeline rate check
The webhook handler MUST check the rate limit after dedup and before scheduling any
background task. If rate limit is exceeded, return HTTP 429 with
`{"error": "rate_limit_exceeded", "retry_after": <seconds>}`.

### FR-002 — telegram_id as key
The rate check MUST use `telegram_id` (int) as the identifier. No DB lookup required.
`RateLimiter` shall accept `int | UUID` for the identifier.

### FR-003 — Commands exempt from per-minute limit
Telegram commands (`/start`, `/help`) are low-frequency and MUST NOT be blocked by the
per-minute rate limit. They are still subject to the daily limit.

### FR-004 — 429 response format
```json
{"error": "rate_limit_exceeded", "retry_after": 60}
```
Telegram ignores 429 body, but the format must be consistent for observability.

### FR-005 — Rate limit breach logged
When a rate limit fires, emit:
```
logger.warning("[RATE_LIMIT] telegram_id=%d reason=%s retry_after=%d", ...)
```

### FR-006 — Unit-testable
`RateLimiter.check_by_telegram_id(telegram_id: int)` is independently testable with
mocked `InMemoryCache`.

## Out of Scope

- Multi-instance safe persistence (Supabase table) — tracked as future Spec NNN
- Voice webhook rate limiting
- Admin override endpoint

## Files Modified

| File | Change |
|------|--------|
| `nikita/platforms/telegram/rate_limiter.py` | Add `check_by_telegram_id(telegram_id: int)` method |
| `nikita/api/routes/telegram.py` | Call rate check after dedup, return 429 |
| `tests/platforms/test_rate_limiter.py` | Tests for `check_by_telegram_id` |
| `tests/api/routes/test_telegram.py` | Tests for 429 response path |

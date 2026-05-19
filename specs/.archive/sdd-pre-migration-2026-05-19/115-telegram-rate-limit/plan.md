# Plan — Spec 115: Telegram Webhook Per-User Rate Limiting

## User Stories

### Story 1: RateLimiter supports telegram_id keys (TDD)
**AC**: FR-002, FR-006
**Files**: `nikita/platforms/telegram/rate_limiter.py`, `tests/platforms/test_rate_limiter.py`

Add `check_by_telegram_id(telegram_id: int) -> RateLimitResult` to `RateLimiter`.
Internally calls `self.check(UUID(int=telegram_id % (2**128)))` — reuses all existing
cache key and counter logic. Tests mock `InMemoryCache` directly.

**Tests first**:
- `test_check_by_telegram_id_allowed` — first call returns allowed=True
- `test_check_by_telegram_id_minute_exceeded` — 21st call returns allowed=False, reason="minute_limit_exceeded"
- `test_check_by_telegram_id_day_exceeded` — 501st call returns allowed=False, reason="day_limit_exceeded"

### Story 2: Webhook handler returns 429 on rate limit (TDD)
**AC**: FR-001, FR-003, FR-004, FR-005
**Files**: `nikita/api/routes/telegram.py`, `tests/api/routes/test_telegram.py`

After the dedup check, for non-command message updates:
```python
if telegram_id and not is_command:
    result = await rate_limiter.check_by_telegram_id(telegram_id)
    if not result.allowed:
        logger.warning("[RATE_LIMIT] telegram_id=%d reason=%s retry_after=%d",
                       telegram_id, result.reason, result.retry_after_seconds or 60)
        return JSONResponse(
            status_code=429,
            content={"error": "rate_limit_exceeded",
                     "retry_after": result.retry_after_seconds or 60},
        )
```

**Tests first**:
- `test_webhook_rate_limit_returns_429` — mock rate_limiter.check returns denied → assert 429
- `test_webhook_rate_limit_commands_exempt` — /start command → rate check NOT called
- `test_webhook_rate_limit_allowed_proceeds` — allowed → pipeline dispatched normally

## Implementation Order

1. Write failing tests (Story 1) → implement `check_by_telegram_id` → tests pass
2. Write failing tests (Story 2) → implement webhook guard → tests pass
3. Commit tests + implementation (two commits minimum)

## Key Constraints

- `rate_limiter` is already instantiated at the top of `webhook_handler` (line 232)
- `telegram_id` is extracted at line 589 — rate check inserts AFTER line 599 (is_command check)
- Return type must be `JSONResponse` not `WebhookResponse` for 429 (different status code)
- `retry_after_seconds` from `RateLimitResult` maps to `retry_after` in response body

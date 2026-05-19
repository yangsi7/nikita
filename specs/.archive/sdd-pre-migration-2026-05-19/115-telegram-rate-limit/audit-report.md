# Audit Report — Spec 115: Telegram Webhook Per-User Rate Limiting

## Status: PASS

## Validator Results

### Frontend Validator — N/A
No UI changes. Skipped.

### Architecture Validator — PASS
- Rate limiter created once per router instance (closure variable) — correct singleton pattern
- `RateLimiter` / `InMemoryCache` / `get_shared_cache` correctly separated into `platforms/telegram/rate_limiter.py`
- No circular imports; dependency direction is correct (routes → platforms)

### Data Layer Validator — PASS
- `InMemoryCache` used for MVP (documented as non-persistent, single-instance)
- `DatabaseRateLimiter` stub ready for production promotion (persists across Cloud Run instances)
- No DB schema changes required for current implementation

### Auth Validator — PASS
- Rate limit applied AFTER webhook secret validation (SEC-01 not bypassed)
- Commands (`/start`, `/help`, etc.) correctly exempt per FR-003
- `telegram_id` guard prevents rate check on updates without a sender

### Testing Validator — PASS
- Story 1 (rate_limiter.py): 13 tests covering all AC (FR-006-001/002/003, T024.1-4)
- Story 2 (telegram.py webhook): 3 tests covering FR-001/003/004
- `TestCheckByTelegramId`: 4 tests covering FR-002
- All 17 tests GREEN
- TDD sequence followed: RED commit → GREEN commit
- `clear_dedup_cache` autouse fixture prevents cross-test pollution from module-level `_UPDATE_ID_CACHE`

### API Validator — PASS
- Returns HTTP 429 with `{"error": "rate_limit_exceeded", "retry_after": N}` body
- `retry_after_seconds` sourced from `RateLimitResult` (60s for minute limit, seconds-until-midnight for day limit)
- Commands exempt before rate check, dedup check before rate check
- Logging: `[RATE_LIMIT]` warning on blocked requests

## Acceptance Criteria Verification

| AC | Criterion | Status |
|----|-----------|--------|
| FR-001 | Webhook returns 429 when rate limit exceeded | ✅ |
| FR-002 | `check_by_telegram_id(telegram_id: int)` method using synthetic UUID | ✅ |
| FR-003 | Commands (`/...`) exempt from rate limiting | ✅ |
| FR-004 | 429 body includes `retry_after` seconds | ✅ |
| FR-005 | Rate limit: 20/min, 500/day | ✅ (RateLimiter constants) |
| FR-006 | Warning at 450/500 threshold | ✅ (warning_threshold_reached flag) |

## Files Changed

| File | Change |
|------|--------|
| `nikita/platforms/telegram/rate_limiter.py` | Added `check_by_telegram_id()` method |
| `nikita/api/routes/telegram.py` | Added `webhook_rate_limiter` closure + 429 guard in `receive_webhook` |
| `tests/platforms/telegram/test_rate_limiter.py` | Story 1 tests (13 tests) |
| `tests/api/routes/test_telegram.py` | Story 2 tests (3 tests) + `clear_dedup_cache` fixture |

## Known Limitations (Documented)

- `InMemoryCache` does not persist across Cloud Run restarts or instances
- Multi-instance deployments require `DatabaseRateLimiter` (implementation ready, not wired)
- BKD-007 comment added in `telegram.py` documenting per-process dedup limitation

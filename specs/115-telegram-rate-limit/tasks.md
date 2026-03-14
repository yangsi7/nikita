# Tasks — Spec 115: Telegram Webhook Per-User Rate Limiting

## Story 1: check_by_telegram_id in RateLimiter

- [ ] T1: Write failing tests for `check_by_telegram_id` in `tests/platforms/test_rate_limiter.py`
  - allowed case, minute_exceeded case, day_exceeded case
- [ ] T2: Implement `check_by_telegram_id(telegram_id: int)` in `rate_limiter.py`
- [ ] T3: Run Story 1 tests — all pass

## Story 2: Webhook 429 guard

- [ ] T4: Write failing tests for 429 path in `tests/api/routes/test_telegram.py`
  - rate_limited returns 429, commands exempt, allowed proceeds
- [ ] T5: Implement rate check in `telegram.py` webhook handler
- [ ] T6: Run Story 2 tests — all pass

## Commit sequence

1. `test(telegram): Spec 115 — rate limiter + webhook 429 tests (RED)`
2. `feat(telegram): Spec 115 — per-user webhook rate limiting (GREEN)`

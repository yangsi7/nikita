## API Validation Report

**Spec:** specs/115-telegram-rate-limit/spec.md + plan.md
**Status:** FAIL
**Timestamp:** 2026-03-14T12:00:00Z

### Summary
- CRITICAL: 1
- HIGH: 3
- MEDIUM: 3
- LOW: 2

### Findings

| # | Severity | Category | Issue | Location | Recommendation |
|---|----------|----------|-------|----------|----------------|
| 1 | CRITICAL | Response Semantics | HTTP 429 will cause Telegram to retry the webhook, creating a retry storm. Telegram treats any non-2xx response as a delivery failure and retries with exponential backoff (up to ~60s). Returning 429 means Telegram will re-send the same update repeatedly, each retry hitting the already-exceeded rate limit and generating more 429s. The update is never acknowledged. | spec.md:21, spec.md:31 | Return HTTP 200 with `{"ok": true}` to acknowledge the webhook, but **skip processing** (do not schedule background task). Log the rate-limit event. The user-facing throttle message can optionally be sent via `bot.send_message()` in a fire-and-forget call. This matches the existing pattern at message_handler.py:238-242 where rate-limited requests `return` (ack'd, not processed). |
| 2 | HIGH | Response Format | Spec omits `Retry-After` HTTP header (only includes it in JSON body). RFC 6585 Section 4 states 429 responses SHOULD include a `Retry-After` header. The codebase already uses `headers={"Retry-After": "60"}` in admin.py:330,336. | spec.md:43-45, plan.md:29 | If 429 is retained (see finding #1), add `headers={"Retry-After": str(retry_after)}` to the `JSONResponse`. However, per finding #1, the correct fix is to return 200 and not use 429 at all for Telegram webhooks. |
| 3 | HIGH | Dependency Access | `rate_limiter` is not available in `receive_webhook()`. It is instantiated inside `build_message_handler()` (line 232) and passed to `MessageHandler` -- it is NOT a FastAPI dependency or accessible in the webhook handler scope. The plan assumes it can be called at line 599, but no `rate_limiter` variable exists in that scope. | plan.md:49-50 | Either (a) create a new FastAPI dependency `get_rate_limiter()` that returns `RateLimiter(cache=get_shared_cache())`, add it to the webhook handler signature, or (b) instantiate a module-level `_rate_limiter = RateLimiter(cache=get_shared_cache())` singleton inside `create_telegram_router()` closure scope (accessible to `receive_webhook` as a closure variable). Option (b) is simpler and consistent with the singleton `get_shared_cache()` pattern. |
| 4 | HIGH | Double Rate-Count | If the pre-pipeline check calls `check_by_telegram_id()` (which internally calls `check()` which calls `cache.incr()`), and the message is allowed through, `MessageHandler.handle()` at line 238 calls `rate_limiter.check(user.id)` again -- incrementing counters a second time for the same message. The telegram_id-based key and UUID-based key will be different cache keys, so both counters increment independently, but the effective limit drops to ~10/min (each message costs 2 increments on different keys). | plan.md:10-11, message_handler.py:238 | The spec should explicitly state whether the existing `MessageHandler` rate check is removed or kept. Recommended: remove the check at message_handler.py:235-242 (move it to webhook level only) to avoid double-counting. The `check_by_telegram_id` at webhook level replaces it. Document this in spec.md under "Files Modified". |
| 5 | MEDIUM | Callback Query Gap | Rate limiting only covers `message` updates (text). `callback_query` updates (onboarding button presses, lines 557-580) are dispatched to background tasks without any rate check. A user could spam callback buttons to exhaust pipeline resources. | telegram.py:557-580, spec.md (not addressed) | Add a note in spec.md "Out of Scope" acknowledging callback_query rate limiting, or add it to the rate check scope. Callback queries are low-risk (onboarding only, idempotent) so "Out of Scope" is acceptable, but should be documented. |
| 6 | MEDIUM | Command Exemption Scope | FR-003 says commands are exempt from per-minute but subject to daily limit. However, the plan code block (plan.md:24-25) shows `if telegram_id and not is_command: result = await rate_limiter.check_by_telegram_id(...)` which skips commands entirely from both per-minute AND daily checks. The `check_by_telegram_id` method increments both counters atomically -- there is no way to check daily-only without also incrementing the minute counter. | spec.md:39-40, plan.md:24-25, rate_limiter.py:144-146 | Either (a) change FR-003 to "commands are exempt from all rate limits" (simplest, matches plan code), or (b) add a `check_daily_only(telegram_id)` method that only increments/checks the day counter. Option (a) is recommended -- commands are rare (/start, /help) and should not count toward any limit. |
| 7 | MEDIUM | UUID Conversion Fragility | Plan proposes `UUID(int=telegram_id % (2**128))` to convert telegram_id to UUID for reusing existing cache logic. This is a lossy modulo operation (telegram_ids are ~10 digits, so no collision in practice, but the modulo is unnecessary and confusing). More importantly, it creates a DIFFERENT cache key than `user.id` (the real UUID), meaning the webhook-level check and the MessageHandler-level check (if both remain) use separate counters. | plan.md:10-11, rate_limiter.py:221-228 | Use `str(telegram_id)` as the cache key directly instead of converting to UUID. Add `check_by_telegram_id()` with its own key format like `rate:{telegram_id}:minute` (string-based). This avoids the UUID conversion entirely and makes the cache key semantics clear. If the MessageHandler check is removed (see finding #4), there is no need to share key format with UUID-based `check()`. |
| 8 | LOW | Test File Path | Spec lists test file as `tests/platforms/test_rate_limiter.py` but existing rate_limiter tests may be in `tests/platforms/telegram/test_rate_limiter.py` (following the module structure convention). | spec.md:70 | Verify existing test file location. Use `tests/platforms/telegram/test_rate_limiter.py` to match the `nikita/platforms/telegram/rate_limiter.py` module path. |
| 9 | LOW | Logging Format | FR-005 specifies `logger.warning("[RATE_LIMIT] telegram_id=%d reason=%s retry_after=%d", ...)` using printf-style formatting, which is correct for structured logging. However, the rest of the codebase (telegram.py) uses f-strings for logging (`f"[LLM-DEBUG] ..."`, `f"[ROUTING] ..."`). | spec.md:51, telegram.py:593-596 | Minor inconsistency. Either format is acceptable, but printf-style is technically preferred for logging (avoids string interpolation when log level is filtered). No change required, but note the divergence from codebase convention. |

### API Inventory

| Method | Endpoint | Purpose | Auth | Request | Response |
|--------|----------|---------|------|---------|----------|
| POST | /telegram/webhook | Receive Telegram updates | Telegram signature (X-Telegram-Bot-Api-Secret-Token) | TelegramUpdate (Pydantic) | WebhookResponse `{"status": "ok"}` or 429 JSONResponse (proposed) |

No new endpoints are introduced by this spec. The change is an inline guard within the existing webhook handler.

### Server Actions

N/A -- this is a Python/FastAPI backend spec, no Next.js server actions involved.

### Request/Response Schemas

**Existing (unchanged):**
```python
class WebhookResponse(BaseModel):
    status: str = "ok"
```

**Proposed 429 response (spec FR-004):**
```python
JSONResponse(
    status_code=429,
    content={"error": "rate_limit_exceeded", "retry_after": 60},
    # MISSING: headers={"Retry-After": "60"}
)
```

**Proposed new method:**
```python
class RateLimiter:
    async def check_by_telegram_id(self, telegram_id: int) -> RateLimitResult:
        """Check rate limit using telegram_id as key."""
        ...
```

**Existing RateLimitResult dataclass (unchanged):**
```python
@dataclass
class RateLimitResult:
    allowed: bool
    reason: Optional[str] = None
    minute_remaining: Optional[int] = None
    day_remaining: Optional[int] = None
    retry_after_seconds: Optional[int] = None
    warning_threshold_reached: bool = False
```

### Error Code Inventory

| Code | Status | Description | User Message |
|------|--------|-------------|-------------|
| rate_limit_exceeded | 429 (proposed) / 200 (recommended) | User exceeded per-minute or daily message limit | Telegram ignores body; user sees nothing (or optional in-character message via bot.send_message) |

### Recommendations

1. **CRITICAL (Finding #1): Do NOT return HTTP 429 to Telegram webhooks.** Telegram treats any non-2xx as a failed delivery and will retry the update with exponential backoff. This creates a retry storm where every retry hits the rate limit again, the update is never acknowledged, and Telegram eventually stops sending ALL updates to the webhook for increasing durations (up to hours). The correct pattern is: return HTTP 200 to acknowledge receipt, skip the background task dispatch, and optionally send the user a rate-limit message via `bot.send_message()`. This matches the existing `MessageHandler` pattern (line 238-242) where rate-limited requests simply `return` without processing.

2. **HIGH (Finding #3): Create a `rate_limiter` accessible in webhook scope.** The simplest approach is to instantiate it as a closure variable inside `create_telegram_router()`:
   ```python
   def create_telegram_router(bot: TelegramBot) -> APIRouter:
       router = APIRouter()
       _rate_limiter = RateLimiter(cache=get_shared_cache())
       # ... _rate_limiter is now accessible in receive_webhook via closure
   ```

3. **HIGH (Finding #4): Remove the duplicate rate check in MessageHandler.** Once the webhook-level check is in place, the check at `message_handler.py:235-242` becomes redundant and causes double-counting. Remove it and document the removal in spec.md "Files Modified" table.

4. **HIGH (Finding #2): If 429 is still used for non-Telegram callers, always include `Retry-After` header.** Follow the pattern established in `admin.py:330`.

5. **MEDIUM (Finding #6): Simplify FR-003 to "commands exempt from all rate limits."** The atomic counter design of `RateLimiter.check()` does not support per-minute-only exemption without a new method. Commands are rare enough that daily-limit exemption is harmless.

6. **MEDIUM (Finding #7): Use string-based cache keys for telegram_id.** Drop the `UUID(int=telegram_id % 2**128)` conversion. Use `f"rate:tg:{telegram_id}:minute"` and `f"rate:tg:{telegram_id}:day:{date}"` directly.

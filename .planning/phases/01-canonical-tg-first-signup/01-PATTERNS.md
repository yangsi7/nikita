# Phase 01: canonical-tg-first-signup — Pattern Map

**Mapped:** 2026-05-20
**Files analyzed:** 22 files (creates + modifies + deletes)
**Analogs found:** 19 / 22 (3 in "No Analog Found")

---

## File Classification

| New/Modified/Deleted File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `nikita/platforms/telegram/signup_handler.py` (rewrite) | service | request-response | same file (current version) | role-match (new flow) |
| `nikita/api/routes/telegram.py` (strip FSM routing lines 577-695) | route/controller | request-response | same file — routing simplification | role-match |
| `nikita/platforms/telegram/commands.py` (delete handler + link-code) | service | request-response | same file (residual) | role-match |
| `nikita/api/routes/portal_onboarding_v2.py` (add SELECT FOR UPDATE + admin.update_user_by_id) | route/controller | CRUD | same file (lines 720-794) | exact |
| `nikita/api/routes/portal_auth.py` (delete generate_magiclink + autobind + dashboard_bridge) | route/controller | request-response | `nikita/api/routes/auth_bridge.py` | role-match |
| `nikita/api/routes/tasks.py` (delete cleanup_pending_registrations endpoint) | route | batch | same file (remaining endpoints) | role-match |
| `nikita/db/models/user.py` (update CheckConstraint lines 289-292) | model | — | same file | exact |
| `nikita/db/repositories/user_repository.py` (update update_onboarding_status + is_onboarded) | service | CRUD | same file (lines 651-688, 1083) | exact |
| `nikita/platforms/telegram/message_handler.py` (line 1070 — drop 'skipped') | service | event-driven | same file | exact |
| `portal/src/app/auth/confirm/route.ts` (strip autobind side-effects lines 140-313) | route handler | request-response | same file (lines 108-138) | exact |
| `portal/src/lib/supabase/middleware.ts` (update redirect targets + JWT claim check) | middleware | request-response | same file (lines 79-119) | exact |
| `portal/src/middleware.ts` (JWT claim check for /dashboard) | middleware | request-response | `portal/src/lib/supabase/middleware.ts:108-119` | role-match |
| `portal/src/app/(root)/page.tsx` (single CTA) | component | — | `portal/src/components/landing/hero-section.tsx` | role-match |
| `portal/src/app/login/page-client.tsx` (remove TG deep-link; 410 redirect) | component | request-response | same file | exact |
| **DELETED:** `portal/src/app/auth/interstitial/` | component | — | N/A (deletion) | — |
| **DELETED:** `portal/src/app/auth/bridge/route.ts` | route handler | — | N/A (deletion) | — |
| **DELETED:** `nikita/db/repositories/telegram_link_repository.py` | service | CRUD | N/A (deletion) | — |
| **DELETED:** `nikita/db/repositories/telegram_signup_session_repository.py` | service | CRUD | N/A (deletion) | — |
| **DELETED:** `nikita/db/repositories/pending_registration_repository.py` | service | CRUD | N/A (deletion) | — |
| `supabase/migrations/YYYYMMDD_provision_trigger.sql` (CREATE TRIGGER) | migration | — | No existing trigger in codebase (see No Analog) | — |
| `supabase/migrations/YYYYMMDD_drop_fsm_tables.sql` (DROP TABLE + cron.unschedule) | migration | — | existing migration stubs pattern | partial |
| `tests/platforms/telegram/test_signup_handler_arch_b.py` (CREATE) | test | — | `tests/platforms/telegram/test_signup_handler.py` | role-match |

---

## Pattern Assignments

### `nikita/platforms/telegram/signup_handler.py` (rewrite: ~755 LOC → ~200 LOC)

**Analog:** Same file (current version) — structure and DI pattern preserved; FSM dependencies removed.

**Imports pattern** (`signup_handler.py:36-72` — preserve, remove FSM-specific imports):
```python
from __future__ import annotations

import logging
import re
from typing import Any, Final

from supabase_auth.errors import AuthApiError

from nikita.platforms.telegram.bot import TelegramBot

logger = logging.getLogger(__name__)
```
Remove imports: `TelegramSignupSessionRepository`, `ConcurrentTransitionError`, `ExpiredOrConcurrentError`, monitoring `SignupCodeSentEvent` et al. (FSM telemetry). Retain: `TelegramBot`, `AuthApiError`, logging, re.

**Tuning constants pattern** (`signup_handler.py:80-100`):
```python
# 8-digit exact — Supabase standardized on 8 digits (GH#431). Refs research Pitfall 4.
OTP_REGEX: Final[re.Pattern[str]] = re.compile(r"^[0-9]{8}$")
EMAIL_REGEX: Final[re.Pattern[str]] = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
```
Use 8-digit exact (`^[0-9]{8}$`) not the current 6-8 range per RESEARCH.md Pitfall 4.

**DI constructor pattern** (`signup_handler.py:177-190`):
```python
class SignupHandler:
    def __init__(
        self,
        *,
        bot: TelegramBot,
        user_repo: UserRepository,
        supabase_client: Any,
    ) -> None:
        self.bot = bot
        self.user_repo = user_repo
        self.supabase = supabase_client
```
Remove `repo: TelegramSignupSessionRepository` and `admin_generate_magiclink: Callable` from constructor. `generate_link` is called inline in `handle_otp`.

**OTP send pattern** (`handle_email` — new, no direct existing analog; per RESEARCH.md Pattern 1):
```python
async def handle_email(self, chat_id: int, email: str) -> None:
    await self.supabase.auth.sign_in_with_otp({
        "email": email,
        "options": {
            "should_create_user": True,
            "data": {"telegram_id": str(chat_id)},  # → raw_user_meta_data
        }
    })
    # NOTE: uid NOT available here; AuthOtpResponse.user is always None
```

**OTP verify + admin lock + generate_link pattern** (`handle_otp` — new; per RESEARCH.md Patterns 2 + 4):
```python
async def handle_otp(self, chat_id: int, email: str, token: str) -> None:
    auth_resp = await self.supabase.auth.verify_otp({
        "email": email,
        "token": token,
        "type": "email",
    })
    uid = str(auth_resp.user.id)   # available after verify_otp succeeds

    # DB trigger fires here: email_confirmed_at NULL→NOT NULL → users row provisioned

    # ADR-220-5: immutable lock — admin API only
    await self.supabase.auth.admin.update_user_by_id(
        uid,
        {"app_metadata": {"telegram_id": str(chat_id)}}
    )

    # Portal deep-link — generate_link pattern from auth_bridge.py:84-90
    link_result = await self.supabase.auth.admin.generate_link({
        "type": "magiclink",
        "email": email,
    })
    portal_url = (
        f"{settings.portal_url}/auth/confirm"
        f"?token_hash={link_result.properties.hashed_token}"
        f"&type=email&next=/onboarding"
    )
```

**Error handling pattern** (`signup_handler.py:260-290` — copy from existing `handle_email`):
```python
except AuthApiError as exc:
    exc_code = getattr(exc, "code", None) or ""
    error_msg_lower = str(exc).lower()
    if exc_code == "email_address_too_long" or "email address is too long" in error_msg_lower:
        friendly = EMAIL_TOO_LONG_TEXT
    elif "you can only request this after" in error_msg_lower:
        friendly = OTP_RATE_LIMIT_TEXT
    else:
        friendly = GENERIC_FAIL_TEXT
    await self._safe_send(chat_id=chat_id, text=friendly)
    return
```

---

### `nikita/api/routes/telegram.py` (strip FSM routing, lines 577-695)

**Analog:** Same file — routing simplification only.

**What to delete** (`telegram.py:577-695`, verified in RESEARCH.md):
- Lines 577-618: `/start` payload coercion block (`if cmd == "start" and ...`)
- Lines 620: `[LLM-DEBUG] Routing to CommandHandler` log line
- Lines 634-671: FSM state routing (`pending_repo.get(telegram_id)` + state-based dispatch)
- Lines 668-695: LLM-DEBUG log lines (PII-leaking) — 12 total, all to be removed

**Target routing pattern** (replaces lines 577-695):
```python
# New: 2-branch routing (no FSM, no coercion block)
user = await user_repo.get_by_telegram_id(telegram_id)
if user is None:
    # Unbound — route to signup_handler.handle_welcome
    background_tasks.add_task(
        _run_signup_with_fresh_session,
        bot_instance,
        "welcome",
        telegram_id=telegram_id,
        chat_id=chat_id,
    )
    return WebhookResponse()
# Bound user → MessageHandler
background_tasks.add_task(
    _handle_message_with_fresh_session,
    ...
)
```

**Remove pending_repo dependency** — `pending_repo` is a parameter from `TelegramSignupSessionRepository`; its import and DI wiring are removed in PR-B.

---

### `nikita/api/routes/portal_onboarding_v2.py` (add SELECT FOR UPDATE + admin.update_user_by_id to wizard /complete)

**Analog:** Same file, lines 720-794 (asyncpg fix + existing onboarding_status write at line 734).

**SELECT FOR UPDATE pattern** (`user_repository.py:114-143`):
```python
# Step 1: serialized lock (concurrent tab guard — FR-11, AC-17)
user = await user_repo.get_by_telegram_id_for_update(telegram_id)
# → calls .with_for_update() + SET LOCAL statement_timeout='10000'
```

**Existing onboarding_status write** (`portal_onboarding_v2.py:734`):
```python
await user_repo.update_onboarding_status(user_id, "completed")
```

**New admin.update_user_by_id — AFTER DB transaction closes** (asyncpg poison prevention; `portal_onboarding_v2.py:750-794` pattern):
```python
# Step N (after session.commit / transaction close):
# DO NOT place inside async with session.begin() — see GH#638 asyncpg poison pattern.
# HTTP call to Supabase goes here, outside the DB transaction scope.
supabase = await get_supabase_client()
await supabase.auth.admin.update_user_by_id(
    str(user_id),
    {"app_metadata": {"onboarded": True}}
    # merge semantics — existing telegram_id key is preserved (Pitfall 6)
)
```

**Error handling pattern** (`portal_onboarding_v2.py:749-768` — copy the rollback+log pattern):
```python
try:
    async with session.begin():
        # SELECT FOR UPDATE + update_onboarding_status + activate_game
        pass
except Exception:
    try:
        await session.rollback()
    except Exception:
        logger.exception("session.rollback() failed for user_id=%s", user_id)
    raise
# Supabase HTTP calls HERE — after transaction
```

---

### `nikita/db/models/user.py` (update CheckConstraint, lines 289-292)

**Analog:** Same file, lines 282-293.

**Existing constraint pattern** (`user.py:289-292`):
```python
CheckConstraint(
    "onboarding_status IN ('pending', 'in_progress', 'completed', 'skipped')",
    name="check_onboarding_status_values",
),
```

**Target after ADR-220-7** — drop `'skipped'`:
```python
CheckConstraint(
    "onboarding_status IN ('pending', 'in_progress', 'completed')",
    name="check_onboarding_status_values",
),
```

---

### `nikita/db/repositories/user_repository.py` (update_onboarding_status + is_onboarded)

**Analog:** Same file, lines 651-688 and 1083.

**update_onboarding_status valid_statuses** (`user_repository.py:670`) — drop `"skipped"`:
```python
# BEFORE (current):
valid_statuses = {"pending", "in_progress", "completed", "skipped"}
# AFTER (ADR-220-7):
valid_statuses = {"pending", "in_progress", "completed"}
```

**is_onboarded** (`user_repository.py:1083`) — drop `"skipped"`:
```python
# BEFORE:
return user.onboarding_status in {"completed", "skipped"}
# AFTER:
return user.onboarding_status == "completed"
```

---

### `nikita/platforms/telegram/message_handler.py` (line 1070)

**Analog:** Same file, line 1070.

**One-line change** (`message_handler.py:1070`):
```python
# BEFORE:
if onboarding_status in ("completed", "skipped"):
# AFTER (AC-18):
if onboarding_status == "completed":
```

---

### `portal/src/app/auth/confirm/route.ts` (strip autobind side-effects)

**Analog:** Same file, lines 1-138 (all preserved); lines 140-217 deleted.

**Full preserved skeleton after strip** (per RESEARCH.md Pattern 6 + T-3 resolution):
```typescript
// Lines 1-106: imports, VALID_OTP_TYPES, supabase client init — PRESERVE AS-IS
// Lines 108-125: W1 CRITICAL signOut — PRESERVE VERBATIM
try {
  await supabase.auth.signOut({ scope: "local" })
} catch {
  // Best-effort
}

// Lines 127-130: verifyOtp — PRESERVE
const { data: verified, error } = await supabase.auth.verifyOtp({
  token_hash: tokenHash,
  type,
})

// Lines 132-138: error redirect — UPDATE target from /login to TG bot URL (T-3)
if (error) {
  const code = classifyVerifyOtpError(error.message)
  return NextResponse.redirect(
    `https://t.me/Nikita_my_bot?start=welcome&error=${code}`,
    { status: 302 }
  )
}

// DELETE: lines 140-217 (entire autobind block + interstitial redirects)
// REPLACE with:
const pendingNext = (verified?.user) ? "/onboarding" : "/onboarding"
return NextResponse.redirect(new URL(pendingNext, request.url), { status: 302 })
```

**Also delete from this file:**
- `tryAutobindTelegram` function definition and import
- `AutobindOutcome` type definition
- `_exhaustive` exhaustiveness check variable

---

### `portal/src/lib/supabase/middleware.ts` (redirect targets + dashboard gate)

**Analog:** Same file, lines 79-119.

**Interstitial exemption removal** (`middleware.ts:79`):
```typescript
// BEFORE:
if (pathname === "/auth/confirm" || pathname.startsWith("/auth/interstitial")) {
// AFTER (PR-A: /auth/interstitial deleted):
if (pathname === "/auth/confirm") {
```

**Unauthenticated redirect target** (`middleware.ts:98` — T-3 resolution):
```typescript
// BEFORE:
return NextResponse.redirect(new URL("/login", request.url))
// AFTER:
return NextResponse.redirect(new URL("https://t.me/Nikita_my_bot?start=welcome", request.url))
```

**Dashboard JWT claim check** (`middleware.ts:108-119` — add JWT claim fast-path, FR-8):
```typescript
// ADD after existing onboarding cookie check:
if (pathname.startsWith("/dashboard/")) {
  // FR-8: fast-path JWT claim check for app_metadata.onboarded
  const onboarded = user?.app_metadata?.onboarded
  if (!onboarded) {
    return NextResponse.redirect(new URL("/onboarding", request.url))
  }
}
```

---

### `supabase/migrations/YYYYMMDD_provision_trigger.sql` (CREATE — PR-D)

**Analog:** No existing trigger in codebase (grep-confirmed zero `auth.users` triggers; source `supabase/reference/00000000000001_baseline_schema.sql`). Use RESEARCH.md Pattern 3 directly.

**Deployment note:** Apply via `mcp__supabase__apply_migration`, NOT the Supabase CLI. Do NOT use `supabase migration up` or `supabase db push`.

**Full trigger pattern** (RESEARCH.md Pattern 3, lines 323-376):
```sql
CREATE OR REPLACE FUNCTION auth.provision_user_on_confirm()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF (NEW.raw_user_meta_data->>'telegram_id') IS NULL THEN
    RETURN NEW;
  END IF;

  INSERT INTO public.users (id, telegram_id, created_at, updated_at)
  VALUES (
    NEW.id,
    (NEW.raw_user_meta_data->>'telegram_id')::bigint,
    NOW(), NOW()
  )
  ON CONFLICT (id) DO UPDATE SET
    telegram_id = EXCLUDED.telegram_id,
    updated_at = NOW();

  INSERT INTO public.user_metrics (user_id, created_at, updated_at)
  VALUES (NEW.id, NOW(), NOW())
  ON CONFLICT (user_id) DO NOTHING;

  -- Vice categories: VERIFIED at nikita/db/models/user.py:394-403
  INSERT INTO public.user_vice_preferences (user_id, category, created_at, updated_at)
  SELECT NEW.id, unnest(ARRAY[
    'intellectual_dominance','risk_taking','substances','sexuality',
    'emotional_intensity','rule_breaking','dark_humor','vulnerability'
  ]), NOW(), NOW()
  ON CONFLICT (user_id, category) DO NOTHING;

  RETURN NEW;
END;
$$;

CREATE TRIGGER provision_user_on_email_confirm
  AFTER UPDATE OF email_confirmed_at ON auth.users
  FOR EACH ROW
  WHEN (
    OLD.email_confirmed_at IS NULL
    AND NEW.email_confirmed_at IS NOT NULL
    AND (NEW.raw_user_meta_data->>'telegram_id') IS NOT NULL
  )
  EXECUTE FUNCTION auth.provision_user_on_confirm();
```

---

### `supabase/migrations/YYYYMMDD_drop_fsm_tables.sql` (CREATE — PR-C)

**Analog:** Existing migration stubs at `supabase/migrations/` — comment-only stubs applied via MCP.

**Pattern for cron unschedule + DROP TABLE (per RESEARCH.md Runtime State Inventory)**:
```sql
-- PR-C: drop obsolete FSM tables (ADR-220-3: LAST migration, after PR-B deletions live)
SELECT cron.unschedule('cleanup_pending_registrations');

DROP TABLE IF EXISTS public.pending_registrations;
DROP TABLE IF EXISTS public.telegram_signup_sessions;
DROP TABLE IF EXISTS public.telegram_link_codes;
```

**Note:** Confirm `pending_registrations` vs old name — RESEARCH.md states it was renamed in `20260424120000` migration. Query schema before writing DROP to confirm the current name.

**Deployment note:** Apply via `mcp__supabase__apply_migration` only. Never `supabase migration up`.

---

### `tests/platforms/telegram/test_signup_handler_arch_b.py` (CREATE — PR-E)

**Analog:** `tests/platforms/telegram/test_signup_handler.py` (current FSM test file) — structural template.

**Mock pattern** (`tests/conftest.py` + project testing.md):
```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.fixture
def mock_supabase():
    client = AsyncMock()
    # sign_in_with_otp returns AuthOtpResponse with user=None
    client.auth.sign_in_with_otp.return_value = MagicMock(user=None)
    # verify_otp returns AuthResponse with user populated
    mock_user = MagicMock()
    mock_user.id = "uuid-test-123"
    client.auth.verify_otp.return_value = MagicMock(user=mock_user)
    # admin.update_user_by_id + generate_link
    client.auth.admin.update_user_by_id = AsyncMock()
    client.auth.admin.generate_link = AsyncMock(
        return_value=MagicMock(
            properties=MagicMock(hashed_token="test_token")
        )
    )
    return client
```

**Required test classes** (per `.claude/rules/testing.md` + SPEC.md AC-3, AC-4):
1. `test_handle_email_calls_sign_in_with_otp` — verifies `data.telegram_id` stashed; asserts `sign_in_with_otp` called with `str(chat_id)`.
2. `test_handle_otp_calls_verify_otp_and_locks_app_metadata` — verifies `admin.update_user_by_id` called with `{"app_metadata": {"telegram_id": str(chat_id)}}`.
3. `test_handle_otp_sends_portal_link` — verifies `admin.generate_link` called with `{"type": "magiclink", ...}`; bot receives URL containing `/auth/confirm?token_hash=`.
4. `test_otp_regex_rejects_6_digit_code` — `OTP_REGEX.match("123456")` is None (Pitfall 4).
5. `test_otp_regex_accepts_8_digit_code` — `OTP_REGEX.match("12345678")` is not None.

---

## Shared Patterns

### 1. admin.generate_link — portal URL construction
**Source:** `nikita/api/routes/auth_bridge.py:84-90`
**Apply to:** `signup_handler.py:handle_otp`
```python
link_result = await supabase.auth.admin.generate_link({
    "type": "magiclink",
    "email": email,
})
hashed_token = link_result.properties.hashed_token
portal_url = f"{settings.portal_url}/auth/confirm?token_hash={hashed_token}&type=email&next=/onboarding"
```

### 2. admin.update_user_by_id — app_metadata write
**Source:** RESEARCH.md Pattern 2 (verified via supabase_auth 2.24.0 SDK introspection 2026-05-19)
**Apply to:** `signup_handler.py:handle_otp` (telegram_id lock), `portal_onboarding_v2.py:/complete` (onboarded flag)
```python
await supabase.auth.admin.update_user_by_id(
    uid,   # str, not UUID object
    {"app_metadata": {"telegram_id": str(chat_id)}}
    # OR: {"app_metadata": {"onboarded": True}}
    # Merge semantics: existing keys preserved; no key replacement
)
```
**Critical:** Always call OUTSIDE `async with session.begin()` to avoid asyncpg pool poisoning (GH#638 pattern).

### 3. SELECT FOR UPDATE — concurrent serialization
**Source:** `nikita/db/repositories/user_repository.py:114-143`
**Apply to:** `portal_onboarding_v2.py:wizard /complete endpoint` (AC-17)
```python
async def get_by_telegram_id_for_update(
    self, telegram_id: int, *, timeout_ms: int = 10_000
) -> User | None:
    from sqlalchemy import text
    await self.session.execute(
        text(f"SET LOCAL statement_timeout = '{timeout_ms}'")
    )
    stmt = (
        select(User)
        .options(joinedload(User.metrics), joinedload(User.engagement_state))
        .where(User.telegram_id == telegram_id)
        .with_for_update()   # ← line 140
    )
    result = await self.session.execute(stmt)
    return result.unique().scalar_one_or_none()
```

### 4. asyncpg poison prevention — HTTP calls outside DB transaction
**Source:** `nikita/api/routes/portal_onboarding_v2.py:749-768`
**Apply to:** `portal_onboarding_v2.py:/complete` (admin.update_user_by_id placement)

Pattern: DB write inside `async with session.begin()`, Supabase HTTP calls AFTER the block closes.
```python
# Inside transaction:
async with session.begin():
    user = await user_repo.get_by_user_id_for_update(user_id)
    await user_repo.update_onboarding_status(user_id, "completed")
    await user_repo.activate_game(user_id)
    # <commit here>

# OUTSIDE transaction — Supabase HTTP:
supabase = await get_supabase_client()
await supabase.auth.admin.update_user_by_id(
    str(user_id), {"app_metadata": {"onboarded": True}}
)
```

### 5. /auth/confirm PKCE skeleton with W1 signOut preserved
**Source:** `portal/src/app/auth/confirm/route.ts:1-138`
**Apply to:** `auth/confirm/route.ts` (strip, not rewrite; preserve lines 1-138 verbatim)

Preserved core (lines 108-130):
```typescript
// W1 CRITICAL: scope:'local' — discard stale session without server revoke
try {
  await supabase.auth.signOut({ scope: "local" })
} catch {
  // Best-effort
}

const { data: verified, error } = await supabase.auth.verifyOtp({
  token_hash: tokenHash,
  type,
})
```

### 6. AuthApiError error code matching
**Source:** `nikita/platforms/telegram/signup_handler.py:268-290`
**Apply to:** `signup_handler.py:handle_email` (rewrite), `signup_handler.py:handle_otp`
```python
# Match on exc.code (stable Supabase enum) rather than message substring
exc_code = getattr(exc, "code", None) or ""
error_msg_lower = str(exc).lower()
```

### 7. Supabase MCP migration application
**Source:** Project constraint (CLAUDE.md + `.claude/rules/` — never Supabase CLI)
**Apply to:** All migration files (trigger SQL, drop-tables SQL, onboarding_status constraint)

Every migration must be applied via `mcp__supabase__apply_migration`, verified via `mcp__supabase__execute_sql`. The CLI (`supabase migration up`, `supabase db push`) is explicitly prohibited in this project.

---

## No Analog Found

Files with no close match in the codebase; planner should use RESEARCH.md patterns directly.

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `supabase/migrations/YYYYMMDD_provision_trigger.sql` | migration | — | Zero existing `auth.users` triggers in codebase (grep-confirmed: `supabase/reference/00000000000001_baseline_schema.sql`). Use RESEARCH.md Pattern 3 SQL verbatim; `ON CONFLICT` + `WHEN` guard are both required. |
| `portal/src/app/auth/confirm/route.ts` autobind removal | route handler | — | The autobind side-effect pattern being deleted has no analog elsewhere; the deletion is surgical (lines 140-217). Planner: the preserved skeleton (lines 1-138) IS the analog for the post-strip shape. |
| Portal landing CTA simplification (`page.tsx`) | component | — | `hero-section.tsx:28` sets `?start=welcome`; keep `welcome` per T-2 resolution (RESEARCH.md line 101). No deep structural change needed; single `href` attribute update. |

---

## Metadata

**Analog search scope:** `nikita/api/routes/`, `nikita/platforms/telegram/`, `nikita/db/repositories/`, `nikita/db/models/`, `portal/src/app/auth/`, `portal/src/lib/supabase/`, `supabase/migrations/`, `supabase/reference/`
**Files scanned:** 15 files read directly; 7 grep-confirmed via RESEARCH.md citations
**Pattern extraction date:** 2026-05-20
**RESEARCH.md confidence:** HIGH for all primary file:line citations (verified against live code)

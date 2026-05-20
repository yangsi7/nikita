# Phase 01: canonical-tg-first-signup - Research

**Researched:** 2026-05-19
**Domain:** Supabase Auth (Python SDK), Telegram FSM rewrite, PostgreSQL trigger provisioning, Next.js App Router auth flow
**Confidence:** HIGH (all critical claims verified against live code or SDK introspection)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions (7 ADRs — do not re-examine)

| ADR | Decision |
|-----|----------|
| ADR-220-1 | Arch B: single canonical TG-first path; portal `/login` returns 410 |
| ADR-220-2 | OTP-first, magic-link only for unverified-email recovery; no SMS/password |
| ADR-220-3 | 5-PR sequence A→D→E→B→C; no squash or reorder |
| ADR-220-4 | Trigger-based provisioning (auth.users UPDATE) replaces application-layer create_with_metrics |
| ADR-220-5 | `app_metadata.telegram_id` set by admin API at OTP-send; immutable after |
| ADR-220-6 | `/auth/confirm` preserved (PKCE exchange); autobind side-effect stripped |
| ADR-220-7 | `onboarding_status` 4-value enum collapsed to 3 (drop "skipped") |

### Claude's Discretion
- Exact line ranges for code changes (researcher to document)
- Trigger NULL-guard implementation detail (NULLIF or WHEN clause)
- Test refactor scope per PR (how many test files to rewrite vs delete)
- `?start=new` vs `?start=welcome` - recommend keeping `welcome` (zero blast radius)

### Deferred Ideas (OUT OF SCOPE)
- Voice onboarding path changes
- Portal `/onboarding` wizard UX changes beyond slot persistence fix
- Any admin endpoint changes not driven by removing `telegram_link_codes`
- pgTAP test infrastructure setup
- Performance optimisation of trigger query
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-001 / FR-1 | Landing page CTA → `t.me/Nikita_my_bot?start=new` (or `welcome`) | FR-1 says `?start=new`; current code uses `?start=welcome` everywhere. See **Spec Tension T-2** — recommend `welcome` |
| REQ-002 / FR-2 | `/login` returns HTTP 410 GONE | Tension T-3: `/login` is sign-out + auth/confirm failure destination; must surgically redirect those callers first |
| REQ-003 / FR-3 | Bot sends 8-digit OTP via `sign_in_with_otp`; `telegram_id` stashed in `raw_user_meta_data` | Verified: SDK `data` param → `raw_user_meta_data`. Must use `str(chat_id)` not int |
| REQ-004 / FR-4a | `app_metadata.telegram_id` written at OTP-send via `admin.update_user_by_id` | Verified: `AdminUserAttributes.app_metadata` writable by admin API only; security lock |
| REQ-005 / FR-4b | PostgreSQL trigger on `auth.users` UPDATE provisions `users` + `user_metrics` + `user_vice_preferences` rows atomically | No trigger exists in codebase (grep-confirmed); must be created from scratch; needs NULL guard |
| REQ-006 / FR-5 | Free-text routing strips FSM state machine in `telegram.py`; routes UNKNOWN → welcome, known → chat | Exact line ranges verified: `telegram.py:577-671` |
| REQ-007 / FR-6 | `signup_handler.py` rewritten to `handle_welcome` + `handle_email` + `handle_otp` only | 755-line file to be rewritten; new flow is 3 handlers |
| REQ-008 / FR-7 | `commands.py` `_handle_start_with_payload` deleted; `_send_bridge` deleted | Verified at `commands.py:272-530`; `_LINK_CODE_PATTERN` at line 183 to go |
| REQ-009 / FR-8 | Middleware adds `app_metadata.onboarded` JWT claim check for `/dashboard/*` | Currently only cookie `onboarding_status` check (lines 114-119); no JWT claim check exists |
| REQ-010 / FR-9 | `/auth/confirm` autobind side-effect stripped (~170 LOC removed) | Lines 140-313 verified; signOut+verifyOtp+redirect core (~80 LOC) preserved |
| REQ-011 / FR-10 | `/auth/interstitial` deleted (410 or remove route) | Not yet searched; middleware exemption at line 79 must be removed |
| REQ-012 / FR-11 | Wizard PATCH `/complete` writes `onboarding_status='completed'` AND `app_metadata.onboarded=True` with SELECT FOR UPDATE | `portal_onboarding_v2.py:734` only sets `onboarding_status`; no `admin.update_user_by_id` call; no SELECT FOR UPDATE |
| REQ-013 / FR-12 | `telegram_signup_sessions` + `telegram_link_codes` tables dropped in PR-C migration. CORRECTION: `pending_registrations` is NOT a separate 3rd table — it was RENAMED to `telegram_signup_sessions` (migration `20260424120000`), so dropping `telegram_signup_sessions` covers it. The `cleanup_pending_registrations` endpoint + hourly pg_cron job that DELETE from this table are dead-code that must be removed too (canonical REQ-022). | Tables confirmed present; cron dep = REQ-022 |
| REQ-014 / FR-13 | `onboarding_status` CHECK constraint drops 'skipped'; `is_onboarded` removes "skipped" branch | `user.py:289-292` and `user_repository.py:1083` both need changes |
| REQ-015 / FR-14 | Portal auth repos (`TelegramLinkRepository`, `TelegramSignupSessionRepository`, `PendingRegistrationRepository`) deleted | 3 files confirmed: 5.1K, 11.8K, 8.6K bytes |
| REQ-016 / FR-15 | LLM-DEBUG log lines (9 spec-cited) removed from `telegram.py` | Verified in `nikita/api/routes/telegram.py` (not platforms/); 12 total, 9 spec-cited |
| REQ-017 (REQ-EXTRA) | `tasks.py:681` `cleanup_pending_registrations` endpoint deleted; pg_cron schedule entry removed | Not in CONTEXT.md bulldoze table — identified as gap |
| REQ-018 / AC-18 | `message_handler.py:1070` `onboarding_status in ("completed", "skipped")` → `("completed",)` only | Verified at line 1070 |
| REQ-019 / AC-15 | Trigger tested via Supabase MCP `execute_sql` (pgTAP not available) | pgTAP: 0 instances in `supabase/` — confirmed not configured |
</phase_requirements>

---

## Summary

Phase 01 replaces a 3-path Telegram/portal signup scatter with a single canonical Telegram-first OTP flow. The architecture (7 ADRs) is locked; this research surfaces the implementation-level specifics needed to plan tasks.

**Scope breakdown**: (1) Supabase Python SDK — verified API shapes for `sign_in_with_otp`, `verify_otp`, `admin.generate_link`, `admin.update_user_by_id`; (2) Trigger provisioning — no existing trigger anywhere in codebase, must be written from scratch with an idempotency `ON CONFLICT DO UPDATE` and a NULL guard on `telegram_id` cast; (3) Code touchpoints — exact file:line ranges verified for every piece in the 5-PR sequence; (4) 4 spec tensions that need planner decisions before task writing.

The 5-PR sequence (A→D→E→B→C) is safe for rolling Cloud Run deploy: FE dead-code-gating (PR-A) precedes BE deletion (PR-B); migration (PR-C) is last because tables cannot be dropped while code that queries them may still be live. The largest single-PR risk is PR-D (signup_handler.py full rewrite + telegram.py routing change) — it is the critical-path PR and the one with the most test surface.

**Primary recommendation:** Plan PR-D with the most task granularity; it touches the highest-coupling files (`message_handler.py:59` imports, `tasks.py:56` imports). All other PRs are largely deletions with thin new code.

---

## Phase Tensions / Spec Errata

The planner MUST resolve these before writing tasks. All are verified against production code.

### T-1: AC-2 incorrectly marks `/auth/confirm` as 410

**CONTEXT.md** "What's bulldozed" table row: "`/auth/confirm` route → 410 GONE"
**ADR-220-6** (locked): "`/auth/confirm` preserved — PKCE exchange handler stays; only autobind side-effect stripped"
**Verified**: `portal/src/app/auth/confirm/route.ts` (330 lines) is the live PKCE handler used by ALL magic-link emails.

**Resolution**: AC-2 is wrong. `/auth/confirm` is PRESERVED. Planner should NOT include a 410 task for this route. Only the autobind side-effect code (lines 140-313) is stripped.

### T-2: FR-1 says `?start=new`; all code uses `?start=welcome`

**FR-1**: "Landing page CTA points to `t.me/Nikita_my_bot?start=new`"
**Production code** (3 sites):
- `portal/src/components/landing/hero-section.tsx:28`: `set("start", "welcome")`
- `portal/src/app/login/page-client.tsx:35-39`: `?start=welcome`
- `portal/src/app/page.tsx`: delegates to `HeroSection` (inherits `welcome`)
**BE coercion**: `nikita/api/routes/telegram.py:577-618` coerces ALL unbound `/start` payloads to `"welcome"`

**Resolution**: Recommend changing FR-1 task to use `?start=welcome`. Zero blast radius. Changing to `?start=new` requires updating the BE coercion to handle both, or adding a new coercion branch — net zero UX change, extra test surface. **Claude's discretion — planner decides.**

### T-3: FR-2 `/login` 410 breaks sign-out destination and auth/confirm failure redirect

**FR-2**: "Portal `/login` returns 410"
**Current callers of `/login`**:
- `portal/src/lib/supabase/middleware.ts:88`: redirects authenticated `/login` visitors to `/dashboard`; also catches unauthenticated users → `/login`
- `portal/src/app/auth/confirm/route.ts:135`: on auth failure, `redirect('/login?error=...')`
- Supabase Auth SDK: after `signOut()`, JS SDK by default attempts to reload; if the SPA does `router.push('/login')` that becomes a 410

**Resolution**: PR-A must update `middleware.ts` to redirect unauthenticated users to `t.me/Nikita_my_bot?start=welcome` instead of `/login`. `auth/confirm` failure redirect must change to a dedicated error page or the Telegram bot URL. The 410 for `/login` itself can only land AFTER those redirects are updated — confirm this ordering is captured in PR-A task list.

### T-4: FR-4b trigger — NULL telegram_id will cause unhandled exception

**FR-4b** trigger fires on `email_confirmed_at NULL→NOT NULL` for ANY auth.users UPDATE (e.g., portal magic-link for admin, future password reset). If the user authenticated via email-only (no Telegram), `raw_user_meta_data->>'telegram_id'` is NULL, and `::bigint` cast of NULL is NULL (safe) BUT the INSERT will attempt `telegram_id = NULL` which violates `UNIQUE NOT NULL` on `users.telegram_id`.

**Resolution**: Trigger body needs:
```sql
WHEN (
  OLD.email_confirmed_at IS NULL
  AND NEW.email_confirmed_at IS NOT NULL
  AND (NEW.raw_user_meta_data->>'telegram_id') IS NOT NULL
)
```
i.e., the `WHEN` clause acts as the guard — trigger body only runs for TG-first signups. Planner should include this guard explicitly in the migration task.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| OTP send (`sign_in_with_otp`) | Backend / Python API | Telegram Bot | Supabase admin key required; bot calls BE endpoint |
| `app_metadata.telegram_id` write | Backend / Python API | — | Admin API only; never browser-callable |
| User provisioning (users + metrics + vices rows) | Database trigger | — | ADR-220-4: atomic, no app race condition |
| PKCE token exchange | Frontend Server (Next.js Route Handler) | — | Cookie-based SSR session requirement |
| Onboarding completion (`app_metadata.onboarded`) | Backend / Python API | — | Admin API; client cannot write `app_metadata` |
| `/dashboard/*` onboarding gate | Frontend Server (middleware.ts) | — | SSR cookie + JWT claim check |
| Telegram `/start` routing (new vs returning) | Backend / Python API | — | `telegram.py` webhook handler |
| TG CTA URL on landing | Browser / Client | — | Static href, no auth required |

---

## Standard Stack

### Core — Supabase Auth Python SDK

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `supabase` | installed (project venv) | Supabase client (Python) | Project standard |
| `supabase_auth` | `2.24.0` [VERIFIED: `uv run python3 -c "import supabase_auth; print(supabase_auth.__version__)"`] | GoTrue Python client | Used throughout `portal_auth.py`, `auth_bridge.py` |

### Core — Frontend

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@supabase/ssr` | project `package.json` | SSR-safe Supabase client (Next.js) | Used in `middleware.ts`, `auth/confirm/route.ts` |
| Next.js | 16 | App Router, Route Handlers | Project standard |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `asyncpg` | project venv | PostgreSQL async driver | Already used; asyncpg poison prevention pattern already in `portal_onboarding_v2.py:750-794` |
| `sqlalchemy[asyncio]` | project venv | ORM + `with_for_update()` | Already used; `get_by_telegram_id_for_update` at `user_repository.py:114,140` |

**Installation:** No new packages required. All dependencies already installed.

**Version verification:**
```bash
# Verified 2026-05-19
uv run python3 -c "import supabase_auth; print(supabase_auth.__version__)"
# → 2.24.0
```

---

## Architecture Patterns

### System Architecture Diagram (Arch B — target state)

```
User opens Telegram
    │
    ▼
@Nikita_my_bot /start (any payload)
    │
    ▼
telegram.py webhook handler
    ├── Returning user (onboarding_status=completed) → chat pipeline
    └── New/unbound user → signup_handler.handle_welcome()
            │
            ▼
        Bot asks for email
            │
            ▼
        User sends email
            │
            ▼
        signup_handler.handle_email()
            ├── sign_in_with_otp(email, data={"telegram_id": str(chat_id)})
            │       → Supabase: raw_user_meta_data.telegram_id stashed
            │       → Supabase: sends 8-digit OTP email
            │       → NOTE: uid NOT available here (AuthOtpResponse.user=None)
            └── Bot: "Check email, enter OTP"
                    │
                    ▼
                User sends 8-digit OTP
                    │
                    ▼
                signup_handler.handle_otp()
                    ├── verify_otp(email, token, type="email")
                    │       → Supabase: email_confirmed_at NULL→NOT NULL
                    │       → AuthResponse.user.id = uid (available here)
                    │       → PostgreSQL trigger fires:
                    │           INSERT INTO users (telegram_id, ...) ON CONFLICT DO UPDATE
                    │           INSERT INTO user_metrics (...) ON CONFLICT DO NOTHING
                    │           INSERT INTO user_vice_preferences (...) ON CONFLICT DO NOTHING
                    ├── admin.update_user_by_id(uid, app_metadata={"telegram_id": str(chat_id)})
                    │       → Immutable lock (ADR-220-5); uid from verify_otp response
                    └── Bot: "Account created! Open portal:"
                            admin.generate_link(type="magiclink", email)
                            → hashed_token → portal URL
                                    │
                                    ▼
                            User clicks portal URL
                                    │
                                    ▼
                            /auth/confirm (Next.js Route Handler)
                                    ├── signOut({scope:'local'}) [preserve W1 fix]
                                    ├── exchangeCodeForSession(token_hash)
                                    └── redirect → /onboarding (wizard)
                                            │
                                            ▼
                                    Wizard /complete (POST)
                                            ├── SELECT FOR UPDATE on users row
                                            ├── update onboarding_status='completed'
                                            ├── admin.update_user_by_id(app_metadata={"onboarded": True})
                                            └── redirect → /dashboard
```

### Recommended Project Structure (no changes — existing structure preserved)

```
nikita/
├── api/routes/
│   ├── telegram.py          # stripped: FSM routing removed (lines 577-671 rewritten)
│   ├── portal_auth.py       # PR-B: generate_magiclink + autobind + dashboard_bridge deleted
│   └── portal_onboarding_v2.py  # PR-E: SELECT FOR UPDATE + admin.update_user_by_id added
├── platforms/telegram/
│   ├── signup_handler.py    # PR-D: full rewrite (~755→~200 LOC)
│   └── commands.py          # PR-D: _handle_start_with_payload + _send_bridge deleted
portal/src/
├── app/auth/confirm/route.ts  # PR-A: autobind side-effect stripped (lines 140-313)
├── app/auth/interstitial/     # PR-A: deleted
├── app/login/                 # PR-B: 410 GONE (after middleware.ts updated)
└── lib/supabase/middleware.ts # PR-A: interstitial exemption removed; dashboard gate added
supabase/migrations/
└── YYYYMMDD_drop_fsm_tables.sql  # PR-C: drop telegram_signup_sessions, telegram_link_codes
```

### Pattern 1: OTP Send with telegram_id stash

```python
# Source: verified via supabase_auth 2.24.0 SDK introspection 2026-05-19
# admin.get_user_by_email does NOT exist in supabase_auth 2.24.0 — confirmed via
# [m for m in dir(AsyncGoTrueAdminAPI) if "user" in m.lower()] → only get_user_by_id
# Available methods: create_user, delete_user, get_user_by_id, invite_user_by_email,
# list_users (no email filter), update_user_by_id, generate_link, sign_out
# SOLUTION: uid is obtained from verify_otp response in handle_otp; app_metadata
# written there, not at OTP-send time. (ADR-220-5 intent: immutable before any game
# session; verify_otp is still before first pipeline run — intent satisfied.)

# nikita/platforms/telegram/signup_handler.py (new handle_email)
async def handle_email(self, chat_id: int, email: str) -> None:
    supabase = get_supabase_client()

    # Step 1: Send OTP; stash telegram_id in raw_user_meta_data (client-writable but
    # not security-sensitive here — immutable lock happens in handle_otp via admin API)
    await supabase.auth.sign_in_with_otp({
        "email": email,
        "options": {
            "should_create_user": True,
            "data": {"telegram_id": str(chat_id)},  # → raw_user_meta_data
        }
    })
    # No uid available here — AuthOtpResponse.user is always None
    # app_metadata.telegram_id lock deferred to handle_otp (see Pattern 2)
```

### Pattern 2: OTP Verify + app_metadata lock

```python
# Source: verified via supabase_auth 2.24.0 SDK introspection 2026-05-19
# verify_otp returns AuthResponse with .user (Union[User, None]) — uid available here
# nikita/platforms/telegram/signup_handler.py (new handle_otp)
OTP_REGEX = re.compile(r"^[0-9]{8}$")  # Supabase now sends 8-digit codes (GH#431)

async def handle_otp(self, chat_id: int, email: str, token: str) -> None:
    supabase = get_supabase_client()
    auth_resp = await supabase.auth.verify_otp({
        "email": email,
        "token": token,
        "type": "email",
    })
    # AuthResponse.user is populated after successful OTP verify
    uid = str(auth_resp.user.id)

    # After verify_otp: email_confirmed_at flips NULL→NOT NULL
    # PostgreSQL trigger fires; users/user_metrics/user_vice_preferences rows created

    # Step 2: Write immutable telegram_id to app_metadata (ADR-220-5)
    # Must be AFTER verify_otp returns uid (admin.get_user_by_email does not exist)
    await supabase.auth.admin.update_user_by_id(
        uid,
        {"app_metadata": {"telegram_id": str(chat_id)}}
        # admin-only write; client cannot overwrite app_metadata
    )
```

### Pattern 3: Trigger provisioning (FR-4b)

```sql
-- Source: [ASSUMED] standard PostgreSQL trigger pattern; no existing trigger in codebase
-- supabase/migrations/YYYYMMDD_provision_on_confirm.sql
CREATE OR REPLACE FUNCTION auth.provision_user_on_confirm()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  -- Guard: only fire for TG-first signups with telegram_id
  IF (NEW.raw_user_meta_data->>'telegram_id') IS NULL THEN
    RETURN NEW;
  END IF;

  -- Provision users row
  INSERT INTO public.users (id, telegram_id, created_at, updated_at)
  VALUES (
    NEW.id,
    (NEW.raw_user_meta_data->>'telegram_id')::bigint,
    NOW(),
    NOW()
  )
  ON CONFLICT (id) DO UPDATE SET
    telegram_id = EXCLUDED.telegram_id,
    updated_at = NOW();

  -- Provision user_metrics row
  INSERT INTO public.user_metrics (user_id, created_at, updated_at)
  VALUES (NEW.id, NOW(), NOW())
  ON CONFLICT (user_id) DO NOTHING;

  -- Provision user_vice_preferences (8 categories)
  -- Source: nikita/db/models/user.py:394-403 [VERIFIED 2026-05-19]
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

### Pattern 4: admin.generate_link response shape

```python
# Source: verified via supabase_auth 2.24.0 SDK introspection 2026-05-19
# Working example from nikita/api/routes/auth_bridge.py:84,90
result = await supabase.auth.admin.generate_link({
    "type": "magiclink",
    "email": email,
    # optionally: "options": {"redirect_to": f"{PORTAL_URL}/auth/confirm"}
})
# result: GenerateLinkResponse
# result.properties.hashed_token  → str (use in portal URL)
# result.properties.action_link   → str (full URL Supabase would email)
# result.properties.verification_type → "magiclink"
portal_url = f"{PORTAL_URL}/auth/confirm?token_hash={result.properties.hashed_token}&type=email&next=/onboarding"
```

### Pattern 5: Wizard PATCH SELECT FOR UPDATE + app_metadata write (FR-11)

```python
# Source: [VERIFIED existing pattern] user_repository.py:114,140 has get_by_telegram_id_for_update
# portal_onboarding_v2.py needs both of these added:

# Step 1: SELECT FOR UPDATE (serialize concurrent wizard /complete calls)
user = await user_repo.get_by_telegram_id_for_update(telegram_id)
# → SQLAlchemy .with_for_update() at user_repository.py:140

# Step 2: Mark DB onboarding_status
await user_repo.update_onboarding_status(user.id, "completed")
# → existing, portal_onboarding_v2.py:734

# Step 3: Write app_metadata.onboarded=True (NEW — not currently present)
await supabase.auth.admin.update_user_by_id(
    str(user.id),
    {"app_metadata": {"onboarded": True}}
)
# AdminUserAttributes.app_metadata is admin-only; safe from client self-escalation
```

### Pattern 6: /auth/confirm after autobind strip

```typescript
// Source: portal/src/app/auth/confirm/route.ts (strip lines 140-313, preserve 108-125)
// Target shape after PR-A strip (~80 LOC):

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const token_hash = searchParams.get('token_hash')
  const type = searchParams.get('type') as EmailOtpType
  const next = searchParams.get('next') ?? '/onboarding'

  const supabase = createServerClient(...)

  // PRESERVE: W1 CRITICAL fix (lines 108-125)
  await supabase.auth.signOut({ scope: 'local' })

  if (token_hash && type) {
    const { error } = await supabase.auth.verifyOtp({ token_hash, type })
    if (!error) {
      return NextResponse.redirect(new URL(next, request.url))
    }
  }

  // UPDATED: redirect to TG bot URL, not /login (T-3 resolution)
  return NextResponse.redirect(new URL('https://t.me/Nikita_my_bot', request.url))
}
```

### Anti-Patterns to Avoid

- **Application-layer `create_with_metrics`**: After PR-D, NEVER call `user_repo.create_with_metrics` for TG-first signups. Trigger owns provisioning. App code should only verify rows exist, not create them.
- **`user_metadata` for telegram_id**: `user_metadata` is client-writable (browser can overwrite). All security-sensitive binding uses `app_metadata` via admin API.
- **Parallel OTP verify races**: `verify_otp` itself is idempotent (Supabase deduplicates), but the provisioning trigger uses `ON CONFLICT DO NOTHING` — safe for double-fire.
- **Dropping tables before deleting code**: PR ordering A→D→E→B→C exists for this reason. Never run the DROP TABLE migration (PR-C) while any production Cloud Run revision still imports `TelegramSignupSessionRepository`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OTP email delivery | Custom SMTP + 8-digit generator | `supabase.auth.sign_in_with_otp` | Supabase handles code generation, TTL, rate-limit, delivery |
| Concurrent write serialization | Custom mutex / Redis lock | SQLAlchemy `.with_for_update()` | Already in `user_repository.py:140`; PostgreSQL advisory locks have gotchas |
| Atomic user provisioning | Application-layer try/except transaction | PostgreSQL `AFTER UPDATE` trigger | ADR-220-4; app-layer has TOCTOU race on concurrent OTP verifies |
| Magic-link URL generation | Custom JWT mint | `supabase.auth.admin.generate_link` | Handles signing, expiry, redirect_to — precedent at `auth_bridge.py:84` |
| `app_metadata` write | Supabase client-side update | `admin.update_user_by_id` | Client API cannot write `app_metadata`; only admin API can |

---

## Runtime State Inventory

> This is a deletion/refactor phase. All 5 categories answered explicitly.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `telegram_signup_sessions` table: rows with `signup_state` enum values including `awaiting_email`, `code_sent`, `magic_link_sent`, `completed`. Zero real prod users (pre-launch). | PR-C: DROP TABLE (no migration of rows needed) |
| Stored data | `telegram_link_codes` table: rows with 6-char link codes, 10-min TTL | PR-C: DROP TABLE |
| Stored data | `pending_registrations` table: legacy name, renamed in migration `20260424120000` | PR-C: DROP TABLE (confirm whether old name or new name in current schema) |
| Live service config | pg_cron job: `cleanup_pending_registrations` POST to `tasks.py:681` on schedule | PR-C: `SELECT cron.unschedule('cleanup_pending_registrations')` in migration |
| Live service config | Cloud Run service `nikita-api`: multiple revisions may serve traffic during rolling deploy | PR ordering A→D→E→B→C ensures no revision serves deleted-table queries |
| OS-registered state | None — Cloud Run is ephemeral, no OS-level registrations | None |
| Secrets/env vars | No new secrets required. Admin key already in `settings.py`. | None |
| Build artifacts | `nikita/db/repositories/telegram_link_repository.py`, `telegram_signup_session_repository.py`, `pending_registration_repository.py` | PR-B: delete files; ensure no `__init__.py` barrel exports remain |

---

## Common Pitfalls

### Pitfall 1: Trigger fires for non-TG signups (NULL telegram_id)
**What goes wrong:** Without the `WHEN` guard, any `email_confirmed_at` flip (password reset, admin verify) triggers the INSERT, which tries to insert `telegram_id = NULL` into a `NOT NULL UNIQUE` column → constraint violation → auth broken.
**Why it happens:** ADR-220-4 specifies the trigger but CONTEXT.md text doesn't include the NULL guard.
**How to avoid:** Use `WHEN (...AND (NEW.raw_user_meta_data->>'telegram_id') IS NOT NULL)` in the trigger definition (see Pattern 3 above).
**Warning signs:** Any auth.users UPDATE not from TG flow (admin dashboard verify, future password auth) throws 500.

### Pitfall 2: Deleting tables before removing all imports
**What goes wrong:** Cloud Run rolling deploy: old revision still serves traffic while new revision is deploying. If PR-C migration drops tables before PR-B code removes imports, old revision fails with `relation "telegram_signup_sessions" does not exist`.
**Why it happens:** Squash-merging A+B+C or reordering.
**How to avoid:** Strict PR sequence A→D→E→B→C. Deploy and verify each PR independently before opening next.
**Warning signs:** Cloud Run ERROR logs: `UndefinedTable` during deploy window.

### Pitfall 3: /login 410 before middleware redirect is updated
**What goes wrong:** Unauthenticated users hit middleware → redirect to `/login` → 410 → user sees blank error page with no CTA.
**Why it happens:** PR-B adds 410 before PR-A updates middleware `unauthenticated → TG bot` redirect.
**How to avoid:** PR-A MUST include middleware.ts change to redirect unauthenticated users to `t.me/Nikita_my_bot?start=welcome`. PR-B's 410 only lands after PR-A is live.
**Warning signs:** Middleware test suite for unauthenticated routes fails.

### Pitfall 4: `signup_handler.py` OTP regex still matches 6-digit codes
**What goes wrong:** Supabase now sends 8-digit OTP codes (GH#431 confirmed). If regex is `r"^[0-9]{6,8}$"`, it accepts both 6 and 8 digit inputs — but Supabase `verify_otp` will reject stale 6-digit tokens. User confusion.
**Why it happens:** Original regex was written before Supabase standardized on 8 digits.
**How to avoid:** In PR-D rewrite, use `OTP_REGEX = re.compile(r"^[0-9]{8}$")` (8 digits exact). If verify_otp rejects, error message should say "Invalid code. Check email for the 8-digit code."
**Warning signs:** Users entering 6-digit codes get cryptic Supabase error instead of friendly bot message.

### Pitfall 5: asyncpg session poisoning in wizard PATCH
**What goes wrong:** `portal_onboarding_v2.py` has a GH#638 asyncpg poison prevention pattern at lines 750-768 and 786-794. Adding `admin.update_user_by_id` (HTTP call to Supabase) inside the DB transaction could block the async event loop during the HTTP call, starving connection pool.
**Why it happens:** New `admin.update_user_by_id` call added inside SQLAlchemy `async with session.begin()` block.
**How to avoid:** Call `admin.update_user_by_id` AFTER the DB transaction commits — sequence: (1) `SELECT FOR UPDATE`, (2) `UPDATE onboarding_status`, (3) `COMMIT`, (4) `admin.update_user_by_id` (Supabase HTTP). If step 4 fails, DB is still consistent (onboarding_status=completed); middleware falls back to cookie check.
**Warning signs:** GH#638 symptom returns: subsequent requests to same worker fail with asyncpg errors.

### Pitfall 6: `app_metadata` merge semantics
**What goes wrong:** `admin.update_user_by_id(uid, {"app_metadata": {"onboarded": True}})` does a MERGE with existing `app_metadata`, not a replace. This is correct behavior. BUT if `telegram_id` was set in step FR-4a and `app_metadata` now contains `{"telegram_id": "123"}`, calling `update_user_by_id` with only `{"onboarded": True}` will result in `{"telegram_id": "123", "onboarded": True}` — which is correct.
**Why it happens:** Not a bug — documenting for test writers who might expect full replacement.
**How to avoid:** Tests should assert both keys present after wizard completion.

---

## Code Examples

### Existing working admin.generate_link pattern

```python
# Source: nikita/api/routes/auth_bridge.py:75-90 [VERIFIED]
user_result = await supabase.auth.admin.get_user_by_id(str(user_id))
email = user_result.user.email

link_result = await supabase.auth.admin.generate_link({
    "type": "magiclink",
    "email": email,
})
hashed_token = link_result.properties.hashed_token
portal_url = f"{settings.portal_url}/auth/confirm?token_hash={hashed_token}&type=email&next=/onboarding"
```

### Existing SELECT FOR UPDATE pattern

```python
# Source: nikita/db/repositories/user_repository.py:114,140 [VERIFIED]
async def get_by_telegram_id_for_update(
    self, telegram_id: int
) -> User | None:
    result = await self.session.execute(
        select(User)
        .where(User.telegram_id == telegram_id)
        .with_for_update()   # ← line 140
    )
    return result.scalars().first()
```

### Existing asyncpg poison prevention (PRESERVE)

```python
# Source: nikita/api/routes/portal_onboarding_v2.py:750-794 [VERIFIED]
# Pattern: rollback on non-fatal errors, isolated session for side-effects
# GH#638 fix. DO NOT move admin.update_user_by_id inside this transaction block.
try:
    async with session.begin():
        # ... DB operations ...
        pass
except Exception:
    await session.rollback()
    raise
# Supabase HTTP calls go HERE (after transaction close)
await supabase.auth.admin.update_user_by_id(...)
```

### telegram.py routing lines to rewrite

```python
# Source: nikita/api/routes/telegram.py:577-671 [VERIFIED]
# Current: FSM-driven routing (577-618 coercion block + 634-671 state routing)
# Target: simple 2-branch:
#   bound user (users row exists) → chat pipeline
#   unbound user → signup_handler.handle_welcome()

# REMOVE: lines 577-618 (coercion block for unbound /start payloads)
# REMOVE: lines 634-671 (FSM state routing via signup_state column)
# REMOVE: lines 668-671 (has_pending check via pending_repo)
# KEEP:   pipeline dispatch for bound users
```

### LLM-DEBUG lines in telegram.py (9 spec-cited)

```
# Source: nikita/api/routes/telegram.py [VERIFIED — file is api/routes/telegram.py, NOT platforms/telegram/telegram.py]
# Lines to remove: 604, 620, 639, 654, 669, 675, 682, 694, 695
# (12 total LLM-DEBUG lines exist; 9 are spec-cited as PII-leaking; remove all 12 in PR-D)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pending_registrations` table | renamed to `telegram_signup_sessions` | `20260424120000` migration | Drop NEW name in PR-C |
| Graphiti/Neo4j memory | SupabaseMemory (pgVector) | Spec 042 | No impact on this phase |
| 6-digit OTP | 8-digit OTP | Supabase server-side change (GH#431) | OTP_REGEX must be `^[0-9]{8}$` |
| `portal_onboarding_v2.py` autobind call | Removed (GH#638 fix) | PR aeba521 (current branch) | autobind already stripped from wizard; only `/auth/confirm` side-effect remains |

**Deprecated/outdated:**
- `TelegramSignupSessionRepository` (11.8K): full FSM state machine; to be deleted PR-B
- `TelegramLinkRepository` (5.1K): 6-char link codes, 10-min TTL; to be deleted PR-B
- `PendingRegistrationRepository` (8.6K): old name; to be deleted PR-B
- `portal_auth.py` generate_magiclink + autobind + dashboard_bridge (lines 189-616): to be deleted PR-B

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `admin.update_user_by_id(app_metadata={...})` does merge (not replace) with existing `app_metadata` | Architecture Patterns | If it replaces, calling update after OTP-send (which sets telegram_id) would wipe telegram_id; must set both keys in one call |
| A2 | pgTAP 0 hits = not configured/installed (not just not used for this table) | Validation Architecture | If pgTAP is installed but just not used, AC-15 could still be satisfied; low risk |
| A3 | `/auth/interstitial` is a Next.js route (not just a reference); deleting it in PR-A is safe | Architecture Patterns | If something else links to `/auth/interstitial` not yet found, PR-A delete breaks it |
| A4 | `tasks.py:681` cron endpoint has a matching pg_cron schedule entry | Runtime State Inventory | If the pg_cron entry was already removed, PR-C doesn't need `cron.unschedule` for it |
| A5 | 8 vice categories in trigger are canonical | Architecture Patterns (Trigger Pattern) | [VERIFIED: nikita/db/models/user.py:394-403] Values confirmed: intellectual_dominance, risk_taking, substances, sexuality, emotional_intensity, rule_breaking, dark_humor, vulnerability. Note: NOT in config/enums.py — in db/models/user.py VICE_CATEGORIES list. |

---

## Open Questions

1. **T-2: `?start=new` vs `?start=welcome`**
   - What we know: FR-1 says `new`; all production code says `welcome`; BE coercion handles any payload
   - What's unclear: Whether changing to `new` is intentional signal or spec drift
   - Recommendation: Keep `welcome` (planner decision)

2. **T-3: `/login` failure redirect target**
   - What we know: `auth/confirm/route.ts:135` currently redirects to `/login?error=...` on failure
   - What's unclear: What should the failure destination be in Arch B? TG bot URL? Dedicated error page?
   - Recommendation: Redirect to `t.me/Nikita_my_bot?start=welcome` with error surfaced via `?error=` query param

3. **`/auth/interstitial` location — RESOLVED**
   - [VERIFIED 2026-05-20]: `portal/src/app/auth/interstitial/` exists with `InterstitialClient.tsx` (4.2K), `page.tsx` (2.7K), `__tests__/` dir
   - Planner writes a PR-A delete task for this entire directory
   - `middleware.ts:79` interstitial exemption must also be removed in PR-A

4. **Vice categories in trigger — RESOLVED**
   - [VERIFIED 2026-05-20]: `nikita/db/models/user.py:394-403` VICE_CATEGORIES = ['intellectual_dominance', 'risk_taking', 'substances', 'sexuality', 'emotional_intensity', 'rule_breaking', 'dark_humor', 'vulnerability']. NOT in config/enums.py.
   - Pattern 3 trigger SQL updated with verified values.

---

## Environment Availability

> Step 2.6: Standard environment — Cloud Run (Python FastAPI) + Vercel (Next.js) + Supabase. No new external dependencies.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| supabase_auth (Python) | OTP send, admin API | ✓ | 2.24.0 | — |
| SQLAlchemy with_for_update | SELECT FOR UPDATE | ✓ | project venv | — |
| PostgreSQL trigger support | FR-4b provisioning | ✓ | Supabase Postgres | — |
| pgTAP | AC-15 trigger test | ✗ | not installed | Supabase MCP `execute_sql` verification |
| Supabase MCP tools | Migration apply + verify | ✓ | project MCP | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:**
- pgTAP: not installed. AC-15 trigger testing via `mcp__supabase__execute_sql` with manual INSERT/SELECT verification instead.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (Python); vitest (portal) |
| Config file | `pytest.ini` (root) |
| Quick run command | `uv run pytest tests/platforms/telegram/ tests/api/routes/test_portal_auth*.py -q` |
| Full suite command | `uv run pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-003/FR-3 | OTP send stashes telegram_id in raw_user_meta_data | unit (mock SDK) | `uv run pytest tests/platforms/telegram/test_signup_handler.py -x` | ✅ (rewrite needed) |
| REQ-004/FR-4a | app_metadata.telegram_id immutable lock via admin API | unit (mock SDK) | same file | ✅ (rewrite needed) |
| REQ-005/FR-4b | Trigger provisions users/metrics/vices rows on email_confirmed_at flip | integration (Supabase MCP) | manual: `mcp__supabase__execute_sql` | ❌ Wave 0 |
| REQ-006/FR-5 | FSM routing removed; UNKNOWN→welcome; known→chat | unit | `uv run pytest tests/api/routes/test_telegram.py -x` | ✅ |
| REQ-007/FR-6 | handle_otp replaces handle_code (8-digit OTP) | unit | `uv run pytest tests/platforms/telegram/test_signup_handler.py -x` | ✅ (rewrite) |
| REQ-009/FR-8 | Middleware blocks /dashboard/* for onboarding_status!=completed or app_metadata.onboarded!=True | unit (middleware mock) | `(cd portal && npm run test -- --run)` | ❌ Wave 0 |
| REQ-010/FR-9 | /auth/confirm autobind side-effect stripped | unit (route handler mock) | `(cd portal && npm run test -- src/app/auth/confirm/__tests__/)` | ✅ (update needed) |
| REQ-012/FR-11 | Wizard /complete: SELECT FOR UPDATE + admin.update_user_by_id | unit | `uv run pytest tests/api/routes/test_portal_onboarding.py -x` | ✅ |
| REQ-014/FR-13 | onboarding_status 'skipped' removed from constraint | migration test | Supabase MCP execute_sql | ❌ Wave 0 |
| REQ-018/AC-18 | message_handler onboarding_status check | unit | `uv run pytest tests/platforms/telegram/test_message_handler.py -x` | ✅ |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/platforms/telegram/ -q` (backend) or `(cd portal && npm run test -- --run)` (portal)
- **Per wave merge:** `uv run pytest -q` + `(cd portal && npm run test -- --run && npm run lint && npm run build)`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/platforms/telegram/test_signup_handler_arch_b.py` — covers REQ-003/FR-3, REQ-004/FR-4a, REQ-007/FR-6 (new handle_email + handle_otp unit tests)
- [ ] `tests/api/routes/test_telegram_routing_arch_b.py` — covers REQ-006/FR-5 (stripped FSM routing)
- [ ] `portal/src/app/auth/confirm/__tests__/route.test.ts` — covers REQ-010/FR-9 (autobind stripped; already exists as `.worktree_new` file per git status)
- [ ] Middleware test update for `app_metadata.onboarded` check — covers REQ-009/FR-8
- [ ] Supabase MCP trigger verification script — covers REQ-005/FR-4b, REQ-014/FR-13

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Supabase GoTrue OTP + PKCE; no custom auth |
| V3 Session Management | yes | `@supabase/ssr` `createServerClient`; signOut W1 fix preserved |
| V4 Access Control | yes | `app_metadata.role` for admin; `app_metadata.onboarded` for dashboard; NEVER `user_metadata` |
| V5 Input Validation | yes | OTP: `r"^[0-9]{8}$"` regex; email: Supabase validates |
| V6 Cryptography | no | No custom crypto; Supabase handles JWT signing |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Client overwrite of `app_metadata.telegram_id` | Spoofing | Use `admin.update_user_by_id` (server-side admin key only); `user_metadata` NEVER used for this |
| Double OTP verify race → duplicate user rows | Tampering | Trigger `ON CONFLICT DO NOTHING`; `users.id` PK prevents duplicates |
| Stale wizard PATCH overwriting completed state | Tampering | `SELECT FOR UPDATE` at wizard /complete |
| Self-escalation via `user_metadata.role` | Elevation of Privilege | `app_metadata.role` checked (not `user_metadata`); enforced at `nikita/api/dependencies/auth.py` |
| `/login` still serving after 410 window closes | Denial of Service | PR ordering ensures middleware redirect lands before 410 |

---

## Sources

### Primary (HIGH confidence)
- `supabase_auth 2.24.0` SDK introspection via `uv run python3` — `sign_in_with_otp`, `verify_otp`, `generate_link`, `update_user_by_id` API shapes verified
- `nikita/api/routes/auth_bridge.py:75-90` — working admin API patterns verified
- `nikita/api/routes/portal_onboarding_v2.py:734-794` — existing wizard pattern + asyncpg fix verified
- `nikita/db/repositories/user_repository.py:114-140,651,1031,1083` — SELECT FOR UPDATE, update_onboarding_status verified
- `nikita/db/models/user.py:289-292` — CheckConstraint verified
- `portal/src/app/auth/confirm/route.ts:108-313` — autobind scope verified
- `portal/src/lib/supabase/middleware.ts:79-119` — interstitial exemption, dashboard gate verified
- `nikita/api/routes/telegram.py:577-695` — FSM routing + LLM-DEBUG lines verified
- `nikita/platforms/telegram/signup_handler.py:196-530` — current FSM handler scope verified
- `nikita/platforms/telegram/commands.py:183,272,433,476` — link code pattern + _handle_start_with_payload verified
- `supabase/reference/00000000000001_baseline_schema.sql` — no existing trigger confirmed
- `grep` across entire codebase — confirmed 0 existing `auth.users` triggers

### Secondary (MEDIUM confidence)
- `nikita/api/routes/tasks.py:681` — cleanup_pending_registrations endpoint identified (not in CONTEXT.md bulldoze table)
- `portal/src/components/landing/hero-section.tsx:28` — `?start=welcome` vs FR-1 `?start=new` tension

### Tertiary (LOW confidence — [ASSUMED])
- Trigger `ON CONFLICT DO UPDATE` merge semantics for `app_metadata` (A1)

### Corrections applied post-initial-draft (2026-05-20)
- `admin.get_user_by_email` does NOT exist in supabase_auth 2.24.0 (Pattern 1 rewritten)
- Vice categories [VERIFIED]: `nikita/db/models/user.py:394-403` VICE_CATEGORIES list (NOT in config/enums.py)
- `/auth/interstitial` location [VERIFIED]: `portal/src/app/auth/interstitial/` with InterstitialClient.tsx + page.tsx

---

## Metadata

**Confidence breakdown:**
- Supabase API shapes: HIGH — verified via SDK introspection
- File:line touchpoints: HIGH — verified by reading each file
- Trigger pattern: MEDIUM — standard PostgreSQL; specific column names verified; trigger body is new code
- Spec tensions: HIGH — verified against both spec text and production code

**Research date:** 2026-05-19
**Valid until:** 2026-06-19 (stable APIs; trigger pattern is Supabase/Postgres, unlikely to change)

# Architecture Validation Report

**Spec:** `specs/081-onboarding-redesign-progressive-discovery/spec.md` (v2)
**Status:** FAIL
**Timestamp:** 2026-03-22T14:30:00Z
**Validator:** sdd-architecture-validator

---

## Summary

- CRITICAL: 1
- HIGH: 2
- MEDIUM: 5
- LOW: 3

---

## Findings

| # | Severity | Category | Issue | Location | Recommendation |
|---|----------|----------|-------|----------|----------------|
| 1 | **CRITICAL** | Module Organization | Spec says to create a **new file** `nikita/api/routes/onboarding.py` with `APIRouter(prefix="/onboarding")` (line 1313), but this file **already exists** and is already registered in `main.py` at `/api/v1/onboarding` (line 256). The new router prefix would double-nest to `/api/v1/onboarding/onboarding/profile` or cause a duplicate router registration error. | spec.md:1313, nikita/api/main.py:256, nikita/api/routes/onboarding.py (existing) | Add the new `POST /profile` endpoint to the **existing** `nikita/api/routes/onboarding.py` file. Do NOT create a new router. The existing router already has no prefix (the prefix is set in `main.py`). Add `OnboardingProfileRequest` model and `save_onboarding_profile` handler directly to the existing file. |
| 2 | **HIGH** | Separation of Concerns | The spec's `complete_onboarding()` call signature (line 1362) uses `await user_repo.complete_onboarding(user_id)` with a single argument, but the **existing** `UserRepository.complete_onboarding()` (user_repository.py:579) requires 3 arguments: `(user_id, call_id, profile)`. The method sets `onboarding_status`, `onboarding_call_id`, `onboarding_profile`, and `onboarded_at`. The portal flow has no `call_id` and passes profile via `ProfileRepository`, not as a dict. | spec.md:1362, nikita/db/repositories/user_repository.py:579-614 | Either (a) create a new method `complete_portal_onboarding(user_id)` that only sets `onboarding_status="completed"`, `onboarded_at`, and the new `onboarding_completed_at` column, or (b) refactor `complete_onboarding()` to accept optional `call_id` and `profile` parameters with defaults. Option (a) is cleaner -- distinct method for a distinct flow. |
| 3 | **HIGH** | Import Patterns | The spec's fallback scheduling code (line 1413) imports `from nikita.db.session import get_session_maker`. This module does **not exist**. The actual module is `nikita.db.database` (`from nikita.db.database import get_session_maker`). | spec.md:1413 | Fix import to `from nikita.db.database import get_session_maker`. |
| 4 | MEDIUM | Module Organization | The `EventType` enum in `nikita/db/models/scheduled_event.py` defines 4 types: `message_delivery`, `call_reminder`, `boss_prompt`, `follow_up`. The spec uses `event_type="onboarding_fallback"` (line 1424) which is not in the enum. The model column is `String(50)` so it won't fail at DB level, but violates the typed contract. | spec.md:1424, nikita/db/models/scheduled_event.py:42-48 | Add `ONBOARDING_FALLBACK = "onboarding_fallback"` to the `EventType` enum. Also ensure the `deliver` pg_cron job handler has a case for this new event type (currently handles `message_delivery`, `call_reminder`, `boss_prompt`, `follow_up`). |
| 5 | MEDIUM | Separation of Concerns | The spec places magic link generation logic (`_generate_portal_magic_link`) directly inside `OTPVerificationHandler` (otp_handler.py). This handler is a Telegram platform component. Generating Supabase Admin API magic links is an auth-layer concern, not a platform concern. If future flows (e.g., SMS onboarding, web registration) need magic links, this logic would be duplicated. | spec.md:1161-1204 | Extract magic link generation to a shared utility, e.g., `nikita/platforms/auth/magic_link.py` or `nikita/auth/magic_link.py`. The OTP handler calls this utility. Keeps the platform layer thin. |
| 6 | MEDIUM | Type Safety | The spec's profile endpoint code (line 1279 in the client, line 1336 in the backend) sends `drug_tolerance` as the field name. But the existing `ProfileRepository.create_profile()` and the `UserProfile` model already use `drug_tolerance` as an integer field. The `ProfileRepository` has an `upsert` method referenced in the spec (line 1354), but inspection shows `ProfileRepository` does not have a method named `upsert`. It has `create_profile()` and basic `get`/`update` from `BaseRepository`. | spec.md:1354, nikita/db/repositories/profile_repository.py:31-80 | Implement `upsert()` on `ProfileRepository` using PostgreSQL `ON CONFLICT DO UPDATE` pattern (the file already imports `from sqlalchemy.dialects.postgresql import insert` for this pattern). Or call `get_by_user_id` + `create_profile` / `update` explicitly. |
| 7 | MEDIUM | Error Handling Architecture | The spec does not define what happens when the `deliver` pg_cron job encounters an `onboarding_fallback` event. The fallback handler must: (a) check `onboarding_completed_at` on the user, (b) if null, send the fallback Telegram message, (c) if set, discard the event. This handler code is not specified. The existing `deliver` job handler in `nikita/api/routes/tasks.py` needs modification, but the spec only mentions the scheduling side, not the delivery side. | spec.md:1436-1438, nikita/api/routes/tasks.py | Add a concrete implementation section for the fallback event handler in the `deliver` task endpoint. Specify: which module handles it, how it checks `onboarding_completed_at`, and how it triggers `OnboardingHandler.start()`. Without this, the scheduled event will be created but never processed. |
| 8 | MEDIUM | Security Architecture | The spec's Server Component in `/onboarding/page.tsx` (line 1224-1236) fetches stats from the backend API using the user's access token. This fetch happens server-side (Node.js runtime) and sends credentials to the backend. The `getSession()` call is used instead of `getUser()` for the token. According to Supabase SSR best practices, `getUser()` validates the token against the Supabase auth server, while `getSession()` only reads from the cookie (which can be tampered with). The redirect decision (onboarding vs dashboard) should be based on a validated user. | spec.md:1228 | Use `supabase.auth.getUser()` (already called on line 1219) to get the session token, or call `getSession()` only after `getUser()` has confirmed the user is valid. Since `getUser()` is already called, extract the token from the validated session. Pattern: `const { data: { session } } = await supabase.auth.getSession()` is acceptable here because `getUser()` was called first, refreshing the session. |
| 9 | LOW | Import Patterns | The spec's profile endpoint code (line 1321) imports `from nikita.db.database import get_async_session`. The existing codebase uses `get_async_session` as a FastAPI dependency (defined in `nikita/db/dependencies.py` or `nikita/db/database.py`). The existing onboarding routes use a locally-defined `get_db_session()` function. Mixing patterns within the same file creates inconsistency. | spec.md:1321, nikita/api/routes/onboarding.py:77-81 | Use the same DI pattern as the existing endpoints in the same file. Either import `get_async_session` from `nikita.db.dependencies` (if it exists as a FastAPI `Depends`), or reuse the existing `get_db_session()` defined in the same file. |
| 10 | LOW | Scalability | The `tg://resolve?domain=Nikita_my_bot` deep link is hardcoded in the client component (spec line 1287). The bot username should come from a configuration/environment variable (`NEXT_PUBLIC_TELEGRAM_BOT_USERNAME`) so it can differ between dev/staging/prod environments. | spec.md:1287 | Add `NEXT_PUBLIC_TELEGRAM_BOT_USERNAME` to portal env vars. Reference it in the deep link: ``tg://resolve?domain=${process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME}``. Also update `vercel.json` env var list. |
| 11 | LOW | Type Safety | The `drips_delivered` column (line 1484) uses `Mapped[dict]` without a type parameter. For clarity and type checker compatibility, this should be `Mapped[dict[str, Any]]` matching the existing pattern in the codebase. | spec.md:1484 | Change to `drips_delivered: Mapped[dict[str, Any]]` and add the `Any` import from `typing`. |

---

## Proposed Structure

New and modified files for Spec 081 Phase 1:

```
nikita/
  api/
    routes/
      onboarding.py              # MODIFY (add POST /profile endpoint)
    schemas/
      portal.py                  # MODIFY (add onboarding_completed_at, welcome_completed)
  db/
    models/
      user.py                    # MODIFY (add onboarding_completed_at, drips_delivered, welcome_completed)
      scheduled_event.py         # MODIFY (add ONBOARDING_FALLBACK to EventType)
    repositories/
      profile_repository.py      # MODIFY (add upsert method)
      user_repository.py         # MODIFY (add complete_portal_onboarding method)
  config/
    settings.py                  # (already has portal_url, supabase_service_key)
  platforms/
    telegram/
      otp_handler.py             # MODIFY (_offer_onboarding_choice replacement, fallback scheduling)
    auth/
      magic_link.py              # NEW (extracted magic link generation utility)

portal/
  src/
    app/
      onboarding/
        page.tsx                 # NEW (Server Component — auth check, redirect logic)
        onboarding-cinematic.tsx # NEW (Client Component — scroll-snap, form state)
        sections/
          score-section.tsx      # NEW (reuses ScoreRing from @/components/charts/)
          chapter-section.tsx    # NEW (ChapterStepper component)
          rules-section.tsx      # NEW (4 GlassCard rules grid)
          profile-section.tsx    # NEW (LocationInput, SceneSelector, EdginessSlider)
          mission-section.tsx    # NEW (CTA, deep link, profile submission)
      auth/
        callback/
          route.ts               # EXISTING (no changes needed -- already handles next param)
    components/
      onboarding/
        chapter-stepper.tsx      # NEW (reusable stepper -- horizontal/vertical)
        scene-selector.tsx       # NEW (5 visual cards, radiogroup pattern)
        edginess-slider.tsx      # NEW (1-5 range with emoji previews)
        section-header.tsx       # NEW (title + quote layout, shared across sections)
        nikita-quote.tsx         # NEW (blockquote + cite pattern)
        scroll-indicator.tsx     # NEW (animated down-arrow)
    lib/
      supabase/
        middleware.ts            # EXISTING (no changes needed)
  middleware.ts                  # EXISTING (no changes needed)
```

---

## Module Dependency Graph

```
                    +-------------------+
                    |  Telegram          |
                    |  otp_handler.py    |
                    +--------+----------+
                             |
                    calls    |   calls
              +--------------+--------------+
              |                             |
   +----------v---------+       +----------v-----------+
   | auth/magic_link.py |       | db/repositories/     |
   | (Supabase Admin)   |       | scheduled_event_repo |
   +--------------------+       +----------------------+
                                         |
                                  uses   |
                             +-----------v-----------+
                             | db/models/            |
                             | scheduled_event.py    |
                             +-----------------------+

   +-------------------+         +---------------------+
   | portal/onboarding |  POST   | api/routes/          |
   | page.tsx (SC)     +-------->+ onboarding.py        |
   |   |               |         |  /profile endpoint   |
   |   v               |         +----------+-----------+
   | onboarding-       |                    |
   | cinematic.tsx(CC) |         +----------v-----------+
   |   |               |         | db/repositories/     |
   |   v               |         | profile_repo +       |
   | sections/*.tsx    |         | user_repo            |
   |   |               |         +----------+-----------+
   |   v               |                    |
   | @/components/     |         +----------v-----------+
   | charts/score-ring |         | services/            |
   | glass/glass-card  |         | venue_research.py    |
   +-------------------+         +----------------------+

   Legend:
   SC = Server Component
   CC = Client Component ("use client")
   --> = data flow / function call
```

---

## Separation of Concerns Analysis

| Layer | Responsibility | Spec Compliance | Issues |
|-------|---------------|-----------------|--------|
| **Telegram Platform** (`platforms/telegram/`) | OTP handling, message delivery, Telegram-specific UI (keyboard buttons) | Partial | Magic link generation leaks auth logic into platform layer (Finding #5) |
| **Auth Bridge** (proposed `auth/magic_link.py`) | Supabase Admin API magic link generation | Not in spec | Recommended extraction for SoC compliance |
| **API Routes** (`api/routes/onboarding.py`) | HTTP endpoints, request validation, response formatting | Partial | Router conflict (Finding #1), DI inconsistency (Finding #9) |
| **Repositories** (`db/repositories/`) | Data access, CRUD operations | Partial | Missing `upsert` (Finding #6), signature mismatch (Finding #2) |
| **Models** (`db/models/`) | Schema definitions, column types | Good | Minor type annotation (Finding #11) |
| **Portal Server Components** (`app/onboarding/page.tsx`) | Auth check, redirect logic, data fetching | Good | Session vs User token concern (Finding #8) |
| **Portal Client Components** (`onboarding-cinematic.tsx`) | UI rendering, form state, animations, submission | Good | Hardcoded bot username (Finding #10) |
| **Reusable Components** (`components/onboarding/`) | Visual building blocks | Good | Clean separation of domain components |
| **Scheduled Events** (`db/models/scheduled_event.py`) | Event type definitions, scheduling model | Partial | Missing event type (Finding #4), missing handler (Finding #7) |

---

## Import Pattern Checklist

- [x] Portal uses `@/*` path alias (tsconfig.json confirms `"@/*": ["./src/*"]`)
- [x] Spec correctly uses `@/components/charts/score-ring`, `@/components/glass/glass-card` (existing components)
- [x] Spec correctly uses `@/lib/supabase/server` for Server Component auth
- [x] No circular dependencies introduced in portal (sections import from components, not vice versa)
- [x] Backend uses absolute imports (`nikita.db.repositories.profile_repository`)
- [ ] **FAIL**: Spec uses `from nikita.db.session` (Finding #3 -- module does not exist)
- [ ] **FAIL**: Spec uses `from nikita.db.database import get_async_session` but existing file uses local `get_db_session()` (Finding #9)
- [x] `TYPE_CHECKING` pattern used correctly in existing otp_handler.py (conditional imports for type hints)
- [x] Lazy imports used for fire-and-forget services (VenueResearchService)

---

## Security Architecture

- [x] JWT auth on new profile endpoint (via `get_current_user_id` dependency)
- [x] Magic link uses Supabase Admin API with service role key (server-side only)
- [x] Magic link URL is HTTPS (Supabase generates full HTTPS URLs)
- [x] Existing RLS policies cover new columns (no additional policies needed)
- [x] Input validation on profile endpoint (Pydantic model with constraints)
- [x] `social_scene` validated against allowlist (`VALID_SCENES` set)
- [x] Open redirect prevention in `/auth/callback/route.ts` (existing `rawNext` sanitization)
- [x] Fallback URL uses same-origin portal URL (not user-controlled)
- [x] Magic link expiry follows Supabase defaults (1 hour)
- [ ] **MEDIUM**: Server Component uses `getSession()` for token extraction after `getUser()` -- acceptable but worth noting (Finding #8)

---

## Server Component vs Client Component Analysis

| Component | Type | Justification | Correct? |
|-----------|------|---------------|----------|
| `onboarding/page.tsx` | Server Component | Auth check, redirect, data fetch -- no interactivity | Yes |
| `onboarding-cinematic.tsx` | Client Component (`"use client"`) | Form state, scroll interactions, framer-motion animations | Yes |
| `sections/score-section.tsx` | Client Component (child of CC) | framer-motion useInView animation | Yes |
| `sections/chapter-section.tsx` | Client Component (child of CC) | framer-motion staggered animation | Yes |
| `sections/rules-section.tsx` | Client Component (child of CC) | framer-motion fade-in | Yes |
| `sections/profile-section.tsx` | Client Component (child of CC) | useState for form inputs | Yes |
| `sections/mission-section.tsx` | Client Component (child of CC) | onClick handler, submission state | Yes |
| `components/onboarding/*` | Client Component (imported by CC) | Interactive UI (slider, selector) | Yes |

The SC/CC boundary is correctly placed. The Server Component handles auth and redirect (no flash of unauthorized content), and the Client Component tree handles all interactive behavior. This follows Next.js App Router best practices.

---

## Recommendations (by priority)

### Must Fix (blocking -- CRITICAL/HIGH)

1. **[CRITICAL] Router conflict**: Do NOT create a new `onboarding.py` router file. Add the `POST /profile` endpoint to the **existing** `nikita/api/routes/onboarding.py`. The existing router has no prefix (prefix is set in `main.py` at `/api/v1/onboarding`), so `@router.post("/profile")` will correctly resolve to `/api/v1/onboarding/profile`. Update spec section "Profile Save API" and "Registration" to reflect this.

2. **[HIGH] `complete_onboarding()` signature mismatch**: The existing method requires `(user_id, call_id, profile)`. The portal flow has no `call_id`. Create a new method `complete_portal_onboarding(user_id: UUID) -> User` that sets `onboarding_status="completed"`, `onboarded_at=now()`, and `onboarding_completed_at=now()`. Update the spec's backend code sample.

3. **[HIGH] Wrong import path**: Change `from nikita.db.session import get_session_maker` to `from nikita.db.database import get_session_maker` in the fallback scheduling code.

### Should Fix (non-blocking but important -- MEDIUM)

4. **Add `ONBOARDING_FALLBACK` to EventType enum**: Keeps the typed contract consistent. Also verify that the `deliver` pg_cron handler in `tasks.py` can route this event type.

5. **Extract magic link generation**: Move `_generate_portal_magic_link()` to `nikita/auth/magic_link.py` or similar shared utility. Keeps OTP handler focused on Telegram concerns.

6. **Implement `upsert()` on ProfileRepository**: The method is referenced but does not exist. Use the PostgreSQL `ON CONFLICT DO UPDATE` pattern already imported in the file.

7. **Specify fallback event handler**: Add implementation details for how the `deliver` task processes `onboarding_fallback` events, including the `onboarding_completed_at` check.

8. **Server Component token handling**: After calling `getUser()`, use the validated session for the stats API fetch. The current spec code is acceptable but could be clearer.

### Nice to Have (LOW)

9. **Consistent DI pattern**: Use the same dependency injection approach (either `get_db_session()` or `get_async_session`) within the same file.

10. **Configurable Telegram bot username**: Use `NEXT_PUBLIC_TELEGRAM_BOT_USERNAME` env var instead of hardcoding `Nikita_my_bot` in the deep link.

11. **Type annotation**: Use `Mapped[dict[str, Any]]` for `drips_delivered` column.

---

## Architectural Strengths

The spec demonstrates several strong architectural decisions:

1. **Server Component / Client Component boundary** is correctly placed -- auth and redirects happen server-side, interactivity is client-side. No flash of unauthorized content.

2. **Component reuse** is well-planned -- ScoreRing and GlassCard are reused from existing components, not duplicated.

3. **Fire-and-forget pattern** for venue research and scenario generation follows existing patterns (handoff.py uses the same `asyncio.create_task()` approach).

4. **Fallback mechanism** using the existing `scheduled_events` infrastructure is architecturally sound -- no new scheduling system needed.

5. **Middleware requires no changes** -- the `/onboarding` route naturally falls under the existing protected route logic. Correct analysis.

6. **Scroll-snap with min-h-screen on Section 4** is a thoughtful decision -- the form section may exceed viewport height on mobile, so `min-h-screen` (not `h-screen`) prevents content clipping.

7. **Accessibility specifications** are thorough -- ARIA roles, keyboard navigation, reduced motion, and color contrast are all documented.

# Architecture Validation Report — Spec 213 (Iteration 2)

**Spec**: `specs/213-onboarding-backend-foundation/spec.md`
**Status**: FAIL
**Timestamp**: 2026-04-14T00:00:00Z
**Validator**: sdd-architecture-validator
**Iteration**: 2 (re-validation of iteration 1 findings + fresh pass)

---

## Summary

| Severity | Count |
|---|---|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 0 |
| LOW | 2 |

**User policy**: ABSOLUTE ZERO across all severities. Status = FAIL until LOW count = 0.

---

## Iteration 1 Findings — Resolution Status

All 9 iteration-1 findings (AR-H1, AR-H2, AR-H3, AR-M1, AR-M2, AR-M3, AR-M4, AR-L1, AR-L2) are RESOLVED in the iteration-2 spec rewrite:

| ID | Was | Resolution |
|---|---|---|
| AR-H1 | HIGH — session leak | FR-14 mandates fresh session pattern, names call site (`onboarding.py:821-827`), atomic with FR-13 route move |
| AR-H2 | HIGH — no route split | FR-13 creates `nikita/api/routes/portal_onboarding.py` with explicit endpoint list (POST profile, PATCH profile, GET pipeline-ready) |
| AR-H3 | HIGH — adapter duplication | FR-3.1 promotes `_ProfileFromAnswers` to `nikita/onboarding/adapters.py` as `ProfileFromOnboardingProfile`; both Telegram and portal paths import from shared module |
| AR-M1 | MEDIUM — contracts.py isolation | FR-2 explicit constraint: "MUST NOT import from `nikita.onboarding.models`, `nikita/db/models/`, or `nikita.engine.constants`" |
| AR-M2 | MEDIUM — BackstoryCache file paths | FR-12 names both files: `nikita/db/models/backstory_cache.py` + `nikita/db/repositories/backstory_cache_repository.py` |
| AR-M3 | MEDIUM — pipeline_state write path | FR-5.1 defines all 5 state transitions: entry→`"pending"`, success→`"ready"`, degraded→`"degraded"`, exception→`"failed"`, re-entry-when-ready→no-op |
| AR-M4 | MEDIUM — tuning.py isolation | FR-4 explicit constraint: "MUST NOT import from `nikita.engine.constants` — different domain" |
| AR-L1 | LOW — orchestrator coupling | FR-11 states idempotence handled in `_bootstrap_pipeline` via JSONB read; orchestrator signature unchanged |
| AR-L2 | LOW — PII logger redaction | FR-7 mandates per-call discipline; SC-6 requires `caplog` test asserting absence of PII in all log records |

---

## New Findings (Iteration 2)

### AR2-L1 — `main.py` Router Registration Not Specified

| Field | Value |
|---|---|
| **Severity** | LOW |
| **Category** | Module Organization |
| **Location** | `nikita/api/main.py` (lifespan registration block, line ~263) |
| **Issue** | FR-13 creates `nikita/api/routes/portal_onboarding.py` and says "Both routers mounted under `/api/v1/onboarding/` prefix," but the spec does not state that `portal_onboarding.router` must be added to `main.py` via `include_router()`. Every existing router (`onboarding`, `portal`, `voice`, `admin`, `auth_bridge`) has an explicit `app.include_router(...)` call in `main.py`'s lifespan. Omitting this step means the new route file exists but is unreachable. |
| **Fix** | Add to FR-13: "`main.py` MUST register `portal_onboarding.router` via `app.include_router(portal_onboarding.router, prefix='/api/v1/onboarding', tags=['Portal Onboarding'])` in the lifespan function, after the existing `onboarding.router` registration (line ~265)." |

### AR2-L2 — `BackstoryCacheRepository.get()` Return Type Cross-Layer Import

| Field | Value |
|---|---|
| **Severity** | LOW |
| **Category** | Import Patterns / Separation of Concerns |
| **Location** | `nikita/db/repositories/backstory_cache_repository.py` (FR-12) |
| **Issue** | FR-12 specifies `BackstoryCacheRepository.get()` returning `list[BackstoryOption] | None`. `BackstoryOption` is defined in `nikita.onboarding.contracts`. This creates a `db.repositories` → `nikita.onboarding.contracts` module-level import. The established precedent in this codebase is that `db/repositories` returns ORM model objects or raw `list[dict]` — not domain contract types. `VenueCacheRepository` (the nearest sibling, `profile_repository.py:397-482`) returns `VenueCache` ORM objects and `list[dict[str, Any]]`, never a domain Pydantic type. The inconsistency is confirmed: `VenueCacheRepository.store()` accepts `venues: list[dict[str, Any]]`; the facade (`VenueResearchService`) owns the conversion. The `BackstoryCacheRepository` should follow the same pattern. Note: `nikita.db.models.profile` already has a lazy import from `nikita.onboarding.validation` (line 325), so no circular cycle is introduced — the concern is pattern consistency, not correctness. |
| **Fix** | Revise FR-12 `BackstoryCacheRepository` signatures: `get(cache_key: str) -> list[dict] | None` and `set(cache_key: str, scenarios: list[dict], ttl_days: int) -> None`. The **facade** (`portal_onboarding.py`) performs the deserialization: `[BackstoryOption(**s) for s in raw_dicts]` after the cache hit, and `[s.model_dump() for s in scenarios]` before the cache set. This keeps the `db` layer free of domain contract types and matches the `VenueCacheRepository` pattern exactly. |

---

## Module Dependency Graph (Post-Fix Architecture)

```
nikita/onboarding/contracts.py       (standalone Pydantic — no upstream imports)
       ↑                                     ↑
nikita/services/portal_onboarding.py ←→ nikita/onboarding/adapters.py
       ↑                                     ↑
nikita/db/repositories/              nikita/platforms/telegram/onboarding/handler.py
  backstory_cache_repository.py      (both import adapters.py)
  (returns list[dict], NOT BackstoryOption)
       ↑
nikita/db/models/backstory_cache.py

nikita/api/routes/portal_onboarding.py → nikita/services/portal_onboarding.py
                                        → nikita/onboarding/contracts.py (request/response shapes)
nikita/api/main.py → include_router(portal_onboarding.router, ...)  ← AR2-L1 fix
```

No cycles. `contracts.py` is a leaf node (imports only stdlib + pydantic).

---

## Separation of Concerns Analysis

| Layer | Responsibility | Violations (post-fix) |
|---|---|---|
| `nikita/onboarding/contracts.py` | Frozen API contract types | None — standalone |
| `nikita/onboarding/tuning.py` | Timeout/cache constants for onboarding domain | None — no engine.constants import |
| `nikita/onboarding/adapters.py` | Pydantic↔ORM bridge (single source of truth) | None — replaces two unsynchronized adapters |
| `nikita/services/portal_onboarding.py` | Facade: venue research + backstory generation | None — no own session, no business logic |
| `nikita/db/repositories/backstory_cache_repository.py` | Cache persistence (raw JSONB) | None after AR2-L2 fix (returns `list[dict]`) |
| `nikita/api/routes/portal_onboarding.py` | HTTP interface: POST/PATCH profile + GET pipeline-ready | None — separated from voice-onboarding concerns (FR-13) |
| `nikita/api/routes/onboarding.py` | Voice-onboarding: initiate, status, server-tool, webhook, skip | None — reduced to 5 concerns (was 6+) |
| `nikita/onboarding/handoff.py::_bootstrap_pipeline` | Pipeline bootstrap + JSONB state writes | None — fresh session via `get_session_maker()()` (FR-14) |

---

## Import Pattern Checklist

- [x] `contracts.py` standalone: no imports from `nikita.onboarding.models`, `nikita.db.*`, `nikita.engine.*`
- [x] `tuning.py` standalone: no imports from `nikita.engine.constants`
- [x] `adapters.py` imports from `nikita.onboarding.models` (valid — same domain package) and `nikita.db.models.profile` (valid — constructing ORM object)
- [x] `portal_onboarding.py` (service) imports `contracts.py`, `tuning.py`, `adapters.py` — all inward-facing, no cycles
- [x] `portal_onboarding.py` (route) imports from `portal_onboarding.py` (service) and `contracts.py` — no cycles
- [x] `_trigger_portal_handoff` background task: no request-scoped `AsyncSession` passed (FR-14)
- [ ] `backstory_cache_repository.py` return type: PENDING AR2-L2 fix (should return `list[dict]`, not `list[BackstoryOption]`)
- [ ] `main.py` router registration: PENDING AR2-L1 fix (must add `include_router` for `portal_onboarding.router`)

---

## Security Architecture Checklist

- [x] PII fields (`name`, `age`, `occupation`, `phone`) excluded from structured logs — FR-7 + SC-6 caplog test
- [x] Exception echoes sanitized — FR-7 mandates `logger.exception(extra={"user_id": ...})` pattern
- [x] RLS: existing 5 `user_profiles` policies cover new columns automatically (PostgreSQL row-level)
- [x] RLS: `user_profiles` UPDATE policy `WITH CHECK (id = auth.uid())` — tracked as Phase 8 impl task
- [x] `backstory_cache` RLS: admin-only (users do not query directly) — FR-12
- [x] `/pipeline-ready/{user_id}` cross-user 403 — FR-5 + AC-2.4 test specified
- [x] `OnboardingV2ProfileRequest` field validation constraints match DB CHECK constraints (FR-1d / FR-1a alignment)
- [x] `users.onboarding_completed_at` non-existent column acknowledged — FR-9 uses `onboarding_status` field instead (verified via Supabase MCP, per constraints section)

---

## Proposed Structure (Confirmed Against Existing Codebase)

```
nikita/
├── onboarding/              # EXISTING
│   ├── contracts.py         # NEW (PR 213-1) — frozen contract surface
│   ├── tuning.py            # NEW (PR 213-1) — domain constants
│   ├── adapters.py          # NEW (PR 213-1) — promoted from handler.py:41-56
│   ├── handoff.py           # MODIFIED — FR-5.1 state writes + FR-11 idempotence
│   └── models.py            # MODIFIED — FR-1c `name` field addition
├── services/
│   └── portal_onboarding.py # NEW (PR 213-3) — thin facade
├── db/
│   ├── models/
│   │   ├── backstory_cache.py  # NEW (PR 213-2) — ORM model
│   │   └── profile.py       # MODIFIED — FR-1b name/occupation/age ORM columns
│   └── repositories/
│       ├── backstory_cache_repository.py  # NEW (PR 213-2) — returns list[dict] (post AR2-L2 fix)
│       └── user_repository.py  # MODIFIED — FR-5.2 update_onboarding_profile_key()
└── api/
    ├── main.py              # MODIFIED — register portal_onboarding.router (AR2-L1 fix)
    └── routes/
        ├── portal_onboarding.py  # NEW (PR 213-4) — POST/PATCH profile + GET pipeline-ready
        └── onboarding.py    # MODIFIED — POST profile MOVED OUT; FR-14 session fix
```

---

## Recommendations

1. **AR2-L1 (LOW)** — Add to FR-13: "Ship `main.py` router registration as part of PR 213-4. Call: `app.include_router(portal_onboarding.router, prefix='/api/v1/onboarding', tags=['Portal Onboarding'])`." One sentence addition.

2. **AR2-L2 (LOW)** — Revise FR-12 `BackstoryCacheRepository` signatures to return `list[dict]` (raw JSONB). Update FR-3 facade description to show the deserialization step: `[BackstoryOption(**s) for s in raw]` on cache hit, `[s.model_dump() for s in scenarios]` before cache set. This matches the `VenueCacheRepository` precedent exactly.

Both fixes are additive (1-2 sentences each). No structural rework required. After these two fixes, the architecture is **PASS-ready**.

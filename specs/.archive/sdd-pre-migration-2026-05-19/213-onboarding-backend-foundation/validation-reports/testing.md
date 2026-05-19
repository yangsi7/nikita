# Testing Validation Report — Spec 213

**Spec**: `specs/213-onboarding-backend-foundation/spec.md`
**Status**: FAIL (iteration 2)
**Timestamp**: 2026-04-14T17:30:00Z
**Validator**: sdd-testing-validator
**Iteration**: 2 (re-validation after iteration-1 rewrite)

---

## Summary

| Severity | Count |
|---|---|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 2 |
| LOW | 2 |

**Iteration 1 → Iteration 2 delta**: 3 HIGH resolved, 5 MEDIUM resolved to 2, 3 LOW resolved to 2.

---

## Iteration 1 HIGH Findings — Resolution Status

| ID | Original Issue | Status |
|---|---|---|
| T-H1 | No test file names for NFR-3 log events | RESOLVED — `tests/onboarding/test_log_observability.py` added to inventory (spec:626) |
| T-H2 | No ASGI integration test for SC-2 blocking gate | RESOLVED — `tests/onboarding/test_pipeline_gate_integration.py` named in inventory (spec:622) with ASGI transport |
| T-H3 | AC-2.2 polling mock fixture undefined (vacuous-pass risk) | RESOLVED — `side_effect=[{"pipeline_state":"pending"}]*4 + [{"pipeline_state":"ready"}]` explicitly specified in AC-2.2 (spec:488) |

---

## Findings

### MEDIUM Findings

| ID | Category | Issue | Location | Recommendation |
|---|---|---|---|---|
| T-M1 | Coverage Infrastructure | NFR-7 CI command omits `nikita.api.routes.portal_onboarding` from `--cov=` arguments. The route file has an explicit 85% target but will not be measured or gated by the CI command as written. Additionally, `--cov-fail-under=90` is a single combined threshold and cannot enforce the per-module split (100% for contracts/tuning/adapters vs 85% for routes vs 90% for facade). | spec:606 | Replace single `--cov-fail-under` with per-module `--cov-fail-under` or use `pytest-cov` `[coverage:report]` config. At minimum add `--cov=nikita.api.routes.portal_onboarding` to the CI command. Accept that enforcement of 100% vs 85% split requires either separate CI steps or `omit`/`fail_under` in `setup.cfg`/`pyproject.toml`. |
| T-M2 | Test Inventory Completeness | Two test file/function names are referenced in AC bodies but absent from the Test File Inventory table (spec:612-628): (1) `tests/api/routes/test_voice_pre_call_webhook.py::test_payload_includes_v2_profile_response` (AC-7.2, spec:553) and (2) `test_portal_onboarding_session_isolation` (Risks table, spec:690). The first file does not exist on disk. An implementer doing TDD strictly from the inventory misses these tests, leaving AC-7.2 (voice webhook V2 payload shape — P2) and the CRITICAL-impact session-leak risk without verified coverage. | spec:553, spec:690 | Add `tests/api/routes/test_voice_pre_call_webhook.py` and `test_portal_onboarding_session_isolation` (proposed home: `tests/services/test_portal_onboarding_facade.py`) to the Test File Inventory with their purpose and marker. |

### LOW Findings

| ID | Category | Issue | Location | Recommendation |
|---|---|---|---|---|
| T-L1 | Spec Accuracy | `compute_backstory_cache_key(profile)` is called in FR-3 (spec:174) but the function is not defined in any FR, not assigned to a module, and does not exist in the codebase. FR-4 defines `AGE_BUCKETS` and `OCCUPATION_CATEGORIES` which are inputs to this function, implying it lives in `tuning.py` or `portal_onboarding.py`, but the spec is silent. An implementer must infer the home module. | spec:174 | Add one sentence to FR-3: "Function `compute_backstory_cache_key` defined in `nikita/onboarding/tuning.py` (FR-4 module); signature: `def compute_backstory_cache_key(profile: UserOnboardingProfile) -> str`." |
| T-L2 | Coverage Gap (minor) | `test_tuning_constants.py` is described as "regression guards on every constant" (spec:616) but FR-4 defines 8 constants including `AGE_BUCKETS` (a tuple of tuples) and `OCCUPATION_CATEGORIES` (a dict). These compound types require non-trivial equality assertions. The spec does not specify what "regression guard" means for compound types — a simple `assert constant == expected_value` check may not catch structural drift (e.g., bucket boundary shift). | spec:274, spec:616 | Add a note to the Test File Inventory row for `test_tuning_constants.py`: "Compound constants (`AGE_BUCKETS`, `OCCUPATION_CATEGORIES`) use deep-equality assertion; `AGE_BUCKETS` checks that every boundary is inclusive via range membership test." |

---

## Testing Pyramid Analysis

**Target**: Unit ~70% / Integration ~25% / E2E ~5%

**Spec inventory (13 test files):**

```
Unit       (~70%): test_tuning_constants, test_contracts, test_adapters,
                   test_pipeline_bootstrap, test_handoff (extended), 
                   test_r8_conversation_continuity, test_log_observability,
                   test_backstory_cache_repository
                   → 8 files, 62%

Integration (~25%): test_portal_onboarding_facade, test_portal_onboarding (routes),
                    test_pipeline_gate_integration, test_rls_user_profiles
                    → 4 files, 31%

E2E          (~5%): test_e2e (extended)
                    → 1 file, 7%
```

**Assessment**: Pyramid is ACCEPTABLE. The spec correctly deviates from strict 70/20/10 toward 62/31/7 — justified by the heavy JSONB + async integration surface (facade with two external services, pipeline gate, RLS policies). Integration layer at 31% is elevated but appropriate for the integration density of this spec.

---

## AC Testability Analysis

| AC ID | AC Description | Testable | Test Type | Issue |
|---|---|---|---|---|
| AC-1.1 | POST accepts name/age/occupation without 422 | Yes | Integration | — |
| AC-1.2 | JSONB contains all fields after submission | Yes | Integration (Supabase MCP) | Supabase MCP read acceptable for integration gate |
| AC-1.3 | user_profiles row contains new columns | Yes | Integration | — |
| AC-1.4 | First Telegram message in 25s with 2 tokens | Yes | E2E | Marked e2e, excluded from unit CI — correct |
| AC-1.5 | No "So we meet again" fallback opener | Yes | Unit | Regex assert — clear |
| AC-2.1 | pipeline-ready returns all 4 states | Yes | Integration | Parametrized over 4 states — clear |
| AC-2.2 | Polling terminates | Yes | Integration | side_effect fixture explicitly specified — no vacuous-pass risk |
| AC-2.3 | 20s timeout → degraded | Yes | Integration | — |
| AC-2.4 | Cross-user 403 with correct body | Yes | Integration | — |
| AC-3.1 | Venue timeout: returns within budget+1s | Yes | Integration | time.monotonic() assertion specified |
| AC-3.2 | caplog contains timeout record | Yes | Integration | caplog fields enumerated |
| AC-3.3 | First message on scene-only fallback | Yes | Unit | — |
| AC-3.4 | pipeline_state → "degraded" on timeout | Yes | Unit | — |
| AC-4.1 | BackstoryGenerator RuntimeError → [] | Yes | Integration | patch target specified at source module |
| AC-4.2 | First message keeps flavor on backstory fail | Yes | Unit | — |
| AC-4.3 | caplog on backstory failure, no PII | Yes | Integration | caplog fields + PII assertion specified |
| AC-4.4 | pipeline_state → "degraded" on backstory fail | Yes | Unit | — |
| AC-5.1 | Pipeline loads seeded turn | Yes | Unit | — |
| AC-5.2 | Agent prompt includes prior assistant turn | Yes | Unit | call_args assertion specified |
| AC-5.3 | No denial phrases N=10 | Yes | Unit | patch target + loop count specified |
| AC-5.4 | Independent from US-1 | Yes | Unit | — |
| AC-6.1 | wizard_step returned in response | Yes | Integration | portal navigation deferred to Spec 214 — correct scope |
| AC-6.2 | PATCH merges JSONB without reset | Yes | Integration | — |
| AC-6.3 | null fields for unset fields | Yes | Integration | — |
| AC-6.4 | Cache hit skips Claude | Yes | Integration | — |
| AC-7.1 | Phone → execute_handoff_with_voice_callback | Yes | Unit | Existing test referenced |
| AC-7.2 | Webhook receives OnboardingV2ProfileResponse | Yes | Integration | File not in Test File Inventory — see T-M2 |
| AC-7.3 | Voice prompt includes backstory hooks | Yes | Unit | — |
| AC-7.4 | Voice-callback failure falls back to Telegram | Yes | Unit | Existing per Spec 212 |
| SC-6 | PII absent from structured logs | Yes | Unit | caplog test named; static rg audit also specified |
| SC-7 | RLS covers new columns | Yes | Integration | @pytest.mark.integration, live Supabase, non-blocking |
| SC-9 | Coverage thresholds met | Partial | CI gate | See T-M1 — CI command incomplete |

---

## Test Scenario Inventory

**E2E Scenarios:**

| Scenario | Priority | User Flow | Status |
|---|---|---|---|
| `test_full_profile_personalizes_first_message` | P1 | Portal profile → Telegram first message with ≥2 tokens | Named in spec:628, @pytest.mark.e2e |

**Integration Test Points:**

| Component | Integration Point | Mock Required |
|---|---|---|
| `portal_onboarding.process()` | VenueResearchService + BackstoryGeneratorService | AsyncMock with side_effect |
| `GET /pipeline-ready/{user_id}` | UserRepository JSONB read | mock_user_repo.get.return_value |
| `POST /onboarding/profile` | FastAPI TestClient | test_portal_onboarding.py |
| `PATCH /onboarding/profile` | jsonb_set merge semantics | test_portal_onboarding.py |
| Pipeline gate ASGI test | ASGI transport + poll loop | test_pipeline_gate_integration.py |
| RLS on user_profiles | Live Supabase | @pytest.mark.integration only |
| BackstoryCacheRepository | upsert + TTL filter | AsyncMock session |

**Unit Test Coverage:**

| Module | Functions/Classes | Coverage Target |
|---|---|---|
| `contracts.py` | 6 Pydantic types | 100% |
| `tuning.py` | 8 constants | 100% |
| `adapters.py` | ProfileFromOnboardingProfile.from_pydantic | 100% |
| `portal_onboarding.py` (service) | process() — happy/timeout/failure/cache | ≥90% line+branch |
| `portal_onboarding.py` (routes) | POST, PATCH, GET pipeline-ready | ≥85% line |
| `handoff.py` (extended) | FirstMessageGenerator.generate with backstory | unit coverage via existing file |

---

## TDD Readiness Checklist

- [x] ACs are specific — all ACs name exact test file + assertion type
- [x] ACs are measurable — quantified: N=10, ≤200ms, ≥2 tokens, 20s cap, etc.
- [x] Test types clear per AC — unit/integration/e2e marker specified per file
- [x] Red-green-refactor path clear — Test File Inventory provides the full TDD surface
- [x] Non-empty fixtures required — AC-2.2 and FR-11 explicitly specify side_effect lists
- [x] Patch targets at source module — FR-3 Patch Convention section (spec:636-639) lists source-module patches
- [ ] Test File Inventory complete — 2 referenced test names absent (T-M2)

---

## Coverage Requirements

- [x] Overall target specified (NFR-7, spec:600-606)
- [x] Critical path coverage — contracts/tuning/adapters at 100%; facade at 90%
- [ ] Per-module enforcement in CI — `--cov-fail-under=90` single threshold; route file absent from `--cov=` args (T-M1)
- [x] Exclusions documented — RLS tests `@pytest.mark.integration` excluded from unit CI gate; E2E `@pytest.mark.e2e` excluded

---

## Recommendations

1. **(T-M1 — Medium)** Add `--cov=nikita.api.routes.portal_onboarding` to the NFR-7 CI command. To enforce per-module thresholds, add a `[coverage:report]` section to `pyproject.toml` with `fail_under` per module, or run two separate `pytest --cov` commands in CI (one for ≥100% modules, one for ≥85% route). Current command silently allows the route file to have 0% coverage.

2. **(T-M2 — Medium)** Add the following rows to the Test File Inventory table:
   - `tests/api/routes/test_voice_pre_call_webhook.py` | AC-7.2: verify V2 profile response shape in voice pre-call webhook payload | integration
   - Row in `tests/services/test_portal_onboarding_facade.py` already covers the facade; add a note that `test_portal_onboarding_session_isolation` lives there, verifying that background tasks open fresh sessions (FR-14 mitigation for CRITICAL-impact risk).

3. **(T-L1 — Low)** Assign `compute_backstory_cache_key` to a module explicitly in FR-3 or FR-4 (recommended: `nikita/onboarding/tuning.py`, since it uses `AGE_BUCKETS` and `OCCUPATION_CATEGORIES`). Add its signature to FR-3 prose and include it in `test_tuning_constants.py` coverage scope.

4. **(T-L2 — Low)** Annotate the `test_tuning_constants.py` inventory row to specify that `AGE_BUCKETS` and `OCCUPATION_CATEGORIES` regression tests use deep-equality plus a structural sanity check (e.g., bucket count, key membership) rather than bare value comparison. This prevents silent drift if a bucket boundary shifts without a failing test.

# Implementation Plan — Spec 216 Onboarding Redesign Cinematic Agentic Wizard

**Spec ID**: 216-onboarding-redesign-cinematic
**Plan Status**: Draft (Phase 5)
**Date**: 2026-04-30
**Predecessor artifacts**: `spec.md`, `subspecs/216-{A..F}/spec.md`, `wireframes/{ascii,figma,motion-spec}.md`, `validation-findings.md` (GATE 2 PASS at 050bdc1; copy refinement amendment 2026-04-30 at 99f0f77 + 19985aa).

---

## 1. Plan Scope

This plan is a **coordination artifact** for the 6-subspec decomposition. Per-PR architecture, file paths, and ACs live in the subspec spec.md files. This master plan owns:

- Cross-PR sequencing + dependency graph
- Cross-cutting type system + interface contracts (already canonicalized in master spec.md §"Type System Anchors")
- PR plan with size estimates + ship gates
- Reuse map (existing files extended vs. new files)
- Risk register with mitigations
- Verification strategy (test ladder, W4 walk gate)

It does NOT duplicate content from subspec specs. When in doubt, the subspec is authoritative.

---

## 2. Architecture Decisions Carried From Spec

These decisions are LOCKED at GATE 1 and were validated at GATE 2. They drive every task in `tasks.md`:

| Decision | Reference | Rationale |
|----------|-----------|-----------|
| Single Telegram-canonical signup path | FR-01 / 216-A | Eliminates 2-route ambiguity; STEP-0 verdict 2026-04-29 |
| Pydantic AI 1.71.0, single agent, discriminated `output_type=[TurnOutput, TurnFailure]` | FR-04 / 216-B | Closes Walk V tool fan-out anti-pattern; agentic-design-patterns Rule #3 |
| Cumulative `WizardSlots` server-side state via `model_copy(update={...})` | FR-03 / 216-B | Closes #441 false-equivalence; Rule #1 |
| Completion gate = `FinalForm.model_validate(state.slots_dict)` | FR-03 / 216-B | Pydantic validation IS the gate; Rule #2 |
| `instructions=callable` per-turn (NOT `system_prompt`) | FR-04 / 216-B | Pydantic AI doc: instructions reevaluated even with `message_history`; Rule #5 |
| `agent.run(..., message_history=...)` for multi-turn | FR-04 / 216-B | Official primitive; Rule #6 |
| Big Five inference HIDDEN from UI | NR-05 / 216-D | Replika/Pi.ai precedent; relational illusion |
| 4 firecrawl tools always-fetch-something + cohort cache | FR-07 / 216-E | AGI-feel agency vs. pre-baked fetches |
| 12-archetype curated taxonomy for backstory | FR-09 / 216-C+D | No LLM-invented labels (validator-rejected) |
| Inherits Spec 208 visual identity verbatim | FR-10 / 216-C | No new design primitives |
| Path A (voice_tone_pref standalone slot) | C1.18 amendment 2026-04-30 | 12-slot taxonomy unchanged; 15 visual screens |
| Combined `together_we_could` + `same_weird_if` dual-textarea screen | C1.18 amendment | CRO free-text-fatigue mitigation; +9% completion (Hinge precedent) |

---

## 3. PR Decomposition + Ship Order (audit-fix iter-2: 216-C split into C1 + C2)

```
              ┌──────────┐
              │  216-A   │  Telegram routing fix (~80 LOC + ~50 LOC tests)
              │ STEP-0   │  GATE: T-A-1 golden test + A1.1-A1.14 ACs green
              └─────┬────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
  ┌──────────┐            ┌──────────┐
  │  216-B   │            │  216-D   │
  │ Wizard   │            │ Data     │  Migration + Big5 + archetypes + cohort (~250 LOC)
  │ core     │            │ inference│
  │ (~350 LOC│           └─────┬────┘
  │ + 250 t) │                 │
  └─────┬────┘                 │
        │                      │
        │      ┌───────────────┘
        │      │
        ▼      ▼
  ┌──────────┐  ┌──────────┐
  │  216-C1  │  │  216-E   │
  │ FE shell │  │ Tools    │  4 firecrawl + cost guard + prompt cache (~200 LOC)
  │ chrome+  │  │ +cache   │
  │ a11y+auth│  └─────┬────┘
  │ (~350 LOC│        │
  └─────┬────┘        │
        │             │
        ▼             │
  ┌──────────┐        │
  │  216-C2  │        │
  │ FE slot  │        │
  │ screens  │        │
  │ +HobbyCh │        │
  │ +Cards   │        │
  │ (~400 LOC│        │
  └─────┬────┘        │
        │             │
        └──────┬──────┘
               ▼
          ┌──────────┐
          │  216-F   │  M1-M4 unit + W4 walk + GH closure (~150 LOC + walk artifact)
          │ Tests+W4 │  (3 mandatory test classes shipped with 216-B as ship gate)
          └──────────┘
```

**Ship order**: A → (B ∥ D) → (C1 ∥ E) → C2 → F.

| PR | Subspec | LOC est. | Tasks | Depends on | Parallelizable with | Ship gate (binary, all ACs in subspec) |
|----|---------|----------|-------|------------|---------------------|----------------------------------------|
| 216-A | telegram-canonical-routing | ~130 | T-A-1..T-A-8 (8) | none | — | A1.1-A1.14 + 8 routing tests green |
| 216-B | agentic-wizard-core | ~600 | T-B-1..T-B-18 (18) | 216-A | 216-D | B1.1-B1.22 + 3 mandatory test classes (T-B-3, T-B-7, T-B-17) green |
| 216-D | data-layer-inference | ~250 | T-D-1..T-D-9 (9) | 216-A | 216-B | D1.1-D1.12 + RLS verified post-migration |
| 216-C1 | cinematic-frontend (shell+chrome+a11y) | ~350 | T-C1-1..T-C1-12 (12) | 216-B + 216-D | 216-E | C1.2-C1.5, C1.8-C1.17, C1.20 + vitest green |
| 216-C2 | cinematic-frontend (screens+chips+cards) | ~400 | T-C2-1..T-C2-6 (6) | 216-C1 | — | C1.1, C1.6-C1.7, C1.18-C1.19 + integration test green |
| 216-E | agentic-tools-firecrawl | ~200 | T-E-1..T-E-9 (9) | 216-B | 216-C1 | E1.1-E1.12 + cost guard test green |
| 216-F | testing-and-w4-walk | ~150 + walk | T-F-1..T-F-7 (7) | A, B, C1, C2, D, E | — | F1.2/F1.4-F1.9 + W4 walk PASS (G.1-G.11). F1.1 already shipped with 216-B as ship gate. |

Total: ~2,080 LOC + walk artifact across **7 PRs** (was 6; 216-C split). Each PR within `pr-workflow.md` 400-line cap.

---

## 4. Reuse Map (Verified 2026-04-29 via intel-explore)

**Existing files extended** (line ranges verified at GATE 2):

| File | Lines | Action | Subspec |
|------|-------|--------|---------|
| `nikita/agents/onboarding/state.py` | `:88-328` | Extend `WizardSlots` to 13 fields (matching SlotKind enum per FR-02 reconciliation) + `FinalForm` model | 216-B |
| `nikita/agents/onboarding/conversation_agent.py` | `:127-197` | REWRITE `_create_conversation_agent` block; types L69-126 reused | 216-B |
| `nikita/agents/onboarding/conversation_prompts.py` | `:33-115`, `:128` | REPLACE `_WIZARD_FRAMING` with M1-M4 templates + `render_dynamic_instructions` rewrite | 216-B |
| `nikita/agents/onboarding/question_registry.py` | `:42-79` | Extend to 13 entries + introduce `SlotKind` StrEnum (13 members per spec L360-374) | 216-B |
| `nikita/agents/onboarding/regex_fallback.py` | `:47` | DELETE — FE controls phone format | 216-B |
| `nikita/api/routes/telegram.py` | `:635-666` | Reroute bare `/start` for unbound users | 216-A |
| `nikita/platforms/telegram/commands.py` | `:343-348` | Refactor `_handle_start` E1 path; remove `_send_bare_portal_auth_link` if unused | 216-A |
| `nikita/api/routes/portal_onboarding.py` | `:799-1231` | DELETE deprecated `/converse` route; replace with `/answer` + `/state` | 216-B |
| `nikita/db/models/user.py` | (existing `User`) | Extend `User` (NOT `UserProfile`) with top-level columns `big5_vector` JSONB, `backstory_seed` text≤300, `brand_resonance_signal` numeric[0,1], `archetype_candidates` JSONB per D1.10 | 216-D |
| `portal/src/app/globals.css` + `components/landing/{aurora-orbs,glow-button}.tsx` | reuse verbatim | NO changes; import only | 216-C |

**New files created**:

| Path | Subspec | Purpose |
|------|---------|---------|
| `nikita/platforms/telegram/signup_handler.py` (verify exists; extend if needed) | 216-A | FSM entry point |
| `tests/platforms/telegram/test_routing.py` | 216-A | bare `/start` golden test |
| `nikita/agents/onboarding/follow_up_registry.yaml` | 216-B | M1 paired static fallbacks |
| `nikita/agents/onboarding/archetypes.py` | 216-D | curated 12-archetype taxonomy + label validator |
| `nikita/agents/onboarding/cohort_chips.py` | 216-D | 6-8 hand-seeded `(city, occupation)` cohort cache |
| `nikita/agents/onboarding/big5_judge.py` | 216-D | Per-turn Haiku Big5 inference |
| `nikita/agents/onboarding/tools/firecrawl_tools.py` | 216-E | 4 fetch_* tools |
| `nikita/agents/onboarding/cost_guard.py` | 216-E | Budget guard + circuit breaker |
| `supabase/migrations/NNN_user_profile_inference.sql` | 216-D | 3 new top-level columns on `public.users` + `archetype_candidates` JSONB + RLS policies + idempotent DO-block CHECK constraints (per D1.10/D1.11/D1.12) |
| `portal/src/app/onboarding/_components/{WizardShell,QuestionCard,ProgressRail,NikitaReaction,WhyWeAsk,HobbyChips,BackstoryArchetypeCards,CombinedDualTextarea,MidpointNudge}.tsx` | 216-C | Wizard component tree |
| `portal/src/app/onboarding/_components/controls/{TextInput,Slider,Chips,Scenarios,Radio,Tel}.tsx` | 216-C | Per-control-type primitives |
| `tests/agents/onboarding/test_{cumulative_state,completion_gate,tool_recovery,meta_prompts,cluster_enum_completeness,follow_up_registry_completeness,big5_judge,archetypes,firecrawl_tools,cost_circuit}.py` | 216-F | Backend test suite |
| `tests/api/routes/test_onboarding_answer.py` | 216-F | API integration |
| `portal/src/app/onboarding/_components/__tests__/{HobbyChips,BackstoryArchetypeCards,ProgressRail,WizardShell,CombinedDualTextarea,MidpointNudge}.test.tsx` | 216-F | Frontend vitest |
| `docs-to-process/20260{XXXX}-live-walk-W4-spec216.md` | 216-F | W4 walk artifact (post-deploy) |

---

## 5. Per-PR Task Index (bridges to `tasks.md`, audit-fix iter-2)

Each PR's tasks live in `tasks.md` with TaskCreate ID assignments. This section enumerates the task IDs per PR to keep cross-references stable. Iter-2 reflects audit findings (orphan ACs bound, 3 mandatory test classes moved to 216-B as ship gate, 216-C split into C1+C2).

| Task ID range | PR | Description | Worker | Count |
|---------------|-----|-------------|--------|-------|
| T-A-1..T-A-8 | 216-A | Routing fix + race + resume + purge guard + cleanup + plus-alias | implementor | 8 |
| T-B-1..T-B-18 | 216-B | Slots/FinalForm, agent rewrite, M1-M4, output_validator, message_history, HTTP API + deprecation shim + rate limit, **3 mandatory test classes (T-B-3, T-B-7, T-B-17)** | implementor | 18 |
| T-D-1..T-D-9 | 216-D | Migration (top-level columns + RLS + idempotent CHECK), Big5 judge, archetypes, cohort cache, ORM extension, PII-safe key, hide-the-framework | implementor | 9 |
| T-C1-1..T-C1-12 | 216-C1 | WizardShell, auth guard, ProgressRail, NikitaReaction/WhyWeAsk, controls, pending/error UI, resume, key uniqueness, auto-redirect, responsive, vocab grep, a11y | implementor | 12 |
| T-C2-1..T-C2-6 | 216-C2 | 15 base screens, HobbyChips, BackstoryArchetypeCards, CombinedDualTextarea, MidpointNudge, integration full-flow | implementor | 6 |
| T-E-1..T-E-9 | 216-E | 4 firecrawl tools, registration, cost guard, cohort cache, WebSearchTool, timeout, log shape, secret handling, prompt cache verification | implementor | 9 |
| T-F-1..T-F-7 | 216-F | M1-M4 unit + cost circuit integration + Big5/archetypes unit + FE vitest + W4 walk + GH closure + ROADMAP sync | implementor + walk subagent | 7 |

**Total: 69 tasks across 7 PRs.** AC coverage: 100% (89/89 subspec ACs bound to ≥1 task; see tasks.md Coverage Matrix).

---

## 6. Cross-Cutting Contracts (already in spec.md, referenced here for plan cohesion)

- **`SlotKind` StrEnum** (`nikita/agents/onboarding/question_registry.py`) — single source of truth across BE/FE.
- **`ConverseDeps` dataclass** — typed sidecar for `Agent(deps_type=ConverseDeps)` + `RunContext[ConverseDeps]`.
- **`AnswerRequest`/`AnswerResponse`/`StateResponse`** — Pydantic v2 HTTP schemas.
- **`ErrorEnvelope` + `ErrorCode` StrEnum** — uniform error surface.
- **`TurnOutput`/`TurnFailure`** discriminated by `kind: Literal[...]`.
- **Cookie contract**: `nikita-session` HttpOnly Secure SameSite=Lax Max-Age=604800.

---

## 7. Verification Strategy

### 7.1 Test ladder (per `.claude/rules/testing.md`)

Three mandatory agentic-flow test classes (CRIT, PR-blocker per `agentic-design-patterns.md`):

1. **Cumulative-state monotonicity** (`test_cumulative_state.py`) — 12-turn fixture asserts `progress_pct[t+1] >= progress_pct[t]`.
2. **Completion-gate triplet** (`test_completion_gate.py`) — empty/partial/full `FinalForm.model_validate` triplet.
3. **Mock-LLM-emits-wrong-tool recovery** (`test_tool_recovery.py`) — wrong-extraction → ModelRetry → recovery via deterministic fallback.

Plus M1-M4 golden snapshots, cluster enum exhaustiveness, follow_up_registry completeness, Big5 judge unit, archetypes label-validator unit, firecrawl budget guard + cohort cache, cost circuit breaker integration.

### 7.2 W4 live walk gate (216-F AC F1.7)

W4 walk MUST PASS G.1-G.11 from handover §Verification:
1. 12 fixed roots presented in correct order
2. M2 cluster confidence ≥0.6 OR depth-2 fires (≥1 occurrence)
3. M1 follow-ups fire on ≥2 prose roots
4. Big5 vector populated with ≥3 dimensions confidence ≥0.5
5. firecrawl tool fires ≥4 times across the wizard
6. 3 archetypes from curated 12 (no invented labels)
7. cost <$0.50/flow
8. visual screen count 15-25 (15 base + dynamic M1)
9. monotonic progress_pct
10. 0 mirror-echo
11. 0 banned vocab in any portal HTML

Walk follows `.claude/rules/live-testing-protocol.md` 12-step protocol. NO DB fabrication. NO `signInWithPassword`. NO `E2E_AUTH_BYPASS`.

### 7.3 Pre-merge gates (every PR)

1. `uv run pytest -q` (full nikita suite) for backend PRs.
2. `(cd portal && npm run test -- --run && npm run lint && npm run build)` for FE PRs.
3. `/qa-review --pr N` until 0 findings across ALL severities.
4. Post-merge smoke (auto-dispatched subagent): curl probe, log sweep, dogfood scenario.

---

## 8. Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R-1 | Two parallel `/start` handlers re-introduced post-216-A merge | LOW | HIGH | Golden test in `test_routing.py` asserts `_handle_start` NOT called for unbound `/start`. CI gate. |
| R-2 | Pydantic AI `output_type` + `builtin_tools` incompatibility on Anthropic | LOW | HIGH | Stay on Tool Output mode (default), do NOT use NativeOutput. Anthropic-only at launch (no Gemini). |
| R-3 | Big5 incremental cost overrun | MED | MED | Circuit at $0.05 budget remaining; per-dim ≥0.7 confidence short-circuits further probes. |
| R-4 | firecrawl latency cliff p99 >8s | MED | MED | Per-tool 3s timeout; `prepared_*` callable returns None when `state.location` absent (turn-0 skip). |
| R-5 | Static fallback registry drift (dynamic node missing fallback) | LOW | MED | Lint test `test_follow_up_registry_completeness.py` enforces; CI gate. |
| R-6 | STEP-0 fix exposes latent FSM bugs (#437 wrong-OTP) | MED | LOW | Acceptable; tracked separately. Document behavior in 216-A AC A1.8. |
| R-7 | Validator drift (re-validation after copy refinement reopens GATE 2) | LOW | LOW | Already absorbed. Validator re-run 2026-04-30 confirmed PASS. |
| R-8 | LLM tool-selection bias re-emerges post-merge | LOW | HIGH | Three mandatory test classes (cumulative-state, completion-gate, tool-recovery) catch regressions. |
| R-9 | Migration on prod with `onboarding_status='pending'` users in flight | LOW | MED | <100 in-flight users; safe to invalidate via migration on deploy. Spec assumption #4. |
| R-10 | Backstory archetype LLM returns invented labels | MED | MED | Validator rejects whole response; retry with stricter prompt; deterministic top-3 fallback. |
| R-11 | Concurrent magic-link clicks corrupt DB | LOW | MED | Idempotency: only one establishes session; other yields 400. AC F.2. Race-condition test. |
| R-12 | Cost circuit fires in normal happy-path flow | LOW | LOW | $0.50 hard ceiling; $0.30 median target; verified W4 walk G.7. |

---

## 9. Constitutional Compliance (Article III)

- [x] **100% requirement coverage**: every FR/NR maps to ≥1 subspec AC. Index verified in spec.md Appendix B.
- [x] **All tasks have 2+ testable ACs**: subspecs carry per-task AC tables; tasks.md will inherit.
- [x] **No circular dependencies**: ship order A → (B∥D) → (C∥E) → F is a DAG.
- [x] **Tasks sized 2-8 hours**: enforced in tasks.md (Phase 6).
- [x] **Dependency graph included**: §3 above.
- [x] **Reuse map**: §4 above.
- [x] **Risk register**: §8 above.
- [x] **Verification strategy**: §7 above.

---

## 10. Out-of-Scope (carry from spec.md §"Out of Scope")

Voice-note input, attachment-style inference, per-cohort hobby chip lists, Tree-of-Thought / MCTS / BSM, multi-language i18n, AB testing infrastructure, wrong-OTP session-purge fix (#437), `_vercel/insights` 404 (#449).

---

## 11. References

- Master spec: `specs/216-onboarding-redesign-cinematic/spec.md`
- 6 subspec specs: `specs/216-onboarding-redesign-cinematic/subspecs/216-{A..F}-*/spec.md`
- Wireframes: `specs/216-onboarding-redesign-cinematic/wireframes/{ascii,figma,motion-spec}.md`
- Validation findings: `specs/216-onboarding-redesign-cinematic/validation-findings.md`
- Validator reports: `specs/216-onboarding-redesign-cinematic/validation-reports/sdd-{api,architecture,auth,data-layer,frontend,testing}-validator.md`
- Rules: `.claude/rules/{agentic-design-patterns,testing,live-testing-protocol,pr-workflow,parallel-agents,subagent-safety}.md`

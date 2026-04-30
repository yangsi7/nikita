# Subspec 216-F — Testing + W4 Live Walk

**Parent**: `specs/216-onboarding-redesign-cinematic/spec.md` Test File Inventory + Verification §
**PR boundary**: 216-F (depends on 216-A, 216-B, 216-C, 216-D, 216-E all merged)
**Estimated**: ~300 LOC (3 mandatory test classes + M1-M4 unit tests + W4 walk script) + ~150 LOC fixtures
**Status**: Draft (GATE 1)

---

## Scope

The verification subspec. Implements:
1. The 3 MANDATORY agentic-flow test classes from `.claude/rules/testing.md` "Agentic-Flow Test Requirements".
2. M1-M4 meta-prompt unit tests with golden snapshot outputs.
3. Cluster enum exhaustiveness lint test.
4. Cost circuit-breaker integration test.
5. W4 battle-test live walk per `live-testing-protocol.md` 12-step protocol.
6. Closes 10 W3 GH issues (#440-#449) via PR cross-reference.

This subspec is the gate that says "ship-ready". Without 216-F passing, the merge is blocked.

## Acceptance Criteria

| AC | Description | Severity |
|----|-------------|----------|
| **F1.1** | All 3 mandatory agentic-flow test classes from `.claude/rules/testing.md` pass: (a) cumulative-state monotonicity (12-turn fixture, `progress_pct[t+1] >= progress_pct[t]` ∀t), (b) completion-gate triplet (empty/partial/full FinalForm.model_validate), (c) mock-LLM-emits-wrong-tool recovery via @output_validator + ModelRetry. | CRIT |
| **F1.2** | M1-M4 unit tests with golden snapshot outputs. **Per-meta-prompt fixture counts (closes testing-validator HIGH-3)**: <br/>• **M1 GenerateFollowUpFromAnswer**: ≥3 fixtures (typical Hinge prose; ambiguous-cluster edge; empty-answer guard) <br/>• **M2 ClassifyAnswerCluster**: ≥12 fixtures (3 per slot × 4 slots: saturday_morning, geek_out_on, together_we_could, primary_hobbies; each set covers high-confidence + ambiguous + low-confidence) <br/>• **M3 RefineSummary**: ≥3 fixtures (under-300-tok no-fire pass-through; over-300-tok summarize; ambiguous-pronoun edge) <br/>• **M4 DetectSaturation**: ≥3 fixtures (turn_count≥2 hard-override → move_on; cluster=ambiguous + turn<3 → probe; Big5 conf≥0.7 → move_on) <br/>**Total ≥21 fixtures.** Golden outputs versioned in `tests/agents/onboarding/golden/`. Tolerance per Open Q3: structural-key-match + key-string regex on prose fields (NOT exact string match). | HIGH |
| **F1.3** | Cluster enum exhaustiveness lint test — every `Literal` cluster value across all slots (hobbies 6, saturday 4, geek 4, together 5, ambiguous fallback) has a paired template registry entry. Test fails if any enum value lacks a template. | HIGH |
| **F1.4** | Cost circuit-breaker integration test — wizard with mocked LLM returning over-budget responses ($0.05 remaining) falls back to static registry; no further LLM calls fire; `is_complete` still reaches True. | HIGH |
| **F1.5** | Big5 inference unit tests with mock Haiku returning golden vectors. 3 fixtures: weak signal (low confidence), strong signal (≥0.7 → short-circuit), conflicting signal (Bayesian merge). | MED |
| **F1.6** | FE vitest covers (closes testing-validator HIGH-1 + HIGH-2): <br/>• `HobbyChips` (3-5 picks enforced + autocomplete + "+ other" hard-cap 40 chars) <br/>• `BackstoryArchetypeCards` (3-card render + no-invent-label guard rejecting non-curated labels) <br/>• `ProgressRail` (monotonicity reflection: pass `progress_pct: 50` then `30` → asserts width never decreases below 50) <br/>• `WizardShell` (AnimatePresence + `useReducedMotion` honored; key=`turn_id` not `slot_kind`) <br/>• `NikitaReaction` (≤140 char render + mirror-echo defensive guard + reduced-motion variant) <br/>• `__tests__/integration_full_flow.test.tsx` — happy-path 12-screen render via mock `/onboarding/answer` responses; asserts each `ProgressRail` tick is monotonic; asserts terminal redirect to `/dashboard` within 10s of `is_complete=true`. <br/>• `control_dispatch.test.tsx` — each `control_type` Literal renders correct component. | HIGH |
| **F1.7** | W4 live-walk PASSES verifies G.1-G.11 from handover §Verification + new ACs C.1-C.11 (visual + telemetry + Big5 + firecrawl + archetype + cost): 12 fixed roots in correct order (slot taxonomy from B1.1 unchanged); M2 fires after each prose; M1 fires depth-1 ≥4 times; Big5 ≥3 dims at conf ≥0.5; firecrawl ≥4 calls per flow; 3 archetypes from curated 12; cost <$0.50; **total visual screen count = 15 base screens (welcome + 11 visual slot screens + backstory + phone + completion; `together_we_could`+`same_weird_if` collected from one combined screen per C1.18) + dynamic M1 follow-ups counted separately, total 15-25 visual screens**; progress monotonic; 0 mirror echo; 0 banned vocab. Live walk follows `live-testing-protocol.md` 12-step protocol exactly. | CRIT |
| **F1.8** | Pre-walk + post-walk DB cleanup (FK-safe per `live-testing-protocol.md`) for `simon.yang.ch+spec216walk@gmail.com`. Simon's main account untouched (verified by row-count assertion). | HIGH |
| **F1.9** | All 10 W3 GH issues (#440-#449) closed referencing the merged PR(s) per phase 5/6 of handover task graph. Verified via `gh issue list --state closed --label W3` returns all 10. | MED |

## Critical Files

### NEW backend tests
- `tests/agents/onboarding/test_cumulative_state.py` (NEW) — Rule #1 monotonicity + `model_copy(update={...})` immutability fixture
- `tests/agents/onboarding/test_completion_gate.py` (NEW) — empty/partial/full FinalForm validation triplet
- `tests/agents/onboarding/test_tool_recovery.py` (NEW) — mock LLM emits wrong-kind, @output_validator raises ModelRetry, agent retries succeed
- `tests/agents/onboarding/test_meta_prompts.py` (NEW) — M1-M4 golden snapshots × 3 fixtures each
- `tests/agents/onboarding/test_cluster_enum_completeness.py` (NEW) — every Literal cluster value has paired template entry
- `tests/agents/onboarding/test_follow_up_registry_completeness.py` (NEW) — every dynamic node has `static_fallback_question`
- `tests/agents/onboarding/test_cost_circuit_integration.py` (NEW) — full wizard with $0.05 budget remaining → static fallback path
- `tests/agents/onboarding/test_big5_judge.py` (created in 216-D, extended here with golden vectors)
- `tests/agents/onboarding/test_archetypes.py` (created in 216-D, extended here with invented-label rejection)
- `tests/agents/onboarding/golden/` (NEW directory) — versioned snapshot outputs

### NEW frontend tests (vitest, see 216-C inventory)
- All vitest files listed in 216-C, plus `__tests__/integration_full_flow.test.tsx` (NEW) — happy-path 12-screen render via mock /onboarding/answer responses

### W4 walk artifact
- `docs-to-process/20260{XXXX}-live-walk-W4-spec216.md` (NEW; written by walk subagent post-deploy) — pre-walk DB cleanup result, step-by-step transcript with traceparents + DB snapshots + screenshots, AC G.1-G.11 + C.1-C.11 matrix, findings table by severity, final verdict PASS/PARTIAL/FAIL

### Event-stream entry
- `event-stream.md` line 3 (newest-at-top): `[YYYY-MM-DD] LIVE_E2E_W4: Spec 216 cinematic agentic wizard battle-test — VERDICT, N findings (CRIT/HIGH/MED/LOW)`

## W4 Walk Plan (post-216-{A..E} merge + deploy)

### Pre-walk gates (run sequentially)
1. **Cloud Run rev verify** — `gcloud run services describe nikita-api --region us-central1 --project gcp-transcribe-test --format json | jq '.status.latestReadyRevisionName'` returns post-216-merge revision.
2. **Vercel deploy verify** — `curl -s -H "Authorization: Bearer $TOKEN" "https://api.vercel.com/v6/deployments?projectId=prj_mP2qGV9ICPdNilcT6Zrf18HY9O7p&limit=1" | jq '.deployments[0].meta.githubCommitSha'` returns merge commit.
3. **CORS canonical** — `curl -sI -H "Origin: https://nikita-mygirl.com" -X OPTIONS "https://nikita-api-1040094048579.us-central1.run.app/api/v1/health"` returns 2xx + correct allow-origin header.
4. **Pre-walk DB cleanup** — FK-safe wipe per `live-testing-protocol.md` template for email `simon.yang.ch+spec216walk@gmail.com`. Both row counts (auth.users + pending_signup_session) post-wipe == 0. Simon's main account untouched.

### 12-step walk (per `live-testing-protocol.md`)
Driven by walk subagent with HARD CAP 130 tool calls. Steps 1-12 from the protocol with concrete MCP names. After each turn capture: `mcp__telegram-mcp__get_messages` (last 5), Cloud Run logs filtered by traceparent (G.1), Supabase state snapshot (G.2), Chrome MCP console + network (G.3), Telegram MCP message latency (G.4).

### G.1-G.11 verification matrix (from handover)
| Check | Method | Pass criterion |
|-------|--------|----------------|
| G.1 | 12 fixed roots presented in order | Cloud Run log filter shows slot_kind sequence matches ORDERED_QUESTIONS |
| G.2 | M2 fires after each prose root | `(slot_kind, cluster, confidence)` logged ≥4× (saturday/geek/together/hobbies) |
| G.3 | M1 fires depth-1 after each prose | dynamic-follow-up turn count ≥4 across wizard |
| G.4 | Big5 vector populated, ≥3 dims at conf ≥0.5 | `SELECT big5_vector FROM users WHERE id=X` post-walk |
| G.5 | firecrawl fired ≥4 times | log filter `tool_name=fetch_*` count ≥4 |
| G.6 | 3 archetypes from curated 12 | `SELECT backstory_pick FROM users; archetype labels validated against archetypes.py 12-list` |
| G.7 | cost_usd <$0.50 | `SELECT cost_usd FROM users WHERE id=X` post-walk |
| G.8 | Total wizard length 15-25 screens | conversation_jsonb turn count |
| G.9 | progress_pct monotonic | reconstruct from log |
| G.10 | 0 mirror echo | `SELECT display_name FROM users WHERE id=X; assert no doubled-name` |
| G.11 | 0 banned vocab in HTML | `curl -s https://nikita-mygirl.com/onboarding \| rg -i "FILE\|dossier\|clearance\|FIELD"` returns 0 matches |

### Post-walk
1. DB cleanup (idempotent re-run of pre-walk SQL)
2. Walk report written to `docs-to-process/20260{XXXX}-live-walk-W4-spec216.md`
3. Findings triaged (CRIT/HIGH/MED/LOW) → GH issues filed per `.claude/rules/issue-triage.md`
4. Event-stream entry prepended
5. ROADMAP update: Spec 216 → SHIPPED if VERDICT=PASS
6. Close W3 GH #440-#449 with reference to merged PRs (#216-{A..F})

## Tests to Write

In addition to ACs F1.1-F1.6, register these regression-guard tests (PR-blockers if they fail):

```python
# tests/agents/onboarding/test_regressions.py

def test_no_progress_pct_compute_function():
    """Rule #4 anti-pattern guard — _compute_progress(latest_kind) must NOT exist."""
    import nikita.api.routes.portal_onboarding as mod
    assert not hasattr(mod, "_compute_progress"), "Walk V anti-pattern resurfaced"

def test_no_extract_star_tools():
    """Rule #3 anti-pattern guard — agent must not register N narrow extract_* tools."""
    from nikita.agents.onboarding.conversation_agent import _create_conversation_agent
    agent = _create_conversation_agent()
    extract_tools = [t for t in agent._function_tools if t.name.startswith("extract_")]
    assert len(extract_tools) == 0, f"Found {len(extract_tools)} extract_* tools (BiasBusters)"

def test_no_completion_boolean_literal():
    """Rule #2 anti-pattern guard — no `is_complete = True/False` literal in onboarding answer route."""
    src = Path("nikita/api/routes/portal_onboarding.py").read_text()
    assert "is_complete = True" not in src
    assert "is_complete = False" not in src
    # FinalForm.model_validate must be the gate
    assert "FinalForm.model_validate" in src

def test_no_static_routing_in_system_prompt():
    """Rule #6 anti-pattern guard — instructions=callable, NOT system_prompt for routing."""
    from nikita.agents.onboarding.conversation_agent import _create_conversation_agent
    agent = _create_conversation_agent()
    # instructions should be a callable, not a static string
    assert callable(agent._instructions) or agent._instructions is None
```

## Open Questions

- **Q1**: W4 walk identity email — `simon.yang.ch+spec216walk@gmail.com` plus-alias confirmed routes to admin Gmail MCP inbox?
- **Q2**: Should W4 use the same Telegram account as W3 (Simon's), or a separate test account? Default: Simon's (only TG MCP session we have); pre-walk cleanup MANDATORY.
- **Q3**: Golden snapshot tolerance for M1-M4 — exact-match vs fuzzy match? Default: structural match (key-shape) + key-string regex on prose fields. LLM-output literal exactness too brittle.

## References

- Master spec Test File Inventory + Verification §
- `.claude/rules/testing.md` — Agentic-Flow Test Requirements (3 mandatory classes)
- `.claude/rules/live-testing-protocol.md` — 12-step walk protocol + DB cleanup template
- `.claude/rules/agentic-design-patterns.md` — Anti-patterns the regression tests guard
- W3 walk report: `docs-to-process/20260428-live-walk-W3-post-pkce.md`
- handover brief Verification § G.1-G.11

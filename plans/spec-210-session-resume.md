# Spec 210 — Session Resume Brief (post-compaction)

**Worktree**: `/Users/yangsim/Nanoleq/sideProjects/nikita/.claude/worktrees/delightful-orbiting-ladybug`
**Branch**: `feat/210-kill-skip-variable-response` (12 behind origin/master, uncommitted dirty tree)
**Master plan**: `/Users/yangsim/.claude/plans/delightful-orbiting-ladybug.md` (~730 lines — full context, all addenda)
**Date**: 2026-04-13 · **Spec**: 210-kill-skip-variable-response · **Title**: log-normal × chapter × momentum response-timing model

---

## Mental model (one paragraph)

Replace the old Gaussian-over-inverted-ranges response-delay model with: `delay = min(cap_ch, exp(μ+σZ) × c_ch × M)`. `M = clip(EWMA_α(user_gaps)/B_ch, 0.1, 5.0)` is a Bayesian-posterior-equivalent momentum multiplier seeded at chapter baseline `B_ch`. Fires ONLY on new-conversation starts (≥15min gap); in-session returns 0. Skip-decision behavior DELETED. Ch 1 capped at 10s for near-zero-wait UX.

**Math constants** (canonical, in `nikita/agents/text/timing.py` + `nikita/agents/text/conversation_rhythm.py`):
- `LOGNORMAL_MU=2.996`, `LOGNORMAL_SIGMA=1.714` → median base ≈ 20s
- `CHAPTER_COEFFICIENTS = {1:0.15, 2:0.30, 3:0.50, 4:0.75, 5:1.00}` (excitement fades)
- `CHAPTER_CAPS_SECONDS = {1:10, 2:60, 3:300, 4:900, 5:1800}`
- `CHAPTER_BASELINES_SECONDS = {1:300, 2:240, 3:180, 4:120, 5:90}`
- `MOMENTUM_ALPHA=0.35`, `MOMENTUM_LO=0.1`, `MOMENTUM_HI=5.0`, `SESSION_BREAK_SECONDS=900`, `WINDOW_SIZE=10`

---

## DONE this session (uncommitted)

| Path | Status | What |
|---|---|---|
| `nikita/agents/text/conversation_rhythm.py` | **NEW** | `compute_momentum(gaps, chapter) -> float`, `_compute_user_gaps(messages) -> list[float]` + constants |
| `nikita/agents/text/timing.py` | **REWRITTEN** v2 | `ResponseTimer.calculate_delay(chapter, *, is_new_conversation=True, momentum=1.0)`, log-normal × chapter × momentum, per-chapter caps. Legacy `TIMING_RANGES` kept for back-compat |
| `nikita/agents/text/handler.py` | **MODIFIED** | Deleted skip-decision logic; added `_is_new_conversation_from_messages()` helper; wired `_compute_user_gaps` + `compute_momentum` into `calculate_delay`. `skip_decision` kwarg kept as deprecated/ignored for test back-compat |
| `nikita/config/settings.py` | **MODIFIED** | `+momentum_enabled: bool = True` (only field added; module constants are canonical, overrides deferred) |
| `tests/agents/text/test_conversation_rhythm.py` | **NEW** | 23 tests across 6 classes (empty/fast/slow/bounds/cold-start/direction/chapter-diff/session-filter/malformed) |
| `tests/agents/text/test_timing.py` | **REWRITTEN** | 17 tests for v2 model (bypasses, caps, momentum scaling, legacy TIMING_RANGES compat) |
| `tests/agents/text/test_handler.py` | **MODIFIED** | 1 assertion updated to match new `calculate_delay` kwargs |
| `tests/agents/text/test_handler_skip.py` | **DELETED** | Tested removed skip-decision behavior |
| `portal/src/app/admin/research-lab/response-timing/page.tsx` | **NEW** (~2000 lines) | Native Next.js client component with 14 sections + mount-guard for hydration safety |
| `.claude/rules/dev-server-monitoring.md` | **NEW** | Rule codifying "monitor both Turbopack stdout AND browser console via Chrome MCP when running dev servers" |
| `specs/210-kill-skip-variable-response/` | **UNTRACKED** | Spec files already exist but FR-005/6/13/14/15 still need v2 rewrite (see PENDING) |

**Test state**: `uv run pytest tests/ -q --ignore=tests/e2e` → **5716 passed, 138 deselected**. `tests/agents/text/test_conversation_rhythm.py` + `test_timing.py` → 40 passed.

**Deleted-behavior note**: `nikita/agents/text/skip.py` + `tests/agents/text/test_skip.py` still EXIST (not deleted) because other places (e.g. `test_repetition_penalty.py`, `test_flag_group_a.py`) import `SkipDecision` for reasons unrelated to the handler wiring. Handler ignores it; module is effectively dead code but keeping it avoids broader test churn. Delete in a follow-up PR.

---

## Portal PR #261 (parallel agent, IFRAME approach) — USER REJECTED

Branch: `worktree-agent-a0bba59e` · PR: https://github.com/yangsi7/nikita/pull/261

**What it adds**: iframe-embedded research-lab index + `[slug]/page.tsx` + manifest (`models.ts`) + sync script + sidebar entry + Playwright tests + stub `docs/models/response-timing.md`.

**User pivot**: "Nah I need the real fucking thing on the portal I already told you." → I built a **native React/Tailwind** component on my worktree branch (`portal/src/app/admin/research-lab/response-timing/page.tsx`) which SUPERSEDES the iframe detail page. Static route wins over `[slug]` dynamic.

**Decision when the dust settles**: cherry-pick useful pieces of PR #261 (manifest + index page + sidebar entry) onto the main-track branch OR merge #261 first and let my native page override the iframe path. Don't merge #261 as-is because its detail page iframes the (non-existent) standalone HTML artifact which the user explicitly rejected.

---

## Portal page — `/admin/research-lab/response-timing` (native)

14 sections, default Chapter 3:
1. Problem recap · 2. Proposed model · 3. Monte Carlo simulator (sliders + histogram + CDF)
4. Ch 1 floor · 5. Momentum layer (formula + trace simulator + feedback-spiral demo)
6. **Conversation transient** (deterministic E[delay] + stochastic trajectory side-by-side) ← user gave detailed feedback
7. **Cold-start distribution** (Nikita resumption after 10-msg warm-up, overlaid histograms)
8. **Chapter × cadence heatmap** (5×6 grid, median delay per cell)
9. **Persona day** (Ghoster / Chatty Cathy / Bored-replier over 24 messages, gate-aware)
10. Life-sim integration (placeholder — future coupling with Nikita's working/sleeping state)
11. Bayesian equivalence · 12. Old vs new · 13. Why log-normal + excitement-fades · 14. Citations + next steps

**Key decisions baked in**:
- Mount-guard for hydration (`useState(false)` + `useEffect(() => setMounted(true), [])`) — fixes the `Math.random()` SSR/client mismatch
- Inline styles preserved (this is an artifact page, not a portal feature surface; design tokens scoped to component subtree)
- `ChapterChips` is a prominent framed row with feels subtitles, applies to §06-09 via prop-drilled state
- §06 has a "READING THE TRANSIENT" callout explaining Bayesian prior / observation convergence

---

## Dev environment

```bash
# Background dev server (bash id: bh77y9p2k — check if still alive)
# Was started with:
cd portal && E2E_AUTH_BYPASS=true E2E_AUTH_ROLE=admin npm run dev -- -p 3006
# → http://localhost:3006/admin/research-lab/response-timing

# If the background process died after compaction, restart:
cd /Users/yangsim/Nanoleq/sideProjects/nikita/.claude/worktrees/delightful-orbiting-ladybug/portal
E2E_AUTH_BYPASS=true E2E_AUTH_ROLE=admin npm run dev -- -p 3006

# Monitor per .claude/rules/dev-server-monitoring.md:
# 1. tail the stdout file returned by Bash run_in_background
# 2. mcp__claude-in-chrome__navigate → mcp__claude-in-chrome__read_console_messages with pattern "(?i)error|warning|hydrat"
# 3. Fix errors BEFORE telling the user to refresh
```

---

## PENDING tasks (priority order)

| # | Task | Blocker | Est |
|---|---|---|---|
| **#16** | MC validator script `scripts/models/response_timing_mc.py` (percentile CSV, histograms, momentum traces, feedback-spiral + unbiasedness assertions, exit 0/1, <30s) | None — math is settled | ~150 LOC |
| **#17** | `docs/models/response-timing.md` long-form (overwrites stub created by portal agent): formulation, params, MC results, citations (Barabási/Stouffer/Wu/Malmgren/Hawkes/Jacobson/Fisher/Berger-Calabrese/Scissors), pitfalls | #16 for MC numbers | ~400 lines |
| **#19** | `.claude/rules/stochastic-models.md` (≤80 lines, codify "pick distribution → MC validator → docs → artifact → link" workflow) + Spec 210 FR-005/6 rewrite + FR-013/14/15 additions + update CLAUDE.md one-line index | None | ~80 + spec edits |
| **Portal cleanup** | Decide fate of PR #261: cherry-pick manifest+sidebar onto main branch OR merge #261 first and let native page override. Delete stub `docs/models/response-timing.md` (portal agent wrote it) before writing the real one in #17 | User decision | 20 min |
| **Life-sim coupling** | Follow-up spec (NOT this PR) — tie parameters to Nikita's working/sleeping/on-phone state. Referenced in §10 placeholder. Requires review of spec 022/055 first | Separate spec | Future |

---

## OPEN design questions from user (defer, note in spec)

1. **Opening-vs-mid-session as continuous soft gate?** Current: hard `is_new_conversation` boolean gate (≥15min → delay fires, else 0). User mused about continuous session-warmth decay. NOT in scope for Spec 210. Future spec if user wants it.
2. **Life-simulation coupling**: "parameters should vary based on what she is doing — working, sleeping, etc." Captured in §10 placeholder + plan `OUT OF SCOPE` list. Future spec.
3. **Ch1 cap = 10s vs 15s?** Current 10s recommended; trivially adjustable via module constant.
4. **α = 0.35 sensitivity**: MC validator will sweep α ∈ {0.2, 0.35, 0.5} to confirm choice.

---

## Context-retrieval commands (for the new Claude session)

```bash
# 1. Orient — check SDD state + ROADMAP
cd /Users/yangsim/Nanoleq/sideProjects/nikita/.claude/worktrees/delightful-orbiting-ladybug
cat .sdd/sdd-state.md event-stream.md | head -60
cat ROADMAP.md | grep -A 2 "Spec 210"

# 2. Read this brief + master plan
cat plans/spec-210-session-resume.md
cat /Users/yangsim/.claude/plans/delightful-orbiting-ladybug.md

# 3. Verify implementation state
git status --short
uv run pytest tests/agents/text/test_conversation_rhythm.py tests/agents/text/test_timing.py -q

# 4. Inspect the three key modules
wc -l nikita/agents/text/conversation_rhythm.py nikita/agents/text/timing.py nikita/agents/text/handler.py
# (respectively ~186, ~221, ~480 lines)

# 5. Re-check dev server (if user wants to continue demo)
ls /private/tmp/claude-501/*/tasks/bh77y9p2k.output 2>/dev/null && tail /private/tmp/claude-501/*/tasks/bh77y9p2k.output
# If dead: cd portal && E2E_AUTH_BYPASS=true E2E_AUTH_ROLE=admin npm run dev -- -p 3006
```

---

## Commit breakdown (when ready to PR this branch)

Per the master plan, keep each commit ≤50 lines, final PR ≤400 lines of Python code (docs/artifact count separately):

1. `feat(agent): compute_momentum + gap extraction (tests first)` — conversation_rhythm + test_conversation_rhythm
2. `feat(agent): log-normal × chapter × momentum ResponseTimer` — timing.py + test_timing.py rewrite
3. `feat(agent): wire momentum + new-conversation gate into handler` — handler.py + test_handler.py assertion
4. `feat(config): momentum_enabled feature flag` — settings.py
5. `chore(tests): delete test_handler_skip.py (Spec 210 supersedes)` — delete
6. `feat(scripts): Monte Carlo validator` — #16
7. `docs(models): long-form response-timing model doc` — #17
8. `feat(portal): admin research-lab response-timing explorer` — portal/research-lab/response-timing/page.tsx
9. `chore(rules): dev-server-monitoring + stochastic-models rules` — .claude/rules/
10. `feat(spec): Spec 210 FR-005/6 rewrite + FR-013/14/15 additions` — #19

PR title: `feat(timing): Spec 210 v2 — log-normal × chapter × momentum (#210)`

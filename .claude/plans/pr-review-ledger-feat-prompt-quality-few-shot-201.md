# Review Ledger — feat/prompt-quality-few-shot-201

## Meta
- PR: #254 — feat(persona,agent): vulnerability gate + chapter-keyed few-shot examples (#201)
- URL: https://github.com/yangsi7/nikita/pull/254
- Scope: PR diff (7 files; branched from master after PR #253)
- Iteration: 0 / 5
- Severity threshold: important
- Mode: fix
- Review type: external (fresh-context)
- Full suite baseline: 5794 passed (165s)

## Changed Files (incl. Self-Improvement housekeeping first commit)
- nikita/agents/text/persona.py (+146) — VULNERABILITY_DIRECTIVES, _format_vulnerability_directive, CHAPTER_EXAMPLE_RESPONSES, get_chapter_examples, add_vulnerability_gate, add_chapter_examples
- nikita/agents/text/agent.py (+18/-1) — 2 new @agent.instructions delegators
- tests/agents/text/test_persona_vulnerability.py (+147) — 15 tests
- tests/agents/text/test_agent_instructions.py (+100) — 7 tests
- .claude/rules/task-verification.md (+18, new — Self-Improvement rule)
- specs/211-task-ledger-truth-audit/README.md (new)
- ROADMAP.md + event-stream.md (session log)

## Findings

| ID | File | Line | Category | Severity | Status | Iter | Reviewer |
|----|------|------|----------|----------|--------|------|----------|
| R1 | nikita/agents/text/persona.py | 191-198 | Correctness | nitpick | SKIPPED | 1 | external |
| R2 | tests/agents/text/test_persona_vulnerability.py | 165-172 | Testing | nitpick | SKIPPED | 1 | external |
| R3 | nikita/agents/text/persona.py | 302-320 | Correctness | nitpick | SKIPPED | 1 | external |

## Fix Log

### Iteration 0 (self-review)
- Dispatched straight to external reviewer given prior rigor (PR #253 converged iter 2).

### Iteration 1 (external fresh-context re-review)
- **CLEAN**: 0 blocking, 0 important.
- Parity check PASSED: all 6 Jinja branches (system_prompt.j2:413-424) match VULNERABILITY_DIRECTIVES[0..5] character-for-character.
- Skip correctness PASSED (both decorators).
- Chapter fallback PASSED (get_chapter_examples(0/-1/99) → Ch1).
- Regression guard PASSED (EXAMPLE_RESPONSES ≥10 preserved).
- No import cycle; persona.py adds zero new top-level `nikita.*` imports.
- Ch1 tone PASSED: all 4 Ch1 examples use humor/deflection, no trauma references.
- 3 nitpicks flagged + deferred (below threshold):
  - R1: `VULNERABILITY_DIRECTIVES[4]` unreachable at runtime because `compute_vulnerability_level` maps Ch4→level 3 (pre-existing design oddity in `nikita/utils/nikita_state.py:156`). Dict entry still useful for Jinja parity — documents the template's level-4 branch. Accepted.
  - R2: `test_flat_example_responses_untouched_by_chapter_additions` has a dead `or "context" in ex` branch (flat list uses `"scenario"`). Harmless; accept as forward-compat tolerance.
  - R3: `add_vulnerability_gate` docstring says "pydantic_ai imports" but deferred import is from `nikita.utils.nikita_state`. Minor comment inaccuracy.
- Suite: 5794 passed. Status: **PASS**.

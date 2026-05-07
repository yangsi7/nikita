# Audit Report — Subspec 217-3A BE Emission Union

**Parent**: `subspecs/217-3A-be-emission-union/{spec,plan,tasks}.md`
**Phase**: 7
**Date**: 2026-05-07

## Verdict: PASS-CONDITIONAL

The subspec is structurally complete and conforms to all 6 hard rules of `agentic-design-patterns.md`. PASS is conditional on:

1. LOC pre-flight check at T-3A-13 (mid-implementation) returning ≤350; otherwise 217-3A.1 split lands first.
2. Calibration fixture (AC-7.4) executed BEFORE the 0.85 threshold is locked.
3. Mock-LLM-wrong-tool recovery test (AC-T-3) actually exercises the `ModelRetry` self-correction path (not a placeholder).

## Cross-check

| Check | Result |
|---|---|
| 6 hard rules referenced | PASS (spec.md §Agentic-Design-Patterns 6-Rule Compliance) |
| Pydantic AI primitives table | PASS (spec.md §Pydantic AI Primitives Used) |
| 3 mandatory agentic-flow tests (testing.md) | PASS (AC-T-1, T-2, T-3) |
| Agent.run contract test | PASS (AC-T-4) |
| Dynamic-instructions invocation test | PASS (AC-T-5) |
| ACs falsifiable | PASS (isinstance, ratio assertions, JSONB column read, ModelRetry assertion) |
| TDD ordering | PASS (T-3A-2..8 RED, T-3A-9..16 GREEN, T-3A-17 verify) |
| LOC pre-flight gate | PASS (T-3A-13 explicit gate; 217-3A.1 contingency documented) |
| Calibration fixture before threshold lock | PASS (T-3A-2 first task before any production code) |
| Pre-push HARD GATE | PASS (T-3A-18) |
| `/qa-review` zero-tolerance | PASS (T-3A-21) |
| Cumulative-state monotonicity preserved | PASS (sidecar, NOT in WizardSlots — Hard Rule #1) |
| Pydantic completion gate UNCHANGED | PASS (AC-9.2) |
| Tool consolidation (3-tool union) | PASS (Hard Rule #3) |
| Three-layer validation | PASS (pre-tool / output_validator ModelRetry / regex post-processing) |
| `message_history=` primitive | PASS (Hard Rule #6) |
| Phase-2 Pydantic AI false-positive resolution cited | PASS (PR body cite in T-3A-20) |

## Open Findings

| Severity | Finding | Resolution |
|---|---|---|
| MEDIUM | LOC overflow risk (245 production estimate vs 350 cap; tight) | Pre-flight gate at T-3A-13; split contingency documented |
| LOW | Threshold 0.85 from brief — not yet calibrated | T-3A-2 calibration fixture before lock |
| LOW | FR-15 (ReinjectSystemPrompt) advisory only — implementor may skip if `result.new_messages()` chaining is used | Document chaining strategy in PR body |

No CRITICAL/HIGH findings.

## Pydantic AI Primary-Source Verification

Phase-2 research-worker scraped https://ai.pydantic.dev/output/ + https://ai.pydantic.dev/message-history/ on 2026-05-07. The current canonical syntax `output_type=[ToolOutput(Cls, name='...'), ...]` is verified for pydantic-ai 1.71.0. Gemini judge's CRITICAL #3 rejection of this syntax is rejected per primary-source-evidence-wins-over-advisor operating principle.

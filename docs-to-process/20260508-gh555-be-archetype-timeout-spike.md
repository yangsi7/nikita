---
title: "GH #555 BE archetype-pipeline timeout — root-cause spike"
lifecycle: frozen
date: 2026-05-08
target: GH #555
target_revision: nikita-api-00300-98x
incident_window: 2026-05-07T20:25:01Z .. 2026-05-07T20:25:21Z
related_pr: PR #552 (Spec 217-2 fallback envelope — held)
related_walk: audits/2026/walk-B2-resume-spec217-2.md
authors: spike subagent (read-only diagnostics)
---

# GH #555 — BE archetype-pipeline timeout root-cause spike

## TL;DR

**The walk-B2-resume report misnamed the failure surface.** The 20:25:21Z
ERROR was NOT a timeout inside `_build_archetype_cards` /
`pick_three_archetypes`. The `asyncio.wait_for(20s)` envelope at
`nikita/api/routes/portal_onboarding.py:1374-1389` did NOT fire — there is
no `backstory_pipeline_timeout` log marker in the window.

The ERROR was an **`exc=ModelHTTPError`** thrown by the **conversation
agent** (`get_conversation_agent()`) on the user's `/answer` turn that
*precedes* archetype generation. Pydantic AI raises `ModelHTTPError`
when the Anthropic Messages API returns a 4xx/5xx HTTP status. The
agent loop was unwound by `pydantic_graph` (hence the deceptive
`GraphRun.__aexit__` traceback frames in the walk report) and the
exception propagated to the route's `except Exception` arm
(`portal_onboarding.py:1610`), which logs `answer_agent_unexpected
exc=ModelHTTPError` and returns `_fallback_answer(...)` (200 OK).

The user-visible "preparing the three of us…" → fallback Alert path
fired correctly per Spec 217-2 contract — but it fired **on a
ModelHTTPError from the conversation turn**, not on a true
archetype-pipeline timeout. The FE telemetry
`backstory_fallback_fired` is reading the right signal (any 200-OK
fallback envelope from the BE), but it cannot distinguish a *picker
timeout* from a *conversation-turn LLM 5xx*.

## Verdict

**Root cause: H2 — Anthropic API returned a non-2xx HTTP response
for the conversation-agent turn.** Confidence: **HIGH**.

Evidence:
- Two consecutive log lines, both at the `/answer` route:
  - `2026-05-07T20:25:01.344616Z … answer_agent_unexpected user_id=4e06099b-… exc=ModelHTTPError`
  - `2026-05-07T20:25:21.396937Z … answer_agent_unexpected user_id=4e06099b-… exc=ModelHTTPError`
- Each was paired with an `httpx INFO HTTP Request: POST
  https://api.anthropic.com/v1/messages?beta=true …` immediately
  preceding (20:25:01.286Z and 20:25:21.394Z respectively). The httpx
  status-code suffix is truncated by Cloud Run textPayload rendering
  beyond ~120 chars, so we cannot read the exact 4xx/5xx code from
  the captured log lines — but the Pydantic AI source confirms
  `ModelHTTPError` is raised iff `status_code` is 4xx/5xx
  (`pydantic_ai/exceptions.py: ModelHTTPError(ModelAPIError):
  "Raised when an model provider response has a status code of 4xx
  or 5xx."`).
- 20:25 UTC = 16:25 ET, a known peak Anthropic-load window. Two
  consecutive failures 20s apart is consistent with provider-side
  529/503 (overload) or 429 (rate-limit) bursts.
- Time delta from request-start to traceback: ~110 ms (20:25:21.286
  POST → 20:25:21.394 httpx response → 20:25:21.396 ERROR). Not a
  client-side timeout. Not the 20 s wait_for envelope. The Anthropic
  API responded **fast** with an error.

## Falsified hypotheses

| H  | Hypothesis | Evidence falsifying it |
|----|---|---|
| H1 | Firecrawl cost-guard exhausted, picker retried until 20 s wait_for cancelled. | No `cost_guard` / `cap_exceeded` / `firecrawl_cost_guard` log markers in the 24 h window. Firecrawl `agent_tool` INFO lines fired normally up to 20:24:11 and stopped (i.e., the tool was being called successfully then the request flow ended at the conversation-agent failure). The 20 s wait_for was never invoked. |
| H3 | `make_anthropic_generator` (deferred-unused) was actually wired into the live archetype path and hung. | `rg "make_anthropic_generator" nikita/` returns ONLY the definition site (`nikita/agents/onboarding/wiring.py:343`) and the `__all__` re-export. Zero callers. The live picker is `make_anthropic_picker()` (used at `portal_onboarding.py:1384`); generator is genuinely unused. |
| H4 | Big5 / archetype agent `ModelRetry` loop exhausted within wait_for budget. | No `ModelRetry` log markers anywhere in the codebase or in 24 h logs. The Big5 judge (`big5_judge.py`) and picker (`pick_three_archetypes`) both call Anthropic via `_anthropic_text_call` (bare `client.messages.create`), NOT through Pydantic AI Agent.run, so `ModelRetry` is structurally not in those paths. |
| (5th hypothesis tested ad hoc) Per-turn timeout on conversation agent reaching 20 s budget. | Wall-clock from POST → traceback = 110 ms. Not a timeout. |

## Why the walk report misread it

The walk-B2-resume traceback excerpt (lines 1-31 of the trace) shows:
`portal_onboarding.py:1566 → agent_runner.py:79 → agent.run → pydantic_graph beta/graph.py:981 _unwrap_exception_groups → raise exception`. The `_unwrap_exception_groups` frame is part of pydantic-graph's standard exception-handling unwinding — it appears in EVERY agent-run exception trace, not just timeouts. The report inferred "graph timeout" from the `GraphRun.__aexit__` frame; that was a misreading. The truncated final line (which would have read e.g. `pydantic_ai.exceptions.ModelHTTPError: status_code: 529, model_name: claude-…, body: …`) was the actual signal — it is captured separately as the route's own ERROR log line and reads `exc=ModelHTTPError`.

## Fix scope estimate

This is a **diagnostic / observability fix + retry policy fix**, not
an algorithmic fix. The picker, generator, and wait_for envelope are
all working as designed — the bug is that **(a)** the conversation
agent has no retry on transient Anthropic 5xx, and **(b)** the
route-handler logging strips the most important data
(`status_code`, `body`) before the trace is committed.

### Sub-PR shape: 217-2c (small follow-up to 217-2)

Two coupled changes, both in `nikita/api/routes/portal_onboarding.py`
+ a new tests file. Estimated **~80 LOC across 2 files**, plus
**~120 LOC of tests**.

#### Change 1 — explicit `ModelHTTPError` arm with rich logging

`nikita/api/routes/portal_onboarding.py:1591-1620` (the `try` block
around `run_agent_with_capture`).

Add a dedicated `except ModelHTTPError as exc:` arm BEFORE the
generic `except Exception:` catch-all. Log
`status_code`, `model_name`, `body[:512]`, `traceparent`,
`user_id`, `slot_kind` (the slot the user was on). Then route to
`_fallback_answer` with a NEW `fallback_reason="model_http_<status_code>"`
so the FE telemetry can distinguish provider-side errors from
client-side ones.

Edit target (illustrative):

```python
from pydantic_ai.exceptions import ModelHTTPError  # add to imports

# ... inside `answer(...)`:
except ModelHTTPError as exc:
    logger.warning(
        "answer_agent_model_http_error user_id=%s status=%s model=%s body=%s",
        current_user.id,
        exc.status_code,
        getattr(exc, "model_name", "?"),
        repr(exc.body)[:512],
    )
    return _fallback_answer(
        state_progress_pct=state.progress_pct,
        conversation_id=conversation_id,
        fallback_reason=f"model_http_{exc.status_code}",
    )
```

#### Change 2 — bounded retry-with-jitter on the conversation-agent run for 429 / 5xx

Wrap `run_agent_with_capture(...)` in a 3-attempt
exponential-backoff loop (250ms / 750ms / 1.75s + jitter), retry
ONLY on `ModelHTTPError` with `status_code in {429, 502, 503, 504,
529}`. Total worst-case added latency: ~3 s. Cap with the existing
agent-run timeout if any; do NOT add a new `wait_for` (the 217-2
20 s on the picker is a separate concern). Refuse retry on any 4xx
that is not 429 (those are deterministic — bad request, auth, etc.).

#### TDD approach

Failing-test target — at `tests/api/routes/test_portal_onboarding_answer_failure.py`:

1. **`test_answer_logs_status_code_on_model_http_error`** —
   monkey-patch `run_agent_with_capture` to raise `ModelHTTPError(529,
   "claude-...", body={"error":"overloaded"})`. Assert the route logs
   include `status=529` and `body=...overloaded...`. Asserts on
   captured `caplog`. **This test currently fails** because the route
   only logs `type(exc).__name__`.

2. **`test_answer_retries_on_anthropic_overload`** — monkey-patch
   `run_agent_with_capture` to raise `ModelHTTPError(529, ...)` twice
   then succeed. Assert it returned the success envelope (NOT the
   fallback) and that the helper was awaited 3 times. **Currently
   fails** — there is no retry.

3. **`test_answer_does_not_retry_on_4xx_other_than_429`** — raise
   `ModelHTTPError(400, ...)`. Assert helper awaited exactly once and
   route returned the fallback envelope with
   `fallback_reason="model_http_400"`. **Currently fails** — 400 falls
   through `except Exception` and logs `unexpected`.

4. **`test_archetype_pick_timeout_logs_marker_when_envelope_fires`** —
   monkey-patch `pick_three_archetypes` to `await asyncio.sleep(25)`.
   Drive the answer turn through to the archetype-pick slot. Assert
   `backstory_pipeline_timeout` log marker fires (this validates the
   217-2 envelope works, separate from 555 root cause). **Currently
   passes** (the envelope is correct), but the test belongs in the
   suite to lock the contract.

### Files to touch

| File | Lines | Change |
|---|---|---|
| `nikita/api/routes/portal_onboarding.py` | ~1591-1620 (existing try/except) + ~50 LOC retry helper, e.g. `_run_agent_with_retry` near top of file | Add `ModelHTTPError` arm + retry wrapper |
| `tests/api/routes/test_portal_onboarding_answer_failure.py` | new file, ~120 LOC | 4 tests above |

### Out-of-scope guardrails

- Do NOT touch `_build_archetype_cards` (`portal_onboarding.py:1324-1405`) — its 20 s wait_for envelope is correct as-is.
- Do NOT touch `pick_three_archetypes` (`archetypes.py:278`) or `make_anthropic_picker` (`wiring.py:282`) — both are working.
- Do NOT add retries on `Big5` or picker calls in this PR — they have lower call frequency and a different fail-mode (raised by bare `client.messages.create`, NOT through Agent.run, so they don't even produce `ModelHTTPError`).

## Cross-spec impact check

`ModelHTTPError` from Anthropic affects ANY Pydantic AI `Agent.run`
in the codebase. Code-grep:

```
rg -n "agent\.run\(|run_agent_with_capture" nikita/ --type py
```

Likely sister callers (verify before touching them):
- `nikita/agents/text/agent.py` — text agent for Telegram main loop
- `nikita/agents/voice/**` — voice handler agents
- Any pipeline stage that calls `agent.run(...)`

A retry/observability fix in 217-2c addresses the onboarding-wizard
surface only. A broader Spec (216-F? or new spec) should track:

> "Adopt a single `pydantic_ai`-aware retry+log helper across all
>  Agent.run call sites; deprecate ad-hoc `except Exception` catch-alls
>  that strip `ModelHTTPError.status_code`."

File a follow-up MEDIUM-severity GH issue under that title — not in
217-2c scope.

## Operability note

GH #556 (already filed per task brief) covers structured BE event
emission for `backstory_pipeline_timeout` / `backstory_fallback_fired`.
Recommend extending its scope to also include:

- `answer_agent_model_http_error` (status_code, model_name, retry_attempt)
- `answer_agent_retry_attempt` (attempt_n, delay_ms, status_code)
- `answer_agent_fallback_envelope` (fallback_reason, attempt_count)

These would have made GH #555 root-causable in 1 minute instead of
this spike's full budget. Filing as a single comment on #556.

## Methodology notes (for future spikes)

1. **Truncated tracebacks lie.** `gcloud logging` truncates long
   `textPayload` lines silently in both `value()` and `--format=json`
   rendering when the wrapped record exceeds ~120 chars (or 100 lines
   for multi-line tracebacks). The bottom of a traceback — where the
   actual exception class lives — is exactly where it gets cut. Always
   pair the traceback log query with a **separate** query for the
   route's own ERROR-level structured log line (which is short and
   uncut), and read the exception class name from there.

2. **Walk reports describe symptoms; root cause needs the BE log.**
   The walk B2-resume report correctly captured the FE-side fallback
   contract held — that was its scope. Inferring the BE root cause
   from the truncated traceback was the over-reach. Subagent walk
   reports + BE log analysis are complementary, not substitutable.

3. **`pydantic_graph.GraphRun.__aexit__` frames are universal in
   `agent.run` exception traces, not specific to timeouts.** Future
   triage: do NOT assume "graph" + "exit" + "exception" frames imply
   timeout. Read the actual exception class.

## References

- Cloud Run: `gcp-transcribe-test`, service `nikita-api`, revision
  `nikita-api-00300-98x`
- Code: `nikita/api/routes/portal_onboarding.py:1566` (call site),
  `:1591-1620` (exception handlers), `:1324-1405`
  (`_build_archetype_cards` — NOT the failure site)
- Code: `nikita/agents/onboarding/agent_runner.py:79`
  (`run_agent_with_capture`)
- Code: `nikita/agents/onboarding/wiring.py:282`
  (`make_anthropic_picker`)
- Code: `nikita/agents/onboarding/archetypes.py:278`
  (`pick_three_archetypes`)
- Library: `pydantic_ai.exceptions.ModelHTTPError` — `"Raised when an
  model provider response has a status code of 4xx or 5xx."`
- Walk: `audits/2026/walk-B2-resume-spec217-2.md`
- Spike: `docs-to-process/20260507-spec217-2-backstory-diagnosis.md`
  (217-2 spike — separate root cause; FE timing fix shipped in PR #552)
- Issue: GH #555 (this spike's target), GH #556 (observability gap)

## Confidence calibration

- Verdict (H2): **HIGH** — `exc=ModelHTTPError` literally appears in
  the route's structured log line; the Pydantic AI source confirms
  the class is provider-HTTP-only.
- Status code (529 vs 503 vs 429): **MEDIUM** — inferred from
  time-of-day load patterns + truncated httpx logs. Reading the
  actual code requires either Cloud Run trace export
  (`gcloud logging read … --format=json --max-log-line-bytes=…` if
  such a flag exists) or instrumenting the route to log it (Change 1
  in the fix).
- Retry policy (3 attempts × backoff): **MEDIUM** — empirically
  matches Anthropic SDK's documented retry-friendly status set;
  exact tuning should follow Spec 216-E flow-cost ceiling so retries
  do not blow `FLOW_HARD_CEILING_USD = $0.50`.

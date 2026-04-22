---
globs: ["tests/**"]
---

# Testing Patterns

## Async Mocks
- All DB operations use `AsyncMock` — see `tests/conftest.py` for standard fixtures
- E2E tests use separate `tests/e2e/conftest.py` (ASGI transport, webhook simulator, no-op cleanup)
- Mock `session.execute()` returning `AsyncMock(scalars=Mock(return_value=Mock(first=...)))` for queries

## Conftest Hierarchy
- `tests/conftest.py`: Root fixtures (mock_session, mock_settings, sample_user, sample_metrics)
- `tests/e2e/conftest.py`: E2E-specific (async_client, webhook_simulator, cleanup no-ops)
- Module-level conftest.py files: Domain fixtures (mock_memory, mock_agent, etc.)

## Singleton Cache-Clearing
- `get_settings()` is a cached singleton — call `get_settings.cache_clear()` in fixture teardown
- If tests bleed state, check for unflushed LRU caches on singletons

## Voice Test Patterns
- Voice tests wrap `asyncio.wait_for` timeouts — unwrap by mocking `asyncio.wait_for` to call coroutine directly
- Mock `ready_prompt` fixture for server tool tests to avoid PromptBuilderStage dependency
- ElevenLabs conversation mocks: `AsyncMock(spec=Conversation)` with `wait_for_session_end`

## Marker Exclusions
- `@pytest.mark.integration`: Skipped in CI (requires live services)
- `@pytest.mark.slow`: Skipped by default, run with `--slow`
- `@pytest.mark.e2e`: Full E2E tests, separate from unit suite

## "Tests That Don't Test" — Anti-Pattern (PR #252)
When a production function iterates over a repository query result, mocking the query to return `[]` means the loop body is NEVER exercised. Coverage metrics pass while the risky branch is 0% covered. GH #248 (silent scheduled-delivery failure) hid in this gap for months despite 11 passing tests in `test_tasks.py`.

**Rules**:
- **Non-empty fixture required**: Any test covering a worker / consumer / iterator that consumes `repo.get_*()` / `find_*()` / `list_*()` must have at least ONE sibling test providing a non-empty fixture list. Mocking to `[]` tests dispatch only, not behavior.
- **No zero-assertion shells**: Every `async def test_*` must assert. If mocking a repo call, pair with `mock_repo.method.assert_awaited_once()` + kwarg assertions on the content/shape passed. A test body with zero `assert` / `assert_*` / `pytest.raises` is a LIE — delete or flesh it out.
- **Patch source module, not importer**: For function-local `from X import Y` imports, patch `X.Y` (source). Function-local imports resolve through `sys.modules` each call; patching the source is sufficient and correct. Double-patching the importer is belt-and-suspenders and obscures intent.

**Example fix** (PR #252 iter 2, `tests/agents/text/test_handler.py::test_calls_repository_create_event_with_session`): previously zero-assertion shell → added `mock_repo.create_event.assert_awaited_once()` + kwarg checks on `content["chat_id"]`, `content["text"]`.

## Pre-PR Grep Gates (run before requesting QA review)

Before opening a PR or dispatching `/qa-review`, run these three greps against the changed files. If any matches, fix before review — they are cheap issues that would otherwise cost one iteration.

```
# 1. Zero-assertion test shells — any `async def test_*` whose body has no assert
grep -nE "^async def test_" <changed test file> | while read line; do ...  # or use: rg -U "async def test_[^(]+\([^)]*\):[\s\S]*?(?=\nasync def|\nclass |\Z)" tests/ | rg -L "assert|pytest\.raises"

# 2. PII leakage — raw name/age/occupation/phone values in log format strings
grep -nE "logger\.(info|warning|error|exception|debug).*%s.*(name|age|occupation|phone)" <changed .py files>

# 3. Raw cache_key in logs — cache_key contains city which is PII-adjacent
grep -n "cache_key=" <changed .py files> | rg -v "cache_key_hash|sha256"
```

All three must return empty before passing to reviewer.

## Agentic-Flow Test Requirements (Walk V precedent, 2026-04-22)

For any test file under `tests/agents/**`, `tests/pipeline/**`, or any test exercising a Pydantic AI `Agent.run(...)`, three test classes are MANDATORY:

1. **Cumulative-state monotonicity** — turn-by-turn fixture (≥3 turns) feeds extractions into the state model and asserts `progress_pct[t+1] >= progress_pct[t]` for every t. If progress drops at any turn, the production code is reading a per-turn snapshot instead of cumulative state. Anti-pattern: `_compute_progress(latest_kind)`.

2. **Completion-gate triplet** — empty state → False/0%, partial state (some slots filled) → False/<100%, full state (all slots valid) → True/100%. Done via `try: FinalForm.model_validate(state); except ValidationError: ...`. If the production code hardcodes the gate (`complete = False` literal), the empty/partial cases pass for the wrong reason.

3. **Mock-LLM-emits-wrong-tool recovery** — fixture with mocked agent returning the wrong extraction kind for an unambiguous user input (e.g., agent returns `IdentityExtraction` for "+1 415 555 0234"). Assert the system recovers via deterministic fallback (regex) OR `ModelRetry` self-correction. If the test cannot exist (no recovery path), the design is brittle to known LLM tool-selection bias.

Refusing to add these tests when introducing a new agent flow is a PR-blocker per `.claude/rules/agentic-design-patterns.md`.

## DB Migration Checklist (new-table RLS completeness)

When adding a new Postgres table, the migration MUST include all of:

- `ALTER TABLE <t> ENABLE ROW LEVEL SECURITY;` (tables without this are open to all authenticated users by default)
- At least one `CREATE POLICY` statement covering the access model (admin-only → `USING (is_admin()) WITH CHECK (is_admin())`; user-scoped → `USING (user_id = (SELECT auth.uid()))`)
- If the policy allows UPDATE, include `WITH CHECK (...)` — a null WITH CHECK silently allows privilege escalation
- DELETE policies should use subquery form `USING (user_id = (SELECT auth.uid()))` for perf + consistency
- Post-migration: verify via `mcp__supabase__list_policies` that every listed policy is active

Reference: Spec 213 FR-12 backstory_cache + FR-7 user_profiles RLS hardening.

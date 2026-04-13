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

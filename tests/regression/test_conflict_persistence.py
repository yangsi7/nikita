"""Regression test for conflict context persistence.

Prevents reverting conflict reading from DB-persisted JSONB (user.conflict_details)
back to in-memory ConflictStore, which loses state on Cloud Run cold starts.

Spec 109 deleted store.py entirely — test_conflict_store_module_removed guards
against re-adding it.
"""
import pytest


class TestConflictPersistence:
    """Ensure voice humanization reads conflicts from DB, not in-memory store."""

    def test_server_tools_does_not_import_conflict_store(self):
        """server_tools.py must NOT use get_conflict_store for humanization context.

        The in-memory ConflictStore loses state on every Cloud Run cold start.
        Conflict context must be read from user.conflict_details JSONB.
        """
        from pathlib import Path
        source = Path("nikita/agents/voice/server_tools.py").read_text()

        # Find the _add_humanization_context function
        func_start = source.find("async def _add_humanization_context")
        assert func_start != -1, "Function _add_humanization_context not found"

        # Find the next function definition (end of this function)
        next_func = source.find("\n    async def ", func_start + 1)
        if next_func == -1:
            next_func = len(source)

        func_body = source[func_start:next_func]

        assert "get_conflict_store" not in func_body, (
            "_add_humanization_context must NOT use get_conflict_store() — "
            "in-memory store is empty after Cloud Run cold starts. "
            "Use user.conflict_details JSONB instead (Spec 057)."
        )
        assert "conflict_details" in func_body, (
            "_add_humanization_context must read from user.conflict_details JSONB — "
            "this persists across Cloud Run cold starts (Spec 057)."
        )

    def test_conflict_store_module_removed(self):
        """Spec 109 FR-001: ConflictStore must be deleted (dead code on Cloud Run).

        If this test fails, someone re-added store.py. All conflict state
        must go through user.conflict_details JSONB instead.
        """
        from pathlib import Path
        assert not Path("nikita/conflicts/store.py").exists(), (
            "nikita/conflicts/store.py was re-added — Spec 109 FR-001 deleted it. "
            "ConflictStore is dead code on Cloud Run (in-memory state lost on cold start). "
            "Use user.conflict_details JSONB instead."
        )

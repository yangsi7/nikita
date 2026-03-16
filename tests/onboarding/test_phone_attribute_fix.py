"""Tests for BUG-1 fix: user.phone_number → user.phone.

The User model has `phone` (not `phone_number`). Two files had the wrong
attribute, silently returning None and skipping voice callbacks:
- nikita/onboarding/server_tools.py:443
- nikita/api/routes/onboarding.py:489, 509

These tests verify the fix by checking that the correct attribute is read.
"""

from __future__ import annotations

import ast
import inspect
import textwrap

import nikita.api.routes.onboarding as onboarding_routes
import nikita.onboarding.server_tools as server_tools_module


class TestServerToolsPhoneFix:
    """server_tools.py must use user.phone, not user.phone_number."""

    def test_no_user_phone_number_in_source(self) -> None:
        """AST check: server_tools.py must not access user.phone_number."""
        source = inspect.getsource(server_tools_module)
        tree = ast.parse(source)

        violations: list[int] = []
        for node in ast.walk(tree):
            # Look for Attribute nodes: user.phone_number
            if (
                isinstance(node, ast.Attribute)
                and node.attr == "phone_number"
                and isinstance(node.value, ast.Name)
                and node.value.id == "user"
            ):
                violations.append(node.lineno)

        assert violations == [], (
            f"server_tools.py still uses user.phone_number at line(s) {violations}. "
            f"User model has 'phone', not 'phone_number'."
        )


class TestOnboardingRoutesPhoneFix:
    """onboarding.py routes must use user.phone, not user.phone_number."""

    def test_no_user_phone_number_in_source(self) -> None:
        """AST check: onboarding routes must not access user.phone_number."""
        source = inspect.getsource(onboarding_routes)
        tree = ast.parse(source)

        violations: list[int] = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and node.attr == "phone_number"
                and isinstance(node.value, ast.Name)
                and node.value.id == "user"
            ):
                violations.append(node.lineno)

        assert violations == [], (
            f"onboarding.py still uses user.phone_number at line(s) {violations}. "
            f"User model has 'phone', not 'phone_number'."
        )

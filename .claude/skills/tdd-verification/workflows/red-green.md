# Red-Green-Refactor Workflow

## Overview

The Red-Green-Refactor cycle is the foundation of TDD. This workflow ensures every fix is properly tested.

---

## Phase 1: RED (Write Failing Test)

### Purpose
Prove the bug exists and define the expected behavior.

### Steps

```bash
# 1. Understand the bug
gh issue view <number>

# 2. Create test file
mkdir -p tests/pipeline_fixes
touch tests/pipeline_fixes/test_issue_<number>_<description>.py

# 3. Write test that demonstrates the bug
cat > tests/pipeline_fixes/test_issue_<number>_<description>.py << 'EOF'
"""Tests for Issue #<number>: <description>."""
import pytest

def test_<description>():
    """Verify <expected behavior>."""
    # Arrange
    ...

    # Act
    result = ...

    # Assert
    assert result == expected, f"Expected {expected}, got {result}"
EOF

# 4. Run test - MUST FAIL
pytest tests/pipeline_fixes/test_issue_<number>_*.py -v -x
```

### Verification Criteria
- [ ] Test clearly demonstrates the bug
- [ ] Test fails with meaningful error message
- [ ] Test name describes expected behavior
- [ ] Test is isolated (no external dependencies)

### Anti-Patterns
- Test passes immediately → Not testing the actual bug
- Test is too complex → Break into smaller tests
- Test depends on production data → Use mocks/fixtures

---

## Phase 2: GREEN (Implement Minimal Fix)

### Purpose
Make the test pass with the smallest possible change.

### Steps

```bash
# 1. Identify the fix location
rg "<error pattern>" nikita/ --type py

# 2. Implement minimal fix
# Edit the file to fix the specific issue

# 3. Run test - MUST PASS
pytest tests/pipeline_fixes/test_issue_<number>_*.py -v -x

# 4. Verify no regressions
pytest tests/<affected_module>/ -v
```

### Verification Criteria
- [ ] Test now passes
- [ ] Fix is minimal (no extra changes)
- [ ] Related tests still pass
- [ ] Code follows existing patterns

### Anti-Patterns
- Over-engineering the fix → Keep it minimal
- Fixing unrelated code → Focus on the issue
- Skipping regression tests → Always run module tests

---

## Phase 3: REFACTOR (Optional)

### Purpose
Improve code quality without changing behavior.

### When to Refactor
- Duplicate code introduced
- Poor variable names
- Missing error handling
- Unclear logic

### Steps

```bash
# 1. Identify refactoring opportunities
# Look for patterns, duplication, clarity issues

# 2. Make small incremental changes
# One change at a time

# 3. Run tests after EACH change
pytest tests/pipeline_fixes/test_issue_<number>_*.py -v

# 4. Commit when all tests pass
git add -A && git commit -m "refactor: improve <description>"
```

### Verification Criteria
- [ ] All tests still pass after refactoring
- [ ] Code is cleaner/more readable
- [ ] No new functionality added
- [ ] Each refactoring step is small

---

## Test Template

```python
"""Tests for Issue #XXX: <description>.

This module tests the fix for GitHub issue #XXX which addresses
<brief description of the bug>.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock

# Import the module under test
from nikita.module import function_to_test


class TestIssueFix:
    """Tests for the specific issue fix."""

    def test_normal_case(self):
        """Verify fix works for normal input."""
        # Arrange
        input_data = ...
        expected = ...

        # Act
        result = function_to_test(input_data)

        # Assert
        assert result == expected

    def test_edge_case(self):
        """Verify fix handles edge case."""
        # Arrange
        edge_input = ...

        # Act
        result = function_to_test(edge_input)

        # Assert
        assert result is not None  # or specific assertion

    def test_error_case(self):
        """Verify fix handles error gracefully."""
        # Arrange
        bad_input = ...

        # Act & Assert
        with pytest.raises(ExpectedException):
            function_to_test(bad_input)


@pytest.mark.asyncio
class TestAsyncIssueFix:
    """Async tests for the issue fix."""

    async def test_async_normal_case(self):
        """Verify async fix works."""
        # Arrange
        mock_session = AsyncMock()

        # Act
        result = await async_function(mock_session)

        # Assert
        assert result == expected
```

---

## Commit Message Format

```
fix(module): <short description> [#XXX]

- Added test in tests/pipeline_fixes/test_issue_XXX_*.py
- Fixed <specific change> in module/file.py:LINE
- Verified with N tests

Closes #XXX
```

---

## Checklist

Before moving to deployment:

- [ ] RED: Test written and fails
- [ ] GREEN: Test passes with minimal fix
- [ ] REFACTOR: Code improved (if needed)
- [ ] Related tests pass
- [ ] Commit message references issue
- [ ] No debug code left behind

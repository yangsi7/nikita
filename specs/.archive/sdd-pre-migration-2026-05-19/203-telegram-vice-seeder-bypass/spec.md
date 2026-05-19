# 203 — Telegram Vice Seeder Bypass — Quick Spec

**Mode:** quick
**Complexity:** 2
**Date:** 2026-03-30
**Issue:** GH #203

## Problem Statement

Telegram text onboarding uses an inline `_initialize_vices_from_profile()` method with its own `vice_mappings` dict that maps `drug_tolerance` directly to intensity levels 1-5. This bypasses `engine/vice/seeder.py` which PR #202 fixed to cap all intensities to 1. Result: Telegram text users get vices seeded at the wrong intensity.

## Acceptance Criteria

- [ ] AC-1: `_initialize_vices_from_profile()` delegates to `seed_vices_from_profile()` from `engine/vice/seeder.py`
- [ ] AC-2: All vice intensities are 1 regardless of `drug_tolerance` value (1-5)
- [ ] AC-3: When `vice_repo` is None, method returns gracefully without error
- [ ] AC-4: Seeded categories match seeder.py tier mapping (2-5 categories, not all 8)

## Files Affected

- `nikita/platforms/telegram/onboarding/handler.py` — replace method body
- `tests/platforms/telegram/test_handler_vice_seeding.py` — new test file (4 tests)

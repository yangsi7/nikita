# Implementation Plan: Context Engine Enhancements

**Spec**: 040-context-engine-enhancements
**Created**: 2026-01-29
**Estimated Hours**: 8

---

## Overview

Enhance the unified context engine to fully utilize backstory data (5 fields) and add onboarding state tracking to ContextPackage.

### CoD^Σ Architecture

```
ContextPackage (models.py)
    ↓ add 3 fields
    ├── is_new_user: bool
    ├── days_since_onboarding: int
    └── onboarding_profile_summary: str

ContextEngine (engine.py)
    ↓ populate new fields
    └── _build_context_package() uses UserData

PromptGenerator (generator.py)
    ↓ expand backstory format
    └── GENERATOR_PROMPT template: backstory section → bullet points
```

---

## Implementation Phases

### Phase 1: Model Updates (US-2) - 1 hour

**Files to modify**:
- `nikita/context_engine/models.py`

**Changes**:
1. Add 3 new fields to `ContextPackage`:
   ```python
   # === Onboarding State ===
   is_new_user: bool = Field(default=True, description="True if onboarded within 7 days")
   days_since_onboarding: int = Field(default=0, ge=0, description="Days since onboarded_at")
   onboarding_profile_summary: str = Field(default="", description="Key preferences from onboarding")
   ```

**Tests** (4 tests):
- `test_context_package_has_onboarding_fields` - Fields exist with defaults
- `test_context_package_is_new_user_calculation` - 7-day threshold
- `test_context_package_days_since_onboarding` - Correct calculation
- `test_context_package_onboarding_profile_summary` - Summary generation

---

### Phase 2: Engine Updates (US-2) - 2 hours

**Files to modify**:
- `nikita/context_engine/engine.py`

**Changes**:
1. In `_build_context_package()`, populate new fields from `UserData`:
   ```python
   # Calculate onboarding state
   onboarded_at = user_data.onboarded_at
   if onboarded_at:
       days_since = (datetime.now(UTC) - onboarded_at).days
       is_new = days_since <= 7
   else:
       days_since = 0
       is_new = True

   # Extract summary from profile
   profile = user_data.onboarding_profile
   summary = self._summarize_onboarding_profile(profile)
   ```

2. Add helper method `_summarize_onboarding_profile(profile: dict) -> str`:
   - Extract key preferences (name, interests, preferences)
   - Limit to 200 chars

**Tests** (4 tests):
- `test_engine_populates_is_new_user_true` - User onboarded 3 days ago
- `test_engine_populates_is_new_user_false` - User onboarded 30 days ago
- `test_engine_populates_days_since_onboarding` - Correct calculation
- `test_engine_summarizes_onboarding_profile` - Summary extraction

---

### Phase 3: Backstory Expansion (US-1) - 2 hours

**Files to modify**:
- `nikita/context_engine/generator.py`

**Changes**:
1. Replace 1-line backstory format with bullet point function:
   ```python
   def _format_backstory(backstory: BackstoryContext | None) -> str:
       """Format backstory as bullet points (62% token savings)."""
       if not backstory or not backstory.has_backstory():
           return "- Standard meeting story"

       lines = []
       if backstory.venue:
           lines.append(f"- Where: {backstory.venue}")
       if backstory.how_we_met:
           lines.append(f"- Context: {backstory.how_we_met}")
       if backstory.the_moment:
           lines.append(f"- The spark: {backstory.the_moment}")
       if backstory.unresolved_hook:
           lines.append(f"- Unfinished: {backstory.unresolved_hook}")
       if backstory.tone:
           lines.append(f"- Tone: {backstory.tone}")

       return "\n".join(lines)
   ```

2. Update `GENERATOR_PROMPT` template backstory section:
   ```
   ### How We Met
   {_format_backstory(context.backstory)}
   ```

**Tests** (5 tests):
- `test_format_backstory_full_5_fields` - All fields present
- `test_format_backstory_partial_2_fields` - Only venue + moment
- `test_format_backstory_empty` - No backstory → default
- `test_format_backstory_bullet_format` - Uses "-" prefix
- `test_backstory_in_generated_prompt` - Integration test

---

### Phase 4: Token Budget (US-3) - 1 hour

**Files to modify**:
- `nikita/context_engine/generator.py`
- `nikita/context_engine/models.py` (if constant defined)

**Changes**:
1. Update `MAX_TOKENS` constant from 10000 to 11000
2. Update any token budget validation

**Tests** (2 tests):
- `test_token_budget_11k_limit` - New limit enforced
- `test_full_context_within_budget` - Complete package fits

---

### Phase 5: Documentation (US-3) - 2 hours

**Files to modify**:
- `memory/memory-system-architecture.md`
- `nikita/context_engine/CLAUDE.md` (create if missing)

**Changes**:
1. Document new ContextPackage fields
2. Document backstory formatting logic
3. Update architecture diagrams

**Tests**: No automated tests (documentation only)

---

## Test Plan

### Unit Tests (15 tests)

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `tests/context_engine/test_models.py` | 4 | ContextPackage new fields |
| `tests/context_engine/test_engine.py` | 4 | Engine population |
| `tests/context_engine/test_generator.py` | 5 | Backstory formatting |
| `tests/context_engine/test_generator.py` | 2 | Token budget |

### Integration Tests (2 tests)

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `tests/context_engine/test_integration.py` | 2 | End-to-end flow |

---

## Dependencies

### Internal
- Spec 039 (unified context engine) - COMPLETE
- DatabaseCollector already loads onboarding fields

### External
- None

---

## Rollback Plan

1. Revert generator.py backstory format to 1-line
2. Keep new ContextPackage fields (backwards compatible)
3. No database migrations to revert

---

## Verification

### Pre-Implementation
- [ ] Spec 039 tests pass (307 tests)
- [ ] DatabaseCollector loads onboarding fields

### Post-Implementation
- [ ] All 17 new tests pass
- [ ] Existing 307 context_engine tests pass
- [ ] Token usage within 11K budget
- [ ] E2E test via Telegram MCP

---

## Estimated Effort

| Phase | Hours | Complexity |
|-------|-------|------------|
| Model Updates | 1 | Low |
| Engine Updates | 2 | Medium |
| Backstory Expansion | 2 | Medium |
| Token Budget | 1 | Low |
| Documentation | 2 | Low |
| **Total** | **8** | Medium |

---

**Version**: 1.0
**Next Step**: Auto-chain to generate-tasks (Phase 6)

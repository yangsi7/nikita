-- Spec 215 PR-F1a §9.1 (FR-12) — preferred_call_window slot.
--
-- Adds a nullable text column to user_profiles for the wizard slot collected
-- in PR-F3 (FR-12). Idempotent via IF NOT EXISTS so the migration is safe to
-- re-apply.
--
-- The column is text (free-form) rather than enum to avoid coupling the
-- schema to the wizard-prompt vocabulary; validation happens in the Pydantic
-- WizardSlots model per .claude/rules/agentic-design-patterns.md (Pydantic
-- completion gates over schema enums).
--
-- RLS on user_profiles is owned by Spec 213 PR 213-3 (already enabled with
-- per-user policies); this column inherits those policies — no policy change
-- required.

ALTER TABLE user_profiles
    ADD COLUMN IF NOT EXISTS preferred_call_window TEXT NULL;

COMMENT ON COLUMN user_profiles.preferred_call_window IS
    'Spec 215 FR-12: free-form preferred-call-window slot collected by the '
    'wizard (e.g., "weekday evenings"). Validated by the Pydantic WizardSlots '
    'model, not at the DB level.';

# Tuning Constants

Magic numbers in production tuning code hide intent and are invisible to review. GH #199 (PR #255) discovered the memory dedup threshold had silently sat at 0.92 since GH #157, repeated as a bare literal at two call sites with no name, no comment, no settings-surface — silently too tight for the therapist-fact E2E variants (similarity ~0.88-0.91) that slipped through.

## Rules

- **Named constants**: every scoring, decay, threshold, tier, and weight must live in a module-level constant (UPPER_SNAKE_CASE) with a multi-line comment containing:
  - The current value
  - Prior values + the PR/GH issue that changed each
  - A one-line rationale (why *this* value)
- **Single source of truth**: the constant is imported once per module; no re-declaring at call sites. `threshold: float = MY_CONSTANT` is correct; `threshold: float = 0.87` is not.
- **Regression guard**: every tuning constant needs a test asserting its exact current value, with a comment pointing to the driving issue. Silent drift is the anti-pattern — intentional change needs explicit proof.
- **Audit before edits**: when editing a threshold, first `rg -n "=\s*0\.[0-9]+" nikita/ | rg -v test` to surface other bare numeric tunings in the same module, and note them in the PR description (don't fix in scope — just track).

## Known hotspots to migrate (opportunistic, not urgent)

- `nikita/engine/constants.py` — decay rates, grace periods, metric weights (mostly already named)
- `nikita/engine/chapters/prompts.py` — boss thresholds are configured in YAML but some intermediate scoring constants may still be bare numerics
- `nikita/pipeline/stages/*.py` — per-stage timeouts, retry counts

## Related
- `.claude/rules/review-findings.md` — finding-to-GH-issue workflow
- Spec 210 (test-quality-audit) — may extend scope to scan test files for hardcoded numeric assertions that reference a production constant the test doesn't import

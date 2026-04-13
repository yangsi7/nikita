---
description: Process for handling code review and audit findings
globs: ["**"]
---

# Review Finding Process

When code reviews or audits reveal misalignments with specs:

1. **Bugs (code doesn't match spec)**: Fix in current PR if small. Create GH issue if complex.
2. **Missing features (spec defines, code omits)**: Create GH issue with `enhancement` label.
3. **Design changes (behavior should differ from spec)**: Create GH issue + new spec via `/feature`.
4. **All findings**: Log in `event-stream.md` with `[REVIEW]` tag and GH issue number.
5. **Few-shot echo rule (GH #200, PR #256)**: when a finding is about a hardcoded canonical string/phrase (boss opening, chapter prompt, persona response), grep every persona/prompt file for mirrored phrasing before finalizing the fix. Few-shot examples are imitation targets — leaving the cliché in one place makes the fix self-reinforce the bug. Scope: `nikita/agents/text/persona.py`, `nikita/engine/chapters/prompts.py`, `nikita/pipeline/templates/*.j2`. Missing this echo-sweep is a PR-blocker.

Format: `gh issue create --title "fix(scope): description" --label "bug" --body "..."`

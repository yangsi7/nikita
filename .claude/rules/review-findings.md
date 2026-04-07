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

Format: `gh issue create --title "fix(scope): description" --label "bug" --body "..."`

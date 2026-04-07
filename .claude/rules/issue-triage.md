---
description: Classify and track issues by severity during audits, reviews, and testing
globs: ["**"]
---

# Issue Triage Protocol

When ANY issue is uncovered during audit, verification, testing, or code review:

**1. Classify** — severity label:

| Level | Definition | Action |
|-------|-----------|--------|
| critical | System broken, data loss, security | **STOP.** Create GH issue. Fix NOW. Re-verify. |
| high | Feature broken, test failures | Create GH issue. Fix before proceeding. |
| medium | Quality gap, missing tests, docs | Create GH issue. Fix if <30 min, else schedule. |
| low | Enhancement, code smell | Create GH issue (`enhancement`). Non-blocking. |

**2. Track** — `gh issue create --title "fix(scope): desc" --label "{severity}"`
**3. Plan** — CRITICAL/HIGH: fix FIRST. MEDIUM: parallel. LOW: backlog.
**4. Fix (TDD)** — Failing test → minimal fix → green → re-verify.
**5. Gate Rule** — No phase transition with open CRITICAL or HIGH issues.

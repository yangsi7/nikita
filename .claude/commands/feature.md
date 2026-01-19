---
description: Create comprehensive feature specification through Socratic questioning - SDD Phase 3
allowed-tools: Bash(fd:*), Bash(git:*), Bash(mkdir:*), Bash(project-intel.mjs:*), Read, Write, Grep, Edit
argument-hint: ["feature description"]
---

# Feature Specification - SDD Phase 3

Create a comprehensive feature specification through interactive dialogue using Socratic questioning.

## Unified Skill Routing

This command routes to **SDD Phase 3: Specification** via the unified skill at @.claude/skills/sdd/SKILL.md.

**Phase 3 Workflow:** @.claude/skills/sdd/workflows/03-specification.md

---

## User Input

```text
$ARGUMENTS
```

---

## Phase 3 Process

Follow the **sdd skill Phase 3** workflow:

### 1. Understand Feature (Socratic Questioning)

**Core Questions:**
1. What problem does this solve? (user pain point)
2. Who is this for? (personas)
3. What does success look like? (metrics)

**Technical Questions:**
4. What's the scope? (in/out of scope)
5. Are there constraints? (timeline, technical)
6. What are the risks? (dependencies, rollback)

### 2. Extract Requirements

From answers, structure as:
```markdown
- **REQ-001:** [Requirement text]
  - **Priority:** Must-have | Should-have | Nice-to-have
  - **User Story:** As a [user], I want [action] so [benefit]
```

### 3. Define Success Criteria

- Functional: Feature works as expected
- Performance: Measurable thresholds
- User Experience: Survey/metrics improvements

### 4. Technical Context

Use project-intel.mjs to understand existing code:
```bash
project-intel.mjs --search "relevant-keyword" --json
project-intel.mjs --dependencies src/file.ts --direction downstream --json
```

### 5. Generate Specification

**Feature Directory:** `specs/NNN-feature-name/`
**Spec File:** `specs/NNN-feature-name/spec.md`

Use @.claude/templates/feature-spec.md format.

---

## Quality Gate

**Article IV Compliance**: Spec must be:
- ✓ Technology-agnostic (WHAT/WHY, not HOW)
- ✓ Complete (no [NEEDS CLARIFICATION] markers)
- ✓ User-centric (tied to personas/journeys)
- ✓ Testable (all requirements have ACs)

---

## Auto-Chain

After Phase 3 completes successfully:
1. Auto-invoke Phase 5 (/plan)
2. Auto-invoke Phase 6 (tasks)
3. Auto-invoke Phase 7 (/audit)

```
/feature → spec.md → /plan → plan.md → tasks.md → /audit → audit-report.md
```

---

## Success Criteria

Before generating spec:
- [ ] Problem statement clear
- [ ] All requirements prioritized
- [ ] Requirements have acceptance criteria
- [ ] Technical approach outlined
- [ ] Risks identified
- [ ] Success metrics defined
- [ ] Out-of-scope documented

---

## Start Now

Begin with opening question:

> "I'll help you create a comprehensive feature specification. Let's start with the basics:
>
> **What feature do you want to build, and what problem does it solve for your users?**
>
> (Feel free to describe it in your own words - I'll help structure it into a formal spec)"

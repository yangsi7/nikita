# Phase 4-5: Reporting and Automatic Workflow Progression

**Purpose**: Report specification completion to user and automatically trigger implementation planning workflow.

---

## Phase 4: Report to User

**Output Format**:

```
✓ Feature specification created: specs/<number>-<name>/spec.md

Intelligence Evidence:
- Queries executed: project-intel.mjs --search, --overview
- Patterns found: <file:line references>
- Related features: <existing feature numbers>

User Stories:
- P1 stories: <count> (MVP scope)
- P2 stories: <count> (enhancements)
- P3 stories: <count> (future)

Clarifications Needed:
- [NEEDS CLARIFICATION markers if any, max 3]

**Automatic Next Steps**:
1. If clarifications needed: Use clarify-specification skill
2. Otherwise: **Automatically create implementation plan**

Invoking /plan command now...

[Plan creation, task generation, and audit will proceed automatically]
```

**Example**:

```
✓ Feature specification created: specs/004-auth-social-login/spec.md

Intelligence Evidence:
- Queries executed: project-intel.mjs --search "auth", --overview
- Patterns found:
  - src/components/Login.tsx:12-45 (existing email/password login)
  - src/utils/auth.ts:23-67 (JWT token management)
- Related features: 002-auth-basic

User Stories:
- P1 stories: 2 (Social login with Google/GitHub, Account linking)
- P2 stories: 1 (Profile sync from social provider)
- P3 stories: 1 (Additional social providers)

Clarifications Needed: None

**Automatic Next Steps**:
Automatically creating implementation plan...

Invoking /plan specs/004-auth-social-login/spec.md

[Planning, task generation, and audit will proceed automatically]
```

---

## Phase 5: Automatic Implementation Planning

**DO NOT ask user to trigger planning** - this is automatic workflow progression (unless clarifications needed).

### Step 5.1: Check for Clarifications

**If [NEEDS CLARIFICATION] markers exist (1-3 markers)**:

```
⚠ Clarifications needed before planning:

1. [NEEDS CLARIFICATION: Should social login support GitHub, Google, or both?]
2. [NEEDS CLARIFICATION: Should users link multiple social accounts to one email?]

**Next Action**:
Use clarify-specification skill to resolve ambiguities.

After clarifications:
- User provides answers via dialogue
- Re-run specify-feature skill with updated requirements
- Automatic workflow progression will continue
```

**User must**:
- Run clarify-specification skill, OR
- Provide answers in conversation
- Re-run specify-feature skill after clarifications

**If NO clarifications** (or max 0-1 minor ones):

```
✓ Specification complete with sufficient detail

Proceeding automatically to implementation planning...
```

### Step 5.2: Invoke /plan Command

**Instruct Claude via SlashCommand tool**:

```markdown
Specification is complete. **Automatically create the implementation plan**:

Run: `/plan specs/$FEATURE/spec.md`

This will:
1. Create implementation plan with tech stack selection
2. Generate research.md, data-model.md, contracts/, quickstart.md
3. Define ≥2 acceptance criteria per user story
4. **Automatically invoke generate-tasks skill**
5. **Automatically invoke /audit quality gate**

The entire workflow from planning → tasks → audit happens automatically. No manual intervention needed.
```

**What /plan does**:

1. **create-implementation-plan skill** activates
   - Reads spec.md (technology-agnostic requirements)
   - Queries project-intel.mjs for existing patterns
   - Selects tech stack and architecture
   - Creates plan.md with:
     - Technical approach and justification
     - File structure and component organization
     - Acceptance criteria (≥2 per user story)
     - Dependencies and integration points

2. **Generates supporting artifacts**:
   - research.md - Technical research and decisions
   - data-model.md - Database/state schemas
   - contracts/ - API contracts (if applicable)
   - quickstart.md - Development setup instructions

3. **Automatically invokes generate-tasks skill**
   - Creates tasks.md
   - Organizes tasks by user story (P1, P2, P3)
   - Maps tasks to acceptance criteria

4. **Automatically invokes /audit**
   - Validates spec.md ↔ plan.md ↔ tasks.md consistency
   - Checks constitutional compliance
   - Verifies requirement coverage

### Step 5.3: Workflow Automation Chain

**After `/plan` is invoked, the automated workflow proceeds**:

```
/plan specs/$FEATURE/spec.md
  ↓ (automatic)
create-implementation-plan skill
  ↓ creates: plan.md, research.md, data-model.md, contracts/, quickstart.md
  ↓ (automatic)
generate-tasks skill
  ↓ creates: tasks.md
  ↓ (automatic)
/audit $FEATURE
  ↓ validates: spec.md ↔ plan.md ↔ tasks.md consistency
  ↓
Quality Gate Result: PASS/FAIL
```

**User sees**:
```
✓ spec.md created
✓ plan.md created
✓ research.md created
✓ data-model.md created
✓ tasks.md created
✓ audit report generated

Audit Result: PASS

Implementation is ready. Run `/implement plan.md` to begin.
```

**User only needs to**:
1. Review audit results
2. Fix any CRITICAL issues (if audit fails)
3. Or proceed with `/implement plan.md` (if audit passes)

---

## Automatic vs Manual Actions

**Automatic (no user action required)**:

- ✓ Invoke /plan command after spec.md created
- ✓ create-implementation-plan skill execution
- ✓ generate-tasks skill execution
- ✓ /audit quality gate execution
- ✓ Artifact generation (plan.md, research.md, data-model.md, tasks.md)

**Manual (user action required)**:

- User runs `/feature "<description>"` to start workflow
- User answers clarifications (if [NEEDS CLARIFICATION] markers exist)
- User reviews audit results
- User fixes CRITICAL issues (if audit fails)
- User runs `/implement plan.md` to begin implementation

---

## Workflow State Diagram

```
User: /feature "description"
    ↓
specify-feature skill (Phase 0-3)
    ↓ creates: spec.md
    ↓
[NEEDS CLARIFICATION?]
    YES → clarify-specification skill → update spec.md → continue
    NO  ↓
    ↓ (automatic)
/plan command (SlashCommand tool)
    ↓
create-implementation-plan skill
    ↓ creates: plan.md, research.md, data-model.md
    ↓ (automatic)
generate-tasks skill
    ↓ creates: tasks.md
    ↓ (automatic)
/audit command
    ↓ validates: consistency
    ↓
[AUDIT PASS?]
    YES → Ready for /implement
    NO  → User fixes CRITICAL issues → re-audit
```

---

## Enforcement Checklist

Before completing this phase, verify:

- [ ] Report generated with all required sections
- [ ] Intelligence evidence documented
- [ ] User stories counted (P1/P2/P3)
- [ ] Clarifications status checked
- [ ] If NO clarifications: /plan command invoked automatically
- [ ] If clarifications exist: User notified to run clarify-specification skill
- [ ] Automatic workflow progression communicated to user

**Note**: This completes specification creation. Next steps happen automatically unless clarifications are needed.

---

## Constitutional Compliance Summary

**Article I: Intelligence-First**
- ✓ project-intel.mjs queries executed before file operations

**Article II: Evidence-Based Reasoning**
- ✓ CoD^Σ trace with evidence saved to /tmp/*.json

**Article IV: Specification-First Development**
- ✓ Specification is technology-agnostic (WHAT/WHY only)
- ✓ Planning happens AFTER specification (automatic via /plan)

**Article VII: User-Story-Centric Organization**
- ✓ User stories are independently testable
- ✓ User stories prioritized (P1/P2/P3)

**Article V: Template-Driven Quality**
- ✓ /audit quality gate automatically invoked
- ✓ Consistency validated before implementation

**Next Workflow**: If clarifications needed, clarify-specification skill. Otherwise, automatic /plan → /tasks → /audit → ready for /implement.

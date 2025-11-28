# Agent Integration & Related Workflows

## Agent Integration

This skill is designed to run within the executor-implement-verify agent's isolated context.

### Executor Agent Execution

**When**: User runs `/implement plan.md` (manual action)

**Agent**: executor-implement-verify

**Delegation Method**: The `/implement` slash command can launch the executor agent with this skill

**Task Tool Invocation** (by orchestrator or user):
```python
Task(
    subagent_type="executor-implement-verify",
    description="Implement tasks from plan with TDD",
    prompt="""
    @.claude/agents/executor-implement-verify.md

    Implement the tasks in plan.md following test-driven development:
    1. Read plan.md and tasks.md
    2. Implement user stories in priority order (P1 → P2 → P3)
    3. Follow TDD: write tests first, implement to pass
    4. Verify each story independently with /verify --story P#
    5. Create handover if blocked

    Target: specs/[feature]/plan.md
    Expected: Progressive delivery with AC verification per story
    """
)
```

**What Executor Receives**:
- plan.md (implementation plan with tech stack)
- tasks.md (user-story-organized task breakdown)
- spec.md (for context on requirements)
- Constitution (Article III TDD, Article VII progressive delivery)
- Templates: verification-report.md, handover.md

**What Executor Returns**:
- Implemented code (tests + implementation)
- Verification reports per story (YYYYMMDD-HHMM-verification-P#.md)
- Handover documents if blocked (YYYYMMDD-HHMM-handover-*.md)
- Updated tasks.md with completion status

### Supporting Agents (When Needed)

**Code Analyzer** - For understanding existing code:
```python
# Executor can delegate to analyzer if needed
Task(
    subagent_type="code-analyzer",
    description="Analyze existing auth module before modification",
    prompt="""
    @.claude/agents/code-analyzer.md

    Analyze src/auth/*.ts to understand current implementation
    before adding OAuth support. Use project-intel.mjs first.
    Output: analysis report with architecture and dependencies.
    """
)
```

**Debugger** - For test failures:
```python
# Executor can delegate to analyzer in debug mode
Task(
    subagent_type="code-analyzer",
    description="Debug failing OAuth integration test",
    prompt="""
    @.claude/agents/code-analyzer.md

    Debug why OAuth callback test is failing with 401 error.
    Use debug-issues skill workflow.
    Output: bug-report.md with root cause and fix.
    """
)
```

### Handover Protocols

**To Planner** (if requirements unclear):
- Create handover.md documenting ambiguity
- Planner clarifies or updates plan
- Resume implementation after resolution

**To Orchestrator** (if blocked by external dependency):
- Create handover.md documenting blocker
- Orchestrator coordinates resolution
- Resume implementation after unblocked

### Verification Workflow

**Automatic /verify Invocation**:
```
implement-and-verify skill (completes story P1)
    ↓ invokes
/verify plan.md --story P1 (SlashCommand tool)
    ↓ runs
AC validation for story P1 only
    ↓ produces
verification-P1.md (PASS/FAIL report)
```

**Progressive Delivery** (Article VII):
- P1 verified → Ship MVP or continue to P2
- P2 verified → Ship enhancement or continue to P3
- Each story independently testable and shippable

## Related Skills & Commands

**Direct Integration**:
- **specify-feature skill** - Provides spec.md with user stories (workflow start)
- **create-implementation-plan skill** - Provides plan.md with ACs (workflow predecessor)
- **generate-tasks skill** - Provides tasks.md with task breakdown (required predecessor)
- **debug-issues skill** - Use when tests fail or blockers occur
- **analyze-code skill** - Use when existing code needs understanding
- **/implement command** - User-facing command that invokes this skill
- **/verify command** - Automatically invoked after each story (per P1, P2, P3)

**Workflow Context**:
- Position: **Phase 4** of SDD workflow (final execution phase)
- Triggers: User runs /implement plan.md after audit passes
- Output: Implemented code + verification reports per story

**Quality Gates**:
- **Pre-Implementation**: quality-checklist.md validation (Article V)
- **Per-Story**: /verify --story P# automatic validation (Article VII)
- **Test-First**: Tests written before implementation (Article III)
- **100% AC Coverage**: Every AC must have passing test

**Progressive Delivery Pattern** (Article VII):
```
P1 implemented → /verify --story P1 → PASS → Ship MVP or Continue
P2 implemented → /verify --story P2 → PASS → Ship Enhancement or Continue
P3 implemented → /verify --story P3 → PASS → Ship Complete Feature
```

Each story is independently shippable, enabling faster value delivery.

## When to Use This Skill

**Use implement-and-verify when:**
- User has a plan ready to execute
- User wants to implement tasks with TDD
- User needs AC verification
- User says "implement the plan"

**Don't use when:**
- No plan exists yet (use create-plan skill)
- User just wants to analyze code (use analyze-code skill)
- User wants to debug (use debugging skill)

## Success Metrics

**Verification Quality:**
- 100% AC coverage required
- All ACs must pass
- No task complete without verification

**Implementation Quality:**
- Tests written first
- Minimal implementation (YAGNI)
- Lint and build pass

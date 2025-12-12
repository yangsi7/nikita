# SDD Prerequisite Check

## Purpose

Invoke the `sdd-coordinator` agent to validate prerequisites before executing any SDD phase.

---

## Task Tool Invocation

```
Task(
  subagent_type="sdd-coordinator",
  description="SDD workflow prerequisite validation",
  prompt="""
    Analyze the current SDD workflow state for this project.

    ## Context
    - User Intent: {detected_intent}
    - Working Directory: {cwd}
    - Target Feature: {feature_name if known}

    ## Required Analysis
    1. Check which SDD artifacts exist:
       - memory/product.md (Phase 1)
       - memory/constitution.md (Phase 2)
       - specs/*/spec.md (Phase 3)
       - specs/*/plan.md (Phase 5)
       - specs/*/tasks.md (Phase 6)
       - specs/*/audit-report.md (Phase 7)

    2. Determine current phase based on existing artifacts

    3. Validate prerequisites for requested action:
       - For /feature: No hard prerequisites (product.md optional)
       - For /plan: spec.md must exist and be clarified
       - For /audit: spec.md, plan.md, tasks.md must exist
       - For /implement: audit must PASS

    4. Check for blocking issues:
       - [NEEDS CLARIFICATION] markers in spec.md
       - CRITICAL issues in audit-report.md
       - Missing required files

    ## Output Format (JSON)
    {
      "current_phase": <1-8>,
      "phase_name": "<phase description>",
      "prerequisites_met": <true|false>,
      "missing_artifacts": ["<list of missing files>"],
      "blocking_issues": ["<list of blockers>"],
      "clarification_needed": <true|false>,
      "audit_status": "<PASS|FAIL|NOT_RUN>",
      "recommended_action": "<specific command>",
      "reason": "<explanation>"
    }
  """
)
```

---

## Response Handling

### Prerequisites Met (Green Path)

```
IF response.prerequisites_met = true:
  Log: "Prerequisites validated. Proceeding to {response.recommended_action}"
  PROCEED to phase-routing.md
```

### Missing Artifacts (Yellow Path)

```
IF response.missing_artifacts.length > 0:
  Report to user:
    "Cannot proceed with {intent}. Missing artifacts:"
    - {artifact_1}
    - {artifact_2}

    "Suggested next step: {response.recommended_action}"

  OFFER to run prerequisite command
```

### Blocking Issues (Red Path)

```
IF response.blocking_issues.length > 0:
  Report to user:
    "Workflow blocked. Issues found:"
    - {issue_1}
    - {issue_2}

    "Resolution: {response.reason}"

  IF response.clarification_needed:
    SUGGEST: "Run /clarify to resolve ambiguities"

  IF response.audit_status = "FAIL":
    SUGGEST: "Fix CRITICAL audit issues before /implement"
```

---

## Prerequisite Matrix

| Target Phase | Required Artifacts | Blocking Conditions |
|--------------|-------------------|---------------------|
| 1. define-product | None | - |
| 2. generate-constitution | product.md | - |
| 3. /feature | (optional) product.md, constitution.md | - |
| 4. /clarify | spec.md with [NEEDS CLARIFICATION] | - |
| 5. /plan | spec.md (clarified) | Unclarified spec |
| 6. /tasks | plan.md | - |
| 7. /audit | spec.md, plan.md, tasks.md | - |
| 8. /implement | tasks.md, audit PASS | Audit FAIL, CRITICAL issues |

---

## Error Handling

### Coordinator Agent Timeout

```
IF Task timeout:
  FALLBACK to manual prerequisite check:
  - fd spec.md specs/
  - rg "\[NEEDS CLARIFICATION\]" specs/
  - Check audit-report.md for CRITICAL
```

### Ambiguous Response

```
IF response.recommended_action is unclear:
  ASK user for clarification:
  "Multiple valid paths detected. Which would you like to pursue?"
  - Option A: {path_1}
  - Option B: {path_2}
```

---

## Integration with Orchestrator

After prerequisite check:
1. Store response in workflow state
2. Pass `recommended_action` to phase-routing.md
3. Pass `blocking_issues` to error handling
4. Log check result to event-stream.md

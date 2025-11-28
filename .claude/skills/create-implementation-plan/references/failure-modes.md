# Failure Modes, Anti-Patterns, and Prerequisites

## Anti-Patterns to Avoid

**DO NOT**:
- Plan before specification exists (Article IV violation)
- Skip intelligence queries (Article I violation)
- Design without checking constitution gates (Article VI violation)
- Create ACs with < 2 per story (Article III violation)
- Mix specification and implementation concerns
- Copy existing code without intelligence analysis
- Create wrapper layers around framework features

**DO**:
- Query intelligence sources before designing
- Check constitution gates pre AND post design
- Create ≥2 testable ACs per user story
- Use CoD^Σ traces with file:line evidence
- Trust framework features (avoid custom implementations)
- Document decisions with rationale in research.md
- Map components to existing architecture patterns

---

## Prerequisites

Before using this skill:
- ✅ spec.md exists (Article IV: cannot create plan without specification)
- ✅ PreToolUse hook validates spec.md presence (automatic enforcement)
- ✅ project-intel.mjs is executable
- ✅ PROJECT_INDEX.json exists
- ⚠️ Optional: constitution.md exists (for Article VI complexity gates)
- ⚠️ Optional: product.md exists (for user-need alignment)

## Dependencies

**Depends On**:
- **specify-feature skill** - MUST run before this skill (Article IV)
- **clarify-specification skill** - Should run if [NEEDS CLARIFICATION] markers exist

**Integrates With**:
- **generate-tasks skill** - Automatically invoked after this skill completes
- **implement-and-verify skill** - Uses plan.md output as input

**Tool Dependencies**:
- project-intel.mjs (intelligence queries for patterns, dependencies)
- MCP Ref tool (library documentation)
- MCP Context7 tool (external framework docs)

## Next Steps

After plan completes, **automatic workflow progression**:

**Automatic Chain** (no manual intervention):
```
create-implementation-plan (creates plan.md, research.md, data-model.md, contracts/)
    ↓ (auto-invokes generate-tasks)
generate-tasks (creates tasks.md)
    ↓ (auto-invokes /audit)
/audit (validates consistency)
    ↓ (if PASS)
Ready for /implement
```

**User Action Required**:
- **If audit PASS**: Run `/implement plan.md` to begin implementation
- **If audit FAIL**: Fix CRITICAL issues (usually in spec or plan), re-run workflow
- **If complexity gates fail**: Justify violations or simplify design

**Outputs Created**:
- `specs/$FEATURE/plan.md` - Main implementation plan
- `specs/$FEATURE/research.md` - Technical decisions and rationale
- `specs/$FEATURE/data-model.md` - Entity schemas (if applicable)
- `specs/$FEATURE/contracts/` - API/interface contracts (if applicable)
- `specs/$FEATURE/quickstart.md` - Test scenarios (if applicable)

**Commands**:
- **/tasks** - Automatically invoked to generate task breakdown
- **/implement plan.md** - User runs after audit passes

---

## Failure Modes

### Common Failures & Solutions

**1. spec.md does not exist (Article IV violation)**
- **Symptom**: PreToolUse hook blocks with "Cannot create plan without specification"
- **Solution**: Run specify-feature skill or /feature command first
- **Prevention**: Follow SDD workflow order: /feature → /plan → /tasks → /implement

**2. Constitution complexity gates fail (Article VI)**
- **Symptom**: Plan requires >3 projects or >2 abstraction layers
- **Solution**: Simplify design OR document justification in plan.md
- **Justification Format**: Table showing violation → why needed → simpler alternative rejected
- **Prevention**: Check constitution.md Article VI limits before designing

**3. Intelligence queries return no patterns**
- **Symptom**: No existing code patterns found for reference
- **Solution**: This is normal for new projects; design from first principles
- **Note**: Intelligence is opportunistic, not required

**4. Tech stack selection conflicts with existing code**
- **Symptom**: Plan proposes different framework than codebase uses
- **Solution**: project-intel.mjs --overview reveals existing stack; align with it
- **Rationale**: Consistency beats novelty (unless justified in research.md)

**5. Missing acceptance criteria (Article III violation)**
- **Symptom**: User story has <2 ACs
- **Solution**: Add testable ACs (Given/When/Then format)
- **Requirement**: Minimum 2 ACs per user story for MVP

**6. Specification contains [NEEDS CLARIFICATION] markers**
- **Symptom**: Spec has unresolved ambiguities
- **Solution**: Invoke clarify-specification skill before continuing with plan
- **Action**: Answer structured questions to resolve ambiguities

**7. generate-tasks auto-invocation fails**
- **Symptom**: plan.md created but tasks.md not generated
- **Solution**: Manually run `/tasks plan.md` command
- **Root Cause**: Skill did not complete auto-invocation step (check Phase 6)

**8. Research document missing critical decisions**
- **Symptom**: /audit reports missing justification for tech choices
- **Solution**: Enhance research.md with decision rationale using CoD^Σ evidence
- **Format**: Decision → Rationale → Evidence (file:line or MCP query)

---

## Key Patterns

**Pattern 1: Workflow Order Enforcement**
```
spec.md exists → PreToolUse validates → plan allowed
spec.md missing → PreToolUse blocks → error message
```

**Pattern 2: Constitutional Complexity Management**
```
Pre-Design check → Design → Post-Design re-check → Document justification OR simplify
```

**Pattern 3: Automatic Workflow Progression**
```
Plan complete → Auto-invoke generate-tasks → Auto-invoke /audit → Wait for /implement
```

**Pattern 4: Failure Recovery**
```
Failure detected → Root cause from symptom → Apply solution → Verify prevention
```

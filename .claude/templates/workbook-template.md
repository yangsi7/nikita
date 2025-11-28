# Workbook: Current Context

**Last Updated**: YYYY-MM-DD
**Status**: [ACTIVE | ARCHIVED]

---

## Instructions for Use

This is your **personal context-engineered notepad** for the current session. Use it to:
- **Note important context** that doesn't fit elsewhere
- **Track reflections** and insights as you work
- **Identify antipatterns** to avoid
- **Make quick drafts** to organize thoughts
- **Short-term planning** for current tasks

**CRITICAL**: Keep this file under 300 lines. Archive outdated content regularly.

---

## Current Session Context

**Session ID**: [session-id from .session-id file]
**Date**: YYYY-MM-DD
**Focus**: [Brief description of what you're working on]

### Working On
- [Current task or feature]
- [Key challenge or question]
- [Next immediate step]

### Current State
```
Phase := [RESEARCH | PLANNING | IMPLEMENTATION | VERIFICATION | COMPLETE]
Progress := X/Y tasks complete (Z%)
Blockers := {blocker1, blocker2, ...}
Next_Action := [Specific next step]
```

---

## Key Context to Remember

### Project State
- **Latest Commit**: [Brief description of what was last committed]
- **Current Branch**: [Branch name if using git]
- **Active Files**: [Files currently being modified]
- **Test Status**: [Latest test results]

### Important Insights
- [Insight 1: Discovery or realization that affects the work]
- [Insight 2: Pattern or approach that proved effective]
- [Insight 3: Gotcha or edge case to watch out for]

### Recent Decisions
- **Decision**: [What was decided]
  - **Reason**: [Why it was decided]
  - **Impact**: [What it affects]
  - **Tradeoffs**: [What was given up]

---

## Chain of Drafts (Thinking Out Loud)

Use this section for quick brainstorming and iteration:

### Draft 1: Initial Thought
[First attempt at solving a problem or organizing ideas]

### Draft 2: Refinement
[Improved version based on initial draft]

### Draft 3: Final Approach
[Polished version ready to implement]

---

## Antipatterns Identified

### What NOT to Do
- ❌ **Antipattern**: [Description of what doesn't work]
  - **Why**: [Why it's problematic]
  - **Instead**: [Better approach]

- ❌ **Antipattern**: [Description of what doesn't work]
  - **Why**: [Why it's problematic]
  - **Instead**: [Better approach]

---

## Patterns That Work

### What TO Do
- ✅ **Pattern**: [Description of effective approach]
  - **Why**: [Why it works well]
  - **When**: [When to use it]
  - **Example**: [Concrete example]

- ✅ **Pattern**: [Description of effective approach]
  - **Why**: [Why it works well]
  - **When**: [When to use it]
  - **Example**: [Concrete example]

---

## Quick Reference

### Common Commands
```bash
# Intelligence queries (always first)
project-intel.mjs --overview --json
project-intel.mjs --search "term" --type tsx --json
project-intel.mjs --symbols path/to/file.ts --json

# SDD workflow
/feature "description"  # Creates spec.md, plan.md, tasks.md
/implement plan.md      # Implements with per-story /verify

# Validation
/audit [feature-id]     # Cross-artifact consistency
/verify plan.md --story P1  # Story-level verification
```

### File Locations
- **Skills**: `.claude/skills/[skill-name]/SKILL.md`
- **Commands**: `.claude/commands/[command].md`
- **Templates**: `.claude/templates/[template].md`
- **Shared**: `.claude/shared-imports/` (constitution.md, CoD_Σ.md)
- **Specs**: `specs/[feature-id]/`
- **Docs**: `docs/architecture/`, `docs/guides/`, `docs/reference/`

### Key Imports
```markdown
# Constitution (principles)
@.claude/shared-imports/constitution.md

# CoD^Σ reasoning
@.claude/shared-imports/CoD_Σ.md

# Intelligence guide
@.claude/shared-imports/project-intel-mjs-guide.md
```

---

## Current Challenges

### Technical Challenges
1. **Challenge**: [Description of technical obstacle]
   - **Status**: [BLOCKED | IN_PROGRESS | RESOLVED]
   - **Approach**: [Current approach to solving it]
   - **Resources**: [Helpful references or people]

2. **Challenge**: [Description of technical obstacle]
   - **Status**: [BLOCKED | IN_PROGRESS | RESOLVED]
   - **Approach**: [Current approach to solving it]
   - **Resources**: [Helpful references or people]

### Design Challenges
1. **Challenge**: [Description of design decision]
   - **Options**: [Option A, Option B, Option C]
   - **Tradeoffs**: [Pros and cons of each]
   - **Decision**: [What was chosen and why]

---

## Recent Completions (Last 5)

Track recent wins to maintain momentum:

1. ✓ **[Task/Feature]** - [Brief description of what was completed]
   - Evidence: [file:line or test output]

2. ✓ **[Task/Feature]** - [Brief description of what was completed]
   - Evidence: [file:line or test output]

3. ✓ **[Task/Feature]** - [Brief description of what was completed]
   - Evidence: [file:line or test output]

4. ✓ **[Task/Feature]** - [Brief description of what was completed]
   - Evidence: [file:line or test output]

5. ✓ **[Task/Feature]** - [Brief description of what was completed]
   - Evidence: [file:line or test output]

---

## Upcoming Work (Next 3-5 Tasks)

What's on the immediate horizon:

1. [ ] **[Task]** - [Brief description]
   - Why: [Why this is next]
   - Depends on: [Prerequisites]

2. [ ] **[Task]** - [Brief description]
   - Why: [Why this is next]
   - Depends on: [Prerequisites]

3. [ ] **[Task]** - [Brief description]
   - Why: [Why this is next]
   - Depends on: [Prerequisites]

---

## Questions to Answer

Keep track of open questions:

1. **Q**: [Question that needs answering]
   - **Context**: [Why this matters]
   - **Leads**: [Where to look for answers]

2. **Q**: [Question that needs answering]
   - **Context**: [Why this matters]
   - **Leads**: [Where to look for answers]

---

## Links and References

### Documentation
- [Link to relevant doc]: [Why it's useful]
- [Link to relevant doc]: [Why it's useful]

### Code Examples
- [file:line]: [What this demonstrates]
- [file:line]: [What this demonstrates]

### External Resources
- [URL]: [What this provides]
- [URL]: [What this provides]

---

## Notes Section (Temporary)

Use this for quick scratchpad notes. Clean up frequently.

### Today's Notes
- [Quick note]
- [Observation]
- [Reminder]

### Things to Remember
- [Important context]
- [Gotcha to watch for]
- [Shortcut discovered]

---

## Maintenance Checklist

**Keep workbook under 300 lines** (currently: ~XXX lines)

Weekly maintenance:
- [ ] Archive outdated context to session directories
- [ ] Clean up notes section
- [ ] Update key context
- [ ] Verify patterns and antipatterns still relevant
- [ ] Remove resolved challenges
- [ ] Update recent completions

---

## Archive Log

When content is removed from workbook, note where it went:

- **YYYY-MM-DD**: Moved [content type] to `docs/sessions/[session-id]/[file]`
- **YYYY-MM-DD**: Moved [content type] to `docs/sessions/[session-id]/[file]`

---

## Related Documents

- **Planning**: @planning.md (master plan, architecture)
- **Todo**: @todo.md (actionable tasks)
- **Events**: @event-stream.md (chronological log)
- **Constitution**: @.claude/shared-imports/constitution.md (principles)
- **Documentation Rules**: @docs/documentation-rules.md (file organization)

---

**Remember**:
- Keep under 300 lines
- Archive old content
- Focus on current context only
- Clean up after each session

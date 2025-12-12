---
description: Create comprehensive feature specification through interactive dialogue using Socratic questioning and iterative refinement with specify-feature skill (project)
allowed-tools: Bash(fd:*), Bash(git:*), Bash(mkdir:*), Bash(project-intel.mjs:*), Read, Write, Grep, Edit
argument-hint: ["feature description"]
---

<!-- SDD Orchestration Note:
For full SDD workflow orchestration with prerequisite validation and plan/todo sync,
the sdd-orchestrator skill auto-triggers on feature creation requests and coordinates
with sdd-coordinator agent. Direct /feature invocation bypasses orchestration. -->

You are now executing the `/feature` command. This command helps create a comprehensive feature specification through interactive dialogue using the **specify-feature skill** (@.claude/skills/specify-feature/SKILL.md) in specification mode.

## Your Task

Guide the user to create a complete feature specification using @.claude/templates/feature-spec.md format through Socratic questioning and iterative refinement.

## Process Overview

### Phase 1: Understand the Feature (Socratic Questioning)

Ask targeted questions to understand the feature:

**Core Questions:**
1. **What problem does this solve?**
   - "What user pain point are you addressing?"
   - "What can't users do today that they'll be able to do?"

2. **Who is this for?**
   - "Which user personas will use this feature?"
   - "Are there different user types with different needs?"

3. **What does success look like?**
   - "How will we know this feature is working correctly?"
   - "What metrics will improve?"

**Technical Questions:**
4. **What's the scope?**
   - "What's IN scope for the first version?"
   - "What's explicitly OUT of scope?"

5. **Are there constraints?**
   - "Timeline constraints?"
   - "Technical constraints (must work with existing auth, etc.)?"
   - "Budget/resource constraints?"

6. **What are the risks?**
   - "What could go wrong?"
   - "What dependencies exist?"
   - "What's the rollback plan?"

### Phase 2: Extract Requirements

From the user's answers, extract structured requirements:

**Requirements Format:**
```markdown
- **REQ-001:** Users can log in with Google OAuth
  - **Priority:** Must-have
  - **User Story:** As a user, I want to log in with my Google account so I don't have to create a new password

- **REQ-002:** Sessions persist for 7 days
  - **Priority:** Must-have
  - **User Story:** As a user, I want to stay logged in so I don't have to re-authenticate every visit

- **REQ-003:** Users can log out
  - **Priority:** Must-have
  - **User Story:** As a user, I want to log out so I can secure my account on shared devices
```

**Categorize by Priority:**
- **Must-have:** Core functionality, can't ship without it
- **Should-have:** Important but can be delayed
- **Nice-to-have:** Enhancement for future versions

### Phase 3: Define Success Criteria

Work with user to define how we'll measure success:

```markdown
## Success Metrics

**Functional:**
- 95%+ of OAuth attempts succeed
- Session management works correctly
- Logout clears all session data

**Performance:**
- OAuth flow completes in < 2 seconds
- No impact on page load times

**User Experience:**
- Users prefer OAuth over traditional login (survey)
- Reduced support tickets about password resets
```

### Phase 4: Identify Technical Considerations

Ask about technical context:

**Integration Questions:**
- "What existing systems does this touch?"
- "Are there APIs we need to integrate with?"
- "What's the database schema impact?"

**Use project-intel.mjs to understand existing code:**
```bash
# Find existing authentication code
project-intel.mjs --search "auth|login|session" --json

# Check what would be impacted
project-intel.mjs --dependencies src/auth/session.ts --direction downstream --json
```

### Phase 5: Generate Specification

Use @.claude/templates/feature-spec.md to create structured spec:

```markdown
---
feature_id: "oauth-authentication"
version: "1.0"
status: "draft|approved|in-progress|completed"
priority: "high|medium|low"
---

# Feature Specification: OAuth Authentication

## Overview

### Problem Statement
Users are frustrated with password management and many prefer using their existing Google accounts for authentication.

### Proposed Solution
Implement Google OAuth 2.0 authentication as an alternative to traditional username/password login.

### Success Criteria
- Users can authenticate using Google OAuth
- 95%+ success rate for OAuth attempts
- No impact on existing username/password flow

---

## Requirements

### Functional Requirements

**REQ-001: Google OAuth Login**
- **Priority:** Must-have
- **User Story:** As a user, I want to log in with my Google account so I don't need to remember another password
- **Acceptance Criteria:**
  - OAuth button visible on login page
  - Clicking button redirects to Google consent screen
  - Successful OAuth redirects back with user authenticated
  - Failed OAuth shows clear error message

**REQ-002: Session Management**
- **Priority:** Must-have
- **User Story:** As a user, I want to stay logged in across visits
- **Acceptance Criteria:**
  - Session persists for 7 days
  - Session refresh works automatically
  - Session storage is secure

**REQ-003: Logout Functionality**
- **Priority:** Must-have
- **User Story:** As a user, I want to log out to secure my account
- **Acceptance Criteria:**
  - Logout button clears session completely
  - Logout redirects to login page
  - After logout, protected routes redirect to login

### Non-Functional Requirements

**REQ-004: Performance**
- OAuth flow completes in < 2 seconds
- No increase in page load time

**REQ-005: Security**
- OAuth tokens stored securely
- CSRF protection implemented
- HTTPS required for OAuth flow

### Out of Scope (for v1)
- Facebook/Twitter OAuth (future version)
- Two-factor authentication (separate feature)
- Account linking (OAuth + password on same account)

---

## Technical Specifications

### Architecture

**Components:**
1. **Frontend:** OAuth button + callback handler
2. **Backend:** OAuth flow + session management
3. **Database:** User table modification (add google_id column)

**Dependencies:**
- Google OAuth 2.0 API
- Existing session management system
- User authentication database

### Data Model

**Changes Required:**
```sql
-- Add google_id to users table
ALTER TABLE users ADD COLUMN google_id VARCHAR(255) NULL;
ALTER TABLE users ADD COLUMN oauth_provider VARCHAR(50) NULL;
```

### API Endpoints

**New Endpoints:**
- `GET /auth/google` - Initiate OAuth flow
- `GET /auth/google/callback` - Handle OAuth redirect
- `POST /auth/logout` - Clear session

---

## Implementation Phases

### Phase 1: Database Schema (Week 1)
- Add google_id column to users table
- Migration script
- Schema validation

### Phase 2: Backend OAuth Flow (Week 2)
- Google OAuth integration
- Session management
- Error handling

### Phase 3: Frontend Integration (Week 3)
- OAuth button component
- Callback handler
- Error display

### Phase 4: Testing & Deployment (Week 4)
- Unit tests
- Integration tests
- Gradual rollout (10% → 50% → 100%)

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Google OAuth API changes | High | Low | Pin API version, monitor deprecations |
| Session hijacking | High | Medium | Implement CSRF tokens, secure cookies |
| Performance degradation | Medium | Low | Load testing before rollout |

---

## Success Metrics

**Adoption:**
- 30%+ of new logins use OAuth within 2 weeks
- 50%+ within 4 weeks

**Reliability:**
- 99%+ OAuth success rate
- < 1% error rate

**Performance:**
- < 2 second OAuth completion
- No impact on page load

---

## Rollback Plan

If critical issues arise:
1. Feature flag to disable OAuth button
2. Existing username/password still works
3. No data loss (OAuth users can reset password)

---

## Approval

**Created by:** [Name]
**Date:** [YYYY-MM-DD]
**Approved by:** [Name]
**Approval Date:** [YYYY-MM-DD]
```

## Templates Reference

**Output Template:**
- @.claude/templates/feature-spec.md - Feature specifications (output)

## Expected Output

**Generated file:** `YYYYMMDD-HHMM-feature-spec-{id}.md`

Must include:
1. **Overview** - Problem, solution, success criteria
2. **Requirements** - Functional and non-functional (with priorities)
3. **Technical Specifications** - Architecture, data model, APIs
4. **Implementation Phases** - Breakdown of work
5. **Risks & Mitigations** - What could go wrong
6. **Success Metrics** - How to measure success
7. **Rollback Plan** - How to undo if needed

## Interactive Workflow

**Start with Open Questions:**
```
"Tell me about the feature you want to build. What problem does it solve?"

[User responds]

"That's helpful! Let me ask a few follow-up questions to make sure I understand..."

1. "Who will use this feature? Are there different user types?"
2. "What does a successful implementation look like?"
3. "Are there any constraints I should know about?"
```

**Refine Iteratively:**
```
"Based on what you've told me, I'm hearing these requirements:
- REQ-001: [Requirement]
- REQ-002: [Requirement]

Does that capture what you're looking for? Anything missing?"

[User confirms or adds]

"Great! Now let me ask about the technical side..."
```

**Validate Completeness:**
```
"Let me check if we've covered everything:
✓ Problem statement clear
✓ Requirements defined with priorities
✓ Success metrics identified
✓ Technical approach outlined
✓ Risks considered

Does this feel complete, or should we dig deeper into any area?"
```

## Success Criteria

Before generating the spec file, verify:
- [ ] Problem statement is clear
- [ ] All requirements have priorities
- [ ] Requirements have acceptance criteria
- [ ] Technical approach outlined
- [ ] Risks identified
- [ ] Success metrics defined
- [ ] Rollback plan exists
- [ ] Out-of-scope items documented

## What Happens Next

After creating the feature spec:
1. Save as `YYYYMMDD-HHMM-feature-spec-{id}.md`
2. User can then run: `/plan <feature-spec-file>` to create implementation plan
3. Then: `/implement <plan-file>` to build it
4. Finally: `/verify <plan-file>` to confirm it works

## Start Now

Begin by asking the user about their feature idea:

**Opening Question:**
"I'll help you create a comprehensive feature specification. Let's start with the basics:

**What feature do you want to build, and what problem does it solve for your users?**

(Feel free to describe it in your own words - I'll help structure it into a formal spec)"

Then guide them through the interactive workflow to create a complete specification.

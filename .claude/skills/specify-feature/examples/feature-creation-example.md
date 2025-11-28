# Example: Feature Specification Creation

**User Input**: "I want to build a user authentication system with social login options"

---

## Execution Walkthrough

### Phase 0: Pre-Specification Quality Gate

**Quality Assessment**:

```
Dimension Scores:
- Problem Clarity: 7/10 (clear need for authentication, some details missing)
- Value Proposition: 6/10 (security mentioned, business value implicit)
- Requirements Completeness: 6/10 (social login mentioned, details unclear)
- Technology-Agnostic: 10/10 (no technical details in user input)
- User-Centric: 7/10 (users mentioned, personas not explicit)

Overall Score: 7.2/10

✓ PROCEED to Phase 1 (score ≥ 7.0)
```

### Phase 1: Intelligence-First Context Gathering

**Step 1.1: Auto-Number Next Feature**:

```bash
fd --type d --max-depth 1 '^[0-9]{3}-' specs/
# Output:
# specs/001-dashboard
# specs/002-api
# specs/003-reporting

# Next feature number: 004
```

**Step 1.2: Query Existing Patterns**:

```bash
project-intel.mjs --search "auth login" --type tsx --json > /tmp/spec_intel_patterns.json
```

**Findings**:
```json
{
  "results": [
    {
      "path": "src/components/Login.tsx",
      "lines": "12-45",
      "content": "existing login form with email/password"
    },
    {
      "path": "src/utils/auth.ts",
      "lines": "23-67",
      "content": "JWT token management utilities"
    }
  ]
}
```

**Step 1.3: Understand Project Architecture**:

```bash
project-intel.mjs --overview --json > /tmp/spec_intel_overview.json
```

**Context**:
```
- Frontend: src/components/, src/pages/
- Backend: api/, services/
- Authentication: src/auth/ (existing directory)
- Utilities: src/utils/
```

### Phase 2: Extract User Requirements

**Problem Statement**:
```markdown
## Problem Statement

**What problem are we solving?**
Users need a secure and convenient way to access their accounts.

**Why does this matter?**
- Security: Protect user data and prevent unauthorized access
- Convenience: Users want quick login without creating new passwords
- Trust: Social login leverages trusted providers (Google, GitHub)

**Who experiences this problem?**
- New users registering for the first time
- Existing users who prefer social authentication
- Users managing multiple accounts across platforms

**Current situation:**
Email/password only. Users must create and remember passwords. No social login option.
```

**User Stories**:
```markdown
## User Story 1 - Basic Email/Password Authentication (Priority: P1)

**As a** new user
**I want to** register and login with email/password
**So that** I can access my account securely

**Why P1**: Core functionality, already partially implemented
**Independent Test**: Create account with email/password, verify login works

**Acceptance Scenarios**:
1. **Given** I provide valid email/password, **When** I register, **Then** account created
2. **Given** I have an account, **When** I login with correct credentials, **Then** I'm authenticated
3. **Given** I enter wrong password, **When** I attempt login, **Then** I see error message

## User Story 2 - Social Login (Google/GitHub) (Priority: P2)

**As a** user
**I want to** login with my Google or GitHub account
**So that** I can access my account without creating a password

**Why P2**: Enhances user experience but not blocking for MVP
**Independent Test**: Click "Login with Google", verify authentication completes

**Acceptance Scenarios**:
1. **Given** I click "Login with Google", **When** I authorize, **Then** I'm logged in
2. **Given** I click "Login with GitHub", **When** I authorize, **Then** I'm logged in
3. **Given** social account has no email, **When** I attempt login, **Then** I see error

## User Story 3 - Account Linking (Priority: P2)

**As a** user with an email/password account
**I want to** link my Google/GitHub account
**So that** I can use either method to login

**Why P2**: User convenience, not required for initial launch
**Independent Test**: Login with email, link social account, logout, login with social

**Acceptance Scenarios**:
1. **Given** I'm logged in, **When** I link social account, **Then** both methods work
2. **Given** social email matches account email, **When** I link, **Then** accounts merged
```

### Phase 3: Generate Specification

**Create Directory**:
```bash
mkdir -p specs/004-auth-social-login
git checkout -b 004-auth-social-login
```

**Generate Specification** (saved to `specs/004-auth-social-login/spec.md`):

```markdown
---
feature: 004-auth-social-login
created: 2025-10-23
status: Draft
priority: P1
---

# Feature Specification: User Authentication with Social Login

## Problem Statement
[From Phase 2]

## User Stories
[From Phase 2 - all 3 stories]

## Functional Requirements

**Core Capabilities**:
1. **Email/Password Authentication**: Register and login with email/password
2. **Social Authentication**: Login with Google or GitHub OAuth
3. **Account Linking**: Connect social accounts to existing email accounts

**Data Visibility**:
- User profile (name, email, avatar)
- Authentication method used
- Linked social accounts (if any)

**User Interactions**:
- Register with email/password
- Login with email/password
- Login with social provider (Google/GitHub)
- Link social account to existing account
- Unlink social account

**Constraints**:
- Social accounts must provide email address
- Email must be unique across all authentication methods
- User can have multiple social accounts linked to one email
- Password reset available for email/password accounts only

## Success Criteria

**User-Centric Metrics**:
- % of users choosing social login: ≥ 30%
- Time to complete registration: < 60 seconds
- Authentication success rate: ≥ 99%

**Business Metrics**:
- Reduced password reset requests: -40%
- Increased registration completion rate: +25%

**Adoption Metrics**:
- % of new users using social login: ≥ 40%

## CoD^Σ Evidence Trace

Intelligence Queries:
- project-intel.mjs --search "auth login" --type tsx --json → /tmp/spec_intel_patterns.json
  Findings:
  - src/components/Login.tsx:12-45 (existing email/password login form)
  - src/utils/auth.ts:23-67 (JWT token management)
  - src/services/authService.ts:15 (login API integration)

- project-intel.mjs --overview --json → /tmp/spec_intel_overview.json
  Context:
  - Authentication features in src/auth/ directory
  - API services in src/services/
  - Shared utilities in src/utils/

Assumptions:
- [ASSUMPTION: Social login will integrate with existing JWT auth system (src/utils/auth.ts:23)]
- [ASSUMPTION: Social providers will return user email for account matching]

Clarifications Needed: None

## Edge Cases

**Boundary Conditions**:
- Social account without email: Reject and show error
- Duplicate email between methods: Merge accounts automatically
- Social account already linked: Show "already linked" message

**Error Scenarios**:
- OAuth authorization denied: Return to login page with message
- Social provider API unavailable: Show fallback to email/password
- Account linking fails: Preserve existing account state

**Data Quality Issues**:
- Social provider returns different email: Use social provider email
- User changes social email: Update linked account email
```

### Phase 4: Report to User

```
✓ Feature specification created: specs/004-auth-social-login/spec.md

Intelligence Evidence:
- Queries executed: project-intel.mjs --search "auth", --overview
- Patterns found:
  - src/components/Login.tsx:12-45 (existing email/password login)
  - src/utils/auth.ts:23-67 (JWT token management)
- Related features: None (first authentication feature)

User Stories:
- P1 stories: 1 (Basic email/password authentication)
- P2 stories: 2 (Social login, Account linking)
- P3 stories: 0

Clarifications Needed: None

**Automatic Next Steps**:
Automatically creating implementation plan...

Invoking /plan specs/004-auth-social-login/spec.md
```

### Phase 5: Automatic Workflow Progression

```
Running /plan command...

create-implementation-plan skill activated
  ↓ creates: plan.md (with tech stack: OAuth2, JWT, Passport.js)
  ↓ creates: research.md (OAuth flow analysis, security considerations)
  ↓ creates: data-model.md (User, SocialAccount models)
  ↓ (automatic)

generate-tasks skill activated
  ↓ creates: tasks.md (organized by user story)
  ↓ (automatic)

/audit command activated
  ↓ validates: spec.md ↔ plan.md ↔ tasks.md consistency
  ↓

Audit Result: PASS

✓ Implementation is ready!

Run `/implement plan.md` to begin story-by-story implementation with TDD.
```

---

## Result

**Files Created**:
1. `specs/004-auth-social-login/spec.md` (technology-agnostic specification)
2. `specs/004-auth-social-login/plan.md` (implementation plan with tech stack)
3. `specs/004-auth-social-login/research.md` (technical research)
4. `specs/004-auth-social-login/data-model.md` (database schemas)
5. `specs/004-auth-social-login/tasks.md` (task breakdown by user story)

**Git Branch**: `004-auth-social-login` (created and checked out)

**Ready For**: `/implement plan.md` to begin TDD implementation

**User Actions Required**:
- Review audit results ✓ (PASS)
- Run `/implement plan.md` to start implementation

**Total Time**: ~2-3 minutes (automated workflow from spec → plan → tasks → audit)

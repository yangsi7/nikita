# Phase 2: Technical Design

**Purpose**: Make technology-specific design decisions and document technical architecture.

**Artifacts Created**:
- Tech stack selection
- Component architecture
- `research.md` - Technical decisions with rationale
- `data-model.md` - Entity modeling (technology-agnostic)
- `contracts/` - API specifications
- `quickstart.md` - Test scenarios for validation

---

## Step 2.1: Select Tech Stack

**Based on intelligence findings and spec requirements**:

**Language/Version**: [from project-intel overview or specify new]
**Primary Dependencies**: [frameworks, libraries with versions]
**Storage**: [database, caching, file system if applicable]
**Testing**: [test frameworks, assertion libraries]
**Target Platform**: [web, mobile, desktop, server]

**CoD^Σ Evidence**:
```
Tech Stack Selection:
project-intel.mjs --overview → existing stack is TypeScript + React + Supabase
Decision: Continue with existing stack for consistency
Evidence: src/*/package.json:12 shows react@18, typescript@5
```

---

## Step 2.2: Design Architecture

**Component Breakdown** (from spec user stories):

For each P1 user story:
1. Identify required components (models, services, UI, API)
2. Map to existing architecture (from intelligence queries)
3. Document new components needed
4. Define interfaces/contracts

**Example**:
```
User Story P1: Email/Password Authentication

Components:
- Model: User (extends existing User model at models/user.ts:8)
- Service: AuthService (new, will integrate with existing auth.ts:23)
- API: POST /auth/login, POST /auth/register (new endpoints)
- UI: LoginForm, RegisterForm (enhance existing at components/auth/)

Integration Points:
- Existing: src/utils/auth.ts:23 (session management)
- New: src/services/auth-service.ts (authentication logic)
```

---

## Step 2.3: Create Research Document

**Generate `research.md`** with:

**Technical Decisions**:
1. Decision: [what was decided]
   - Rationale: [why]
   - Alternatives considered: [what else was considered]
   - Evidence: [file:line from intelligence or MCP query]

**Example**:
```markdown
## Decision 1: OAuth Provider Libraries

Decision: Use @supabase/auth-helpers for OAuth integration

Rationale:
- Already using Supabase for backend (src/lib/supabase.ts:5)
- Native support for Google/GitHub OAuth
- Handles token refresh automatically

Alternatives Considered:
- NextAuth.js: Rejected (adds complexity, not needed with Supabase)
- Custom OAuth: Rejected (reinventing wheel, Article VI violation)

Evidence:
- Intelligence: project-intel found Supabase client at src/lib/supabase.ts:5
- MCP Ref: @supabase/auth-helpers supports Google/GitHub OAuth
```

---

## Step 2.4: Design Data Model

**Generate `data-model.md`** (entities WITHOUT implementation):

**For each entity**:
- Name and purpose
- Attributes (without database types)
- Relationships to other entities
- Validation rules

**Example**:
```markdown
## Entity: User

Purpose: Represents authenticated system user

Attributes:
- id: Unique identifier
- email: Email address (unique, validated)
- password_hash: Hashed password (never plaintext)
- oauth_provider: Optional (google|github)
- oauth_id: Optional provider-specific ID
- created_at: Registration timestamp
- last_login: Last successful login

Relationships:
- Has many: Sessions
- Has many: UserRoles

Validation:
- email: Must be valid email format
- password: Minimum 8 characters, must include number + special char
- oauth_provider + oauth_id: Required together or both null
```

---

## Step 2.5: Define API Contracts

**Generate `contracts/` directory** with API specifications:

**For each endpoint**:
- HTTP method and path
- Request schema
- Response schema
- Error cases
- Authentication required?

**Example**: `contracts/auth-endpoints.md`
```markdown
## POST /api/auth/register

Purpose: Create new user account

Request:
- email: string (required, valid email)
- password: string (required, min 8 chars)

Response (201 Created):
- user: { id, email, created_at }
- session: { access_token, refresh_token, expires_at }

Errors:
- 400: Invalid email format
- 409: Email already exists
- 500: Server error

Authentication: None (public endpoint)
```

---

## Step 2.6: Create Quickstart Validation Scenarios

**Generate `quickstart.md`** with test scenarios:

**For each user story**, document:
- Setup steps
- Exact actions to test
- Expected outcomes
- How to verify success

**Example**:
```markdown
## Scenario 1: User Registration (P1 Story)

Setup:
1. Navigate to /register
2. Have valid email ready

Test Steps:
1. Enter email: test@example.com
2. Enter password: SecurePass123!
3. Click "Register"

Expected Outcome:
- HTTP 201 response
- User created in database
- Session token returned
- Redirected to /dashboard

Verification:
- Check database: SELECT * FROM users WHERE email='test@example.com'
- Check session storage: localStorage.getItem('session')
- Verify redirect: window.location.pathname === '/dashboard'
```

---

## Key Patterns

**Pattern 1: Intelligence-Based Architecture**
```
project-intel.mjs queries → identify existing patterns → extend existing OR create new
```

**Pattern 2: Research Documentation**
```
Decision + Rationale + Alternatives + Evidence (file:line or MCP source)
```

**Pattern 3: Technology-Agnostic Data Modeling**
```
Entity purpose → Attributes (no types) → Relationships → Validation (conceptual)
```

**Pattern 4: Contract-First API Design**
```
Endpoint → Request schema → Response schema → Error cases → Auth requirements
```

**Pattern 5: Quickstart Scenarios**
```
Setup → Test steps → Expected outcome → Verification commands
```

---

## Deliverables

**research.md** - Technical decisions with full rationale
**data-model.md** - Entity specifications (implementation-agnostic)
**contracts/** - API endpoint specifications
**quickstart.md** - Manual test scenarios for validation

All deliverables use CoD^Σ evidence chains linking to intelligence queries or MCP sources.

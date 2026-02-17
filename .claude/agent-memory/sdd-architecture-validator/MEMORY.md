# SDD Architecture Validator - Persistent Memory

**Last Updated**: 2026-02-08

## Key Learnings

### 1. Nikita Codebase Architecture Patterns ✅

**Repository Pattern**:
- All repos inherit from `BaseRepository[T]` (e.g., ConversationRepository, UserRepository)
- Location: `nikita/db/repositories/`
- Pattern: `class XRepository(BaseRepository[Model]): async def method()`
- Always async, uses SQLAlchemy async sessions

**Model Pattern**:
- Models in `nikita/db/models/` inherit from `Base, UUIDMixin, TimestampMixin`
- Foreign keys use `ForeignKey(table, ondelete="CASCADE")`
- Relationships use `relationship(back_populates=...)`
- Type hints: `Mapped[Type] = mapped_column(...)`

**Pipeline Stage Pattern** (Spec 037):
- Base class: `PipelineStage[InputType, OutputType]` at `nikita/context/stages/base.py`
- Provides: timeout_seconds, max_retries, tenacity retry logic, OpenTelemetry tracing
- All stages implement: `async def _run(self, context: PipelineContext, input: InputType) -> OutputType`
- Used by: context/post_processor.py (11 stages)

**Settings Pattern**:
- Pydantic `BaseSettings` with `SettingsConfigDict(env_file=".env")`
- All defaults specified with `Field(default=..., description=...)`
- Case insensitive, extra="ignore"
- Access via: `from nikita.config.settings import get_settings; settings = get_settings()`

**Feature Flags** (Current practice):
- No explicit feature flag infrastructure yet
- Spec 042 will introduce `UNIFIED_PIPELINE_ENABLED: bool` pattern
- Use conditional imports: `if settings.unified_pipeline_enabled: from new_module else: from old_module`

### 2. Spec 042 Validation Findings ✅

**Architecture Quality**: PASS (0 CRITICAL, 0 HIGH)

**Key Strengths**:
- Correct use of BaseRepository for new MemoryFact + ReadyPrompt repos
- Proper thin wrapper pattern (stages 80-300 lines, not re-implementing)
- Clean dependency chain (no cycles): pipeline → db → models → PostgreSQL
- Backward compatible (feature flag allows parallel execution of old + new)

**Minor Items to Address**:
1. Add RLS policies to memory_facts + ready_prompts in migration 0009
2. Confirm inheritance: `class MemoryFactRepository(BaseRepository[MemoryFact])`
3. Clarify: Does feature flag control ONLY agent loading, or pipeline trigger too?

**Naming Concern** (Resolvable):
- Two stage hierarchies: `context/stages/` (Spec 037, deprecated) and `pipeline/stages/` (Spec 042, new)
- Mitigation: Phase 5 deletes entire `context/stages/` directory
- Verdict: Acceptable

### 3. Spec 044 Validation Findings ✅

**Architecture Quality**: PASS (0 CRITICAL, 0 HIGH, 3 MEDIUM)

**Key Strengths**:
- Clean Next.js 15 App Router structure (app/ directory)
- Proper separation: Frontend (portal/) vs Backend (nikita/api/)
- TypeScript strict + Zod validation enforced
- Component hierarchy: Page → Section → Card → Widget
- Supabase SSR auth + RBAC properly specified
- 13 portal + 25+ admin endpoints already exist (no backend rework)

**Medium Findings**:
1. **Import Alias Configuration Missing** (tsconfig.json paths not shown)
2. **Error Handling Strategy Incomplete** (no global error handler, retry strategy unclear)
3. **Security Sanitization Not Explicit** (DOMPurify for user content needs documentation)

**Low Findings**:
1. Recharts lazy loading (next/dynamic) not shown
2. Glassmorphism perf (already in risk assessment)

**Backend Integration**:
- Portal consumes existing API endpoints (nikita/api/routes/portal.py, admin.py)
- Backend uses BaseRepository pattern (no changes needed)
- Type safety: Backend Pydantic schemas → Frontend TypeScript types

### 4. Next.js Architecture Validation Checklist

When validating Next.js specs, check:

**1. Directory Structure** (5 min)
- [ ] App Router structure documented (app/, not pages/)
- [ ] Import aliases configured (tsconfig.json paths: `@/*`)
- [ ] Component organization (ui/, dashboard/, admin/, shared/)
- [ ] File naming conventions (kebab-case for files, PascalCase for components)

**2. Type Safety** (5 min)
- [ ] TypeScript strict mode enforced
- [ ] Backend schema → Frontend type mapping documented
- [ ] Zod validation for API responses
- [ ] No `any` types policy

**3. Auth Architecture** (10 min)
- [ ] Auth provider specified (Supabase, NextAuth, Clerk, etc.)
- [ ] Server-side session validation (middleware.ts)
- [ ] Client-side auth state management
- [ ] Protected routes strategy (redirect vs 403)
- [ ] Role-based access control (if applicable)

**4. Data Fetching** (10 min)
- [ ] Data fetching library (TanStack Query, SWR, etc.)
- [ ] Cache strategy (staleTime, cacheTime)
- [ ] Server Components vs Client Components distinction
- [ ] API client abstraction (fetch wrapper with auth headers)

**5. Error Handling** (10 min)
- [ ] Error boundaries placement
- [ ] Global error handler (API errors)
- [ ] Retry strategy (exponential backoff?)
- [ ] Toast/notification system
- [ ] Empty states for no data

**6. Security** (10 min)
- [ ] Input sanitization (DOMPurify for user content)
- [ ] XSS prevention strategy
- [ ] CSRF protection (session cookies)
- [ ] Secrets management (env vars, server-only)
- [ ] Rate limiting (backend enforced)

**7. Performance** (5 min)
- [ ] Code-splitting strategy (route-level + component-level)
- [ ] Lazy loading heavy libraries (charts, editors)
- [ ] Image optimization (next/image)
- [ ] Font optimization (next/font)

**8. Component Patterns** (5 min)
- [ ] UI library specified (shadcn/ui, MUI, etc.)
- [ ] Component hierarchy clear (atomic design?)
- [ ] Shared component location (components/shared/)
- [ ] Loading states (skeletons, spinners)

**9. Module Organization** (5 min)
- [ ] lib/ for utilities and business logic
- [ ] hooks/ for custom React hooks
- [ ] components/ for UI components
- [ ] app/ for pages and layouts
- [ ] No circular dependencies strategy

**10. Deployment** (5 min)
- [ ] Deployment target (Vercel, AWS, etc.)
- [ ] Environment variables documented
- [ ] Build configuration (next.config.ts)
- [ ] API rewrites/redirects (if applicable)

### 5. Common Next.js Architecture Anti-Patterns

**Anti-Pattern 1: Missing tsconfig.json paths**
- Symptom: No `@/` import alias configuration shown
- Impact: Developer experience suffers, relative imports become messy
- Fix: Add `"paths": { "@/*": ["./src/*"] }` to tsconfig.json

**Anti-Pattern 2: No error handling strategy**
- Symptom: Only component-level error boundaries, no global API error handler
- Impact: Unhandled API errors crash app or show generic messages
- Fix: TanStack Query retry config + global error types + toast system

**Anti-Pattern 3: Security sanitization implicit**
- Symptom: "React escapes by default" without explicit sanitization for user content
- Impact: XSS vulnerabilities if using dangerouslySetInnerHTML or rendering user HTML
- Fix: Document DOMPurify usage for conversation messages, admin user input

**Anti-Pattern 4: No code-splitting for heavy libraries**
- Symptom: Recharts, chart libraries imported directly in components
- Impact: Large initial bundle, slow page loads
- Fix: next/dynamic with loading skeleton for chart components

**Anti-Pattern 5: Unclear Server vs Client Component boundaries**
- Symptom: No specification of which components are RSC vs client
- Impact: Over-hydration, unnecessary client-side JavaScript
- Fix: Document `"use client"` directives for interactive components

### 6. Architecture Validation Report Structure (Template)

```markdown
# Architecture Validation: Spec NNN

**Date**: YYYY-MM-DD
**Spec**: /path/to/spec.md
**Status**: PASS | FAIL
**Validator**: SDD Architecture Validator

## Executive Summary
[Verdict, key strengths, findings summary]

## Validation Results
### 1. Project Structure
### 2. Module Organization
### 3. Import Patterns
### 4. Separation of Concerns
### 5. Type Safety
### 6. Error Handling Architecture
### 7. Security Architecture
### 8. Scalability Considerations

## Alignment with Existing Architecture
[Backend integration, type safety, patterns]

## Findings Summary Table
| Severity | Category | Issue | Location | Recommendation |

## Proposed Additions to plan.md
[Code snippets for missing sections]

## Module Dependency Graph (ASCII)

## Separation of Concerns Analysis Table

## Import Pattern Checklist

## Security Architecture Checklist

## Recommendations (Priority Order)

## Final Verdict

## Validation Metadata
```

---

## Spec 044 Reference Notes

**Project Type**: Next.js 15 Portal (new build from scratch)
**Old Portal**: Deleted during cleanup (spec.md:6)
**Backend**: nikita/api/ (13 portal + 25+ admin endpoints exist)

**Key Files**:
- spec.md: 25 FRs (FR-001 to FR-030), 15 user stories
- plan.md: 7 phases, component hierarchy, file structure
- tasks.md: 55 tasks, ~300 tests estimated
- audit-report.md: 6 validators PASS, 3 minor advisories

**Tech Stack**:
- Next.js 15 (App Router, TypeScript strict)
- Tailwind CSS 4 + shadcn/ui + Radix UI
- Recharts (charts) + Framer Motion (animations)
- Supabase SSR (@supabase/ssr) for auth
- TanStack Query (React Query) for data fetching
- React Hook Form + Zod for forms

**Architecture Patterns**:
- Component hierarchy: Page → Section → Card → Widget
- Data fetching: TanStack Query hooks → API client → Backend
- Auth: Supabase middleware → Protected routes
- Styling: Design tokens in globals.css + tailwind.config.ts

**Validation Results**:
- 0 CRITICAL, 0 HIGH
- 3 MEDIUM: Import alias config, error handling, security sanitization
- 2 LOW: Code-splitting, glassmorphism perf

**Recommendations**:
1. Add tsconfig.json paths to plan.md
2. Add error handling strategy (retry, global handler)
3. Add security sanitization examples (DOMPurify)
4. Add next/dynamic for Recharts lazy loading

---

## Patterns for Future Validations

### Next.js Specs
1. Check tsconfig.json paths in plan.md (common gap)
2. Verify error handling strategy (TanStack Query retry config)
3. Check security sanitization for user content
4. Verify code-splitting for heavy libraries
5. Check Server Component vs Client Component strategy

### Python Backend Specs
1. Check BaseRepository inheritance
2. Verify async/await patterns
3. Check RLS policies in migrations
4. Verify Pydantic schema field constraints
5. Check circular dependency prevention

### Full-Stack Specs
1. Verify frontend types mirror backend schemas
2. Check API version prefix (/api/v1/*)
3. Verify environment variable separation (public vs server-only)
4. Check auth flow (backend session + frontend middleware)

---

## Quick Reference: Severity Classification

| Severity | Criteria |
|----------|----------|
| **CRITICAL** | No directory structure, undefined module boundaries, missing security considerations, circular dependencies |
| **HIGH** | Unclear separation of concerns, no error handling architecture, missing type strategy, broken auth flow |
| **MEDIUM** | Unspecified import patterns, vague naming conventions, no scalability considerations, incomplete security docs |
| **LOW** | Style preferences, optimization suggestions, nice-to-have patterns |

**Pass Criteria**: 0 CRITICAL + 0 HIGH findings

---

## Tools Usage Notes

- Use **Read** to examine spec.md, plan.md, tasks.md, audit-report.md
- Use **Glob** to find existing tsconfig.json, package.json, Next.js configs
- Use **Grep** to search for patterns (env vars, import aliases, backend endpoints)
- Use **Bash** to check directory structure, file counts

**Performance**: Limit rg/fd output to prevent context overflow (use `| head -N`)

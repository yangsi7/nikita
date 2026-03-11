## API Validation Report

**Spec:** `/Users/yangsim/Nanoleq/sideProjects/nikita/specs/112-portal-e2e-hardening/spec.md`
**Status:** FAIL
**Timestamp:** 2026-03-11T12:00:00Z

### Summary
- CRITICAL: 0
- HIGH: 3
- MEDIUM: 5
- LOW: 4

### Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| HIGH | Mock Fidelity | Spec lists 12 factory functions but does not define their response shapes. `mockConversations()` must match `ConversationsResponse` (paginated with `conversations`, `total_count`, `page`, `page_size`) not a bare array. The portal `portalApi.getConversations()` types the response as `{ conversations: Conversation[]; total: number }` (note: `total` not `total_count`) -- this is ALREADY a TS/backend drift. Factory must match real backend schema (`total_count`), not the TS type. | spec.md:98-101 | Add a "Mock Schema Reference" section mapping each factory function to its exact Pydantic response model. Document the `total` vs `total_count` TS drift (portal types.ts:80 vs portal schema ConversationsResponse) as a known issue to fix alongside. |
| HIGH | Mock Fidelity | `ConversationMessage` TS interface has `id: string` and `created_at: string` fields (types.ts:83-87) but backend `ConversationMessage` Pydantic schema has `role`, `content`, `timestamp` -- no `id` field, `timestamp` not `created_at`. Mock factories must match the BACKEND shape, but tests will render via frontend components that expect the TS shape. This mismatch means mock data shaped to backend schema will cause frontend rendering bugs in tests. | types.ts:82-87 vs portal.py schema line 113-118 | Spec should document this interface drift as a prerequisite fix or explicitly state factories match the TS interface (browser-side mocking intercepts before JSON reaches the component). Since `page.route()` returns data consumed by browser JS, factories should match what the TS types expect, but document the backend divergence. |
| HIGH | Mock Fidelity | `PipelineRun` TS interface (types.ts:228-238) has `success: boolean` and `stages: Array<{name, duration_ms, status}>` but backend `PipelineHistoryItem` schema (admin.py:408-417) has `status: str` (not boolean `success`), `duration_ms`, `started_at`, `completed_at`, `error_message` -- no `stages` array. The `mockPipelineEvents()` factory (spec FR-001 AC-1.1) is listed but mock shape is undefined. Admin pipeline page tests will fail if factories don't match what the frontend components actually render. | spec.md:98, types.ts:228-238 vs admin.py:408-417 | Define exact mock shapes for `mockPipelineEvents()` and add `mockPipelineHistory()` if admin-user-detail tests need pipeline history. Cross-reference the TS `PipelineRun` interface with the backend `PipelineHistoryItem` schema and resolve the drift. |
| MEDIUM | Factory Coverage | `mockApiRoutes(page)` (AC-1.4) needs to intercept both `/api/v1/portal/*` AND `/api/v1/admin/*` endpoints, but spec doesn't list the full set of URL patterns to intercept. Portal uses 20+ distinct endpoints across `portalApi` (17 functions) and `adminApi` (18 functions). Missing intercepts will cause tests to hit the real (unavailable) backend and hang/fail. | spec.md:101 | Document the complete list of URL patterns `mockApiRoutes` must intercept. At minimum for player project: `/portal/stats`, `/portal/score-history*`, `/portal/engagement`, `/portal/decay`, `/portal/vices`, `/portal/conversations*`, `/portal/daily-summaries*`, `/portal/settings`, `/portal/emotional-state*`, `/portal/life-events*`, `/portal/thoughts*`, `/portal/narrative-arcs*`, `/portal/social-circle`, `/portal/psyche-tips`, `/portal/score-history/detailed*`, `/portal/threads*`. For admin: `/admin/stats`, `/admin/users*`, `/admin/conversations*`, `/admin/prompts*`, `/admin/processing-stats`, `/admin/unified-pipeline/health`, `/admin/events*`, `/admin/pipeline/timings*`. |
| MEDIUM | Auth Bypass | Spec says mock player user has `user_metadata: {}` (AC-2.2) but middleware `isAdmin()` check at middleware.ts:33-37 checks `user_metadata?.role === "admin"` OR `email?.endsWith("@nanoleq.com")`. The bypass needs to return a full Supabase `User` object shape (not just `{id, email, user_metadata}`) since `createServerClient().auth.getUser()` returns `{ data: { user: User }, error: null }`. The mock must match this exact shape including the wrapping `data` object. | spec.md:109-110 vs middleware.ts:29 | Specify the complete mock return shape: `{ data: { user: { id, email, user_metadata, ... } }, error: null }`. The bypass code in middleware.ts must short-circuit before `supabase.auth.getUser()` and return a synthetic response that the rest of `updateSession()` can consume. |
| MEDIUM | Supabase Browser Calls | `page.route()` intercepts browser HTTP requests. The portal's `apiClient` (client.ts:4-11) calls `supabase.auth.getSession()` to get the auth token BEFORE making API calls. In E2E with auth bypass, Supabase browser client will fail to get a session (no real auth), causing `getAuthToken()` to return `null`, which means API mock intercepts will receive requests WITHOUT `Authorization` headers. This is fine since mocks don't validate auth, but not documented. | client.ts:4-11 | Document in spec that browser-side Supabase auth calls (`getSession()`) will return null session in E2E mode, and that `page.route()` intercepts do not validate the Authorization header. Alternatively, also mock the Supabase auth REST endpoints to return a fake session so the `Authorization: Bearer <token>` header is populated (matching production behavior more closely). |
| MEDIUM | Route Coverage | Route 3 (`/auth/callback`) is listed as covered by `auth-flow` spec but `/auth/callback` is a Next.js route handler (server-side), not testable via `page.route()` mocking. The existing `auth-flow.spec.ts` presumably tests the redirect flow. Spec should clarify this is out of scope for content validation (redirect-only). | spec.md:200-201 | Explicitly note that `/auth/callback` is redirect-only and excluded from content validation assertions. Already noted as "Redirect only" but should confirm no new test changes needed. |
| MEDIUM | Two WebServers | Playwright config with two `webServer` entries (player on 3003, admin on 3004) is not directly supported by Playwright's single `webServer` config. Playwright supports `webServer` as an array, but each project must reference the correct base URL. The spec says "each with their own webServer" but Playwright projects share the top-level webServer(s). | spec.md:111, plan.md:11-12 | Use Playwright's `webServer` array syntax (supported since Playwright 1.35) with both servers, and set `use: { baseURL }` per project. Example: `webServer: [{ command: "E2E_AUTH_ROLE=player npm run dev -- --port 3003", url: "http://localhost:3003" }, { command: "E2E_AUTH_ROLE=admin npm run dev -- --port 3004", url: "http://localhost:3004" }]` with `projects: [{ name: "player", use: { baseURL: "http://localhost:3003" } }, ...]`. |
| LOW | Factory Naming | `mockNikitaMind()`, `mockNikitaCircle()`, `mockNikitaDay()`, `mockNikitaStories()` map to portal API endpoints `/portal/thoughts`, `/portal/social-circle`, `/portal/life-events` + `/portal/psyche-tips`, and `/portal/narrative-arcs` respectively. The naming convention (Mind/Circle/Day/Stories) follows the portal page names, not the API endpoint names. This is a readability concern -- developers must know that `mockNikitaMind()` returns `ThoughtsResponse` + `EmotionalStateResponse` shape. | spec.md:98 | Add a comment block or table in `factories.ts` mapping factory names to their corresponding API endpoints and response types. Consider using API-aligned names (`mockThoughts()`, `mockSocialCircle()`, etc.) with aliases for the page-centric names. |
| LOW | Existing Fixtures | `hasSidebarNav()` in current `fixtures.ts:88-94` already uses `.catch(() => false)` anti-pattern. Spec mentions refactoring `fixtures.ts` (T2.5) but doesn't explicitly call out this function for rewrite. | fixtures.ts:90 | Ensure T2.5 refactor removes the `.catch(() => false)` from `hasSidebarNav()` or replaces it entirely with `data-testid` based navigation assertions. |
| LOW | Error State Testing | Spec mentions testing invalid IDs for dynamic routes (AC-7.4 conversation-detail, AC-8.3/8.4 admin routes) but doesn't specify the error mock response shape. Backend returns `{ detail: "Conversation not found" }` with 404 status -- mock should match this. | spec.md:283 | Define error mock shape: `page.route('**/conversations/invalid-id', route => route.fulfill({ status: 404, body: JSON.stringify({ detail: "Not found" }) }))`. |
| LOW | CI Timeout | AC-8.7 says "Total CI time increase < 5 minutes" but doesn't account for two dev servers starting (player + admin). Each Next.js dev server cold start takes 15-30s. With two servers, startup is 30-60s, not 20s as estimated. | spec.md:186 | Update estimate: dev server startup ~40s (two instances), Playwright install ~60s, tests ~120s, overhead ~20s = ~4 min. Still under 5 min but estimate should be corrected. |

### API Inventory

This spec does NOT modify backend APIs. All API interaction is via `page.route()` mocking in Playwright. The following endpoints need mock interceptors:

**Portal Endpoints (player project):**

| Method | Endpoint | Purpose | Mock Factory |
|--------|----------|---------|-------------|
| GET | /api/v1/portal/stats | Dashboard stats | mockUser() |
| GET | /api/v1/portal/score-history | Score chart data | (part of mockUser or separate) |
| GET | /api/v1/portal/engagement | Engagement state | (part of mockMetrics or separate) |
| GET | /api/v1/portal/decay | Decay status | (need factory) |
| GET | /api/v1/portal/vices | Vice preferences | mockVices() |
| GET | /api/v1/portal/conversations | Conversation list | mockConversations() |
| GET | /api/v1/portal/conversations/:id | Conversation detail | mockConversations() |
| GET | /api/v1/portal/daily-summaries | Daily summaries | mockDiary() |
| GET | /api/v1/portal/settings | User settings | (need factory) |
| GET | /api/v1/portal/emotional-state | Emotional state | (need factory) |
| GET | /api/v1/portal/emotional-state/history | Emotion history | (need factory) |
| GET | /api/v1/portal/life-events | Life events | mockNikitaDay() |
| GET | /api/v1/portal/thoughts | Nikita's thoughts | mockNikitaMind() |
| GET | /api/v1/portal/narrative-arcs | Story arcs | mockNikitaStories() |
| GET | /api/v1/portal/social-circle | Social circle | mockNikitaCircle() |
| GET | /api/v1/portal/psyche-tips | Psyche tips | mockNikitaDay() |
| GET | /api/v1/portal/score-history/detailed | Detailed scores | mockInsights() |
| GET | /api/v1/portal/threads | Threads | (need factory) |

**Admin Endpoints (admin project):**

| Method | Endpoint | Purpose | Mock Factory |
|--------|----------|---------|-------------|
| GET | /api/v1/admin/stats | Admin stats | (need factory) |
| GET | /api/v1/admin/users | User list | (need factory) |
| GET | /api/v1/admin/users/:id | User detail | (need factory) |
| GET | /api/v1/admin/users/:id/metrics | User metrics | mockMetrics() |
| GET | /api/v1/admin/users/:id/engagement | User engagement | (need factory) |
| GET | /api/v1/admin/users/:id/vices | User vices | mockVices() |
| GET | /api/v1/admin/users/:id/conversations | User convos | mockConversations() |
| GET | /api/v1/admin/users/:id/scores | User scores | (need factory) |
| GET | /api/v1/admin/users/:id/pipeline-history | Pipeline history | mockPipelineEvents() |
| GET | /api/v1/admin/conversations | Conversation list | (need factory) |
| GET | /api/v1/admin/conversations/:id/events | Pipeline events | mockPipelineEvents() |
| GET | /api/v1/admin/conversations/:id/pipeline | Pipeline status | (need factory) |
| GET | /api/v1/admin/prompts | Prompt list | (need factory) |
| GET | /api/v1/admin/processing-stats | Job stats | mockJobs() |
| GET | /api/v1/admin/unified-pipeline/health | Pipeline health | (need factory) |
| GET | /api/v1/admin/events | Pipeline events list | mockPipelineEvents() |
| GET | /api/v1/admin/pipeline/timings | Pipeline timings | (need factory) |

### Schema Drift Inventory (Backend Pydantic vs Frontend TS)

These pre-existing drifts affect mock factory accuracy:

| Field | Backend (Pydantic) | Frontend (TS) | Impact |
|-------|-------------------|---------------|--------|
| ConversationsResponse.total_count | `total_count: int` | `total: number` (portalApi types it as `{ total: number }`) | Factory must use `total_count` (backend truth); TS type is wrong |
| ConversationMessage.timestamp | `timestamp: datetime \| None` | `created_at: string` | Factory must use `timestamp`; TS `created_at` is wrong |
| ConversationMessage.id | Not present | `id: string` | TS type has extra field not in backend |
| PipelineRun.success | Not present (backend has `status: str`) | `success: boolean` | Complete shape mismatch |
| PipelineRun.stages | Not present | `stages: Array<{name, duration_ms, status}>` | Backend PipelineHistoryItem has no stages array |
| PromptRecord.platform | Not present in GeneratedPromptResponse | `platform: string` | TS type has extra field |
| AdminUser.telegram_id | `int \| None` | `string \| None` | Type mismatch (number vs string) |
| Conversation.user_id | Not present in portal ConversationListItem | `user_id: string` | TS type has extra field (only admin schema has user_id) |

### Recommendations

1. **HIGH -- Mock Schema Reference Table**: Add a section to the spec mapping each of the 12 factory functions to their exact Pydantic response model class names and key fields. Without this, implementers will guess at shapes and create mocks that don't match the real API, defeating the purpose of mock-based E2E testing. The 8 schema drifts documented above MUST be resolved (either fix TS types or document as known gaps).

2. **HIGH -- ConversationMessage Drift**: The `ConversationMessage` TS interface diverges from the backend schema. Since `page.route()` mocks are consumed by browser JavaScript that uses the TS types, decide whether factories match TS types (pragmatic) or backend schemas (correct). Document the decision explicitly. Recommend fixing the TS types to match backend, then building factories from fixed types.

3. **HIGH -- PipelineRun/PipelineHistoryItem Drift**: The `PipelineRun` TS interface is completely different from the backend `PipelineHistoryItem`. The admin-user-detail test (T8.4) will need `mockPipelineHistory()` data. Either fix the TS type or build the factory to match what the frontend component actually renders (which may have its own transformation layer).

4. **MEDIUM -- Complete Intercept URL List**: The `mockApiRoutes(page)` function must intercept ~35 distinct URL patterns. List them in the spec or a companion document to prevent missing-intercept bugs where tests hang waiting for unreachable backends.

5. **MEDIUM -- Browser-side Supabase Auth**: Document that `supabase.auth.getSession()` returns null in E2E mode. Consider intercepting Supabase REST auth endpoints (`**/auth/v1/token*`) to return a mock session, ensuring the `Authorization` header is populated in API requests (closer to production behavior, and prevents future tests from accidentally depending on the header).

### Positive Patterns

- Env-gated auth bypass with production guard (`NODE_ENV !== "production"`) is well-designed and safe
- Two Playwright projects (player/admin) cleanly separate role-based test isolation
- `data-testid` strategy follows Playwright best practices and avoids CSS selector fragility
- Factory functions with partial overrides (`mockUser({ chapter: 3 })`) enable composable test scenarios
- TDD approach for meta-tests (US-6 before US-2) follows project conventions
- Phase A/B split keeps PRs under 400-line limit per project conventions

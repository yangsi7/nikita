## Data Layer Validation Report

**Spec:** `/Users/yangsim/Nanoleq/sideProjects/nikita/specs/112-portal-e2e-hardening/spec.md`
**Status:** PASS
**Timestamp:** 2026-03-11T12:00:00Z

### Summary
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 3
- LOW: 2

### Context

This spec does NOT modify database schema, tables, RLS policies, indexes, storage, or migrations. It adds Playwright E2E tests with mock data factories that intercept API responses via `page.route()`. The data layer concern is **mock data fidelity**: factory functions must return objects matching the TypeScript interfaces in `portal/src/lib/api/types.ts`.

### Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| MEDIUM | Mock Fidelity | `mockInsights()` factory listed but no corresponding `Insights` type exists in `types.ts`. The `/dashboard/insights` page uses `DetailedScoreHistory`, `EmotionalStateHistory`, and `ThreadList` — there is no single "insights" API response shape. | spec.md AC-1.1 (line 98) | Clarify what `mockInsights()` returns. It likely needs to mock multiple API calls (`getDetailedScoreHistory`, `getEmotionalStateHistory`, `getThreads`). Consider renaming to `mockInsightsPage()` and having it return a bundle of responses, or splitting into the individual factories. |
| MEDIUM | Mock Fidelity | `mockNikitaMind()`, `mockNikitaCircle()`, `mockNikitaDay()`, `mockNikitaStories()` — these factory names do not directly map to single TypeScript types. The actual types are: Mind = `EmotionalStateResponse` + `ThoughtsResponse`, Circle = `SocialCircleResponse`, Day = `LifeEventsResponse` + `PsycheTipsData`, Stories = `NarrativeArcsResponse`. | spec.md AC-1.1 (line 98) | Document the mapping from factory names to TypeScript types. `mockNikitaCircle()` maps cleanly to `SocialCircleResponse`, `mockNikitaStories()` to `NarrativeArcsResponse`. But `mockNikitaMind()` and `mockNikitaDay()` each serve multiple API endpoints. The implementer needs to know which types to compose. |
| MEDIUM | Mock Fidelity | `mockJobs()` factory — the `/admin/jobs` page uses two different types: `JobStatus[]` (from a jobs endpoint) and `ProcessingStats` (from `getProcessingStats`). The spec does not clarify which shape `mockJobs()` returns. | spec.md AC-1.1 (line 98) | Specify whether `mockJobs()` returns `JobStatus[]`, `ProcessingStats`, or a composite. The admin jobs page likely needs both. |
| LOW | Type Completeness | `mockPipelineEvents()` is listed but the spec does not specify whether it returns `PipelineEvent[]` or the wrapper `{ conversation_id, events, count }`. The admin API returns the wrapper. | spec.md AC-1.1 (line 98) | Specify that `mockPipelineEvents()` should return `{ conversation_id: string, events: PipelineEvent[], count: number }` to match `adminApi.getConversationEvents()` return type. |
| LOW | Documentation | The spec lists 12 factory functions but does not include a type mapping table showing which TypeScript interface each factory produces. This could lead to implementation drift. | spec.md FR-001 (lines 93-101) | Add a factory-to-type mapping table to the spec, e.g.: `mockUser() -> UserStats`, `mockMetrics() -> UserMetrics`, `mockConversations() -> { conversations: Conversation[], total: number }`, etc. |

### Entity Inventory

Not applicable — this spec does not define or modify database entities. The relevant data layer is the TypeScript type system in `portal/src/lib/api/types.ts` (466 lines, 40+ interfaces).

### Factory-to-Type Mapping (Inferred)

| Factory Function | Inferred TypeScript Type(s) | Source API Call |
|------------------|-----------------------------|----------------|
| `mockUser()` | `UserStats` | `portalApi.getStats()` |
| `mockMetrics()` | `UserMetrics` | embedded in `UserStats.metrics` |
| `mockConversations()` | `{ conversations: Conversation[], total: number }` | `portalApi.getConversations()` |
| `mockPipelineEvents()` | `{ conversation_id: string, events: PipelineEvent[], count: number }` | `adminApi.getConversationEvents()` |
| `mockJobs()` | `JobStatus[]` and/or `ProcessingStats` | multiple admin endpoints |
| `mockVices()` | `VicePreference[]` | `portalApi.getVices()` |
| `mockInsights()` | `DetailedScoreHistory` + `EmotionalStateHistory` + `ThreadList` (composite) | multiple portal endpoints |
| `mockDiary()` | `DailySummary[]` | `portalApi.getDailySummaries()` |
| `mockNikitaMind()` | `EmotionalStateResponse` + `ThoughtsResponse` (composite) | `portalApi.getEmotionalState()` + `portalApi.getThoughts()` |
| `mockNikitaCircle()` | `SocialCircleResponse` | `portalApi.getSocialCircle()` |
| `mockNikitaDay()` | `LifeEventsResponse` + `PsycheTipsData` (composite) | `portalApi.getLifeEvents()` + `portalApi.getPsycheTips()` |
| `mockNikitaStories()` | `NarrativeArcsResponse` | `portalApi.getNarrativeArcs()` |

### Additional Types Needed by mockApiRoutes() (Not Listed as Factories)

These API responses are used by pages covered in the spec but have no factory listed in AC-1.1:

| Missing Factory | Type | Used By Route |
|----------------|------|---------------|
| `mockScoreHistory()` | `ScoreHistory` | `/dashboard` (score chart) |
| `mockEngagement()` | `EngagementData` | `/dashboard/engagement` |
| `mockDecayStatus()` | `DecayStatus` | `/dashboard` |
| `mockSettings()` | `UserSettings` | `/dashboard/settings` |
| `mockAdminUsers()` | `AdminUser[]` | `/admin` |
| `mockAdminStats()` | `AdminStats` | `/admin` |
| `mockAdminUserDetail()` | `AdminUserDetail` | `/admin/users/[id]` |
| `mockPipelineHealth()` | `PipelineHealth` | `/admin/pipeline` |
| `mockPrompts()` | `GeneratedPromptsResponse` | `/admin/prompts` |
| `mockTextConversations()` | `AdminConversationsResponse` | `/admin/text` |
| `mockVoiceConversations()` | `AdminConversationsResponse` | `/admin/voice` |

Note: These may be handled internally by `mockApiRoutes()` without being exported as named factories. The spec says `mockApiRoutes(page)` registers "all page.route() interceptors with factory defaults" (AC-1.4), so these types will need mock data regardless. This is not a blocking issue — the implementer will discover these during TDD (US-6 meta-tests written first). Flagged as informational.

### Relationship Map

```
No database relationships modified by this spec.
Types.ts interfaces mirror backend Pydantic models:
  UserStats -contains-> UserMetrics
  ConversationDetail -contains-> ConversationMessage[]
  PipelineHealth -contains-> PipelineStageHealth[]
  AdminConversationsResponse -contains-> AdminConversationItem[]
```

### RLS Policy Checklist

- [x] N/A — No database changes. All data is mocked at the network layer via `page.route()`.

### Index Requirements

N/A — No database changes.

### Storage / Realtime / Migration

N/A — No database changes.

### Recommendations

1. **MEDIUM:** Add a factory-to-type mapping table to the spec (FR-001 section) so implementers know exactly which TypeScript interfaces each factory must produce. The inferred mapping table above can be used as-is.

2. **MEDIUM:** Clarify composite factories (`mockInsights`, `mockNikitaMind`, `mockNikitaDay`, `mockJobs`). These page-level factories need to return bundles for multiple API endpoints. Document whether they return a composite object or whether `mockApiRoutes()` handles the decomposition internally.

3. **MEDIUM:** Consider listing the additional ~11 types needed by `mockApiRoutes()` that are not currently named as factory functions (see "Additional Types Needed" table). These will be discovered during implementation but documenting them prevents surprises.

4. **LOW:** Specify wrapper vs. raw array for `mockPipelineEvents()` and `mockConversations()` — the API returns envelope objects (`{ events: [], count }`, `{ conversations: [], total }`), not raw arrays.

5. **LOW:** The `AdminUser.telegram_id` is typed as `string | null` while `AdminUserDetail.telegram_id` is `number | null` in `types.ts`. This is an existing type inconsistency (not introduced by this spec) but factory authors should be aware to avoid type errors. Consider filing a separate issue to align these types.

### Verdict

**PASS** — No CRITICAL or HIGH findings. This spec correctly identifies that no database schema changes are needed. The 3 MEDIUM findings are documentation gaps in the factory-to-type mapping that will not block implementation (TDD approach in US-6 will catch mismatches). The existing TypeScript types in `portal/src/lib/api/types.ts` are comprehensive and well-structured, providing a solid foundation for type-safe factory functions.

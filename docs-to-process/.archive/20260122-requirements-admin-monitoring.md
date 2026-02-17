# Admin User Monitoring Dashboard - Requirements

**Created**: 2026-01-22
**Status**: Approved by User

---

## 1. Scope & Users

| Requirement | Decision |
|-------------|----------|
| Primary User | simon.yang.ch@gmail.com (project owner) |
| Approach | Extend and significantly overhaul specs 016-020 |
| Auth | Existing @silent-agents.com domain check |
| Expansion | Single user focus initially, generalize later |

**Rationale**: Specs 016-020 provide foundation but need major updates for current feature-rich Nikita (33 specs complete, voice + text agents, 3 memory graphs, humanization pipeline).

---

## 2. Data Coverage (ALL Entities)

### 2.1 Conversations + Generated Prompts
- Full message threads (user + assistant)
- 9-stage post-processing pipeline visibility (from Spec 031)
- Generated prompt layers (system, humanization, context tiers)
- Source: `conversations`, `conversation_messages`, `generated_prompts` tables

### 2.2 Scoring + Voice Sessions
- Metric deltas (trust, intimacy, attraction, commitment)
- Boss encounter outcomes (pass/fail, judgment reasoning)
- ElevenLabs voice session transcripts
- Scoring history timeline
- Source: `scoring_history`, `conversations` (voice), ElevenLabs webhooks

### 2.3 Job Executions + Errors
- Pipeline stage success/failure rates
- Stuck conversation detection (from Spec 031 T4.1-T4.3)
- Job execution logs with timing
- Error categorization and search
- Source: `job_executions` table

### 2.4 Memory Graphs
- user_facts from user_graph
- relationship_episodes from relationship_graph
- nikita_events from nikita_graph
- Thread status (open/resolved)
- Source: Neo4j Aura via Graphiti client

---

## 3. UI/UX Requirements

### 3.1 Layout
- **Structure**: Tabbed sections per entity type
- **Tabs**: Conversations | Prompts | Scoring | Voice | Jobs | Memory | Errors

### 3.2 Time Range
- **Default**: Last 7 days
- **Feature**: Custom date range picker
- **Performance**: Paginated queries for large datasets

### 3.3 Drill-Down Capability
- Click conversation → full thread + prompts + scoring in context
- Click prompt → see all layers (system, humanization, vice injection)
- Click job → see full execution trace
- Click error → see stack trace + context

### 3.4 Visualization
- **Charts**: Score trends, error rates, engagement over time
- **Tables**: Searchable, sortable, filterable data tables
- **Combined**: Charts for overview, tables for detail

### 3.5 Refresh Strategy
- Manual refresh button
- Auto-refresh after user actions (drill-down, filter change)
- No WebSocket (simplest implementation)

---

## 4. Performance & Security

### 4.1 Performance
- Dashboard overview: <2s load time
- Detail views: <500ms response
- Pagination: 50 items per page default
- Date range queries: Indexed for speed

### 4.2 Security
- Admin auth: @silent-agents.com email domain check (existing)
- Data visibility: Full data (no redaction for admin)
- Audit: Log admin access to sensitive data

---

## 5. Technical Constraints

### 5.1 Backend
- Extend `nikita/api/routes/admin.py`
- Reuse existing repositories
- FastAPI + SQLAlchemy + Supabase
- New schemas in `nikita/api/schemas/admin.py`

### 5.2 Frontend
- Next.js + shadcn/ui + Tailwind (portal patterns)
- Location: `portal/src/app/admin/monitoring/`
- Reuse existing components where possible

### 5.3 Integration Points
- Specs 016-020: Existing admin routes and UI
- Spec 031: Job execution logging, stuck detection
- Spec 029: 3-graph memory retrieval
- Spec 030: Context continuity, token budget

---

## 6. Success Criteria

- [ ] All 7 tabs functional with real data
- [ ] Full drill-down from summary to detail
- [ ] Charts render for score trends, error rates
- [ ] Search and filter working across all tables
- [ ] <2s load time for dashboard overview
- [ ] <500ms for detail views
- [ ] 100% data coverage for test user

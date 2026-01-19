# Memory Changelog

Documents changes to what is currently implemented in the Nikita codebase.

## [0.6.0] - 2026-01-11 - System Audit & Context Enhancements

### Critical Issue Fixes (Issues #13-21)
- **Issue #13**: Wired engagement state machine into message flow (`_update_engagement_after_scoring`)
- **Issue #14**: Fixed pg_cron job URLs (`/tasks/*` → `/api/v1/tasks/*`)
- **Issue #15**: Added score_delta storage to conversations after scoring
- **Issue #16**: Fixed pg_cron job syntax (proper `::jsonb` casting)
- **Issue #17**: Added voice scoring to webhook handler
- **Issue #18**: Deleted duplicate pg_cron job
- **Issue #19**: Added `last_interaction_at` update on every message
- **Issue #20**: Fixed MetaPromptService clarifying questions handling
- **Issue #21**: Expanded context_snapshot from 5 to 20+ fields

### Voice Agent Context Enhancements
- **Server Tools**: Added `active_thoughts`, `today_summary`, `week_summaries`, `backstory` to `get_context()`
- **Prompt Logging**: Enabled voice prompt logging (`skip_logging=False`)
- **Context Snapshot**: Expanded MetaPromptService logging to 20+ fields for debugging

### Tests
- 21 voice server_tools tests passing (17 original + 4 new)
- 177 voice module tests passing

## [0.5.0] - 2026-01-10 - Voice Agent Deployment

### Voice Agent (Spec 007 Complete)
- **14 modules** implemented in `nikita/agents/voice/`
- **186 tests** passing
- **ElevenLabs Conversational AI 2.0** integration with Server Tools pattern

### API Endpoints (5 deployed)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/voice/availability/{user_id}` | GET | Check call availability |
| `/api/v1/voice/initiate` | POST | Start voice call |
| `/api/v1/voice/pre-call` | POST | Inbound webhook (Twilio → ElevenLabs) |
| `/api/v1/voice/server-tool` | POST | Server tool dispatch |
| `/api/v1/voice/webhook` | POST | Call events (connected, ended) |

### Server Tools
- `get_context`: User facts, threads, memories
- `get_memory`: Query Graphiti for relevant memories
- `score_turn`: Score individual conversation turn
- `update_memory`: Store new facts in knowledge graph

### Issue Fixes (Issues #6-12)
- **Issue #6**: Fixed DynamicVariables None handling (chapter, relationship_score)
- **Issue #7**: Fixed engagement_state.state attribute access
- **Issue #8**: Added secret__signed_token to dynamic_variables
- **Issue #10**: Enabled TTS settings override in ElevenLabs Dashboard
- **Issue #11**: Fixed webhook signature format (`t=timestamp,v0=hash`)
- **Issue #12**: Fixed webhook payload parsing (uses `type` not `event_type`)

## [0.4.0] - 2025-12-18 - MVP COMPLETE

### MVP Completion
- **All 14 specifications** audited and passing
- **E2E verification** passed for all components
- **1248 tests** passing, 18 skipped

### Gap Fixes (B-1/2/3 + C-1/2/3/4/5/6)
- **B-1**: Neo4j configured in Cloud Run production
- **B-2**: Boss scoring integrated in handler.py
- **B-3**: DecayProcessor wired in /tasks/decay endpoint
- **C-1**: Vice role mismatch fixed (assistant → nikita)
- **C-2**: Thread resolution detection (template + service + post-processor)
- **C-3**: Chapter behaviors verified working via prompts
- **C-4**: Engagement LLM detection + scoring multipliers
- **C-5/C-6**: Daily summaries with full LLM generation

### Engine Modules (All Complete)
| Module | Tests |
|--------|-------|
| `engine/scoring/` | 60 |
| `engine/engagement/` | 179 |
| `engine/decay/` | 52 |
| `engine/chapters/` | 142 |
| `engine/vice/` | 81 |

### Background Tasks (pg_cron)
- `/tasks/decay` - Hourly decay with grace periods
- `/tasks/summary` - LLM-based daily summaries
- `/tasks/cleanup` - Expired registration cleanup
- `/tasks/process-conversations` - Inactive conversation detection

### Onboarding (Spec 015)
- OTP flow replaces magic link for Telegram users
- 6-digit code verification via Supabase Auth

## [0.3.0] - 2025-12-09

### Portal Frontend
- **Added** `portal/src/lib/supabase/proxy.ts` - Supabase SSR session refresh utility
- **Changed** `portal/src/proxy.ts` - Refactored to use shared updateSession utility
- **Fixed** Session cookie handling - Proper refresh for both server components and browser

### Backend
- **No changes** - Backend JWT auth already deployed in 0.2.0

## [0.2.0] - 2025-12-09

### Backend
- **Added** `nikita/api/dependencies/auth.py` - Supabase JWT authentication
  - PyJWT-based token validation with HS256 algorithm
  - Validates `sub` claim for user ID extraction
  - Proper 401/403 error responses with WWW-Authenticate header
- **Added** `SUPABASE_JWT_SECRET` environment variable to Cloud Run
- **Added** PyJWT 2.8.0 dependency to pyproject.toml
- **Changed** `nikita/api/routes/portal.py` - Uses JWT auth dependency
  - All endpoints now require valid Supabase JWT
  - Portal-first users auto-created on first dashboard visit
- **Changed** `nikita/api/schemas/portal.py` - Added metrics to UserStatsResponse

### Portal Frontend
- **Fixed** Next.js 16 proxy naming (confirmed `proxy.ts` is correct, not middleware.ts)
- **Added** Magic link code detection on landing page

## [0.1.0] - 2025-12-08

### Portal Frontend (008-player-portal)
- **Added** Next.js 16.0.7 application in `portal/` directory
- **Added** Magic link authentication with Supabase
- **Added** Dashboard layout with:
  - Stats card (relationship score, chapter, metrics)
  - Score history chart
  - Engagement state display
  - Conversation history
- **Added** Playwright E2E test suite (28 tests)
- **Added** CI/CD with ESLint, TypeScript, and pre-commit hooks

### Tech Stack
| Component | Technology |
|-----------|------------|
| Framework | Next.js 16.0.7 |
| Auth | @supabase/ssr 0.8.0 |
| Styling | Tailwind CSS 4 + shadcn/ui |
| Testing | Playwright 1.57.0 |

## [Previous] - 2025-12-01 to 2025-12-07

### Phase 2: Telegram Integration
- Telegram bot deployed to Cloud Run
- Webhook endpoint at `/api/v1/telegram/webhook`
- Message handling with text agent integration
- Rate limiting and error handling

### Phase 1: Text Agent
- Pydantic AI text agent with Claude Sonnet
- 156 tests passing
- Context engineering pipeline
- Memory integration with Graphiti

---

## File Status

| File | Purpose | Last Updated |
|------|---------|--------------|
| architecture.md | System design | 2025-12-18 |
| backend.md | API patterns | 2026-01-11 |
| constitution.md | Development principles | 2025-11-29 |
| game-mechanics.md | Scoring, chapters, decay | 2025-12-18 |
| integrations.md | External services | 2026-01-11 |
| product.md | Product definition | 2025-11-28 |
| user-journeys.md | User flows | 2025-12-18 |
| README.md | Hub navigation | 2026-01-11 |
| CHANGELOG.md | Version history | 2026-01-11 |

# Diagram: Testing Observability Map

**Type**: Structural — Observation Points per System Layer
**Scope**: Where tests can observe and verify system state at each step
**Sources**:
- `nikita/db/models/` — all table models (26 model files)
- `nikita/api/routes/admin.py` — admin API endpoints
- `nikita/pipeline/orchestrator.py` — stage definitions
- `tests/` — test patterns (pytest, ASGI transport, Supabase MCP)
- `docs/deployment.md` — Cloud Run log access

---

```
+====================================================================+
|  OBSERVATION LAYERS                                                |
+====================================================================+

  +--[ DB Layer ]----------------------------------------------+
  | Direct Supabase SQL queries (Supabase MCP or psycopg2)     |
  |                                                            |
  | Core user state:                                           |
  |   users                  chapter, game_status, metrics,   |
  |                          conflict_details JSONB,           |
  |                          cached_voice_prompt               |
  |   user_metrics           intimacy, passion, trust,         |
  |                          secureness (4 metrics)            |
  |   score_history          per-turn delta rows               |
  |   engagement_state       current FSM state                 |
  |   engagement_history     FSM transition log                |
  |   user_vice_preferences  category, intensity_level         |
  |                                                            |
  | Conversation state:                                        |
  |   conversations          messages JSONB, status, summary   |
  |   conversation_threads   open topics (persistence stage)   |
  |   nikita_thoughts        extracted facts (extraction stage)|
  |                                                            |
  | Memory:                                                    |
  |   memory_facts           pgVector embeddings (dedup 0.95)  |
  |                                                            |
  | Life simulation:                                           |
  |   nikita_life_events     simulated events (life_sim stage) |
  |   nikita_emotional_states computed state (emotional stage) |
  |   nikita_narrative_arcs  story arc tracking                |
  |                                                            |
  | Pipeline health:                                           |
  |   pipeline_events        per-stage observability events    |
  |   job_executions         cron job run records              |
  |   ready_prompts          pre-built prompts (text + voice)  |
  |                                                            |
  | Scheduling:                                                |
  |   scheduled_events       pending deliveries                |
  |   scheduled_touchpoints  proactive message queue           |
  |                                                            |
  | Voice:                                                     |
  |   voice_calls            call records (inbound + outbound) |
  |   rate_limit             per-user rate tracking            |
  +------------------------------------------------------------+

  +--[ API Layer ]----------------------------------------------+
  | FastAPI test client (ASGI transport, tests/conftest.py)     |
  |                                                             |
  | Admin endpoints (nikita/api/routes/admin.py):               |
  |   GET /admin/pipeline-health                                |
  |       job_executions + pipeline_events summary              |
  |   GET /admin/users/{id}/metrics                             |
  |       live user_metrics read                                |
  |   GET /admin/users/{id}/history                             |
  |       score_history with delta breakdown                    |
  |   GET /admin/users/{id}/engagement                          |
  |       engagement_state + engagement_history                 |
  |   GET /admin/users/{id}/memory                              |
  |       memory_facts (paginated)                              |
  |   GET /admin/users/{id}/conversations                       |
  |       conversation list + message counts                    |
  |                                                             |
  | Portal endpoints (nikita/api/routes/portal.py):             |
  |   GET /portal/stats                                         |
  |   GET /portal/dashboard/*                                   |
  +-------------------------------------------------------------+

  +--[ MCP Layer ]----------------------------------------------+
  | Integration / E2E test toolchain                            |
  |                                                             |
  |   Supabase MCP     Direct SQL queries against live DB       |
  |                    Table counts, row assertions, JSONB reads |
  |                                                             |
  |   Telegram MCP     Send/receive messages as test user       |
  |                    Assert Nikita response content/timing    |
  |                    Session expires: re-run                  |
  |                    session_string_generator.py              |
  |                                                             |
  |   Gmail MCP        Assert magic link emails delivered       |
  |                    Portal auth flow verification            |
  |                                                             |
  |   ElevenLabs       Conversation transcript fetch            |
  |   conversations    (via /api/v1/voice/webhook test)         |
  +-------------------------------------------------------------+

  +--[ Logs Layer ]--------------------------------------------+
  | Cloud Run structured logs (structlog)                      |
  |   gcloud run logs read nikita-api --region us-central1     |
  |                                                            |
  | Key log markers:                                           |
  |   pipeline_started    conversation_id, user_id, platform   |
  |   stage_completed     stage=N duration_ms=X                |
  |   stage_failed        stage=N critical=True/False          |
  |   pipeline_completed  total_ms=X stages=11 errors=N        |
  |   pipeline_skipped_   game_status=game_over/won            |
  |     terminal_state                                         |
  |   voice_prompt_stale  age_hours > 4                        |
  |   observability_flush pipeline_events bulk INSERT          |
  +------------------------------------------------------------+

  +--[ Portal Layer ]------------------------------------------+
  | Next.js app (portal/src/app/) — 13 dashboard pages        |
  |                                                            |
  | Admin panel:  /admin/                                      |
  |   User list, metrics drill-down, pipeline health          |
  |   Voice call log, engagement timeline                     |
  |                                                            |
  | Dashboard pages (user-facing):                            |
  |   /dashboard/metrics       4-metric radar chart           |
  |   /dashboard/engagement    FSM state + history timeline   |
  |   /dashboard/memory        memory_facts browser           |
  |   /dashboard/chapters      chapter + boss status          |
  |   /dashboard/voice         voice call history             |
  +------------------------------------------------------------+


+====================================================================+
|  PER PIPELINE STAGE: OBSERVATION POINTS                            |
+====================================================================+

Stage 1: extraction   [CRITICAL]
  +------------------------------+
  | Input assertion:             |
  |   conversations.messages     |
  |   (message count > 0)        |
  | Output assertions:           |
  |   nikita_thoughts rows added |
  |   ctx.extracted_facts != []  |
  | Failure signal:              |
  |   pipeline_events WHERE      |
  |   stage='extraction'         |
  |   AND status='failed'        |
  +------------------------------+

Stage 2: persistence  [non-crit]
  +------------------------------+
  | Output assertions:           |
  |   conversation_threads rows  |
  |   (open topics written)      |
  | Note: runs BEFORE stage 3;   |
  |   verify ordering in         |
  |   job_executions timings     |
  +------------------------------+

Stage 3: memory_update [CRITICAL]
  +------------------------------+
  | Output assertions:           |
  |   memory_facts count up      |
  |   Dedup: duplicate fact does |
  |   NOT create 2nd row         |
  |   (cosine threshold 0.95)    |
  | pgVector check (MCP SQL):    |
  |   SELECT COUNT(*) FROM       |
  |   memory_facts WHERE         |
  |   user_id = $1               |
  +------------------------------+

Stage 4: life_sim     [non-crit]
  +------------------------------+
  | Output assertions:           |
  |   nikita_life_events rows    |
  |   nikita_narrative_arcs rows |
  | Absence OK on short convos   |
  +------------------------------+

Stage 5: emotional    [non-crit]
  +------------------------------+
  | Output assertions:           |
  |   nikita_emotional_states    |
  |   row upserted (user_id key) |
  | Observable via:              |
  |   GET /admin/users/{id}/     |
  |       metrics (mood field)   |
  +------------------------------+

Stage 6: vice         [non-crit]
  +------------------------------+
  | Output assertions:           |
  |   user_vice_preferences rows |
  |   category + intensity_level |
  | Observable via:              |
  |   GET /admin/users/{id}/     |
  |       metrics                |
  +------------------------------+

Stage 7: game_state   [non-crit]
  +------------------------------+
  | Output assertions:           |
  |   users.chapter changed      |
  |   users.game_status changed  |
  |   score_history new row      |
  | Boss trigger check:          |
  |   users.game_status =        |
  |   'boss_fight'               |
  +------------------------------+

Stage 8: conflict     [non-crit]
  +------------------------------+
  | Output assertions:           |
  |   users.conflict_details     |
  |   JSONB populated/cleared    |
  +------------------------------+

Stage 9: touchpoint   [non-crit]
  +------------------------------+
  | Output assertions:           |
  |   scheduled_touchpoints row  |
  |   ctx.touchpoint_scheduled   |
  |   = True                     |
  +------------------------------+

Stage 10: summary     [non-crit]
  +------------------------------+
  | Output assertions:           |
  |   conversations.summary      |
  |   field populated            |
  +------------------------------+

Stage 11: prompt_builder [non-crit]
  +------------------------------+
  | Output assertions:           |
  |   ready_prompts row          |
  |   (platform='text' AND       |
  |    platform='voice')         |
  |   users.cached_voice_prompt  |
  |   updated                    |
  | Staleness check:             |
  |   cached_voice_prompt_at     |
  |   < NOW() - 4 hours?         |
  |   (logged as warning)        |
  +------------------------------+

  After all stages:
  +------------------------------+
  | pipeline_events table:       |
  |   11 stage events +          |
  |   1 pipeline.complete event  |
  |   (if observability_enabled) |
  |                              |
  | job_executions table:        |
  |   1 row per cron run with    |
  |   stage_timings JSON         |
  +------------------------------+


+====================================================================+
|  TEST PATTERN QUICK REFERENCE                                      |
+====================================================================+

  Unit tests (pytest, async mocks):
    tests/pipeline/          -- per-stage unit tests
    tests/platforms/telegram/ -- MessageHandler unit tests
    tests/agents/voice/      -- voice agent unit tests
    tests/engine/            -- scoring, engagement, chapters
    Pattern: AsyncMock, session.rollback() mock
    See: tests/conftest.py for shared fixtures

  Integration tests (ASGI transport):
    tests/e2e/               -- E2E journey tests
    Pattern: httpx.AsyncClient(app=app, transport=ASGITransport)
    Webhook simulator, no-op cleanup fixtures
    See: tests/e2e/conftest.py

  E2E tests (/e2e skill, 13 epics, 363 scenarios):
    Telegram MCP: send message, assert reply within N seconds
    Supabase MCP: assert DB row state after pipeline runs
    Gmail MCP:    assert auth emails delivered
    Portal:       Chrome DevTools MCP for UI assertions

  Admin API assertion pattern:
    GET /admin/users/{id}/metrics  --> assert intimacy/passion/trust/secureness
    GET /admin/pipeline-health     --> assert no failed stages in last N runs
    GET /admin/users/{id}/history  --> assert score_history delta sequence

Legend:
  --> observation / assertion direction
  [CRITICAL] pipeline halts on failure -- test for error propagation
  [non-crit] pipeline continues -- test for graceful degradation
```

---

**Test Coverage Map**

| System Area | Unit Test Path | E2E Observable Via |
|-------------|---------------|-------------------|
| Message handling | `tests/platforms/telegram/` | Telegram MCP |
| Scoring engine | `tests/engine/scoring/` | `score_history` table, admin API |
| Engagement FSM | `tests/engine/engagement/` | `engagement_state` table, admin API |
| Pipeline stages | `tests/pipeline/` | `pipeline_events`, per-stage tables |
| Voice inbound | `tests/agents/voice/test_inbound.py` | `voice_calls` table |
| Voice server tools | `tests/agents/voice/test_server_tools.py` | `memory_facts`, `score_history` |
| Memory (pgVector) | `tests/agents/voice/test_context_block.py` | `memory_facts` count + dedup |
| Boss encounters | `tests/platforms/telegram/test_message_handler_boss.py` | `users.game_status` |
| Portal auth | `portal/src/__tests__/` | Gmail MCP, Chrome DevTools |

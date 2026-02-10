# Workbook - Session Context
<!-- Max 300 lines, prune aggressively -->

## Current Session: Pipeline Fix Sprint (2026-02-10)

### Status: COMPLETE — Pipeline working, all artifacts stored

**Root Causes Fixed:**

| Bug | Severity | Fix | Commit |
|-----|----------|-----|--------|
| BUG-001: orchestrator.process() missing conversation/user | CRITICAL | Load User via UserRepository, pass to orchestrator | a3d17c0 |
| BUG-002: pydantic-ai result_type→output_type | CRITICAL | Migrated 7 files to new API | 592fa15 |
| BUG-003: pydantic-ai>=1.0.0 not pinned | HIGH | Pin in pyproject.toml + fix test mocks | c4de9c9 |
| BUG-004: AnthropicModel api_key param removed in 1.x | MEDIUM | Remove api_key, reads from env | bc1b287 |
| BUG-005: MissingGreenlet + game_state logging | MEDIUM | try/except + fix format string | 79f664e |

**Verified Artifacts in Supabase:**
- conversation_summary: LLM-generated rich summaries for 2 conversations
- emotional_tone: "mixed" extracted and stored
- ready_prompts: 4,163 tokens, personalized system prompt
- pg_cron: 5/5 jobs active

**Cloud Run:** Rev 00194-g6f, 100% traffic, minInstances=1

**Remaining non-critical:**
1. life_sim stage: SQL syntax error (`:` in query)
2. Memory facts: No NEW facts from pipeline runs (existing 15 from neo4j migration)
3. LLM timeout: One 120s timeout on text agent (performance issue)

---

## Previous Sessions (Compact)

| Date | Session | Key Result |
|------|---------|------------|
| 2026-02-10 | Live E2E Fix Sprint | 6 fixes, mark_processed, pg_cron restored, minInstances=1 |
| 2026-02-09 | Post-Release Sprint | 86 E2E tests, prod hardening, all gates PASS |
| 2026-02-09 | Release Sprint | 5 GH issues closed, 37 E2E tests, spec hygiene |
| 2026-02-08 | Spec 044 Implementation | 94 files, 19 routes, 3,917 tests, Vercel deploy |
| 2026-02-07 | Iteration Sprint | E2E fix (19→0), doc cleanup, 3,895 tests |
| 2026-02-06 | Spec 042 SDD + Impl | 45/45 tasks, ~11K lines deleted, 3,797 tests |

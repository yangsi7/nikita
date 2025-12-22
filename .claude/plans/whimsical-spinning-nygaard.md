# E2E Testing Orchestration Plan

**Date**: 2025-12-18
**Status**: Prompt Rewrite Complete
**Task**: Rewrite voice memo into structured agentic prompt

---

## Original Request

User provided a voice memo requesting an end-to-end testing plan for the Nikita system with:
- Fresh user onboarding (delete account, start from scratch)
- Step-by-step verification at each stage
- Division of labor (Claude checks DB/logs, User checks Telegram/Portal)
- Visibility into system prompts used for each conversation
- Post-processing pipeline verification
- Use of discovery-driven planning skill with parallel subagents

---

## Rewritten Prompt (Following Best Practices)

```xml
<task_definition>
Create a comprehensive E2E testing orchestration plan for the Nikita AI girlfriend simulation system. This plan will guide a collaborative human-AI testing session where we verify every component end-to-end, from fresh user onboarding through post-processing pipelines.
</task_definition>

<context>
<system_overview>
Nikita is a dual-agent AI girlfriend simulation with:
- Text agent (Pydantic AI + Claude Sonnet) deployed on Cloud Run
- Telegram bot integration for user messaging
- Supabase PostgreSQL for user data, conversations, and game state
- Neo4j Aura for temporal knowledge graphs (Graphiti)
- Post-processing pipeline triggered ~15 min after conversation ends
- Game mechanics: scoring, chapters, decay, vice detection, engagement states
</system_overview>

<test_environment>
- Backend URL: https://nikita-api-1040094048579.us-central1.run.app
- Database: Supabase (accessible via MCP tools)
- Scheduling: pg_cron endpoints (/tasks/decay, /tasks/summary, /tasks/process-conversations)
- Telegram bot: @[bot_handle]
</test_environment>

<tester_roles>
<human_tester>User with Telegram access and portal login</human_tester>
<ai_tester>Claude Code with Supabase MCP, log access, and code inspection</ai_tester>
</tester_roles>
</context>

<objective>
Design an exhaustive E2E test plan that:
1. Starts from a clean slate (user account deleted, fresh registration)
2. Verifies every stage of the user journey with specific assertions
3. Clearly divides verification responsibilities between human and AI
4. Captures and analyzes system prompts used in each Nikita response
5. Validates the post-processing pipeline stages (extraction, threads, thoughts, memory, summaries)
6. Ensures all pg_cron background jobs execute correctly
</objective>

<instructions>
<phase name="research">
Use the discovery-driven-planning skill to:

1. **Parallel Codebase Exploration** (spawn up to 3 subagents):
   - Agent 1: Trace the complete onboarding flow (Telegram /start → registration → OTP → auth confirmation)
   - Agent 2: Trace the message handling flow (webhook → conversation → text agent → response → Telegram delivery)
   - Agent 3: Trace the post-processing pipeline (session detection → 9 stages → memory persistence)

2. **Documentation Review**:
   - Read memory/user-journeys.md for expected user flows
   - Read memory/backend.md for API endpoints and their behaviors
   - Read memory/architecture.md for component interactions
   - Identify all verification points and their expected states

3. **System Prompt Analysis**:
   - Locate where system prompts are constructed (nikita/meta_prompts/)
   - Understand dynamic context injection (user history, engagement state, chapter, vice)
   - Plan how to capture and display the actual system prompt used per message
</phase>

<phase name="test_plan_structure">
For each user journey stage, document:

<test_step_template>
<step_id>[Sequential ID]</step_id>
<action>What the human tester does</action>
<expected_behavior>What should happen in the system</expected_behavior>
<ai_verification>
  <check type="database">Supabase query to verify state</check>
  <check type="logs">Log patterns to look for</check>
  <check type="code">Code paths that should execute</check>
</ai_verification>
<human_verification>What the user should see/confirm</human_verification>
<system_prompt_capture>How to retrieve the system prompt used (if applicable)</system_prompt_capture>
<success_criteria>Specific assertions that must pass</success_criteria>
</test_step_template>
</phase>

<phase name="verification_matrix">
Create a matrix showing:

| Component | AI Can Verify | Human Must Verify | Method |
|-----------|---------------|-------------------|--------|
| DB records | ✅ | - | Supabase MCP queries |
| API responses | ✅ | - | Log inspection |
| Telegram messages | - | ✅ | Visual confirmation |
| Portal UI | - | ✅ | Browser interaction |
| System prompts | ✅ | - | Meta prompt service logs |
| Background jobs | ✅ | - | /tasks/* endpoint calls |
</phase>

<phase name="coverage_areas">
Ensure the test plan covers:

1. **Onboarding Flow**
   - /start command processing
   - OTP generation and verification
   - User record creation (users table)
   - Initial game state (chapter 1, score 50, engagement neutral)

2. **Conversation Flow**
   - Webhook message receipt and validation
   - Conversation creation/continuation
   - Text agent invocation with correct context
   - LLM response generation
   - Telegram message delivery
   - **System prompt used** (capture full prompt including dynamic context)

3. **Post-Processing Pipeline** (all 9 stages)
   - Session detection (15+ min inactivity)
   - Fact extraction via MetaPromptService
   - Thread creation with correct types
   - Thought extraction with correct types
   - Neo4j memory graph updates
   - Vice behavior detection
   - Daily summary generation
   - Conversation finalization

4. **Background Jobs** (pg_cron)
   - /tasks/decay - Score decay processing
   - /tasks/summary - LLM daily summaries
   - /tasks/cleanup - Expired registration cleanup
   - /tasks/process-conversations - Inactive conversation detection

5. **Portal Integration**
   - Magic link authentication
   - Dashboard stats display
   - Score history chart
   - Conversation history
</phase>
</instructions>

<output_format>
<test_plan>
## E2E Test Plan: Nikita System Verification

### Pre-Test Setup
[Account cleanup steps, environment verification]

### Test Stages
[Numbered stages with all template fields filled]

### Verification Runbook
[Step-by-step commands for AI to execute during testing]

### Human Tester Instructions
[Clear instructions for what the user should do and observe]

### Post-Processing Verification
[Specific queries and expected results for pipeline validation]

### System Prompt Capture Points
[How and when to capture the dynamic system prompts]

### Success Criteria Summary
[Checklist of all assertions that must pass for E2E success]
</test_plan>
</output_format>

<constraints>
- Do NOT make any changes to production data or code during research
- All verification queries must be read-only
- Use MCP Supabase tools for database inspection
- Use gcloud commands for Cloud Run logs (read-only)
- Ask the human tester clarifying questions before finalizing the plan
</constraints>

<thinking_process>
Before generating the plan:
1. What are the critical paths that must work for MVP?
2. Where have we seen failures in previous E2E tests (reference event-stream.md)?
3. What data can I query vs what needs human observation?
4. How do I capture the actual system prompt sent to Claude for each message?
5. What is the expected timing for post-processing triggers?
</thinking_process>
```

---

## Implementation Approach

1. **Invoke discovery-driven-planning skill** - for structured research phase
2. **Spawn parallel Explore agents** - to trace 3 major flows simultaneously
3. **Build verification runbook** - SQL queries, log commands, assertions
4. **Create human tester script** - clear actions and expected observations
5. **Ask clarifying questions** - before finalizing test coverage

---

## Clarifying Questions to Ask User

Before creating the plan, confirm:
1. Do you want to test with your real Telegram account or a test account?
2. Should we capture system prompts by adding logging or checking existing logs?
3. How long do you have for this testing session (affects depth)?
4. Should we test all background jobs or focus on critical path only?

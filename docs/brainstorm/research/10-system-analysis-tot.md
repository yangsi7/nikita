# System Architecture Tree-of-Thought Analysis — Nikita

**Created**: 2026-02-16
**Purpose**: Comprehensive architecture map identifying leverage points (easy to enhance) and constraints (hard to change)
**Max Lines**: 500

---

## 1. SYSTEM ARCHITECTURE TREE

**Notation**: `→` dependency, `⊕` parallel, `∘` sequential, `⇄` bidirectional, `⊃` contains, `↔` data flow

```
NIKITA_SYSTEM [Serverless AI Girlfriend Game]
│
├─[→] ENTRY POINTS (3 channels)
│  ├─[⊕] Telegram (@Nikita_my_bot)
│  │  └─→ POST /api/v1/telegram/webhook [nikita/api/routes/telegram.py:47]
│  │     └─→ TelegramMessageHandler [nikita/platforms/telegram/message_handler.py]
│  │
│  ├─[⊕] Voice (ElevenLabs)
│  │  ├─→ Inbound: Twilio → ElevenLabs → Server Tools [nikita/api/routes/voice.py:251]
│  │  └─→ Outbound: Scheduled events → ElevenLabs API
│  │
│  └─[⊕] Portal (Next.js/Vercel)
│     └─→ GET /api/v1/portal/* [nikita/api/routes/portal.py]
│
├─[→] CORE PIPELINE (9 stages, sequential)
│  └─→ PipelineOrchestrator [nikita/pipeline/orchestrator.py:26]
│     ├─[∘] 1. ExtractionStage (CRITICAL) [nikita/pipeline/stages/extraction.py]
│     │  └─→ LLM extracts facts from conversation
│     ├─[∘] 2. MemoryUpdateStage (CRITICAL) [nikita/pipeline/stages/memory_update.py]
│     │  └─→ pgVector insertion (SupabaseMemory)
│     ├─[∘] 3. LifeSimStage [nikita/pipeline/stages/life_sim.py]
│     │  └─→ Generate Nikita's simulated life events
│     ├─[∘] 4. EmotionalStage [nikita/pipeline/stages/emotional.py]
│     │  └─→ Update relationship dynamics
│     ├─[∘] 5. GameStateStage [nikita/pipeline/stages/game_state.py]
│     │  └─→ Chapter progression, boss triggers
│     ├─[∘] 6. ConflictStage [nikita/pipeline/stages/conflict.py]
│     │  └─→ Detect/resolve arguments
│     ├─[∘] 7. TouchpointStage [nikita/pipeline/stages/touchpoint.py]
│     │  └─→ Schedule proactive outreach
│     ├─[∘] 8. SummaryStage [nikita/pipeline/stages/summary.py]
│     │  └─→ Daily summary generation
│     └─[∘] 9. PromptBuilderStage [nikita/pipeline/stages/prompt_builder.py]
│        └─→ Rebuild cached system prompt
│
├─[→] GAME ENGINE (scoring, chapters, decay)
│  ├─[⊃] scoring/ [nikita/engine/scoring/]
│  │  ├─→ ScoreCalculator [calculator.py:250] — LLM-based analysis
│  │  ├─→ ResponseAnalysis [models.py] — intimacy/passion/trust/secureness deltas
│  │  └─→ Composite formula: 0.30I + 0.25P + 0.25T + 0.20S [constants.py:51-57]
│  │
│  ├─[⊃] chapters/ [nikita/engine/chapters/]
│  │  ├─→ BossStateMachine [boss.py] — 5 bosses, 3 attempts per boss
│  │  ├─→ Thresholds: [55%, 60%, 65%, 70%, 75%] [constants.py:138-144]
│  │  └─→ GAME_OVER at 3rd boss fail OR score=0
│  │
│  ├─[⊃] decay/ [nikita/engine/decay/]
│  │  ├─→ Hourly decay rates: [0.8%, 0.6%, 0.4%, 0.3%, 0.2%] [constants.py:147-153]
│  │  ├─→ Grace periods: [8h, 16h, 24h, 48h, 72h] [constants.py:156-162]
│  │  └─→ Triggered by: pg_cron → POST /tasks/decay [api/routes/tasks.py]
│  │
│  ├─[⊃] engagement/ [nikita/engine/engagement/]
│  │  └─→ 6 states: healthy, distant, clingy, recovering_distant, recovering_clingy, critical
│  │
│  └─[⊃] vice/ [nikita/engine/vice/]
│     └─→ 8 categories: intellectual, risk, substances, sexuality, emotional, rule_breaking, dark_humor, vulnerability
│
├─[→] MEMORY SYSTEM (pgVector)
│  └─→ SupabaseMemory [nikita/memory/supabase_memory.py:44]
│     ├─→ add_fact() — deduplication via cosine similarity [supabase_memory.py:151]
│     ├─→ search() — semantic search (1536-dim embeddings) [supabase_memory.py:191]
│     ├─→ 3 graph types: user, nikita, relationship [constants.py:23-28]
│     └─→ OpenAI text-embedding-3-small [supabase_memory.py:32]
│
├─[→] TEXT AGENT (Pydantic AI)
│  └─→ NikitaAgent [nikita/agents/text/agent.py:56]
│     ├─→ Model: claude-sonnet-4-5-20250929 [agent.py:35]
│     ├─→ Tools: recall_memory, note_user_fact [agent.py:108, 136]
│     ├─→ Prompt layers:
│     │  ├─[1] NIKITA_PERSONA (base) [nikita/agents/text/persona.py]
│     │  ├─[2] CHAPTER_BEHAVIORS[chapter] [engine/constants.py:100]
│     │  └─[3] Personalized context (ready_prompts or MetaPromptService)
│     └─→ Message history (conversation continuity) [agent.py:402-432]
│
├─[→] VOICE AGENT (ElevenLabs)
│  └─→ VoiceService [nikita/agents/voice/service.py]
│     ├─→ Conversational AI 2.0 (Server Tools pattern)
│     ├─→ 5 tools: get_context, get_memory, get_insights, score_turn, update_memory
│     ├─→ Agent IDs: per-chapter switching [nikita/config/elevenlabs.py]
│     └─→ Inbound: Twilio → ElevenLabs → HTTP callbacks [api/routes/voice.py]
│
├─[→] DATABASE (Supabase PostgreSQL)
│  ├─[⊃] Core tables (22 models)
│  │  ├─→ users [id, telegram_id, relationship_score, chapter, game_status]
│  │  ├─→ user_metrics [intimacy, passion, trust, secureness]
│  │  ├─→ user_vice_preferences [category, intensity_level, engagement_score]
│  │  ├─→ conversations [messages JSONB, platform, score_delta]
│  │  ├─→ score_history [event logs for graphs]
│  │  ├─→ memory_facts [pgVector — fact, embedding vector(1536), hash]
│  │  ├─→ ready_prompts [cached system prompts, valid_until]
│  │  ├─→ scheduled_events [proactive messaging queue]
│  │  └─→ engagement_state [current engagement state FSM]
│  │
│  └─[⊃] Repositories (21 repos) [nikita/db/repositories/]
│     ├─→ UserRepository [user_repository.py]
│     ├─→ ConversationRepository [conversation_repository.py]
│     ├─→ MemoryFactRepository [memory_fact_repository.py]
│     └─→ ... (18 more)
│
├─[→] BACKGROUND TASKS (pg_cron)
│  └─→ Scheduled via Supabase pg_cron
│     ├─→ Hourly: /tasks/decay [Apply decay to inactive users]
│     ├─→ Daily: /tasks/summary [Generate daily summaries]
│     ├─→ Every minute: /tasks/process-conversations [Pipeline trigger]
│     └─→ Daily: /tasks/cleanup [Expire old prompts/events]
│
└─[→] PORTAL (Next.js 16)
   ├─→ Dashboard routes (19 routes) [portal/src/app/dashboard/]
   ├─→ Admin routes (9 routes) [portal/src/app/admin/]
   └─→ Direct Supabase client (RLS + Auth)
```

---

## 2. DATA FLOW MAP

### Entry → Pipeline → Storage → Next Prompt

```
[USER INPUT]
    ↓
┌──────────────────────────────────────┐
│ 1. ENTRY POINT (Telegram/Voice)     │
│    ├─ Webhook receives message       │
│    └─ Route to message handler       │
└──────────────────┬───────────────────┘
                   ↓
┌──────────────────────────────────────┐
│ 2. TEXT AGENT (generate_response)   │
│    ├─ Load user state (User + Metrics)
│    ├─ Build system prompt:          │
│    │  ├─ NIKITA_PERSONA (base)      │
│    │  ├─ Chapter behavior overlay   │
│    │  └─ Memory context (5 facts)   │
│    ├─ Call Claude Sonnet 4.5        │
│    │  └─ Tools: recall_memory, note_user_fact
│    └─ Return response text           │
└──────────────────┬───────────────────┘
                   ↓
┌──────────────────────────────────────┐
│ 3. SCORING (post-response)           │
│    ├─ ScoreCalculator.analyze()     │
│    │  └─ LLM returns deltas:        │
│    │     intimacy: -10 to +10       │
│    │     passion: -10 to +10        │
│    │     trust: -10 to +10          │
│    │     secureness: -10 to +10     │
│    ├─ Apply deltas to user_metrics  │
│    ├─ Recalculate composite score   │
│    └─ Log to score_history          │
└──────────────────┬───────────────────┘
                   ↓
┌──────────────────────────────────────┐
│ 4. CHAPTER CHECK                     │
│    ├─ Check boss threshold           │
│    │  └─ If score >= threshold:     │
│    │     ├─ Set game_status = 'boss_fight'
│    │     └─ Inject boss prompt      │
│    └─ Check game over conditions:   │
│       ├─ score = 0 → GAME_OVER      │
│       └─ 3 boss fails → GAME_OVER   │
└──────────────────┬───────────────────┘
                   ↓
┌──────────────────────────────────────┐
│ 5. CONVERSATION END DETECTION        │
│    └─ After 30min inactive:          │
│       └─ Mark conversation ended_at  │
└──────────────────┬───────────────────┘
                   ↓
┌──────────────────────────────────────┐
│ 6. PIPELINE TRIGGER (pg_cron)        │
│    └─ Every minute:                  │
│       POST /tasks/process-conversations
│       └─ Find ended conversations    │
│          with processed_at = NULL    │
└──────────────────┬───────────────────┘
                   ↓
┌──────────────────────────────────────┐
│ 7. UNIFIED PIPELINE (9 stages)       │
│    ├─ ExtractionStage               │
│    │  └─ LLM extracts facts from msgs
│    ├─ MemoryUpdateStage              │
│    │  └─ Insert facts → memory_facts │
│    ├─ LifeSimStage                   │
│    │  └─ Generate Nikita life events │
│    ├─ EmotionalStage                 │
│    │  └─ Update relationship state   │
│    ├─ GameStateStage                 │
│    │  └─ Chapter/boss logic          │
│    ├─ ConflictStage                  │
│    │  └─ Detect arguments            │
│    ├─ TouchpointStage                │
│    │  └─ Schedule proactive messages │
│    ├─ SummaryStage                   │
│    │  └─ Generate daily summary      │
│    └─ PromptBuilderStage             │
│       └─ Rebuild ready_prompts table │
└──────────────────┬───────────────────┘
                   ↓
┌──────────────────────────────────────┐
│ 8. STORAGE (Supabase PostgreSQL)    │
│    ├─ memory_facts (pgVector)       │
│    ├─ ready_prompts (cached prompts)│
│    ├─ scheduled_events (touchpoints)│
│    └─ daily_summaries               │
└──────────────────┬───────────────────┘
                   ↓
┌──────────────────────────────────────┐
│ 9. NEXT INTERACTION                  │
│    └─ Load ready_prompts for fast   │
│       context injection (<100ms)     │
└──────────────────────────────────────┘
```

**Key Transformations**:
1. **Message → Deltas**: LLM converts conversation to metric changes
2. **Deltas → Score**: Weighted formula produces composite score
3. **Conversation → Facts**: Extraction stage creates knowledge graph entries
4. **Facts → Embeddings**: OpenAI generates 1536-dim vectors
5. **Embeddings → Context**: pgVector cosine search retrieves relevant memories
6. **Context → Prompt**: Template injection for next LLM call

---

## 3. LEVERAGE POINTS (Easy to Enhance)

### 3.1 Pipeline Extension Points

**Where**: `nikita/pipeline/stages/`
**Pattern**: Add new stage class inheriting from `PipelineStage`

```python
# Example: Add emotion detection stage
class EmotionDetectionStage(PipelineStage):
    name = "emotion_detection"
    is_critical = False

    async def run(self, context: PipelineContext) -> StageResult:
        # Analyze user's emotional state
        # Update context.user_state
        return StageResult(success=True)

# Register in orchestrator.py STAGE_DEFINITIONS:
("emotion_detection", "nikita.pipeline.stages.emotion.EmotionDetectionStage", False)
```

**Why Easy**:
- Sequential architecture with clear stage boundaries
- Non-critical stages fail gracefully
- Context passed through `PipelineContext` object
- No need to modify existing stages

**What Could Be Added**:
- Personality trait tracking (Big Five, MBTI)
- Sentiment analysis per message
- Topic modeling (cluster conversations)
- User intent classification
- Relationship milestone detection

---

### 3.2 Memory Graph Expansion

**Where**: `nikita/memory/supabase_memory.py`
**Current**: 3 graph types (user, nikita, relationship)
**Extension**: Add new `fact_type` values

```python
# Add new graph type
ALL_GRAPH_TYPES = ["user", "relationship", "nikita", "world", "social"]

# Use it
await memory.add_fact(
    fact="Sarah (user's sister) is getting married next month",
    graph_type="social",  # NEW
    user_id=user_id,
)
```

**Why Easy**:
- `fact_type` is a TEXT column (no enum constraint)
- No schema migration needed
- pgVector search works across all types
- Display logic can filter by type

**What Could Be Added**:
- `world` — External events Nikita reacts to (news, sports)
- `social` — User's social network (family, friends, coworkers)
- `goals` — User's aspirations and progress
- `conflicts` — Unresolved tensions for long-term arcs

---

### 3.3 Vice System Personalization

**Where**: `nikita/engine/vice/`
**Current**: 8 vice categories with intensity tracking
**Data Available**: `user_vice_preferences.engagement_score`

```python
# Underutilized data
SELECT category, engagement_score
FROM user_vice_preferences
WHERE user_id = ?
ORDER BY engagement_score DESC
LIMIT 3;

# Could power:
# - Custom chapter behaviors based on top 3 vices
# - Dynamic prompt injection: "She knows you love dark humor"
# - Boss encounters tailored to user's preferences
```

**Why Easy**:
- Data already collected via `ViceAnalyzer` [nikita/engine/vice/analyzer.py]
- Simple SQL query in prompt builder
- No new LLM calls needed (just template injection)

**What Could Be Added**:
- Vice-specific conversation starters
- Personalized flirting styles
- Custom boss challenges (e.g., "intellectual dominance" boss = debate)
- Vice progression tracking (unlocking deeper topics)

---

### 3.4 Proactive Messaging Scheduling

**Where**: `nikita/db/models/scheduled_event.py`
**Current**: Table exists, TouchpointStage generates events
**Underused**: Only basic "send_message" events

```python
# Rich event payload already supported
CREATE TABLE scheduled_events (
    event_type TEXT,  # send_message, outbound_call, daily_summary
    payload JSONB,    # Can store ANY metadata
    due_at TIMESTAMPTZ
);

# Could add:
{
  "event_type": "memory_nudge",
  "payload": {
    "context": "Last discussed coffee preferences 3 days ago",
    "suggested_opener": "How's that new espresso machine treating you?"
  }
}
```

**Why Easy**:
- Infrastructure already exists (scheduled_events table + pg_cron)
- Just need to add event handlers in `nikita/api/routes/tasks.py`
- No schema changes needed (JSONB payload is flexible)

**What Could Be Added**:
- Birthday/anniversary reminders
- Callback to unfinished conversations
- "Thinking of you" random messages
- Daily check-ins with mood adaptation

---

### 3.5 Admin Portal Expansions

**Where**: `portal/src/app/admin/`
**Current**: 9 admin routes, data already exposed via `/api/v1/admin/*`
**Available Data**: Full user state, pipeline status, prompts, memory facts

**Why Easy**:
- Backend endpoints already exist [nikita/api/routes/admin.py]
- shadcn/ui components in place
- No new database queries needed

**What Could Be Added**:
- Conversation replay UI (like ChatGPT)
- Memory graph visualization (D3.js network graph)
- Vice preference heatmaps
- Pipeline stage performance metrics dashboard
- Boss encounter success rates across all users

---

## 4. CONSTRAINTS (Hard to Change)

### 4.1 Database Schema Changes

**Why Hard**:
- Supabase migrations require downtime
- RLS policies must be updated for new tables
- Foreign key constraints require careful sequencing
- Existing data must be migrated

**Examples of Hard Changes**:
- Splitting `user_metrics` into separate tables
- Changing `relationship_score` from Decimal to Integer
- Adding new foreign keys to existing tables
- Renaming columns (breaks existing queries)

**Migration Pattern** (if necessary):
```sql
-- 1. Add new column (nullable)
ALTER TABLE users ADD COLUMN new_column TEXT;

-- 2. Backfill data
UPDATE users SET new_column = old_column WHERE ...;

-- 3. Make NOT NULL (after backfill)
ALTER TABLE users ALTER COLUMN new_column SET NOT NULL;

-- 4. Drop old column (last step)
ALTER TABLE users DROP COLUMN old_column;
```

---

### 4.2 Claude Model Changes

**Why Hard**:
- Different models have different prompt formats
- Token limits vary (Sonnet 4.5: 200K context, Haiku: 200K)
- Tool calling schemas must match exactly
- Cost implications (Sonnet >> Haiku)

**Current Dependencies**:
```python
# nikita/agents/text/agent.py:35
MODEL_NAME = "anthropic:claude-sonnet-4-5-20250929"

# All prompts tuned for Sonnet 4.5 behavior
# Changing to Opus 4.6 or Haiku would require:
# - Prompt retuning
# - Token budget adjustments
# - Tool call testing
# - Cost analysis
```

**If You Must Change**:
1. Test on dev environment first
2. Run A/B test with feature flag
3. Monitor quality metrics (scoring accuracy, response coherence)
4. Update `DEFAULT_USAGE_LIMITS` [agent.py:43-47]

---

### 4.3 pgVector → Alternative Vector DB

**Why Hard**:
- 1536-dim embeddings stored in Supabase
- Cosine similarity search queries embedded in repository
- No abstraction layer (direct SQL)
- Migration would require:
  - Export all embeddings
  - Rewrite `MemoryFactRepository` [nikita/db/repositories/memory_fact_repository.py]
  - Update all search queries
  - Test deduplication logic

**Current Lock-in**:
```python
# nikita/db/repositories/memory_fact_repository.py:150
# Direct pgVector syntax
.order_by(MemoryFact.embedding.cosine_distance(query_embedding))
```

**Alternative** (if growth demands it):
- Pinecone, Weaviate, Qdrant
- Would need adapter pattern around SupabaseMemory

---

### 4.4 ElevenLabs Voice Agent

**Why Hard**:
- Server Tools pattern is ElevenLabs-specific
- 5 custom tools defined in their dashboard
- Agent IDs per-chapter configured externally
- No open-source alternative with same quality

**Lock-in Points**:
```python
# nikita/agents/voice/server_tools.py
# Tools must match ElevenLabs schema exactly
{
  "name": "get_context",
  "description": "...",
  "parameters": {...}  # Must be JSON Schema
}
```

**Migration Path** (if needed):
1. Could abstract to generic "VoiceProvider" interface
2. Implement ElevenLabsProvider, TwilioProvider, etc.
3. But would lose Conversational AI 2.0 features

---

### 4.5 Serverless Architecture (Cloud Run)

**Why Hard**:
- Cold start times (300-600ms)
- No persistent state between requests
- Must scale to zero (cost constraint)
- Session management requires external store (Supabase)

**Current Optimizations**:
```python
# nikita/agents/text/agent.py:169
@lru_cache(maxsize=1)
def get_nikita_agent():
    # Agent singleton to reduce cold start impact
```

**Migration to Always-On** (if traffic grows):
- Would need to set `--min-instances=1` (breaks guard-deploy.sh rule)
- Or move to GKE/ECS for persistent containers
- Trade-off: $50-200/month minimum vs $0 at scale-to-zero

---

## 5. EXTENSION POINTS (Concrete Implementation Locations)

### 5.1 New Pipeline Stages

**File**: `nikita/pipeline/orchestrator.py:38-49`

```python
# Add to STAGE_DEFINITIONS list
STAGE_DEFINITIONS = [
    # ... existing stages ...
    ("my_new_stage", "nikita.pipeline.stages.my_stage.MyStage", False),
]
```

**Stage Template**:
```python
# nikita/pipeline/stages/my_stage.py
from nikita.pipeline.stages.base import PipelineStage, StageResult
from nikita.pipeline.models import PipelineContext

class MyStage(PipelineStage):
    name = "my_new_stage"
    is_critical = False  # False = failure won't stop pipeline

    async def run(self, context: PipelineContext) -> StageResult:
        # Access user state
        user_id = context.user_id
        conversation = context.conversation

        # Do work...

        # Update context for next stage
        context.custom_data["my_result"] = {...}

        return StageResult(success=True)
```

---

### 5.2 New Database Tables

**Location**: `nikita/db/models/`
**Pattern**: SQLAlchemy ORM + Repository

```python
# 1. Create model: nikita/db/models/my_table.py
class MyTable(Base, TimestampMixin):
    __tablename__ = "my_table"
    id = mapped_column(PG_UUID, primary_key=True)
    user_id = mapped_column(PG_UUID, ForeignKey("users.id"))
    data = mapped_column(JSONB)

# 2. Create repository: nikita/db/repositories/my_repository.py
class MyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: UUID, data: dict):
        obj = MyTable(user_id=user_id, data=data)
        self.session.add(obj)
        await self.session.commit()

# 3. Add migration: Direct SQL via Supabase dashboard
CREATE TABLE my_table (...);
ALTER TABLE my_table ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users see own data" ON my_table ...;
```

---

### 5.3 New API Endpoints

**Location**: `nikita/api/routes/`

```python
# nikita/api/routes/my_route.py
from fastapi import APIRouter, Depends
from nikita.db.repositories.my_repository import MyRepository

router = APIRouter()

@router.get("/my-endpoint/{user_id}")
async def get_my_data(
    user_id: UUID,
    repo: MyRepository = Depends(get_my_repository),
):
    data = await repo.get_by_user(user_id)
    return {"data": data}

# Register in main.py:
from nikita.api.routes import my_route
app.include_router(my_route.router, prefix="/api/v1/my", tags=["My"])
```

---

### 5.4 New Portal Pages

**Location**: `portal/src/app/dashboard/`

```tsx
// portal/src/app/dashboard/my-page/page.tsx
export default function MyPage() {
  // Use existing shadcn components
  return (
    <div className="container">
      <Card>
        <CardHeader>My New Feature</CardHeader>
        <CardContent>
          {/* Fetch from /api/v1/portal/my-endpoint */}
        </CardContent>
      </Card>
    </div>
  );
}
```

---

### 5.5 Missing Portal Data Display

**Available but Not Displayed**:

1. **Memory Facts** — `GET /api/v1/admin/users/{user_id}/memory` exists
   - Could add: `portal/src/app/dashboard/memory/page.tsx`
   - Display: Network graph of user/nikita/relationship facts

2. **Vice Preferences** — `GET /api/v1/admin/users/{user_id}/vices` exists
   - Could add: Radar chart of 8 vice categories

3. **Engagement State** — `GET /api/v1/portal/engagement` exists
   - Could add: Visual FSM diagram (6 states with transitions)

4. **Pipeline Execution Logs** — `GET /api/v1/admin/users/{user_id}/pipeline-history` exists
   - Could add: Timeline view of stage executions

5. **Conversation Prompts** — `GET /api/v1/admin/conversations/{id}/prompts` exists
   - Could add: Side-by-side prompt vs response viewer

---

## 6. ESSENTIAL FILES FOR UNDERSTANDING

**Core Architecture** (Must Read):
1. `/Users/yangsim/Nanoleq/sideProjects/nikita/memory/architecture.md` — System overview
2. `/Users/yangsim/Nanoleq/sideProjects/nikita/nikita/pipeline/orchestrator.py` — 9-stage pipeline
3. `/Users/yangsim/Nanoleq/sideProjects/nikita/nikita/agents/text/agent.py` — Text agent core
4. `/Users/yangsim/Nanoleq/sideProjects/nikita/nikita/db/models/user.py` — Data model
5. `/Users/yangsim/Nanoleq/sideProjects/nikita/nikita/engine/constants.py` — Game mechanics

**Game Logic**:
6. `/Users/yangsim/Nanoleq/sideProjects/nikita/nikita/engine/scoring/calculator.py` — LLM-based scoring
7. `/Users/yangsim/Nanoleq/sideProjects/nikita/nikita/engine/chapters/boss.py` — Boss state machine
8. `/Users/yangsim/Nanoleq/sideProjects/nikita/nikita/engine/decay/calculator.py` — Decay logic

**Memory & Context**:
9. `/Users/yangsim/Nanoleq/sideProjects/nikita/nikita/memory/supabase_memory.py` — pgVector memory
10. `/Users/yangsim/Nanoleq/sideProjects/nikita/nikita/db/repositories/memory_fact_repository.py` — Memory queries

**API Layer**:
11. `/Users/yangsim/Nanoleq/sideProjects/nikita/nikita/api/main.py` — FastAPI app setup
12. `/Users/yangsim/Nanoleq/sideProjects/nikita/nikita/api/routes/telegram.py` — Telegram webhook
13. `/Users/yangsim/Nanoleq/sideProjects/nikita/nikita/api/routes/voice.py` — Voice server tools

**Configuration**:
14. `/Users/yangsim/Nanoleq/sideProjects/nikita/nikita/config/settings.py` — Environment settings
15. `/Users/yangsim/Nanoleq/sideProjects/nikita/nikita/config/elevenlabs.py` — Voice agent config

---

**End of Analysis**

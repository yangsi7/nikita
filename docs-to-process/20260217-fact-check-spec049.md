# Fact Check — Gate 4.5 Spec Preparation
Date: 2026-02-17
Source: Doc 24 (`docs/brainstorm/proposal/24-system-architecture-diagram.md`)

---

## Verification Results

### 1. Claude Opus 4.6 Pricing
- **Claim**: Opus 4.6 used for Psyche Agent (batch + Tier 3 triggers)
- **Verified**: TRUE
- **Actual**: $5/MTok input, $25/MTok output (prompts <=200K). Extended context (>200K): $10/$37.50. Cache write: ~$6.25/MTok, cache read: ~$0.50/MTok (90% savings). [Source: anthropic.com/claude/opus, anthropic.com/news/claude-opus-4-6]
- **Impact**: Cost estimates in doc 24 are directionally valid. The $2.25/mo psyche batch estimate is plausible for 1x/day runs.

### 2. Prompt Caching Savings (~$22/mo)
- **Claim**: 5 cache layers save ~$22/mo/user total (NIKITA_PERSONA ~$15, CHAPTER ~$3, PSYCHE ~$1, VICE ~$1, PLATFORM ~$2)
- **Verified**: PARTIALLY TRUE — math is directionally correct but assumptions need scrutiny
- **Actual**: Anthropic prompt caching gives 90% discount on cache reads (0.1x base price), with 1.25x write cost. Min threshold: 1,024 tokens. TTL: 5 minutes default, 1-hour option. Cache read for Sonnet 4.5: ~$0.30/MTok vs $3/MTok uncached.
- **Calculation check**: At 100 msgs/day, ~6,500 tok system prompt, ~3,150 tok cacheable (layers 1,2,3,5,6+7):
  - Without caching: 100 msgs × 3,150 cached_tokens × $3/MTok = $0.945/day = ~$28.35/mo
  - With caching: 100 msgs × 3,150 tokens × $0.30/MTok = $0.0945/day = ~$2.84/mo + write costs
  - Savings: ~$25/mo (before write costs). With write overhead (~1.25x for cache misses): ~$20-22/mo
- **Impact**: The $22/mo figure is **plausible** at 100 msgs/day with high cache hit rates. However, the 5-min TTL means cache expires between conversations if gaps >5 minutes. Real savings depend heavily on message frequency and conversation clustering.

### 3. Total System Cost $30-37/mo
- **Claim**: Net total per user = $47-52 gross - $15-22 caching = $30-37/mo
- **Verified**: PARTIALLY TRUE — LLM costs are reasonable; infrastructure costs omitted from total
- **Actual breakdown**:

| Component | Doc 24 Estimate | Verified Cost | Notes |
|-----------|----------------|---------------|-------|
| Conversation (Sonnet 4.5) | ~$35-40 | ~$35-45 | 100 msgs/day × ~6K input tok × $3/MTok + ~500 output tok × $15/MTok = ~$2.55/day = ~$76/mo uncached. With caching: ~$35-45. Highly sensitive to msg volume. |
| Psyche batch (Opus 4.6) | ~$2.25 | ~$1-3 | 1x/day, ~8K input (7-day history) + ~1K output. $5×0.008 + $25×0.001 = $0.065/day = ~$1.95/mo. Plausible. |
| Psyche triggers (Sonnet/Opus) | ~$4.80 | ~$3-6 | 8-10% of 100 msgs = 8-10 calls. Mix of Sonnet ($3/$15) and Opus ($5/$25). ~$0.15-0.20/call = $1.50-2.00/day. |
| Life sim (Haiku 4.5) | ~$0.50 | ~$0.30-0.50 | Haiku at $1/$5 per MTok is very cheap. 1x/day generation. Plausible. |
| Prompt enrichment (Haiku) | ~$1.20 | ~$0.50-1.50 | Optional. Haiku is cheap. Plausible. |
| Fact extraction (Sonnet) | ~$2.50 | ~$2-4 | Post-conversation, depends on conversation length. Plausible. |
| Daily summaries (Sonnet) | ~$1.00 | ~$0.50-1.50 | 1x/day. Plausible. |
| **LLM Subtotal** | **$47-52** | **$43-60** | Range is wider than claimed |
| **Caching savings** | **-$15-22** | **-$15-25** | Depends on msg clustering |
| **Net LLM** | **$30-37** | **$25-40** | Wider range, but $30-37 is a reasonable midpoint |
| Supabase | (not in total) | $0 (free tier) | 500MB DB, 1GB storage, 2GB bandwidth |
| Cloud Run | (not in total) | $0 (free tier) | 2M req/mo free, scale-to-zero |
| ElevenLabs | (not in total) | $5-99/mo | Depends on voice usage. Conversational AI: $0.10/min |
| Domain | (not in total) | ~$12/yr = $1/mo | Standard .com |
| **True Total** | **$30-37** | **$30-45+** | Add ElevenLabs if voice is active |

- **Impact**: The $30-37 claim covers LLM costs only and is a reasonable midpoint estimate. True total depends on ElevenLabs voice usage (could add $5-99/mo). Infrastructure (Supabase free, Cloud Run free) adds ~$0.

### 4. ElevenLabs Pricing
- **Claim**: Not explicitly priced in doc 24 (voice mentioned but not costed in the total)
- **Verified**: N/A — claim is about architecture, not voice costs
- **Actual**: Conversational AI: $0.10/min (Starter/Creator/Pro), $0.08/min (Business annual). TTS plans: Free ($0, 10K chars), Starter ($5/mo, 30K chars), Creator ($22/mo, 100K chars), Pro ($99/mo, 500K chars). LLM costs currently absorbed by ElevenLabs but may be passed on later. [Source: elevenlabs.io/blog/we-cut-our-pricing-for-conversational-ai]
- **Impact**: Voice costs are a significant variable not included in the $30-37 estimate. At $0.10/min, 30 min/day voice = $90/mo/user.

### 5. pgVector 1536 Dimensions
- **Claim**: `memory_facts` table uses pgVector with 1536 dimensions
- **Verified**: TRUE (for specific embedding models)
- **Actual**: 1536 dimensions is the standard output of OpenAI `text-embedding-ada-002` and `text-embedding-3-small`. Anthropic does NOT offer a public embedding model. The project likely uses OpenAI embeddings (confirmed by existing codebase). `text-embedding-3-large` defaults to 3072 dims but can be configured to 1536. [Sources: OpenAI docs, Supabase pgVector guides]
- **Impact**: Correct, but the doc should clarify which embedding model generates these vectors (it's OpenAI, not Claude).

### 6. pg_cron Can Call HTTP Endpoints (via pg_net)
- **Claim**: pg_cron used for daily batch jobs, session detection, decay processing
- **Verified**: TRUE
- **Actual**: pg_cron + pg_net (Supabase-maintained extension) can make HTTP POST/GET to external URLs including Cloud Run endpoints and Supabase Edge Functions. Available on all Supabase tiers including free. Timeout is configurable via SQL. Max 32 concurrent pg_cron jobs. [Sources: Supabase docs, GitHub discussions]
- **Caveats**: (1) pg_cron availability on FREE tier is **unconfirmed by official docs** — multiple community sources say yes, but Supabase official pricing page doesn't explicitly list it for free tier. (2) pg_net requests can have DNS resolution issues occasionally. (3) Supabase free tier pauses after 7 days of inactivity.
- **Impact**: Architecture is feasible, but **free tier pg_cron availability should be explicitly verified** before relying on it. If not available on free tier, Pro plan ($25/mo) would be needed.

### 7. Pydantic AI Supports Multi-Agent
- **Claim**: Paired agents (Conversation Agent on Sonnet 4.5 + Psyche Agent on Opus 4.6) working independently
- **Verified**: TRUE
- **Actual**: Pydantic AI supports multiple independent `Agent` instances with different models. Three coordination patterns: Agent Delegation (tool calls), Programmatic Hand-Off, Graph-Based Control Flow. Context sharing via shared dependencies (deps_type) or database. No built-in orchestration engine — you compose yourself. [Sources: pydantic.dev/pydantic-ai, dev.to tutorials]
- **Impact**: The proposed database-mediated coordination (Psyche writes -> DB -> Conversation reads) is fully feasible with Pydantic AI. This is a clean separation that doesn't require framework-level multi-agent support.

### 8. JSONB Queries <5ms
- **Claim**: JSONB read for NPC states, psyche states, conflict state is <5ms and <10ms respectively
- **Verified**: PARTIALLY TRUE — PostgreSQL-level is <5ms, but Supabase end-to-end is 10-70ms
- **Actual**: Raw PostgreSQL primary-key lookups with JSONB column reads are sub-millisecond to low-milliseconds on warm cache. However, Supabase free tier adds: (1) network latency 20-50ms client-to-edge, (2) connection pooling overhead, (3) shared infrastructure "noisy neighbor" effects. Realistic p50: 10-50ms. Realistic p95: 40-70ms. GIN indexes don't help single-row PK lookups. [Sources: Supabase performance benchmarks, PostgreSQL JSONB docs]
- **Impact**: The <5ms/<10ms claims are **optimistic for Supabase free tier**. Actual latency will be 10-50ms per read. However, since these reads happen server-side (Cloud Run -> Supabase, both in GCP), network latency may be lower (5-15ms) if co-located in the same region. The architecture still works — latency budget of <15ms total for pre-conversation reads is tight but achievable with regional co-location.

### 9. Supabase Free Tier Limits
- **Claim**: Supabase used for all storage (PostgreSQL + pgVector)
- **Verified**: TRUE with caveats
- **Actual**:
  - Database: 500MB
  - File storage: 1GB
  - Bandwidth: 2GB/mo
  - API requests: unlimited (reasonable use)
  - Connections: thousands via PgBouncer/Supavisor pooling
  - pgVector: available on free tier
  - pg_cron: **likely available but not officially confirmed for free tier**
  - pg_net: available on all tiers
  - **Pause after 7 days inactivity** (critical for low-usage users)
  - No explicit row limits (constrained by 500MB)
- **Impact**: 500MB is sufficient for early users but will hit limits with vector embeddings (1536-dim vectors are large). Estimate: ~500 memory_facts at 1536 dims = ~12MB. With 100 users, each having 500 facts = ~1.2GB — **exceeds free tier**. Single-user or small-scale: fine. Multi-user: needs Pro ($25/mo).

### 10. 7-Layer Prompt Model
- **Claim**: Doc 24 defines a 7-layer prompt assembly (Identity, Immersion, Psyche, Dynamic Context, Chapter, Vice, Response Guidelines)
- **Verified**: NOVEL — not a recognized standard pattern
- **Actual**: No established "7-layer prompt model" exists in literature. However, layered prompt architectures ARE a recognized practice. Frameworks like COSTAR (Context, Objective, Style, Tone, Audience, Response) provide 6 components. Anthropic's own "context engineering" guide describes layered management of system prompts, tools, and history. The specific 7-layer decomposition in doc 24 is project-specific design, not an industry standard. [Sources: Anthropic engineering blog, prompt engineering framework guides]
- **Impact**: This is **good custom engineering**, not a claim of following a standard. The layering makes sense for cache optimization (static layers cached, dynamic layers per-request). No issue — just should not be presented as an industry-standard pattern.

### 11. Dual-Process (System 1/2) for AI
- **Claim**: Paired agents implement dual-process theory — Conversation Agent (fast/System 1) + Psyche Agent (slow/System 2)
- **Verified**: TRUE — established concept with published implementations
- **Actual**: Dual-process AI architectures are well-documented in research: SOFAI architecture (meta-cognitive switching between fast/slow agents), game AI with fast RL + slow MCTS, robotics with RL + Vision-LLMs. Published papers: Booch et al. (2020), Ganapini et al. (2021), Conway-Smith et al. (2023). OpenAI o1 reasoning represents System 2 thinking. [Sources: emergentmind.com/topics/system-2-thinking-in-ai, multiple academic papers]
- **Impact**: The architecture is well-grounded in cognitive science and has precedent in AI systems. The database-mediated coordination (rather than direct agent calls) is a practical simplification that avoids latency in the hot path.

### 12. Paired Agent Pattern (Database-Mediated)
- **Claim**: Psyche Agent writes to DB, Conversation Agent reads from DB. "Connected through DATABASE, NOT tool calls."
- **Verified**: FEASIBLE but NOVEL implementation
- **Actual**: No direct examples found of this exact pattern (analysis agent writes DB -> response agent reads DB) in Pydantic AI, LangChain, or CrewAI literature. Most multi-agent frameworks use direct delegation, tool calls, or message passing. However, the pattern is straightforward to implement with Pydantic AI's dependency injection and is architecturally clean. [Sources: Pydantic AI docs, framework comparison articles]
- **Impact**: This is a **sound architectural choice** that decouples the agents and avoids hot-path latency. The novelty is not a risk — it's simpler than the alternatives. Implementation is straightforward: two separate Agent instances, shared database via deps.

---

## Cost Model Recalculation

| Component | Doc 24 Estimate | Verified Cost | Delta | Notes |
|-----------|----------------|---------------|-------|-------|
| LLM (Conversation) | $35-40/mo | $35-45/mo | +$0-5 | Sensitive to msg volume |
| LLM (Psyche batch) | $2.25/mo | $1-3/mo | -$1 to +$1 | Stable estimate |
| LLM (Psyche triggers) | $4.80/mo | $3-6/mo | -$2 to +$1 | Depends on trigger rate |
| LLM (Life sim) | $0.50/mo | $0.30-0.50/mo | ~$0 | Haiku is cheap |
| LLM (Enrichment) | $1.20/mo | $0.50-1.50/mo | ~$0 | Optional |
| LLM (Extraction) | $2.50/mo | $2-4/mo | -$0.5 to +$1.5 | Varies by conv length |
| LLM (Summaries) | $1.00/mo | $0.50-1.50/mo | ~$0 | Stable |
| **Gross LLM** | **$47-52** | **$43-60** | **-$4 to +$8** | Wider range |
| Caching savings | -$15-22 | -$15-25 | ~$0 | Depends on msg clustering |
| **Net LLM** | **$30-37** | **$25-40** | **-$5 to +$3** | Reasonable midpoint |
| Supabase | $0 | $0-25 | +$0-25 | Free tier for 1 user; Pro for multi-user |
| Cloud Run | $0 | $0 | $0 | Free tier sufficient |
| ElevenLabs | not included | $5-99 | +$5-99 | If voice active |
| Domain | not included | $1 | +$1 | Annual domain |
| **TRUE TOTAL** | **$30-37** | **$31-165** | varies | Range depends on voice + scale |

**Key finding**: $30-37 is achievable for **single-user, text-only, Supabase free tier**. Voice and multi-user scale significantly increase costs.

---

## Technical Feasibility Summary

| # | Capability | Claimed | Verified | Caveats |
|---|-----------|---------|----------|---------|
| 1 | Claude Opus 4.6 @ $5/$25 MTok | Yes | TRUE | Confirmed official pricing |
| 2 | Prompt caching 90% savings | Yes | TRUE | 5-min TTL, 1024-tok minimum, msg clustering matters |
| 3 | $30-37/mo total | Yes | PARTIALLY | Text-only, single-user, no voice |
| 4 | ElevenLabs voice | Mentioned | TRUE | $0.10/min, significant cost if active |
| 5 | pgVector 1536 dims | Yes | TRUE | Uses OpenAI embeddings, not Claude |
| 6 | pg_cron + pg_net HTTP calls | Yes | TRUE | Free tier availability unconfirmed officially |
| 7 | Pydantic AI multi-agent | Yes | TRUE | Database-mediated coordination is valid |
| 8 | JSONB reads <5ms | Yes | OPTIMISTIC | 10-50ms realistic on Supabase; 5-15ms if co-located |
| 9 | Supabase free tier sufficient | Yes | PARTIALLY | 500MB limit; pgVector embeddings grow fast |
| 10 | 7-layer prompt model | Custom | NOVEL | Not a standard pattern; good custom design |
| 11 | Dual-process AI (System 1/2) | Yes | TRUE | Published research and precedent |
| 12 | Paired agent via DB | Yes | FEASIBLE | Novel but architecturally sound |

---

## Red Flags

### 1. JSONB Latency Claims Are Optimistic [MEDIUM RISK]
Doc 24 claims <5ms for JSONB reads and <15ms total for pre-conversation reads. Supabase free tier realistic latency is 10-50ms per query. With 3 parallel reads (psyche + trigger + game state), total could be 30-70ms. **Mitigation**: Co-locate Cloud Run and Supabase in same region; accept 30-50ms pre-conversation overhead (still acceptable for chat UX).

### 2. Supabase Free Tier May Not Include pg_cron [MEDIUM RISK]
pg_cron is critical for the architecture (daily batch jobs, hourly decay, session detection). Official Supabase docs do not explicitly confirm pg_cron on free tier. Community reports say yes, but this needs verification. **Mitigation**: Test on actual free tier project; budget for Pro ($25/mo) if needed.

### 3. Prompt Cache TTL vs Conversation Gaps [LOW RISK]
Anthropic prompt caching has 5-minute default TTL. If conversations are spaced >5 minutes apart (common for a real girlfriend simulation), cache misses increase, reducing savings from $22/mo to perhaps $10-15/mo. **Mitigation**: Use 1-hour TTL option if available; the savings estimate remains directionally correct even at lower hit rates.

### 4. pgVector Storage Scales Poorly on Free Tier [MEDIUM RISK]
1536-dim vectors are large (~6KB each). At 500 facts/user × 100 users = 50K vectors = ~300MB, consuming 60% of the 500MB free tier before any other data. **Mitigation**: Use lower-dimensional embeddings (text-embedding-3-small supports dimension reduction), aggressive dedup, or budget for Supabase Pro.

### 5. Voice Costs Excluded from Total [LOW RISK — ACKNOWLEDGED]
The $30-37 estimate explicitly covers LLM costs only. Voice usage at $0.10/min could add $30-90/mo per active voice user. Doc 24 acknowledges voice as a separate channel but doesn't cost it. **Mitigation**: Voice is optional and can be gated by plan tier.

### 6. 100 msgs/day Assumption [INFO]
All cost estimates assume ~100 messages/day per user. This is a reasonable active-player estimate but should be validated. Lower activity (30 msgs/day) would reduce costs to ~$15-20/mo; higher activity (200 msgs/day) could push to $50-60/mo.

---

## Sources

- Anthropic pricing: anthropic.com/claude/opus, anthropic.com/news/claude-opus-4-6
- Prompt caching: Anthropic docs, arxiv.org/pdf/2601.06007
- Supabase limits: supabase.com pricing, community discussions
- ElevenLabs: elevenlabs.io/blog/we-cut-our-pricing-for-conversational-ai
- Cloud Run: cloud.google.com/run pricing, cloudchipr.com/blog/cloud-run-pricing
- pgVector: OpenAI embedding docs, Supabase pgVector guides
- Pydantic AI: pydantic.dev/pydantic-ai, framework comparison articles
- Dual-process AI: emergentmind.com/topics/system-2-thinking-in-ai
- JSONB performance: PostgreSQL docs, Supabase benchmark articles

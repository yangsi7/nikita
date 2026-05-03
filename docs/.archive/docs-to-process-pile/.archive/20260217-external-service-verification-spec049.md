# External Service Verification Report -- Spec 049 Gate 4.5 Audit

**Date**: 2026-02-17
**Type**: research
**Confidence**: 92%
**Researcher**: Claude Opus 4.6 (External Service Researcher agent)

## Executive Summary

Six external service claims from the Gate 4.5 audit documents were verified against current (February 2026) official documentation. **Five of six claims are PARTIALLY TRUE with important nuances**, and one (OpenAI embeddings) is TRUE. The most impactful finding is that Anthropic prompt caching minimum token thresholds vary significantly by model (1,024-4,096 tokens, not a flat 1,024), and ElevenLabs Conversational AI pricing has dropped from the claimed $0.10/min to potentially $0.08/min on annual Business plans. No claim was outright FALSE.

## Anchor Sources

1. **Anthropic Prompt Caching Docs** -- https://platform.claude.com/docs/en/build-with-claude/prompt-caching
   - Authority: 10/10 (official). Comprehensive, includes pricing tables, model-specific thresholds, TTL details.
2. **Anthropic Pricing Docs** -- https://platform.claude.com/docs/en/about-claude/pricing
   - Authority: 10/10 (official). Full model pricing matrix including batch, long context, fast mode.

---

## Claim 1: Anthropic Prompt Caching

### Claim
Cache gives 90% discount on reads, 1.25x write cost. Min threshold: 1,024 tokens. TTL: 5 minutes default, 1-hour option. Max 4 cache_control breakpoints.

### Verified: PARTIALLY TRUE

### Current Reality (Feb 2026)

**Pricing multipliers -- CONFIRMED**:
- Cache reads: 0.1x base input price (= 90% discount) -- CORRECT
- 5-minute cache writes: 1.25x base input price -- CORRECT
- 1-hour cache writes: 2x base input price -- CORRECT (not mentioned in claim)

**TTL options -- CONFIRMED**:
- Default: 5 minutes (refreshed on each use at no cost) -- CORRECT
- Extended: 1 hour (at 2x write cost) -- CORRECT

**Max breakpoints -- CONFIRMED**:
- Max 4 cache_control breakpoints per request -- CORRECT

**Min token threshold -- INCORRECT (varies by model)**:
The claim states "Min threshold: 1,024 tokens" but the actual thresholds are model-specific:

| Model | Min Cacheable Tokens |
|-------|---------------------|
| Claude Opus 4.6, Opus 4.5 | **4,096** |
| Claude Sonnet 4.5, Opus 4.1, Opus 4, Sonnet 4, Sonnet 3.7 | **1,024** |
| Claude Haiku 4.5 | **4,096** |
| Claude Haiku 3.5, Haiku 3 | **2,048** |

**New detail not in claim**: Starting Feb 5, 2026, caching uses workspace-level isolation (previously organization-level). The 20-block lookback window for automatic prefix checking is also not mentioned.

### Source
- https://platform.claude.com/docs/en/build-with-claude/prompt-caching (official, current)
- https://platform.claude.com/docs/en/about-claude/pricing (official, current)

### Impact on Specs
The Nikita project uses Claude Opus 4.6. The minimum cacheable threshold is **4,096 tokens** (not 1,024). If the system prompt + tool definitions are under 4,096 tokens, caching will NOT activate. This is a significant implementation detail. Any cost projections using the 1,024 threshold for Opus models are incorrect.

---

## Claim 2: Claude Model Pricing (Feb 2026)

### Claim
- Opus 4.6: $5/MTok input, $25/MTok output
- Sonnet 4.5: $3/MTok input, $15/MTok output
- Haiku 4.5: $1/MTok input, $5/MTok output

### Verified: TRUE

### Current Reality (Feb 2026)

| Model | Input | Output | Batch Input | Batch Output |
|-------|-------|--------|-------------|--------------|
| Claude Opus 4.6 | $5/MTok | $25/MTok | $2.50/MTok | $12.50/MTok |
| Claude Opus 4.5 | $5/MTok | $25/MTok | $2.50/MTok | $12.50/MTok |
| Claude Sonnet 4.5 | $3/MTok | $15/MTok | $1.50/MTok | $7.50/MTok |
| Claude Haiku 4.5 | $1/MTok | $5/MTok | $0.50/MTok | $2.50/MTok |

**Additional pricing tiers not in original claim**:
- **Fast Mode** (Opus 4.6 only): $30/MTok input, $150/MTok output (6x standard)
- **Long Context** (>200K tokens): Opus 4.6 at $10 input / $37.50 output; Sonnet 4.5 at $6 input / $22.50 output
- **Batch API**: 50% discount on all models (input and output)
- **Data Residency** (US-only inference): 1.1x multiplier on all token categories

### Source
- https://platform.claude.com/docs/en/about-claude/pricing (official, current)

### Impact on Specs
Base pricing is confirmed correct. The Batch API 50% discount and long context pricing may be relevant for batch processing workloads. Fast mode pricing ($30/$150 per MTok) is 6x standard -- relevant if fast mode is ever considered for the pipeline.

---

## Claim 3: Pydantic AI Multi-Agent Support

### Claim
Supports multiple independent Agent instances with different models. Three coordination patterns: Agent Delegation (tool calls), Programmatic Hand-Off, Graph-Based Control Flow. Database-mediated coordination is valid.

### Verified: PARTIALLY TRUE (expanded since claim was written)

### Current Reality (Feb 2026)

Pydantic AI now documents **four** coordination patterns (not three):

1. **Agent Delegation** -- One agent calls another agent via tool calls. Different models per agent supported. UsageLimits available to prevent runaway costs. -- CONFIRMED
2. **Programmatic Hand-Off** -- Multiple agents called in succession by application code. Human-in-the-loop supported. Agents don't need same deps. -- CONFIRMED
3. **Graph-Based Control Flow** -- State machine approach using type hints for complex multi-agent orchestration. -- CONFIRMED
4. **Deep Agents** (NEW) -- Autonomous agents combining planning, file operations, subagent delegation, and sandboxed code execution. This pattern was not in the original claim.

**Database-mediated coordination**: NOT explicitly documented in Pydantic AI docs. However, the Programmatic Hand-Off pattern inherently supports database-mediated coordination because the application code between agent calls can read/write to any database. The framework is agnostic to how state is shared -- it just passes `message_history` and custom `deps` between runs.

Additionally, Pydantic AI now supports the **A2A (Agent-to-Agent) Protocol** for inter-agent communication, though this is a separate protocol layer.

### Source
- https://ai.pydantic.dev/multi-agent-applications/ (official docs)
- https://github.com/pydantic/pydantic-ai/blob/main/docs/multi-agent-applications.md (source)

### Impact on Specs
The claim is valid. The Nikita project's "paired agent via database" pattern (text agent + voice agent sharing state via Supabase) is architecturally sound and aligns with the Programmatic Hand-Off pattern. The new Deep Agents pattern could be relevant for future agentic features. No changes needed.

---

## Claim 4: Supabase Free Tier pg_cron Availability

### Claim
pg_cron is "likely available but not officially confirmed for free tier." The project already has 6 active pg_cron jobs.

### Verified: TRUE (confirmed available, not just "likely")

### Current Reality (Feb 2026)

**pg_cron IS available on the Supabase free tier.** This was confirmed by a Supabase collaborator (GaryAustin1) in a GitHub Discussion:

> "Cron is only limited by the resources it uses CPU/Memory/Disk wise on any tier."

Key details:
- **No tier-specific restrictions** -- pg_cron works on Free, Pro, and Enterprise
- **Resource-limited, not feature-gated** -- CPU/memory/disk are the constraints
- **Recommended max**: 8 concurrent jobs for best performance (official docs)
- **Max job duration**: 10 minutes per job (recommended)
- **Scheduling range**: Every second to once a year
- **Important maintenance**: The `cron.job_run_details` table grows rapidly with frequent jobs; needs periodic cleanup
- **Free tier caveat**: Projects inactive for 7 days get paused, but pg_cron jobs themselves count as activity

### Source
- https://supabase.com/docs/guides/cron (official docs)
- https://supabase.com/docs/guides/database/extensions/pg_cron (extension docs)
- https://github.com/orgs/supabase/discussions/37405 (community confirmation from Supabase collaborator)

### Impact on Specs
The claim was overly cautious. pg_cron IS confirmed on free tier. The project's 6 active jobs are well within the recommended 8 concurrent limit. The main risk is the `cron.job_run_details` table bloat -- ensure periodic cleanup is implemented. No spec changes needed, but documentation should be updated from "likely available" to "confirmed available."

---

## Claim 5: ElevenLabs Conversational AI Pricing

### Claim
Conversational AI costs $0.10/min. TTS plans range from Free ($0) to Pro ($99/mo).

### Verified: PARTIALLY TRUE (pricing has changed)

### Current Reality (Feb 2026)

**Conversational AI per-minute pricing**:
- Starter/Creator/Pro plans: ~$0.10/min (reduced ~50% from earlier rates in Feb 2025)
- Annual Business plan: **$0.08/min**
- Enterprise: custom (lower than $0.08)

**Important caveat**: These prices do NOT include LLM costs. ElevenLabs is currently absorbing LLM costs but has stated they will eventually pass those costs through to users.

**Plan tiers** (updated structure):
- **Free**: $0/mo -- 20 minutes included
- **Starter**: $5/mo (was higher)
- **Creator**: $22/mo
- **Pro**: $99/mo -- CONFIRMED
- **Scale**: $330/mo
- **Business**: $1,320/mo -- 13,750 minutes Conversational AI

**Credit system**: ElevenLabs uses a credit system where 10,000 credits = ~15 minutes of Conversational AI agent time.

**Overage rates**: Range from $0.06-$0.15/min depending on plan tier. Business plan overage is consistent at $0.08/min.

**Rebranding**: "Conversational AI" has been rebranded to "ElevenLabs Agents" (formerly ElevenAgents).

### Source
- https://elevenlabs.io/pricing (official, current -- CSS-heavy, limited data extraction)
- https://help.elevenlabs.io/hc/en-us/articles/29298065878929 (support article)
- https://elevenlabs.io/blog/we-cut-our-pricing-for-conversational-ai (blog announcement)
- https://flexprice.io/blog/elevenlabs-pricing-breakdown (third-party breakdown)

### Impact on Specs
The $0.10/min claim is approximately correct for standard plans but could be as low as $0.08/min on Business annual. The hidden LLM cost absorption is a future risk -- when ElevenLabs stops absorbing LLM costs, the effective per-minute rate could increase significantly. Cost projections should include a buffer for this. The Pro plan at $99/mo is confirmed correct.

---

## Claim 6: OpenAI Embedding Dimensions

### Claim
text-embedding-3-small outputs 1536 dimensions. text-embedding-ada-002 also outputs 1536.

### Verified: TRUE

### Current Reality (Feb 2026)

| Model | Native Dimensions | Reduced Dimensions (MRL) | Pricing |
|-------|------------------|--------------------------|---------|
| text-embedding-3-small | **1,536** | 512 | $0.02/MTok |
| text-embedding-3-large | **3,072** | 256, 1,024 | $0.13/MTok |
| text-embedding-ada-002 | **1,536** | Not supported | $0.10/MTok |

**Key details**:
- Both text-embedding-3-small and ada-002 output **1,536 dimensions** -- CONFIRMED
- text-embedding-3-small is 5x cheaper than ada-002 ($0.02 vs $0.10 per MTok)
- text-embedding-3-small outperforms ada-002 on benchmarks (MIRACL: 44.0% vs 31.4%)
- **Matryoshka Representation Learning (MRL)**: text-embedding-3-* models support dimension reduction via the `dimensions` API parameter. A 256-dim text-embedding-3-large outperforms a full 1,536-dim ada-002
- Batch API pricing: $0.01/MTok for text-embedding-3-small (50% discount)

### Source
- https://platform.openai.com/docs/models/text-embedding-3-small (official)
- https://openai.com/index/new-embedding-models-and-api-updates/ (official blog)
- https://www.pinecone.io/learn/openai-embeddings-v3/ (Pinecone guide)

### Impact on Specs
Claim is fully correct. The Nikita project uses text-embedding-3-small with 1,536 dimensions for pgVector. No changes needed. However, the MRL dimension reduction capability is worth noting -- if storage costs become a concern, embeddings could be reduced to 512 dimensions with minimal quality loss.

---

## Summary Table

| # | Service | Claim Status | Key Discrepancy | Impact | Action Needed |
|---|---------|-------------|-----------------|--------|---------------|
| 1 | Anthropic Prompt Caching | PARTIALLY TRUE | Min threshold is 4,096 for Opus 4.6 (not 1,024) | HIGH | Update spec: Opus uses 4,096 min threshold |
| 2 | Claude Model Pricing | TRUE | None (batch/fast/long context pricing not mentioned) | LOW | Informational: batch 50% discount available |
| 3 | Pydantic AI Multi-Agent | PARTIALLY TRUE | 4 patterns now (Deep Agents added), DB-mediated not explicit but feasible | LOW | No changes; architecture is sound |
| 4 | Supabase pg_cron Free Tier | TRUE | Confirmed available (was "likely") | LOW | Update docs: confirmed, not "likely" |
| 5 | ElevenLabs Conv AI Pricing | PARTIALLY TRUE | $0.08-0.10/min range; LLM costs absorbed temporarily | MEDIUM | Add cost buffer for future LLM pass-through |
| 6 | OpenAI Embedding Dimensions | TRUE | None | NONE | No action needed |

## Knowledge Gaps

1. **ElevenLabs exact overage rates per tier**: The pricing page is CSS-heavy and resists scraping. The exact per-tier overage breakdown could not be fully verified from official sources.
2. **Supabase pg_cron maximum jobs hard limit**: The docs recommend 8 concurrent, but no hard limit is documented. The project's 6 jobs are safe.
3. **Anthropic workspace-level cache isolation**: New as of Feb 5, 2026. If the project uses multiple workspaces, caching strategy needs review.

## Recommendations

1. **HIGH PRIORITY**: Update any cost modeling that assumes 1,024-token minimum for Opus 4.6 prompt caching. The actual minimum is 4,096 tokens. Verify the system prompt + tools exceed this threshold.
2. **MEDIUM PRIORITY**: Add a cost buffer (20-30%) to ElevenLabs Conversational AI projections for when LLM costs stop being absorbed.
3. **LOW PRIORITY**: Update Supabase pg_cron documentation from "likely available" to "confirmed available on all tiers."
4. **LOW PRIORITY**: Consider Batch API (50% discount) for any non-real-time Claude workloads.

---

## Source Index

| # | Title | URL | Authority | Recency | Key Contribution |
|---|-------|-----|-----------|---------|------------------|
| 1 | Anthropic Prompt Caching Docs | https://platform.claude.com/docs/en/build-with-claude/prompt-caching | 10 | 2026 | Anchor -- min thresholds, TTL, breakpoints |
| 2 | Anthropic Pricing Docs | https://platform.claude.com/docs/en/about-claude/pricing | 10 | 2026 | Anchor -- full pricing matrix all models |
| 3 | Pydantic AI Multi-Agent Docs | https://ai.pydantic.dev/multi-agent-applications/ | 10 | 2025 | All 4 coordination patterns |
| 4 | Pydantic AI GitHub Source | https://github.com/pydantic/pydantic-ai/blob/main/docs/multi-agent-applications.md | 10 | 2025 | Programmatic hand-off code examples |
| 5 | Supabase Cron Docs | https://supabase.com/docs/guides/cron | 10 | 2025 | pg_cron capabilities and recommendations |
| 6 | Supabase pg_cron Extension Docs | https://supabase.com/docs/guides/database/extensions/pg_cron | 10 | 2025 | Extension-level details |
| 7 | Supabase pg_cron Discussion #37405 | https://github.com/orgs/supabase/discussions/37405 | 8 | 2025 | Free tier confirmation from staff |
| 8 | ElevenLabs Help: Agent Costs | https://help.elevenlabs.io/hc/en-us/articles/29298065878929 | 9 | 2025 | Per-minute pricing details |
| 9 | ElevenLabs Pricing Cut Blog | https://elevenlabs.io/blog/we-cut-our-pricing-for-conversational-ai | 8 | 2025 | ~50% price reduction announcement |
| 10 | Flexprice ElevenLabs Breakdown | https://flexprice.io/blog/elevenlabs-pricing-breakdown | 6 | 2026 | Third-party pricing analysis |
| 11 | OpenAI text-embedding-3-small Docs | https://platform.openai.com/docs/models/text-embedding-3-small | 10 | 2026 | Official model specs |
| 12 | OpenAI Embedding Models Blog | https://openai.com/index/new-embedding-models-and-api-updates/ | 10 | 2024 | MRL support, dimension details |
| 13 | Pinecone OpenAI Embeddings v3 Guide | https://www.pinecone.io/learn/openai-embeddings-v3/ | 8 | 2024 | Detailed MRL dimension comparison |
| 14 | SaaSworthy ElevenLabs Pricing | https://www.saasworthy.com/product/elevenlabs-io/pricing | 5 | 2026 | Cross-reference for plan tiers |
| 15 | Costgoat Claude API Calculator | https://costgoat.com/pricing/claude-api | 5 | 2026 | Cross-reference for pricing |

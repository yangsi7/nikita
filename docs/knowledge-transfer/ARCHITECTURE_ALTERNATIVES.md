# Architecture Alternatives

```yaml
context_priority: medium
audience: ai_agents
last_updated: 2026-02-03
related_docs:
  - CONTEXT_ENGINE.md
  - ANTI_PATTERNS.md
  - PROJECT_OVERVIEW.md
```

## Overview

This document captures research findings on alternative architectures, technologies, and approaches that were evaluated or could be considered for future development.

---

## Memory System Alternatives

### Current: Graphiti + Neo4j Aura

**Pros**:
- Temporal knowledge graphs with automatic entity extraction
- Relationship modeling between facts
- Semantic search capabilities

**Cons**:
- 30-60s cold start on free tier
- Complex query patterns
- Learning curve for graph thinking
- Retrieval quality inconsistent

### Alternative 1: RAG with Vector Database

**Option**: pgVector (already in Supabase) or Pinecone

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RAG ARCHITECTURE                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                    │
│  │  Messages   │───▶│  Chunker    │───▶│  Embedder   │                    │
│  └─────────────┘    └─────────────┘    └──────┬──────┘                    │
│                                               │                            │
│                                               ▼                            │
│                                      ┌─────────────────┐                  │
│                                      │  Vector Store   │                  │
│                                      │  (pgVector)     │                  │
│                                      └────────┬────────┘                  │
│                                               │                            │
│  ┌─────────────┐                             │                            │
│  │   Query     │─────────────────────────────┘                            │
│  └──────┬──────┘                                                          │
│         │                                                                  │
│         ▼                                                                  │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐       │
│  │ Semantic Search │───▶│   Reranker      │───▶│   Context       │       │
│  │  (k-NN)         │    │   (optional)    │    │   Assembly      │       │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Pros**:
- Already have pgVector in Supabase
- Simpler mental model
- Faster retrieval (~100ms)
- No cold start issues

**Cons**:
- Loses relationship modeling
- No automatic entity extraction
- Manual chunking strategies needed

**Evaluation Score**: 7/10 - Simpler but less powerful

### Alternative 2: Hybrid (RAG + Structured Facts)

**Option**: pgVector for retrieval + Supabase tables for structured facts

```python
# Structured facts table
class UserFact(Base):
    id = Column(UUID, primary_key=True)
    user_id = Column(UUID, ForeignKey("users.id"))
    category = Column(String)  # personal, preference, relationship
    fact = Column(Text)
    confidence = Column(Float)
    source = Column(String)  # conversation, voice, inferred
    embedding = Column(Vector(1536))  # For similarity search
    created_at = Column(DateTime)
    last_referenced = Column(DateTime)
```

**Pros**:
- Combines structured + unstructured
- Fast retrieval from single database
- Explicit fact management
- No external dependencies

**Cons**:
- Manual fact extraction needed
- More schema management

**Evaluation Score**: 8/10 - Best balance

### Alternative 3: LangGraph Memory

**Option**: LangChain's memory abstractions

**Pros**:
- Pre-built memory patterns
- Active development
- Good documentation

**Cons**:
- Another framework dependency
- May not fit custom needs
- Abstraction overhead

**Evaluation Score**: 5/10 - Too opinionated

### RECOMMENDATION

**Short-term**: Keep Graphiti but add caching layer
**Medium-term**: Evaluate hybrid approach with pgVector
**Long-term**: Consider building custom fact store

---

## Agent Framework Alternatives

### Current: Pydantic AI

**Pros**:
- Type-safe with Pydantic
- Clean API
- Good Claude support

**Cons**:
- Relatively new
- Smaller community
- Limited tooling

### Alternative 1: LangChain

**Pros**:
- Largest ecosystem
- Many integrations
- Active development

**Cons**:
- Abstraction overhead
- Frequent breaking changes
- Complex for simple use cases

**Evaluation Score**: 6/10 - Overkill for current needs

### Alternative 2: OpenAI Agents SDK

**Pros**:
- Official support
- Production-ready
- Good documentation

**Cons**:
- OpenAI-focused (not Claude)
- Vendor lock-in potential

**Evaluation Score**: 4/10 - Wrong vendor

### Alternative 3: Marvin

**Pros**:
- Lightweight
- Pythonic
- Good for extraction

**Cons**:
- Less mature
- Limited features

**Evaluation Score**: 6/10 - Could complement Pydantic AI

### Alternative 4: Claude Agent SDK (Anthropic)

**Status**: Announced but limited availability

**Potential**:
- Native Claude support
- Anthropic-backed
- Computer use capabilities

**Evaluation Score**: TBD - Watch for release

### RECOMMENDATION

**Keep Pydantic AI** - Good fit, stable, type-safe

---

## Voice Platform Alternatives

### Current: ElevenLabs Conversational AI

**Pros**:
- High-quality voices
- Built-in conversation handling
- Server tools for context

**Cons**:
- Limited customization
- 2s timeout on tools
- External context management

### Alternative 1: Twilio + Custom Voice

**Architecture**:
```
Phone → Twilio → Speech-to-Text → Claude → Text-to-Speech → Twilio → Phone
```

**Pros**:
- Full control
- Use any LLM
- Custom latency tuning

**Cons**:
- More infrastructure
- Latency management
- Voice quality varies

**Evaluation Score**: 6/10 - More control, more work

### Alternative 2: Vapi

**Pros**:
- Similar to ElevenLabs
- Multiple voice options
- Good API

**Cons**:
- Smaller company
- Less mature

**Evaluation Score**: 6/10 - Comparable option

### Alternative 3: Retell AI

**Pros**:
- Enterprise-focused
- Good latency
- Custom voices

**Cons**:
- Higher cost
- Less flexible

**Evaluation Score**: 5/10 - Enterprise play

### RECOMMENDATION

**Keep ElevenLabs** but address context gap:
1. Pre-compute context and cache
2. Use webhook for async updates
3. Accept 2s limitation for tools

---

## Database Alternatives

### Current: Supabase (PostgreSQL)

**Pros**:
- Free tier generous
- Built-in auth
- RLS for security
- pgVector included

**Cons**:
- Vendor lock-in
- Limited observability

### Alternative 1: Self-hosted PostgreSQL

**Pros**:
- Full control
- No vendor lock-in
- Cost predictable

**Cons**:
- More ops work
- Backup responsibility
- No built-in auth

**Evaluation Score**: 5/10 - More work, less benefit

### Alternative 2: PlanetScale (MySQL)

**Pros**:
- Great developer experience
- Branching for schema changes
- Generous free tier

**Cons**:
- MySQL not PostgreSQL
- No pgVector equivalent
- Different ecosystem

**Evaluation Score**: 4/10 - Too different

### Alternative 3: Neon (PostgreSQL)

**Pros**:
- Serverless Postgres
- Branching
- Good free tier

**Cons**:
- Newer service
- Less ecosystem

**Evaluation Score**: 7/10 - Good alternative if Supabase issues

### RECOMMENDATION

**Keep Supabase** - Good fit, integrated auth, pgVector

---

## Compute Alternatives

### Current: Google Cloud Run

**Pros**:
- Scales to zero
- Pay per request
- Easy deployment
- Good cold start

**Cons**:
- 300s max timeout
- Vendor lock-in

### Alternative 1: AWS Lambda + API Gateway

**Pros**:
- Massive ecosystem
- Fine-grained pricing

**Cons**:
- Cold starts worse
- More configuration
- 29s timeout (API Gateway)

**Evaluation Score**: 5/10 - Timeout too short

### Alternative 2: Fly.io

**Pros**:
- Great developer experience
- Global edge
- Docker-native

**Cons**:
- Smaller ecosystem
- Less enterprise features

**Evaluation Score**: 7/10 - Good alternative

### Alternative 3: Railway

**Pros**:
- Simple deployment
- Good pricing
- Nice UI

**Cons**:
- Less mature
- Limited features

**Evaluation Score**: 6/10 - Simpler but less powerful

### RECOMMENDATION

**Keep Cloud Run** - Good balance of features and cost

---

## LLM Alternatives

### Current: Claude Sonnet 4.5

**Pros**:
- Best instruction following
- Good at conversation
- Reasonable cost

**Cons**:
- API availability varies
- Rate limits

### Alternative 1: GPT-4o

**Pros**:
- Widely available
- Fast
- Good ecosystem

**Cons**:
- Less personality
- Different prompt patterns

**Evaluation Score**: 7/10 - Good backup

### Alternative 2: Gemini 2.0

**Pros**:
- Multimodal
- Fast
- Good pricing

**Cons**:
- Different behavior
- Less tested for persona

**Evaluation Score**: 6/10 - Watch development

### Alternative 3: Llama 3 (Self-hosted)

**Pros**:
- No API costs
- Full control
- Privacy

**Cons**:
- Significant infrastructure
- Quality gap
- Maintenance burden

**Evaluation Score**: 4/10 - Too much overhead

### RECOMMENDATION

**Keep Claude** - Best fit for personality simulation

---

## Context Engine Alternatives

### Current: Custom 8-collector system

**Pros**:
- Tailored to needs
- Full control
- Typed outputs

**Cons**:
- Custom maintenance
- Complexity
- Voice parity gap

### Alternative 1: Pre-computed Context Snapshots

**Architecture**:
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PRE-COMPUTED CONTEXT                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Background Job (every 5 min):                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  For each active user:                                               │  │
│  │  1. Run all 8 collectors                                             │  │
│  │  2. Assemble ContextPackage                                          │  │
│  │  3. Store in Redis: context:{user_id} → JSON                        │  │
│  │  4. TTL: 10 minutes                                                  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  Request Time:                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  1. Get context from Redis (< 10ms)                                  │  │
│  │  2. If miss: compute on-demand + cache                              │  │
│  │  3. Add real-time data (message, timestamp)                         │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Pros**:
- Fast retrieval (< 10ms)
- Voice and text parity
- Reduced timeout issues

**Cons**:
- Stale data (up to 5 min)
- Redis dependency
- Background job complexity

**Evaluation Score**: 8/10 - Best for voice parity

### Alternative 2: Tiered Collection

**Architecture**:
```
Tier 1 (Always): User profile, metrics, chapter (< 100ms)
Tier 2 (If time): Memory, threads, summaries (< 2s)
Tier 3 (If time): Full humanization, social (< 5s)
```

**Pros**:
- Graceful degradation
- Works with voice timeout
- No extra infrastructure

**Cons**:
- Variable context quality
- Complex tier logic

**Evaluation Score**: 7/10 - Good middle ground

### RECOMMENDATION

**Implement pre-computed snapshots** for voice parity

---

## Summary Decision Matrix

| Area | Current | Best Alternative | Action |
|------|---------|------------------|--------|
| Memory | Graphiti | Hybrid (pgVector + facts) | Evaluate Q2 |
| Agent | Pydantic AI | Keep | No change |
| Voice | ElevenLabs | Keep + context caching | Implement Q1 |
| Database | Supabase | Keep | No change |
| Compute | Cloud Run | Keep | No change |
| LLM | Claude Sonnet | Keep (GPT-4o backup) | Monitor |
| Context | Custom | Pre-computed snapshots | Implement Q1 |

---

## Future Research Areas

1. **Voice-Text Unification** - Single context engine for both
2. **Real-time Memory** - Streaming fact extraction
3. **Personalization ML** - Learn optimal context per user
4. **Cost Optimization** - Prompt caching, batching

---

## Related Documentation

- **Current Context Engine**: [CONTEXT_ENGINE.md](CONTEXT_ENGINE.md)
- **Anti-Patterns**: [ANTI_PATTERNS.md](ANTI_PATTERNS.md)
- **Voice Implementation**: [VOICE_IMPLEMENTATION.md](VOICE_IMPLEMENTATION.md)

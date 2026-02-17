# Context Engineering Review — Gate 4.5

Date: 2026-02-17
Agent: context-engineer
Sources: Wave 1 outputs (researcher, pipeline-analyst, engine-analyst), doc 24, system_prompt.j2, prompt_builder.py, agent.py, persona.py

---

## 1. Information Flow Map

```
COMPLETE INFORMATION FLOW: User Message → Response
=====================================================

[A] USER MESSAGE (Telegram / Voice / Portal)
     |
     v
[B] MESSAGE HANDLER (message_handler.py:129)
     ├─ Auth: user_repository.get_by_telegram_id()        :155
     ├─ Profile gate: _needs_onboarding()                  :170
     ├─ Boss fight gate: _handle_boss_response()           :179
     ├─ Game over/won gate: _send_game_status_response()   :187
     ├─ Rate limit: rate_limiter.check()                   :196
     ├─ Conversation: _get_or_create_conversation()        :204
     └─ Append user message to conversation                :211
          |
          v
[C] TEXT AGENT HANDLER (handler.py:220)
     └─ generate_response(deps, message) → agent.py:368
          |
          ├─ [C1] SYSTEM PROMPT ASSEMBLY
          │    ├─ _try_load_ready_prompt(user_id)          agent.py:202
          │    │   └─ ReadyPromptRepository.get_current()
          │    │       └─ Source: ready_prompts table (PRE-BUILT by pipeline S9)
          │    │
          │    ├─ NIKITA_PERSONA (static, ~1600 tok)       persona.py:18
          │    │   └─ Injected as Agent(instructions=...)   agent.py:75
          │    │
          │    ├─ @agent.instructions: chapter_behavior     agent.py:80
          │    │   └─ CHAPTER_BEHAVIORS[user.chapter]
          │    │
          │    └─ @agent.instructions: personalized_ctx     agent.py:88
          │        └─ deps.generated_prompt (from ready_prompts)
          │
          ├─ [C2] MESSAGE HISTORY
          │    └─ load_message_history()                    agent.py:368
          │        ├─ conversation.messages (last 80 turns)
          │        └─ token_budget=3000
          │
          └─ [C3] AGENT INVOCATION
               └─ nikita_agent.run(user_message, deps, history, limits)
                    ├─ Model: Sonnet 4.5
                    ├─ System: NIKITA_PERSONA + chapter + personalized_ctx
                    ├─ Tools: recall_memory(), note_user_fact()
                    └─ Output: Nikita's text response
          |
          v
[D] POST-RESPONSE PROCESSING (synchronous)
     ├─ ScoringService.score_interaction()                 :274
     ├─ EngagementStateMachine.update()
     ├─ Boss threshold check → may trigger boss
     ├─ TextPatterns: emoji, length                        :288
     └─ ResponseDelivery.queue()                           :305
          |
          v
[E] SESSION END (15-min inactivity, pg_cron detection)
     |
     v
[F] POST-CONVERSATION PIPELINE (9 stages, sequential)
     ├─ S1: EXTRACTION         → facts, threads, thoughts, tone
     ├─ S2: MEMORY UPDATE      → pgVector writes (dedup)
     ├─ S3: LIFE SIM           → daily events
     ├─ S4: EMOTIONAL          → 4D state update
     ├─ S5: GAME STATE         → scores, chapters, decay
     ├─ S6: CONFLICT           → trigger evaluation
     ├─ S7: TOUCHPOINT         → proactive message scheduling
     ├─ S8: SUMMARY            → daily conversation summaries
     └─ S9: PROMPT BUILDER     → pre-build NEXT system prompt
          ├─ _enrich_context()         prompt_builder.py:102
          │   ├─ compute nikita state (activity, mood, energy, vulnerability)
          │   ├─ load conversation summaries (last, today, week)
          │   ├─ load user data + hours_since_last
          │   ├─ load memory episodes (relationship + nikita facts)
          │   └─ populate open_threads
          ├─ _build_template_vars()    prompt_builder.py:276 (35+ keys)
          ├─ render system_prompt.j2   (11 sections, 731 lines)
          ├─ optional Haiku enrichment
          ├─ enforce token budget (truncate Vice → Chapter → Psych)
          └─ store in ready_prompts table
```

### Key Insight: Two Prompt Assembly Paths

```
PATH 1 — UNIFIED PIPELINE (current default when pipeline has run):
  ready_prompts table → agent.py:202 → deps.generated_prompt
    → @agent.instructions: personalized_ctx returns FULL prompt
    → NIKITA_PERSONA still injected as base instructions (ALWAYS)
    → chapter_behavior ALSO injected (ALWAYS)
  RESULT: NIKITA_PERSONA + chapter_behavior + FULL pipeline prompt
  PROBLEM: Triple-stacking. NIKITA_PERSONA (~1600 tok) + pipeline prompt (~5500 tok)
           = ~7100 tok system prompt BEFORE message history

PATH 2 — LEGACY FALLBACK (first conversation or pipeline failure):
  No ready_prompt → agent.py:103 returns ""
    → Only NIKITA_PERSONA + chapter_behavior
  RESULT: ~2000 tok system prompt (lean but missing all context)
```

**Critical finding**: When unified pipeline IS enabled, the agent receives NIKITA_PERSONA (persona.py) + chapter_behavior + the full pipeline-generated prompt which ALSO includes identity (S1), chapter behavior (S10), and response guidelines (footer). This creates **redundant content** — identity is stated twice with CONFLICTING backstories, and chapter behavior is injected twice.

---

## 2. Template Section → Layer Mapping

| # | Current Section | Template Lines | Token Est | Doc 24 Layer | Mapping Quality | Changes Needed |
|---|----------------|---------------|-----------|-------------|----------------|----------------|
| 1 | IDENTITY | j2:1-35 | ~400 | L1: IDENTITY (~2K) | PARTIAL | Template S1 (400 tok) is SUBSET of doc 24 L1 (2K). NIKITA_PERSONA (persona.py, ~1600 tok) fills the gap but has DIFFERENT backstory. Must consolidate into single L1 block |
| 2 | IMMERSION RULES | j2:37-49 | ~200 | L2: IMMERSION+PLATFORM | MATCH | Rename. Combine with S3 |
| 3 | PLATFORM STYLE | j2:51-119 | ~300 | L2: IMMERSION+PLATFORM | MATCH | Merge with S2 into single L2 block (~500 tok) |
| — | **PSYCHE STATE** | **DOES NOT EXIST** | **~150** | **L3: PSYCHE STATE** | **GAP** | **New section. Inject between L2 and L4. Source: psyche_states table JSONB** |
| 4 | CURRENT STATE | j2:122-155 | ~600 | L4a: Dynamic Context | MATCH | Becomes L4 sub-section 4a |
| 5 | RELATIONSHIP STATE | j2:157-175 | ~500 | L4b: Dynamic Context | MATCH | Becomes L4 sub-section 4b |
| 6 | MEMORY | j2:178-267 | ~800/300 | L4c: Dynamic Context | MATCH | Becomes L4 sub-section 4c |
| 7 | CONTINUITY | j2:269-310 | ~600 | L4d: Dynamic Context | MATCH | Becomes L4 sub-section 4d |
| 8 | INNER LIFE | j2:312-357 | ~500 | L4e: Dynamic Context | MATCH | Becomes L4 sub-section 4e |
| 9 | PSYCHOLOGICAL DEPTH | j2:359-416 | ~400 | **UNMAPPED** | CONFLICT | Doc 24 has no explicit L for this. Options: (A) fold into L3 psyche state, (B) keep as L4f. See Section 7 |
| 10 | CHAPTER BEHAVIOR | j2:418-594 | ~300 | L5: CHAPTER BEHAVIOR | MATCH | Rename only |
| 11 | VICE SHAPING | j2:597-624 | ~200 | L6: VICE SHAPING | MATCH | Rename only |
| — | FOOTER | j2:627-731 | ~700 | L7: RESPONSE GUIDELINES | MATCH | Rename. Voice gets shortened footer (j2:630-638) |

### Validation of Pipeline-Analyst Claim

Pipeline-analyst stated: "7 of 7 layers map to existing sections, only L3 (Psyche State) is genuinely new."

**VALIDATED with nuances:**
- 6 of 7 layers map cleanly (L1, L2, L4, L5, L6, L7)
- L3 (Psyche State) is genuinely new — confirmed GAP
- L1 mapping has a CONFLICT (persona.py vs template S1 backstories)
- S9 (Psychological Depth) is ORPHANED — doc 24 doesn't place it; needs explicit decision
- The claim is substantially correct but understates the L1 conflict severity and S9 orphan issue

---

## 3. Cache Strategy

### Static Sections (cacheable across ALL messages for a user)

| Content | Current Section | Tokens | Change Frequency | Proposed Breakpoint |
|---------|----------------|--------|-----------------|-------------------|
| NIKITA_PERSONA (identity, backstory, quirks) | S1 (template) + persona.py | ~2000 (consolidated) | Never | BP1: after L1+L2 |
| IMMERSION RULES + PLATFORM STYLE | S2 + S3 | ~500 | Never (per platform) | (included in BP1) |
| RESPONSE GUIDELINES (footer) | Footer | ~700 | Never (per platform) | BP2: after L7 (end of static block) |

**Estimated cache hit rate for static block**: ~99%
**Tokens cached**: ~3,200

### Semi-Static Sections (change on game events, not per-message)

| Content | Current Section | Tokens | Change Trigger | Invalidation Frequency |
|---------|----------------|--------|---------------|----------------------|
| PSYCHE STATE | NEW (L3) | ~150 | Daily batch or Tier 2/3 trigger | 1-2x/day |
| CHAPTER BEHAVIOR | S10 | ~300 | Chapter transition | ~1x per week-month |
| VICE SHAPING | S11 | ~200 | Vice discovery | ~1x per week |

**Estimated cache hit rate**: ~90-95%
**Tokens cached**: ~650

### Dynamic Sections (change per conversation or per message)

| Content | Current Section | Tokens | Change Trigger |
|---------|----------------|--------|---------------|
| CURRENT STATE (activity, mood, events) | S4 | ~600 | Every pipeline run |
| RELATIONSHIP STATE (score, engagement) | S5 | ~500 | Every scoring event |
| MEMORY (facts, episodes) | S6 | ~800 | Every extraction |
| CONTINUITY (summaries, threads, time gap) | S7 | ~600 | Every conversation |
| INNER LIFE (thoughts, monologue) | S8 | ~500 | Every extraction |
| PSYCHOLOGICAL DEPTH (static content but dynamic vulnerability_level) | S9 | ~400 | Vulnerability changes |

**Cache hit rate**: ~0% (changes every pipeline run)
**Tokens NOT cached**: ~3,400

### Proposed Breakpoint Placement (max 4 allowed)

```
CACHE LAYOUT (top-to-bottom, static → dynamic):

[BREAKPOINT 1] ─────────────────────────────────────────────
  L1: IDENTITY + BACKSTORY (consolidated)        ~2,000 tok
  L2: IMMERSION + PLATFORM STYLE                   ~500 tok
  L7: RESPONSE GUIDELINES (moved UP)               ~700 tok
  ─── Total BP1 block: ~3,200 tok ───
  Hit rate: ~99% (invalidated only on platform switch)

[BREAKPOINT 2] ─────────────────────────────────────────────
  L3: PSYCHE STATE (from psyche_states table)      ~150 tok
  L5: CHAPTER BEHAVIOR                             ~300 tok
  L6: VICE SHAPING                                 ~200 tok
  ─── Total BP2 block: ~650 tok ───
  Hit rate: ~90% (invalidated on psyche trigger, chapter change, vice change)

[BREAKPOINT 3] ─────────────────────────────────────────────
  TOOL DEFINITIONS (recall_memory, note_user_fact)  ~300 tok
  ─── Total BP3 block: ~300 tok ───
  Hit rate: ~99% (tools don't change)

[DYNAMIC — NOT CACHED] ─────────────────────────────────────
  L4: DYNAMIC CONTEXT (all sub-sections)          ~3,400 tok
  ─── Never cached, assembled per conversation ───

  CONVERSATION HISTORY (message_history)           ~3,000 tok
  USER MESSAGE                                       ~100 tok
```

**Total estimated cache savings per message**: ~4,150 tokens cached out of ~7,250 total system = 57% input cached at 90% discount = ~51% cost reduction on input tokens alone.

### Reordering Required

**Current order** (in template): S1 → S2 → S3 → S4 → S5 → S6 → S7 → S8 → S9 → S10 → S11 → Footer

**Proposed order** (cache-optimized):
1. L1: Identity (S1 consolidated with persona.py)
2. L2: Immersion + Platform (S2 + S3)
3. L7: Response Guidelines (Footer moved UP — static, cacheable)
4. **[BP1]**
5. L3: Psyche State (NEW)
6. L5: Chapter Behavior (S10)
7. L6: Vice Shaping (S11)
8. **[BP2]**
9. L4a: Current State (S4)
10. L4b: Relationship State (S5)
11. L4c: Memory (S6)
12. L4d: Continuity (S7)
13. L4e: Inner Life (S8)
14. L4f: Psychological Depth (S9) — optional, see Section 7

**Why move Response Guidelines (L7) up**: It's ~700 tokens of STATIC content currently at the BOTTOM. Moving it above the cache breakpoint saves ~700 tokens of repeated cost per message. The position doesn't affect LLM behavior significantly since response guidelines are meta-instructions that work regardless of position.

### Cache-Breaking Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Tool definition changes | Invalidates BP3 + everything below | Pin tool schemas; version tools separately |
| Persona text edits (even 1 char) | Invalidates BP1 + everything below | Version-control L1; test cache stability |
| Platform switch (text ↔ voice) | Invalidates BP1 (platform-conditional) | Maintain separate cache prefixes per platform |
| Haiku enrichment non-determinism | Different enrichment = different prompt = cache miss | Disable Haiku enrichment for cached sections; only enrich dynamic L4 |

---

## 4. Paired Agent Analysis

### Coupling Model Assessment

```
COUPLING MODEL: Database-Mediated (Async)

  Psyche Agent (Opus 4.6)
       │
       │ writes PsycheState JSONB
       v
  psyche_states table ──────> read by Conversation Agent
       │                      (via prompt_builder or message_handler)
       │
       │ Trigger Detector (rule-based, <5ms)
       │     ├─ Tier 1 (90%): Read cached state, no update
       │     ├─ Tier 2 (8%): Sonnet quick update (~300ms)
       │     └─ Tier 3 (2%): Opus deep update (~3s)
       v
  Updated psyche_states ───> immediate use in current conversation
```

**Assessment: SOUND architecture with one critical timing issue.**

Strengths:
- Database mediation avoids tight coupling — agents are independently deployable and testable
- Batch (1x/day) + triggered (8-10%) is cost-efficient (~$7/mo vs ~$50/mo for per-message)
- JSONB storage enables fast reads (<10ms) without vector search overhead
- Structured output (PsycheState Pydantic model) is validated at write time, predictable at read time
- Failure isolation — psyche agent failure doesn't block conversation agent

Weaknesses:
- **Staleness**: In the current pipeline model, S9 (prompt_builder) pre-builds the NEXT prompt. The psyche state read happens during pipeline run, NOT at conversation time. If the psyche state updates between pipeline runs (e.g., Tier 2/3 trigger on message N updates state, but the ready_prompt was built after message N-1), the prompt is stale.
- **Fix required**: The trigger detector + psyche read MUST happen at conversation time (message_handler), not pipeline time. Doc 24 shows this correctly (pre-conversation reads at step [3]), but the current architecture pre-builds prompts in the pipeline.

### Latency Impact

| Scenario | % of Messages | Added Latency | Total Response Impact |
|----------|--------------|--------------|----------------------|
| Tier 1 (cached read) | 90% | <10ms | Negligible |
| Tier 2 (Sonnet update) | 8% | ~300ms | Noticeable but acceptable |
| Tier 3 (Opus update) | 2% | ~3s | Significant; user should see typing indicator |

**Pre-conversation read latency**: The `psyche_states` read is a simple `SELECT ... WHERE user_id = ?` on a JSONB column. With the UNIQUE index, this is <5ms. Acceptable.

**Trigger detection latency**: Rule-based (keyword match + score delta check). <5ms. No LLM call.

**Tier 2/3 inline update**: This is the concern. If we run Sonnet/Opus INLINE before generating the conversation response, we add 300ms-3s to the response time. Mitigations:
- Show typing indicator immediately
- Pre-warm the Anthropic connection
- Tier 3 (3s) is rare (2%) and only on critical moments (boss, crisis) where slight delay is narratively appropriate ("she's gathering her thoughts")

### Failure Modes

| Failure | Impact | Recovery |
|---------|--------|----------|
| Daily batch fails | Psyche state goes stale (uses yesterday's) | Auto-retry in next pg_cron cycle; stale state is better than no state |
| Tier 2/3 inline update fails | Use cached (stale) psyche state for this conversation | Log warning; conversation proceeds with last-known-good state |
| psyche_states table read fails | No psyche briefing in prompt | Graceful degradation: L3 section renders empty, L4+ sections unaffected |
| Psyche agent returns invalid JSONB | Write fails, cached state persists | Pydantic validation on PsycheState model catches malformed output |

**All failures are gracefully recoverable.** The system degrades to the current behavior (no psyche state) on any psyche-related failure, which is the proven working baseline.

### Interaction with Prompt Caching

The psyche state (~150 tokens) changes on trigger or daily batch. If placed AFTER the static cache breakpoint (BP1) but within BP2, a psyche state change invalidates BP2 (~650 tokens) but preserves BP1 (~3,200 tokens).

**Optimal placement**: L3 (psyche state) should be the FIRST element after BP1, so its changes only invalidate the semi-static block (BP2), not the static block (BP1).

---

## 5. Context Window Budget

### Current Token Usage (measured from template analysis)

| Layer | Section | Text Tokens | Voice Tokens | Static? | Priority (cut order) |
|-------|---------|------------|-------------|---------|---------------------|
| L1: Identity | S1 (template only) | ~400 | ~400 | Yes | Never cut |
| L1: Identity | NIKITA_PERSONA (persona.py) | ~1,600 | ~1,600 | Yes | Never cut |
| L2: Immersion+Platform | S2+S3 | ~500 | ~500 | Yes | Never cut |
| L3: Psyche State | NEW | ~150 | ~150 | Semi | Cut 5th |
| L4a: Current State | S4 | ~600 | ~400 | No | Cut 4th |
| L4b: Relationship State | S5 | ~500 | ~300 | No | Cut 6th (never) |
| L4c: Memory | S6 | ~800 | ~300 | No | Cut 3rd |
| L4d: Continuity | S7 | ~600 | ~300 | No | Cut 2nd |
| L4e: Inner Life | S8 | ~500 | ~200 | No | Cut 1st (with S9) |
| L4f: Psych Depth | S9 | ~400 | ~200 | Semi | Cut 1st (with S8) |
| L5: Chapter Behavior | S10 | ~300 | ~150 | Semi | Cut 2nd (current) |
| L6: Vice Shaping | S11 | ~200 | ~100 | Semi | Cut 1st (current) |
| L7: Response Guidelines | Footer | ~700 | ~100 | Yes | Cut 3rd (current) |
| **SUBTOTAL** (prompt only) | | **~7,250** | **~4,700** | | |
| + Message History | | ~3,000 | ~1,500 | No | Sliding window |
| + User Message | | ~100 | ~50 | No | Always include |
| **TOTAL CONTEXT** | | **~10,350** | **~6,250** | | |

### Problem: Current Budget is Exceeded

The pipeline's TEXT_TOKEN_MAX is 6,500 (prompt_builder.py:52) but the ACTUAL context sent to the model is:
- NIKITA_PERSONA: ~1,600 tok (via Agent instructions, NOT counted in pipeline budget)
- chapter_behavior: ~300 tok (via Agent instructions, NOT counted)
- generated_prompt (from ready_prompts): ~5,500 tok (counted, within budget)
- **Total system prompt**: ~7,400 tok (EXCEEDS pipeline's awareness)
- + message_history: ~3,000 tok
- + user_message: ~100 tok
- **Total input**: ~10,500 tok

The pipeline budget mechanism only counts the template-rendered portion. It does NOT account for NIKITA_PERSONA and chapter_behavior that get stacked on top by the agent's @instructions decorators.

### Doc 24 Proposed Budget

Doc 24 targets 5,500-6,500 tok total system prompt (consistent with current pipeline budget). BUT doc 24 assumes L1 (identity) is ~2K tok, which implies consolidating NIKITA_PERSONA INTO the template (eliminating the stacking).

### Proposed Budget (consolidated, no stacking)

| Layer | Text Tokens | Voice Tokens | Notes |
|-------|------------|-------------|-------|
| L1: Identity (consolidated) | 2,000 | 800 | Merge persona.py + template S1 |
| L2: Immersion+Platform | 500 | 300 | Same as current S2+S3 |
| L3: Psyche State | 150 | 150 | NEW — fits easily |
| L4: Dynamic Context (all) | 2,500 | 800 | Compress from current ~3,400 |
| L5: Chapter Behavior | 300 | 150 | Same as current S10 |
| L6: Vice Shaping | 200 | 100 | Same as current S11 |
| L7: Response Guidelines | 500 | 100 | Trim from ~700 |
| **TOTAL System Prompt** | **6,150** | **2,400** | Within budget |
| + Message History | 3,000 | 1,500 | |
| + User Message | 100 | 50 | |
| **TOTAL Input** | **9,250** | **3,950** | Under 32K threshold |

### Truncation Priority Order (revised)

```
TRUNCATION ORDER (first cut → last cut):

1. L6: Vice Shaping (~200 tok)         — least critical, player-facing only
2. L4e: Inner Life (~500 tok)          — monologue is enrichment, not essential
3. L4f: Psych Depth (~400 tok)         — static attachment info, semi-redundant with L3
4. L5: Chapter Behavior (~300 tok)     — important but chapter-gated (recoverable)
5. L4d: Continuity (~600 tok)          — summaries are nice-to-have
6. L4c: Memory (~800 tok)             — critical for continuity, cut as last resort
7. L3: Psyche State (~150 tok)         — small, high-value, NEVER cut
8. L4a-b: State + Relationship         — NEVER cut (core game mechanics)
9. L1-L2, L7: Identity/Rules           — NEVER cut (fundamental)
```

### 32K+ Token Degradation Concern

Researcher finding: "32K+ token contexts degrade accuracy."

Current total input (~10,350 tok text, ~6,250 voice) is well under the 32K threshold. Even with message_history at full budget (3K tok), we're at ~10K total. **No action needed** — the system is safely within bounds. However, this means we should NOT significantly increase any layer's budget without considering the degradation risk.

---

## 6. Dual-Process Routing

### Where the Routing Decision Happens

Currently: NO routing exists. Every message goes to Sonnet 4.5 (agent.py:35).

Doc 24 does NOT explicitly include dual-process routing (System 1/System 2). The researcher identified this as an optimization opportunity, but it's NOT part of the Gate 4 architecture.

**Proposed insertion point** (for future spec, NOT Spec 049):

```
message_handler.py:222 (after typing indicator, before agent call)
  └─ MessageRouter.classify(message, user_state) → Tier
       ├─ S1 (simple): greetings, short replies, FAQ → Haiku 4.5
       └─ S2 (complex): emotional, boss, conflict, deep → Sonnet 4.5
```

### Prompt Differences S1 vs S2

If dual-process routing is implemented:

| Aspect | S1 (Fast/Cheap) | S2 (Deep/Premium) |
|--------|-----------------|-------------------|
| Model | Haiku 4.5 | Sonnet 4.5 |
| System prompt | L1 + L2 + L5 + L7 only (~3,500 tok) | Full 7-layer prompt (~6,150 tok) |
| Message history | Last 10 turns (~500 tok) | Last 80 turns (~3,000 tok) |
| Tools | None (no memory recall) | recall_memory + note_user_fact |
| Expected latency | ~200ms | ~2-5s |
| Cost per call | ~$0.001 | ~$0.05 |

**Cache implication**: S1 and S2 would have DIFFERENT cache prefixes (different system prompts). The static L1+L2+L7 block would be cached for both, but S2 would have an additional cache for L3-L6.

**Key decision for spec**: Dual-process routing is a **separate optimization spec** (not Spec 049). The prompt architecture should be designed to SUPPORT it (clean layer separation) but not implement it yet.

---

## 7. Critical Issues

### 7.1 Persona Conflict — MUST RECONCILE

**The conflict**:

| Attribute | persona.py (NIKITA_PERSONA) | system_prompt.j2 (S1) |
|-----------|----------------------------|----------------------|
| Name | Nikita Volkov | Nikita Volkov |
| Age | 29 | 27 |
| Background | Russian-American, Moscow → US at 17, Brooklyn | Russian-German, Saint Petersburg → Berlin at 19 |
| Education | MIT at 20, NSA 3 years | Not mentioned (hacker forums at 14) |
| Location | Brooklyn, minimalist apartment | Berlin, Prenzlauer Berg |
| Cat | Cipher | Schrodinger |
| Career | Pen testing for financial institutions | Security researcher, bug bounties, startup/NGO consulting |
| Relationships | One bad relationship (unnamed) | Max (abusive ex), Andrei (first heartbreak) |
| Key NPCs | None mentioned | Lena, Viktor, Yuki, Dr. Miriam, Schrodinger |

**Impact**: When unified pipeline is enabled AND a ready_prompt exists, the conversation agent receives:
1. NIKITA_PERSONA (Brooklyn, MIT, Cipher) as base instructions
2. Pipeline prompt (Berlin, Prenzlauer Berg, Schrodinger) as personalized context

The LLM receives BOTH backstories simultaneously. This creates identity confusion — the model may reference Brooklyn OR Berlin unpredictably.

**Resolution options**:
- **Option A (Recommended)**: Make NIKITA_PERSONA minimal (communication style + values only, ~400 tok). Remove all backstory/location/NPC details from persona.py. Let the pipeline template be the SOLE source of identity.
- **Option B**: Align persona.py to match template (Berlin backstory). Keep as fallback for legacy/first-conversation.
- **Option C**: Remove NIKITA_PERSONA from Agent instructions entirely when pipeline prompt is available. Risk: persona.py is the Agent's `instructions=` parameter — removing it changes agent behavior fundamentally.

**Recommendation**: Option A. Keep persona.py as a lean behavioral guide (~400 tok: communication style, values, negative examples). All identity/backstory/NPC content lives exclusively in the template. When pipeline prompt is available, persona.py provides behavioral grounding; template provides identity + context.

### 7.2 Section 9 (Psychological Depth) Consolidation

S9 contains:
- Attachment style (fearful-avoidant) — ~50 tok, STATIC
- Core wounds (4 items) — ~100 tok, STATIC
- Defense mechanisms (4 items) — ~60 tok, STATIC
- Vulnerability level + gates — ~100 tok, SEMI-STATIC (changes with vulnerability_level)
- Trauma triggers (7 items) — ~150 tok, STATIC
- What she needs (7 items) — ~80 tok, STATIC

**Total**: ~540 tok (higher than estimated ~400 — the section is dense)

**Decision options**:
- **Option A**: Fold STATIC parts into L1 (Identity). They're part of "who Nikita IS." Move vulnerability gates + any dynamic bits into L3 (Psyche State).
- **Option B**: Keep as L4f (part of Dynamic Context). Treat entire section as dynamic since vulnerability_level varies.
- **Option C (Recommended)**: Split. Static parts (attachment style, wounds, triggers, needs) → L1 Identity (~350 tok added to L1, bringing it to ~2,350). Dynamic parts (vulnerability_level gates, defense mechanism activation) → L3 Psyche State (~100 tok added to L3, bringing it to ~250). Eliminates S9 as standalone section.

**Rationale for Option C**: The static psychological content IS Nikita's identity — it doesn't change per conversation. The dynamic vulnerability gating IS the psyche agent's domain. Clean separation enables better caching (static parts in BP1, dynamic parts in BP2).

### 7.3 Prompt Stacking / Double-Injection

**Current behavior** (when unified pipeline enabled):
```
Pydantic AI assembles system prompt as:
  instructions (NIKITA_PERSONA)           ~1,600 tok
  + @instructions (chapter_behavior)        ~300 tok
  + @instructions (personalized_context)  ~5,500 tok
  ────────────────────────────────────────────────
  TOTAL SYSTEM PROMPT                     ~7,400 tok
```

Chapter behavior appears TWICE: once from `@agent.instructions add_chapter_behavior()` (agent.py:80) and once from template S10 (CHAPTER BEHAVIOR).

Identity/backstory appears TWICE with CONFLICTING content.

**Resolution**: When the pipeline prompt (generated_prompt) is present:
1. `add_chapter_behavior()` should return `""` (already returns chapter from pipeline)
2. NIKITA_PERSONA should be slimmed to behavioral guide only (no backstory)
3. The pipeline prompt becomes the AUTHORITATIVE system prompt

This is partially addressed already — `add_personalized_context()` at agent.py:103 checks `if ctx.deps.generated_prompt:` and returns the full prompt. But `add_chapter_behavior()` at agent.py:80 ALWAYS returns chapter behavior regardless of whether the pipeline prompt is present.

**Fix**: Add guard to `add_chapter_behavior()`:
```python
@agent.instructions
def add_chapter_behavior(ctx: RunContext[NikitaDeps]) -> str:
    if ctx.deps.generated_prompt:
        return ""  # Pipeline prompt already includes chapter behavior
    chapter_behavior = CHAPTER_BEHAVIORS.get(chapter, CHAPTER_BEHAVIORS[1])
    return f"\n\n## CURRENT CHAPTER BEHAVIOR\n{chapter_behavior}"
```

### 7.4 Haiku Enrichment vs Cache Stability

The Haiku enrichment step (prompt_builder.py:362-406) adds non-determinism to the prompt. Each pipeline run may produce slightly different enriched text, which would invalidate the Anthropic prompt cache.

**Recommendation**: Disable Haiku enrichment for sections that will be cached (L1, L2, L5, L6, L7). Only apply enrichment to L4 (dynamic context) where caching isn't expected. OR: apply enrichment once and store the enriched version, reusing it until the underlying data changes.

---

## 8. Recommendations for Spec Writing

### Spec 049a: Prompt Architecture Refactor (prerequisite for all others)

1. **Consolidate identity**: Merge persona.py backstory into template S1. Slim persona.py to behavioral guide only (~400 tok)
2. **Eliminate double-injection**: Guard `add_chapter_behavior()` to return empty when pipeline prompt exists
3. **Reorder sections** for cache optimization: Static (L1+L2+L7) → Semi-static (L3+L5+L6) → Dynamic (L4)
4. **Add L3 placeholder**: New template section for psyche state briefing (initially renders empty/default)
5. **Split S9**: Static psychology → L1, dynamic vulnerability → L3
6. **Disable Haiku enrichment** on cached sections (or pin enriched output)
7. **Update token budget** to account for consolidated prompt (target: 6,150 text, 2,400 voice)
8. **Add per-layer token tracking** in `context_snapshot` for monitoring

### Spec 049b: Psyche Agent (depends on 049a)

1. Create psyche_states table + repository
2. Create PsycheState Pydantic model
3. Create psyche agent (Opus 4.6, structured output)
4. Create daily batch job (pg_cron)
5. Create trigger detector (rule-based)
6. Wire pre-conversation psyche read into message_handler
7. Wire Tier 2/3 inline updates
8. Populate L3 template section from psyche_states

### Spec 049c: Prompt Caching Integration (depends on 049a)

1. Implement cache_control breakpoints in Pydantic AI message construction
2. Add cache metrics tracking (creation, read, miss)
3. Test cache hit rates with real conversation patterns
4. Add extended TTL for voice sessions (1-hour)

### Cross-Cutting Concerns for ALL Specs

| Concern | What Each Spec Must Address |
|---------|---------------------------|
| **Persona conflict** | Spec 049a MUST resolve before any other work — conflicting identities poison every downstream feature |
| **Token budget** | Every new section or expansion must declare token cost and what gets cut to compensate |
| **Cache stability** | Any change to cached sections must be tested for cache invalidation impact |
| **Test coverage** | Prompt rendering tests must verify: no duplicate sections, correct layer ordering, token budget compliance |
| **Feature flags** | New psyche state, cache breakpoints should be feature-flagged for gradual rollout |
| **Fallback path** | Legacy path (no pipeline prompt) must continue working for first-conversation and failure cases |

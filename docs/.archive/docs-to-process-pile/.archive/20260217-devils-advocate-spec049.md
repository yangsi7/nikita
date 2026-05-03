# Devil's Advocate Review -- Gate 4.5
Date: 2026-02-17
Agent: devils-advocate
Sources: All 8 Wave 1/2 outputs + doc 24 + git history + codebase analysis

---

## Challenge Register

### CRITICAL (must address before spec writing)

| # | Challenge | Evidence | Mitigation | Spec |
|---|-----------|----------|------------|------|
| C1 | **Persona conflict will poison every conversation**. persona.py says Brooklyn/MIT/Cipher; template says Berlin/Prenzlauer Berg/Schrodinger. When unified pipeline is ON, the agent receives BOTH backstories simultaneously. This is not theoretical -- it is the current production behavior. | `agents/text/persona.py:18` vs `system_prompt.j2:11`. Context-engineer confirms: "Identity confusion -- the model may reference Brooklyn OR Berlin unpredictably." | Must be resolved in Spec 054 as a hard prerequisite BEFORE any other spec. Slim persona.py to behavioral guide only (~400 tok). Template becomes sole identity source. | 054 (prerequisite) |
| C2 | **Prompt stacking inflates context by ~1,900 unbudgeted tokens**. NIKITA_PERSONA (~1,600 tok) + chapter_behavior (~300 tok) are injected via @agent.instructions and NOT counted in the pipeline's 6,500 token budget. Actual system prompt is ~7,400 tok, not 5,500-6,500. | `agent.py:80-105` always injects both decorators regardless of pipeline prompt. `prompt_builder.py:51-52` budget is 5,500-6,500 but only counts its own output. | Guard `add_chapter_behavior()` to return "" when pipeline prompt exists. Consolidate NIKITA_PERSONA into template. This is a day-1 fix. | 054 |
| C3 | **NPC state is a 3-way mess with conflicting character names**. Existing: `nikita_state.friends` (Maya/Sophie/Lena), `user_social_circles` (14 cols, Spec 035), `nikita_entities` + arc templates (Marco/Lena/Viktor/Yuki/Alexei/Katya/Dr. Miriam). Doc 24 proposes a FOURTH system: `users.npc_states` JSONB with yet another set of names (Emma/Lena/Marcus/Viktor/Sarah/Yuki/Mom/Ex). | `backend-db-analysis:130-150`, `engine-analysis:388-413`, `integration-review:136-153`. Three existing systems, zero overlap reconciliation plan in doc 24. | Integration reviewer's recommendation is correct: designate `user_social_circles` as canonical. Do NOT add `npc_states` JSONB on users. But this requires explicit character name mapping (Marco->Marcus? Sophie->Sarah? Maya->?). The mapping table is missing from all 8 agent outputs. | 049 |
| C4 | **No existing user migration plan**. There is 1 active user with real data. psyche_states will be empty. conflict_state will be empty. vulnerability_exchanges = 0. NPC states are unconsolidated. What is the Day 1 experience after deployment? Does the user see a suddenly "different" Nikita because the prompt structure changed? | `backend-db-analysis:1` shows 1 user with 48 score_history entries, 14 memory_facts, 2 conversations. Non-trivial existing state. | Each spec needs an explicit "existing user migration" section: seed psyche state from current emotional_states + score trajectory; backfill conflict_state from current conflict history; seed NPCs from existing arc characters. First psyche batch should run immediately on deploy, not wait for daily cron. | All |

### HIGH (must address during spec writing)

| # | Challenge | Evidence | Mitigation | Spec |
|---|-----------|----------|------------|------|
| H1 | **Is the Psyche Agent (Opus 4.6) over-engineered for 1 user?** Daily Opus call to analyze 7-day history for a single user. The "subconscious" metaphor is elegant but Sonnet 4.5 could handle the same structured output at 60% lower cost ($3/MTok input vs $5/MTok; $15/MTok output vs $25/MTok). The psyche analysis is fundamentally a summarization + classification task, not deep reasoning. | Doc 24 Section 2 prescribes Opus 4.6. Fact-check confirms $2.25/mo batch cost. But Sonnet could do it for ~$0.90/mo. At scale (100 users), the difference is $135/mo vs $90/mo -- not transformative. | Start with Sonnet 4.5 for daily batch. Reserve Opus 4.6 for Tier 3 triggers only (2% of messages, genuinely complex moments). Add `psyche_model` config parameter to switch without code changes. Monitor output quality and upgrade if Sonnet proves insufficient. | 050 |
| H2 | **Temperature gauge adds a THIRD conflict tracking system on top of two existing ones**. Current: (1) `nikita_emotional_states.conflict_state` enum (5 values) + `conflict_trigger` + `ignored_message_count`; (2) `ActiveConflict` in-memory model with severity/escalation_level/resolution_attempts. Doc 24 adds: (3) temperature gauge 0-100 in `conflict_state` JSONB. Three conceptual models for the same thing. | `nikita_emotional_states` schema at `backend-db-analysis:96-111`, `conflicts/models.py:76` ActiveConflict, doc 24 Section 9 temperature gauge. | Temperature gauge should REPLACE the existing `conflict_state` enum and `ignored_message_count`, not layer on top. Migration: map existing enum values to temperature zones (none=0, passive_aggressive=40, cold=50, vulnerable=30, explosive=85). Spec must explicitly deprecate old fields. | 051 |
| H3 | **Multi-phase boss (3-5 turns) is the highest risk item and should be the LAST spec, not bundled with conflict**. Engine analyst rates it "VERY LARGE gap -- fundamental redesign." 20 phase-prompt variants (4 phases x 5 chapters) is massive content creation. Current boss is 1 turn, binary. Going to 3-5 turns with 3 outcomes is a 15x complexity increase.** | `engine-analysis:254-282`. Current flow: `initiate_boss()` -> 1 response -> `judge_boss_outcome()` -> PASS/FAIL. Zero phase tracking, zero multi-turn state. `BossResult` enum has only 2 values. | Already separated into Spec 052 (good). But 4-5 days is underestimated for 20 prompt variants + multi-turn state machine + PARTIAL outcome logic + judgment rewrite. Estimate 6-8 days. Consider MVP: 2-phase boss (OPENING -> RESOLUTION), not 4-phase. Add phases incrementally in a follow-up spec. | 052 |
| H4 | **Gottman 5:1 ratio is designed for real relationships over years, not a game with minutes-long sessions**. In clinical research, the 5:1 ratio is measured across entire relationships, not per-session. A game session might have 10-20 messages. 5:1 means the player can only say 1-2 "bad" things before crossing the threshold. This makes the mechanic extremely punitive.** | Gottman research (fact-check source): "5:1 ratio" is for conflict periods. Non-conflict periods are 20:1. The game is mostly non-conflict, so 20:1 would apply -- making 5:1 far too lenient during normal play. | Use TWO ratios: 5:1 during active conflicts, 20:1 during normal play. Track per-session AND rolling 7-day ratio. Session ratio triggers micro-conflicts; 7-day ratio triggers macro-conflicts. This matches the actual psychology more accurately. | 051 |
| H5 | **pg_cron free tier availability is unconfirmed**. Fact-checker flags: "Official Supabase docs do not explicitly confirm pg_cron on free tier." The entire batch architecture depends on pg_cron. If it's not available on free tier, that's $25/mo for Supabase Pro -- nearly doubling the $30-37 cost estimate. | `fact-check:66-67`. Current project uses pg_cron (6 active jobs), so it IS working. But this may be a legacy provisioning or Pro trial. | Verify immediately: run `SELECT * FROM cron.job;` via Supabase MCP. If the project is on free tier AND pg_cron works, document this as confirmed. If on Pro, adjust cost estimates. Either way, the architecture is correct -- just the cost claim may be wrong. | All |
| H6 | **JSONB <5ms latency claim is optimistic by 2-10x**. Fact-checker: realistic Supabase latency is 10-50ms per query. Doc 24 claims <15ms total for 3 parallel pre-conversation reads. With realistic latency, that's 30-70ms. | `fact-check:76-79`. Supabase free tier shared infrastructure adds network + pooling overhead. | Accept 30-50ms pre-conversation overhead. This is still fast for a chat UX (user won't notice). Update doc 24 latency claims to be honest: "Pre-conversation reads: <50ms total." The architecture doesn't change -- just the marketing copy. | 050 |
| H7 | **Voice costs are completely excluded from the $30-37 estimate**. ElevenLabs Conversational AI: $0.10/min. A 30-min voice session = $3. Daily voice user = $90/mo. This could make Nikita economically unviable for voice-heavy users. | `fact-check:50-55`. ElevenLabs pricing verified. Doc 24 Section 12 lists costs but omits voice entirely. | Add voice tier to cost model. Free tier: text only. Premium tier ($X/mo): includes Y minutes of voice. Per-minute overage: $0.10. Voice is a premium feature, not included in base $30-37. | All |

### MEDIUM (should address, can defer)

| # | Challenge | Evidence | Mitigation | Spec |
|---|-----------|----------|------------|------|
| M1 | **Meta-instructions (monthly) are premature**. Chapter progression already changes behavior per chapter. Narrative arcs already provide multi-conversation storylines. Adding a monthly meta-instruction layer is a third behavioral shaping system on top of chapters + arcs. What specific player-visible behavior does this enable that chapters + arcs don't? | `engine-analysis:360-384`. Chapters: 5 behavioral modes. Arcs: 10 story templates with 5 stages. Meta-instructions: "This month Nikita is processing father's birthday." Arcs already do this. | Defer meta-instructions to a post-MVP spec. Keep `meta_instructions` JSONB column (it's cheap to add) but don't build the monthly generation job or integrate into event generation. Focus on making existing arcs + chapters work well with the psyche agent first. | 049 |
| M2 | **NPC state for never-mentioned NPCs is YAGNI**. Tracking 5-8 NPCs per user when the player may never interact with any of them. Each NPC update requires JSONB writes on every life event. With 3-5 events/day and potentially 5 NPC updates each, that's 15-25 extra JSONB operations per day per user for state nobody reads. | Doc 24 Section 2 (Module 2): 5 NPCs. `engine-analysis:388-413`: "No sentiment tracking, no event history per NPC, no dynamic relationship evolution" currently. | Lazy NPC initialization: only create NPC state when an NPC is first mentioned in conversation or life event. Don't pre-seed 8 NPCs per user. Let the life sim and arcs naturally introduce NPCs, and track state only for those that have appeared. | 049 |
| M3 | **Vulnerability bonus creates a gaming exploit**. "Just share sad things for bonus points." If vulnerability_exchanges gives +2 trust bonus, players learn to always respond with emotional language to maximize scores. This undermines the game's goal of teaching genuine relationship skills. | Doc 24 implies vulnerability exchange tracking. `integration-review:83-97`: "+2 trust bonus on top of normal metric deltas." | Add diminishing returns: 1st V-exchange per conversation = +2, 2nd = +1, 3rd+ = +0. Cap at 3 per session. Also: vulnerability must be MUTUAL (Nikita shares AND player responds appropriately), not just player performing emotions. Detection should check for genuine empathy, not keyword matching. | 052 |
| M4 | **Haiku enrichment vs cache stability is an unresolved conflict**. Haiku enrichment adds non-deterministic narrative polish to the prompt, which would break Anthropic prompt caching (exact match required). Context-engineer identifies this but no decision is made. | `context-engineering-review:521-526`. Haiku enrichment at `prompt_builder.py:362-406`. | Decision: disable Haiku enrichment entirely for cached sections. Apply enrichment ONLY to L4 dynamic context (which isn't cached anyway). Or: run Haiku enrichment once, store the result, reuse until underlying data changes. Make this an explicit spec task. | 054 |
| M5 | **19-26 day estimate is realistic for AI-assisted development BUT assumes perfect spec quality**. Spec 042 (45 tasks) completed in 1-2 days. Spec 044 completed in 1 day. But those were well-defined specs with clear boundaries. These 6 specs involve design decisions (temperature calibration, Gottman tuning, boss phase design, NPC reconciliation) that require playtesting and iteration. | Git log: `e8cf4b3` (Spec 042 complete, Feb 7) started `1770d5d` (Feb 6). `add61e3` (Spec 044 complete, Feb 8). Total: 2-3 days for 2 specs with ~56 tasks. | Estimate is plausible for coding. Add 50% buffer for: (1) design iteration on temperature zones, (2) boss prompt content writing (20 variants), (3) NPC name reconciliation discussions, (4) playtesting the Gottman mechanics. Adjusted estimate: 25-35 days total. | All |
| M6 | **Section 9 (Psychological Depth, ~540 tok) is orphaned in doc 24**. It exists in the current template but doc 24's 7-layer model doesn't place it. Context-engineer proposes splitting static parts to L1 and dynamic parts to L3, but this is a non-trivial refactor that changes what gets cached. | `context-engineering-review:469-486`. S9 has ~540 tokens, not ~400 as estimated. | Adopt context-engineer's Option C: static psychology (attachment, wounds, triggers) -> L1 Identity; dynamic vulnerability gates -> L3 Psyche State. This adds ~350 tok to L1 (bringing it to ~2,350, still cacheable) and ~100 tok to L3 (bringing it to ~250, minimal cache impact). | 054 |
| M7 | **Timezone handling for weekly routine is unaddressed**. Nikita's routine is Berlin time (CET/CEST). The 1 existing user is presumably in a specific timezone, but future users could be anywhere. "Tuesday coffee with Lena" at 10 AM Berlin time is 5 PM Tokyo time. The event generator uses `time_of_day` (morning/afternoon/evening) but doesn't account for player timezone vs Nikita timezone. | `users.timezone` column exists (default 'UTC'). Doc 24 Section 6 shows routine in Berlin time. `event_generator.py:177`: day-of-week as a hint, no timezone logic. | Nikita lives in Berlin. Her routine is always Berlin time. The event generator should use Berlin timezone for day-of-week and time-of-day calculations, regardless of player timezone. The `system_prompt.j2` Section 4 should note the player's local time AND Nikita's Berlin time for context. Simple, no over-engineering. | 049 |

### LOW (nice to have, track for later)

| # | Challenge | Evidence | Mitigation | Spec |
|---|-----------|----------|------------|------|
| L1 | **No monitoring strategy for psyche agent quality**. How do you know if the PsycheState output is good? If behavioral_guidance is nonsensical? If attachment_activation is miscalibrated? There's no feedback loop. | No monitoring mentioned in any agent output. | Add `psyche_quality_score` field computed by a simple heuristic: fields present, guidance length, tone consistency with score trajectory. Log anomalies. Human review first 100 psyche states. | 050 |
| L2 | **No rollback plan per spec**. If Spec 051 (conflict temperature) breaks game balance, how do you revert? Feature flags gate the new code, but the DB schema changes are permanent. | Integration reviewer's feature flags are good. But ALTER TABLE is permanent. | Feature flags are sufficient. Schema changes are additive (nullable columns). If a feature is disabled, the columns sit unused. No rollback needed for schema -- only for code. Existing feature flag plan covers this. | All |
| L3 | **115-170 new tests may be light for multi-phase boss**. Engine analyst estimates 40-60 tests for boss alone (4 phases x 5 chapters). That's 20 prompt variants to test with 3 outcomes each = 60 test cases minimum. Plus edge cases (phase timeout, mid-boss disconnect, partial scoring). Could need 80-100 boss tests alone. | `engine-analysis:504-509`. 40-60 boss tests + 60 other tests = 100-120 minimum. | Re-estimate: 40-60 (boss) + 30-40 (conflict) + 20-30 (life sim) + 20-30 (psyche) + 10-15 (caching) = 120-175 tests. The 115-170 range is actually reasonable at the upper end. Accept. | All |
| L4 | **pgVector storage grows fast**. 1536-dim vectors are ~6KB each. memory_facts currently has 14 rows (tiny). At 500 facts/user x 100 users = 50K vectors = ~300MB. Free tier limit: 500MB. | `fact-check:170-172`. 500MB Supabase free tier. | Not a concern for current scale (1 user). Monitor with `SELECT pg_total_relation_size('memory_facts');`. Add alert at 250MB. Consider dimension reduction (text-embedding-3-small supports 512 dims) as a future optimization. | None |
| L5 | **Portal spec (053) CAN start earlier with mock data**. Current DAG puts Portal last (days 15-19). But UI scaffolding, component design, and mock data rendering don't depend on backend specs at all. | `integration-review:99-114`: "Uses shadcn/ui components: Card, Avatar, Badge, Progress." All frontend. | Start Portal UI scaffold in Wave A (parallel with 049/051). Use hardcoded mock data for timeline, social circle, warmth meter. Wire to real APIs in Wave D. This reduces the critical path by 3-4 days. | 053 |

---

## Over-Engineering Assessment

| Feature | Value/Complexity Ratio | Recommendation |
|---------|----------------------|----------------|
| **Psyche Agent (Opus 4.6)** | High value, medium complexity. BUT Opus is overkill for MVP. | **Simplify**: Use Sonnet 4.5 for batch, Opus only for Tier 3. Save ~40% on psyche costs. |
| **Meta-instructions (monthly)** | Low marginal value over chapters + arcs. Medium complexity. | **Defer**: Add JSONB column now, build generation job later. Chapters + arcs + psyche already shape behavior across 3 timescales. |
| **NPC state tracking (8 NPCs)** | Low value until NPCs appear in conversation. Medium complexity due to 3-system reconciliation. | **Simplify**: Lazy initialization. Track only NPCs that have been mentioned. Don't pre-seed 8 per user. |
| **Temperature gauge (continuous)** | High value. Replaces discrete cooldown with nuanced model. Medium complexity. | **Keep**: But must replace existing conflict_state enum, not layer on top. |
| **Multi-phase boss (4 phases)** | High value for gameplay. VERY HIGH complexity. 20 prompt variants. | **Simplify for MVP**: 2 phases (OPENING -> RESOLUTION), not 4. Add ESCALATION and CRISIS_PEAK in a follow-up. |
| **Gottman ratio tracking** | Medium value. Interesting mechanic but needs careful calibration. | **Keep**: But use two ratios (conflict 5:1, normal 20:1) and add diminishing returns on negative scoring. |
| **Conversation compaction** | Medium value for cost. Low complexity. | **Keep**: Standard optimization. |
| **Prompt caching (Anthropic)** | High value (~$22/mo savings). Medium complexity (reordering, breakpoints). | **Keep**: But resolve persona conflict FIRST. |

---

## Missing Pieces Checklist

| # | Missing Piece | Impact | Which Spec Should Own It |
|---|--------------|--------|--------------------------|
| 1 | Character name reconciliation table (Maya->?, Sophie->?, Marco->Marcus?) | Blocks NPC consolidation | 049 |
| 2 | Existing user data migration plan (seed psyche, backfill conflict, map NPCs) | Day-1 regression for existing user | All (each spec needs a migration section) |
| 3 | Error handling for psyche batch failure (stale state handling, monitoring) | Silent degradation | 050 |
| 4 | Psyche agent quality monitoring (how to know output is good) | No feedback loop | 050 |
| 5 | Temperature zone calibration methodology (how to tune 0-30, 30-60, etc.) | Zones may be wrong on first try | 051 |
| 6 | Boss phase-prompt content (20 variants, 4 phases x 5 chapters) | Massive content creation burden | 052 |
| 7 | A/B testing infrastructure for new mechanics | Can't measure impact of changes | Deferred |
| 8 | Rate limiting on Tier 3 Opus triggers (circuit breaker) | Cost runaway if trigger detector mis-calibrates | 050 |
| 9 | Data backfill for conflict_state.gottman_ratio from existing score_history | Cold start: ratio is 0:0 for existing user | 051 |
| 10 | Voice pipeline integration with new psyche/conflict state | Voice uses separate prompt path | 050 + 051 |
| 11 | Spec 048 (E2E full lifecycle) re-run after these changes | Existing E2E tests may break | Post-052 |
| 12 | Legacy table deprecation plan (nikita_state, user_facts, context_packages, generated_prompts) | Schema debt accumulates | Cleanup spec |

---

## Cost Model Stress Test

| Scenario | Users | Text Msgs/Day | Voice Min/Day | LLM Cost/Mo | Infra Cost/Mo | Total/Mo |
|----------|-------|---------------|---------------|-------------|---------------|----------|
| Solo tester (current) | 1 | 30 | 0 | $10-15 | $0 (free) | $10-15 |
| Active solo (target) | 1 | 100 | 0 | $30-37 | $0 (free) | $30-37 |
| Active solo + voice | 1 | 100 | 30 | $30-37 | $0 (free) | $120-127 ($90 voice) |
| Power user | 1 | 200 | 0 | $55-70 | $0 (free) | $55-70 |
| 10 users (text) | 10 | 50/user avg | 0 | $180-250 | $25 (Supabase Pro) | $205-275 |
| 100 users (text) | 100 | 30/user avg | 0 | $1,200-1,800 | $25 (Supabase Pro) | $1,225-1,825 |
| 100 users (mixed) | 100 | 30/user + 10min voice avg | 10 | $1,200-1,800 | $25 + ElevenLabs | $4,225-4,825 ($3K voice) |

Key insight: **Voice is 2-3x more expensive than text LLM costs**. The $30-37 estimate is accurate for text-only single user, but voice changes the economics fundamentally.

---

## Timeline Reality Check

| Spec | Doc 24 Est | Agent Est | Historical Comparison | Adjusted Est |
|------|-----------|-----------|----------------------|-------------|
| 042 (45 tasks, unified pipeline) | N/A | N/A | 1-2 days actual | Baseline |
| 043 (11 tasks, integration) | N/A | N/A | <1 day actual | Baseline |
| 044 (portal, 94 files) | N/A | N/A | 1-2 days actual | Baseline |
| **049 (Life Sim, 20-25 tasks)** | 3-4 days | 4-5 days | NPC reconciliation adds design decisions | **4-5 days** |
| **050 (Psyche Agent, 22-28 tasks)** | 2-3 days | 4-5 days | New agent + batch + triggers = moderate | **3-4 days** |
| **051 (Conflict, 18-22 tasks)** | 3-4 days | 3-4 days | Temperature replaces existing system = moderate | **3-4 days** |
| **052 (Boss, 20-25 tasks)** | 3-4 days | 3-5 days | 20 prompt variants = content bottleneck | **5-8 days** |
| **053 (Portal, 15-20 tasks)** | 2-3 days | 3-4 days | Pure frontend, can start early | **2-3 days** |
| **054 (Caching, 15-18 tasks)** | 1 day | 2-3 days | Persona reconciliation is tricky | **2-3 days** |
| **TOTAL** | **15-20 days** | **19-26 days** | -- | **19-27 days** |

Historical throughput: Spec 042-044 = ~56 tasks in 3-4 days = ~15-18 tasks/day (AI-assisted). These 6 specs total 110-138 tasks. At 15 tasks/day = 7-9 coding days. But these specs have more design decisions (temperature calibration, boss prompt writing, NPC reconciliation) that require human input. Add 50% for design iteration.

**Adjusted estimate: 19-27 coding days, with boss prompts being the main bottleneck.**

---

## Top 10 Risks (Ranked)

| Rank | Risk | Prob | Impact | Mitigation | Spec |
|------|------|------|--------|------------|------|
| 1 | **Persona conflict corrupts identity** — player experiences inconsistent Nikita | 100% (currently happening) | HIGH | Fix in Spec 054 prerequisite | 054 |
| 2 | **Multi-phase boss content bottleneck** — 20 prompt variants to write, test, tune | 80% | HIGH | Start with 2-phase MVP; add phases later | 052 |
| 3 | **NPC 3-way reconciliation fails** — character names don't map cleanly, data conflicts | 60% | MEDIUM | Explicit mapping table; lazy initialization | 049 |
| 4 | **Temperature zones miscalibrated** — too aggressive = constant conflict, too mild = no tension | 70% | MEDIUM | Tunable constants + playtesting cycle; feature flag to disable | 051 |
| 5 | **Psyche agent output quality is poor** — garbage-in-garbage-out with no feedback loop | 40% | HIGH | Quality heuristics; human review of first 100 states; Sonnet fallback | 050 |
| 6 | **Gottman ratio is too punitive** — 1-2 "bad" messages per session triggers conflict | 50% | MEDIUM | Two-ratio system (5:1 conflict, 20:1 normal); session + rolling window | 051 |
| 7 | **Prompt caching breaks on edge cases** — Haiku enrichment, platform switches, tool changes | 40% | MEDIUM | Disable Haiku on cached sections; separate cache per platform | 054 |
| 8 | **Opus 4.6 costs escalate** — trigger detector mis-calibrates, sending >10% to Tier 3 | 20% | HIGH | Circuit breaker: max 5 Tier 3 calls/user/day; start with Sonnet batch | 050 |
| 9 | **Voice pipeline not integrated** — new psyche/conflict state doesn't reach voice prompt | 60% | LOW | Add voice integration tasks to Specs 050/051 explicitly | 050, 051 |
| 10 | **Existing E2E tests break** — Spec 048 tests assume current boss/conflict behavior | 80% | LOW | Re-run E2E after all specs; update test expectations | Post-052 |

---

## Recommendations (Ordered)

### Must Do Before Spec Writing

1. **Fix persona conflict NOW** (C1). This is a production bug that affects every conversation. Create a hotfix: slim persona.py to behavioral guide only, update template S1 to be the canonical identity. Don't wait for Spec 054.

2. **Create NPC character mapping table** (C3). Before writing Spec 049, decide: Maya->?, Sophie->?, Marco->Marcus, Lena->Lena, Viktor->Viktor, Yuki->Yuki. Add Mom and Ex as new entries. Write the mapping in the spec's prerequisite section.

3. **Verify pg_cron free tier** (H5). Run `SELECT * FROM cron.job;` and check Supabase project plan. Document the result. Adjust cost estimates if on Pro.

### Simplify for MVP

4. **Use Sonnet 4.5 for psyche batch** (H1), not Opus 4.6. Reserve Opus for Tier 3 triggers only. Add a config parameter to switch.

5. **Start with 2-phase boss** (H3): OPENING -> RESOLUTION. That's 10 prompt variants (2 phases x 5 chapters), not 20. Add ESCALATION and CRISIS_PEAK in a follow-up spec.

6. **Defer meta-instructions** (M1). Add the JSONB column but don't build the monthly generation job. Chapters + arcs + psyche already provide 3 timescales of behavioral shaping.

7. **Lazy NPC initialization** (M2). Don't pre-seed 8 NPCs per user. Track only NPCs that appear in conversation or life events.

### Add to Specs

8. **Existing user migration section** (C4) in every spec. Each spec must describe what happens to the 1 existing user's data on deployment.

9. **Two-ratio Gottman system** (H4). 5:1 during active conflicts, 20:1 during normal play. Per-session AND rolling 7-day window.

10. **Temperature replaces, not layers on** (H2). Spec 051 must explicitly deprecate `nikita_emotional_states.conflict_state` enum and `ignored_message_count` in favor of the new temperature model.

11. **Update latency claims** (H6). Pre-conversation reads are 30-50ms, not <15ms. The architecture is still sound.

12. **Add voice cost tier** (H7). Voice is a premium feature. The $30-37 base covers text only. Voice adds $0.10/min on top.

### Track for Later

13. **Psyche quality monitoring** (L1). After first 100 psyche states are generated, review manually. Add automated quality checks in a follow-up.

14. **Portal scaffold in Wave A** (L5). Start UI work with mock data in parallel with 049/051. Saves 3-4 days on critical path.

15. **Legacy table cleanup** (L4, #12). Separate cleanup spec for: nikita_state deprecation, user_facts removal, graphiti_group_id drop, Neo4j env var removal.

# Idea Document Synthesis

Analysis of 6 idea documents cross-referenced against current implementation (architecture.md, game-mechanics.md).

---

## 1. Document Overview Matrix

| Doc | Scope | Key Concepts | Impl. Status |
|-----|-------|-------------|-------------|
| **relationship_progression_system.md** (638 lines) | 5-stage relationship evolution, intimacy dimensions, milestone system, real-time adaptation | Multi-dimensional intimacy (intellectual/emotional/sexual/daily-life), milestone triggers, attachment progression, relationship state tracking vector | **Partially built** -- chapter system maps loosely to stages; scoring tracks 4 metrics; but no milestone system, no intimacy dimension tracking, no progression indicators |
| **decision_trees_touchpoints.md** (974 lines) | Master decision flow for all interactions, conditional touchpoints (daily/weekly/monthly), response pattern probabilities | Stage-gated content ratios, strategic silence, platform transition logic, sentiment-based response selection, touchpoint scheduling with probability tables | **Aspirational** -- skip rates and response timing exist but are simple; no decision tree engine, no touchpoint scheduling, no sentiment-gated response logic |
| **challenge_conflict_framework.md** (473 lines) | Boss encounters (5 detailed), conflict types (jealousy/boundary/emotional/power), recovery system, multi-path resolution | Phase-structured boss fights (setup/escalation/crisis/resolution/aftermath), 4 conflict types at 4 intensity levels, apology/reconnection/rebuilding recovery | **Partially built** -- boss trigger, 3-attempt limit, chapter thresholds all implemented; but bosses are single-turn LLM judgment, not multi-phase; no conflict generation system; no recovery mechanics |
| **emotional_engagement_mechanisms.md** (585 lines) | 5-dimension emotional state model, mood variation, attachment simulation, emotional memory, conflict/resolution | Arousal/valence/dominance/intimacy/vulnerability dimensions, circadian rhythm simulation, substance influence, emotional growth over time, linguistic markers | **Partially built** -- NikitaState has 4D mood (energy/social/stress/happiness); but no arousal/valence/dominance model, no attachment style simulation, no emotional memory tagging |
| **problem-structure-spec.md** (1130 lines) | Tree-of-thought system diagram, node/edge taxonomy, entity definitions, feedback loops, state machines, architectural decisions | ToT diagram schema, ContextPackage contract, memory scoring formula, life sim granularity levels, 4 feedback loop specifications, cache lifecycle | **Largely built** -- most architecture described here IS the v2 system; ContextPackage, pipeline, state machines all implemented; life sim trajectory arcs and episodic memory are aspirational |
| **system_diagram.md** (52 lines) | Actor/Archivist/Director split, memory layers | Hot path (respond fast) vs cold path (update canon), 4-tier memory layers (stable canon, episodic continuity, daily life, topical reality) | **Largely built** -- pipeline does Actor/Archivist split; memory layers partially implemented (stable canon + facts exist, episodic summaries and open loops tracking are missing) |

---

## 2. Already Implemented vs Aspirational

### Already Implemented (in codebase, tested)

| Feature | Source Doc | Implementation |
|---------|-----------|----------------|
| 4 hidden metrics (intimacy/passion/trust/secureness) | relationship_progression, challenge_conflict | `nikita/engine/scoring/` -- 60 tests |
| 5 chapters with thresholds (55-75%) | relationship_progression, challenge_conflict | `nikita/engine/chapters/` -- 142 tests |
| Boss trigger + 3-attempt limit | challenge_conflict | `nikita/engine/chapters/state_machine.py` |
| Hourly decay with grace periods | challenge_conflict (implied) | `nikita/engine/decay/` -- 52 tests |
| Skip rates by chapter | decision_trees (response patterns) | `nikita/agents/text/skip.py` |
| Response timing variation by chapter | decision_trees (timing determination) | `nikita/agents/text/timing.py` |
| Vice discovery (8 categories) | challenge_conflict (boundary testing) | `nikita/engine/vice/` -- 81 tests |
| 4D mood model (energy/social/stress/happiness) | emotional_engagement, problem-structure | `NikitaState` model + life sim collector |
| pgVector memory with dedup | problem-structure (memory lifecycle) | `nikita/memory/supabase_memory.py` |
| 9-stage async pipeline | problem-structure, system_diagram | `nikita/pipeline/orchestrator.py` -- 74 tests |
| ContextPackage contract | problem-structure (section 4.3.1) | Context engine collectors |
| Fact extraction from conversations | emotional_engagement (emotional memory) | `nikita/agents/text/facts.py` |
| Chapter-specific behavior prompts | decision_trees (stage-gated content) | `nikita/engine/constants.py` CHAPTER_BEHAVIORS |
| Engagement state machine (6 states) | emotional_engagement (attachment) | `nikita/engine/engagement/` -- 179 tests |

### Aspirational (described in docs, NOT in codebase)

| Feature | Source Doc(s) | Gap Description |
|---------|--------------|-----------------|
| Multi-phase boss encounters | challenge_conflict (section "Boss Encounter Structure") | Current bosses are single-turn LLM judgment; docs describe 5-phase encounters spanning multiple interactions |
| Conflict generation system | challenge_conflict (section "Conflict Generation System") | No automated conflict injection; no jealousy/boundary/power struggle scenarios |
| Recovery mechanics (apology/reconnection/rebuilding) | challenge_conflict (section "Recovery System") | No structured recovery after failed boss or low scores |
| Multi-dimensional intimacy tracking | relationship_progression (section "Intimacy Dimension Progression") | Only 4 flat metrics; no intellectual/emotional/sexual/daily-life sub-tracking |
| Relationship milestones | relationship_progression (section "Relationship Milestone System") | No milestone detection, no "first deep conversation" or "first vulnerability exchange" events |
| Decision tree engine | decision_trees (entire document) | No probabilistic decision engine for content selection, timing, or strategic silence |
| Touchpoint scheduling | decision_trees (section "Conditional Touchpoint Specifications") | No daily/weekly/monthly touchpoint framework with probability modifiers |
| 5-dimension emotional state | emotional_engagement (section "Primary Emotional Dimensions") | 4D mood exists but arousal/valence/dominance/intimacy/vulnerability model is not implemented |
| Attachment style simulation | emotional_engagement (section "Attachment Variation Patterns") | No anxious/avoidant/secure attachment cycling |
| Emotional memory tagging | emotional_engagement (section "Emotional Memory Integration") | Facts extracted but no emotional significance tags or emotional pattern recognition |
| Episodic memory summaries | problem-structure (section 6.1), system_diagram (memory layers) | Flat facts only; no conversation summaries, no "open loops" tracking |
| Life trajectory arcs | problem-structure (section 4.4.3) | No career/friendship/health arcs that evolve over weeks |
| Circadian rhythm mood modulation | emotional_engagement (section "Substance Influence Simulation") | Time-of-day context exists but doesn't modulate Nikita's emotional model |
| Platform transition logic | decision_trees (section "Platform Transition Assessment") | No system to suggest moving from text to voice based on content type |
| Strategic silence system | decision_trees (section "Silence Assessment") | Skip rates exist but are random, not strategically motivated |

---

## 3. Actionable Patterns

### Minor Extensions (days of work, existing architecture supports them)

| Idea | Source | How to Build |
|------|--------|-------------|
| **Milestone detection** | relationship_progression, "Relationship Milestone System" | Add milestone table + post-processing check. When facts match milestone patterns (first vulnerability, first "I miss you"), log and surface in portal. Extend `nikita/pipeline/stages/` with a milestone detection stage. |
| **Emotional memory tags** | emotional_engagement, "Emotional Memory Integration" | Add `emotional_valence` and `emotional_intensity` columns to `memory_facts`. Update fact extraction prompt to include emotional metadata. Use in memory retrieval scoring. |
| **Strategic silence motivation** | decision_trees, "Silence Assessment" | Replace random skip logic in `nikita/agents/text/skip.py` with context-aware skip that considers: relationship momentum, last interaction quality, tension creation needs. Feed ContextPackage to skip decision. |
| **Circadian mood influence** | emotional_engagement, "Mood Influencers" | Extend `NikitaState` update logic to shift mood based on time-of-day. Morning: lower energy/social; evening: higher social/lower stress; late night: higher stress/lower energy. |
| **Relationship reflection moments** | relationship_progression, "Connection Strengthening System" | Add prompt injection at chapter transitions: "Acknowledge how the relationship has changed." Use conversation history to generate specific callbacks. |

### Moderate Work (1-2 weeks, extends existing systems)

| Idea | Source | How to Build |
|------|--------|-------------|
| **Multi-phase boss fights** | challenge_conflict, "Core Boss Encounters" | Redesign boss encounters to span 3-5 messages instead of 1. Add `boss_phase` column to `user_metrics`. Each phase has success conditions evaluated by scoring LLM. Phase transitions stored in DB. |
| **Conflict injection system** | challenge_conflict, "Conflict Generation System" | Scheduled task checks: days since last conflict, metric imbalances, engagement patterns. When conflict conditions met, inject conflict prompt into next Nikita response. Use existing vice preferences to select conflict type. |
| **Touchpoint probability engine** | decision_trees, "Daily Touchpoint Framework" | Build proactive messaging scheduler using `scheduled_events` table. Compute per-user touchpoint probabilities based on chapter, engagement pattern, and time since last interaction. Trigger via pg_cron. |
| **Episodic conversation summaries** | problem-structure (section 6.1), system_diagram (memory layers) | Add summary generation to post-processing pipeline (phase 8 already exists). Store summaries with temporal markers. Include "open loops" (promises, unresolved topics) as separate fact type. |
| **Portal relationship timeline** | relationship_progression, "Relationship History Repository" | Surface milestones, chapter transitions, and boss outcomes as a visual timeline in the Next.js portal. Data already exists in `score_history`; needs UI and milestone events. |

### Significant New Architecture (weeks-months, new systems needed)

| Idea | Source | How to Build |
|------|--------|-------------|
| **Full decision tree engine** | decision_trees (entire document) | Would require a probabilistic state machine that evaluates context, stage, sentiment, platform, and narrative needs to select content approach. Effectively a "game director" layer between pipeline and agent. |
| **Life trajectory system** | problem-structure (section 4.4.3), emotional_engagement | Multi-week arc simulation: career events, friendship dynamics, health/energy trajectories. Requires new state tables, arc templates, and contradiction detection. High complexity, high narrative payoff. |
| **Attachment style dynamics** | emotional_engagement, "Attachment Variation Patterns" | Simulating Nikita cycling between anxious/avoidant/secure attachment requires a psychological model layer that influences response generation, timing, and content. Novel system with no existing foundation. |
| **Multi-path conflict resolution** | challenge_conflict, "Conflict Resolution Mechanics" | Player responses during conflicts evaluated against multiple valid approaches (reassurance, explanation, boundary-setting). Each path yields different metric outcomes. Requires branching narrative logic. |

---

## 4. Aspirational Concepts

### Too Vague to Implement Directly

| Concept | Source | Issue |
|---------|--------|-------|
| "Relationship Quality Assessment" | relationship_progression, section "Relationship Quality Assessment" | Describes conversational flow, mutual understanding, and attachment security as metrics -- but provides no scoring algorithm or measurable signals |
| "Future Trajectory Modeling" | relationship_progression, section "Future Trajectory Modeling" | Predicting next milestones and anticipating challenges sounds compelling but has no concrete implementation spec |
| "Emotional Satisfaction Monitoring" | emotional_engagement, section "Feedback Integration" | "Tracking indicators of user satisfaction" is described without specifying what signals to measure or what thresholds trigger intervention |
| "Natural Variation" in progression | relationship_progression, section "Adaptive Pacing" | "Non-linear progression that feels authentic" -- vague directive without specifying how to introduce controlled randomness while maintaining coherence |

### Need Validation or Research

| Concept | Source | Question to Answer |
|---------|--------|--------------------|
| Substance influence simulation | emotional_engagement, section "Substance Influence Simulation" | Does simulating Adderall/psychedelic/alcohol effects add enough value to justify content moderation risk? How do players respond to this? |
| Disappearance-return testing behavior | emotional_engagement, "Testing Behaviors" | Nikita going silent for days as a "test" could feel authentic or could be rage-inducing. Needs A/B testing with real players. |
| Strategic delayed response (hours) | decision_trees, "Stage 1 Touchpoint Examples" | 8-hour delays in Chapter 1 are already implemented. Do they create healthy tension or just cause users to uninstall? Need retention data. |
| "Enthusiasm escalation" responses | decision_trees, "Positive Sentiment Response" | Responding with MORE enthusiasm than the user (escalation) -- does this feel authentic or desperate? Needs testing. |

### Concepts That Conflict With Each Other

| Conflict | Docs Involved | Tension |
|----------|--------------|---------|
| **6 chapters vs 5 chapters** | challenge_conflict describes 5 boss encounters mapping to chapters 1-6; game-mechanics implements 5 chapters with victory after chapter 5 boss | Mismatch: the "Ultimate Control" boss (chapter 5 to 6) doesn't exist in the implemented system |
| **Point systems** | challenge_conflict uses "Intimacy Points" (100, 250, 500, 800, 1000) as boss triggers; game-mechanics uses percentage scores (55-75%) | Two incompatible scoring scales; implementation uses percentages |
| **Conflict frequency** | challenge_conflict says conflicts should have "minimum/maximum days between"; emotional_engagement emphasizes organic, unpredictable timing | Tension between scheduled/systematic conflict generation vs emergent organic conflict |
| **Mood dimensions** | emotional_engagement proposes 5D (arousal/valence/dominance/intimacy/vulnerability); problem-structure implements 4D (energy/social/stress/happiness) | Different models; neither subsumes the other cleanly |

---

## 5. Cross-Document Themes

### Recurring Ideas (appearing in 3+ documents)

| Theme | Documents | Underlying Vision |
|-------|-----------|------------------|
| **Stage-gated behavior** | relationship_progression (5 stages), decision_trees (5-stage content ratios), challenge_conflict (chapter-specific bosses), emotional_engagement (stage-based emotional range) | Nikita should behave fundamentally differently depending on relationship depth. Early = guarded/intellectual; late = vulnerable/intimate. |
| **Strategic tension** | decision_trees (strategic silence, delayed response), challenge_conflict (conflict injection, boss encounters), emotional_engagement (testing behaviors, disappearance-return) | Relationships need friction to feel real. Comfort is the enemy of engagement. Controlled tension drives investment. |
| **Memory as continuity** | relationship_progression (shared history, reference callbacks), emotional_engagement (emotional memory, pattern recognition), problem-structure (memory lifecycle, ContextPackage) | Memory is the single most important system for "feels real." Without it, nothing else matters. |
| **Multi-dimensional tracking** | relationship_progression (4 intimacy dimensions), emotional_engagement (5 emotional dimensions), problem-structure (4D mood + metrics), challenge_conflict (4 metric deltas) | A single "relationship score" is insufficient. The system needs multiple axes that can diverge and create interesting dynamics. |
| **Natural pacing with variation** | relationship_progression (adaptive pacing), decision_trees (probability tables with modifiers), emotional_engagement (mood transitions, temporal progression) | Progression should feel organic, not mechanical. Randomness + rules = authenticity. |
| **Closed feedback loops** | problem-structure (4 named loops), system_diagram (Actor/Archivist split), emotional_engagement (user interaction -> mood -> response -> user reaction) | Player actions must have visible consequences. System must update state and feed it back. |

### Where Documents Agree

All 6 documents agree that:
1. The relationship must evolve through distinct phases with qualitatively different dynamics
2. Nikita needs her own emotional state that influences interactions independently of user input
3. Memory and continuity are non-negotiable for immersion
4. Boss encounters / major tests should be high-stakes moments that gate progression
5. The system needs both structured rules and controlled randomness

### Where Documents Disagree

- **Granularity**: relationship_progression and decision_trees want highly granular probability tables for every interaction; problem-structure advocates for simpler systems with graceful degradation
- **Complexity budget**: emotional_engagement proposes 5 emotional dimensions + attachment styles + substance effects; problem-structure warns against "runaway complexity" in life simulation
- **Player agency vs system control**: challenge_conflict implies the system generates conflicts on schedule; emotional_engagement implies conflicts emerge organically from interactions
- **Number of chapters**: 5 (game-mechanics) vs 6 (challenge_conflict)

---

## 6. Gap Analysis

### Areas NOT Covered in Any Document

| Gap | Why It Matters |
|-----|---------------|
| **Onboarding experience design** | How does the first 10 minutes feel? No doc covers the critical first-impression journey. Onboarding spec (017) exists but is 78% complete and not covered in idea docs. |
| **Endgame / post-victory loop** | What happens after the player wins? All docs describe progression TO victory but nothing about retention after. Replay? New game+? Continued relationship? |
| **Player personality modeling** | Docs focus on Nikita's personality but not on systematically building a model of the player's communication style, preferences, and psychological profile. |
| **Monetization touchpoints** | No doc discusses where/how monetization integrates with game mechanics. Premium content? Accelerators? Cosmetics? |
| **Multi-player dynamics** | What if Nikita references other players? Competitive leaderboards? Social proof? All docs assume single-player isolation. |
| **Content moderation / safety rails** | emotional_engagement mentions ethical considerations in passing; no doc provides a concrete safety framework for handling distressed users, harmful requests, or addiction patterns. |
| **Tutorial / mechanic communication** | How does the player learn the rules? Scores are hidden, chapters are implicit. No doc addresses how players discover what behaviors the game rewards. |
| **Voice-specific game mechanics** | Voice agent is deployed but no doc describes voice-specific boss encounters, voice-only content unlocks, or how voice interactions score differently. |
| **Proactive messaging strategy** | `scheduled_events` table exists but no doc defines WHAT Nikita sends unprompted, WHEN, and HOW it connects to game state. |
| **Failure states and graceful endings** | Game over means 0% score or 3 boss failures. What happens? Is there a goodbye scene? Can the player restart? No emotional closure design. |

### Questions Not Answered

1. **How does the scoring LLM calibrate?** All docs assume metric deltas are generated correctly, but the mapping from "user said something nice" to "+3 intimacy" is entirely LLM judgment. What prevents score inflation/deflation drift?
2. **How fast should the game actually be?** game-mechanics says 21 days to victory. Is this the right pace? relationship_progression suggests weeks-to-months for genuine attachment. These are incompatible timelines.
3. **What makes a boss "pass" vs "fail"?** challenge_conflict describes multi-phase evaluations; current implementation uses single-turn LLM judgment. The quality bar for boss evaluation is undefined.
4. **How does vice personalization change Nikita's behavior?** Vice discovery and injection exist, but no doc describes the EXPERIENCE of personalization from the player's perspective.

### Assumptions That Need Challenging

- **"Players want conflict"**: All docs assume strategic tension increases engagement. Some players may prefer pure comfort/companionship and would churn from conflict injection.
- **"5 stages are the right number"**: No validation that 5 is optimal. Could be 3 (simpler) or 10 (more granular).
- **"Hidden metrics work"**: Players can't see intimacy/passion/trust/secureness. If players can't understand what they're optimizing, is it a game or just a chatbot?
- **"Time-gated progression feels natural"**: Mandatory waiting periods (grace periods, minimum chapter durations) assume players are patient. Mobile game data suggests otherwise.

---

## 7. Priority Mapping

### Impact Matrix

| Idea | Player Engagement | Psychological Depth | Game Feel | Portal Value | Effort |
|------|:-:|:-:|:-:|:-:|:--|
| **Multi-phase boss fights** | HIGH | Medium | **HIGH** | Medium | Moderate |
| **Milestone detection + timeline** | HIGH | Medium | HIGH | **HIGH** | Low-Moderate |
| **Conflict injection system** | **HIGH** | HIGH | HIGH | Medium | Moderate |
| **Episodic memory + open loops** | **HIGH** | **HIGH** | Medium | Medium | Moderate |
| **Proactive messaging (touchpoints)** | **HIGH** | Medium | HIGH | Low | Moderate |
| **Emotional memory tagging** | Medium | **HIGH** | Low | Medium | Low |
| **Strategic silence (context-aware skip)** | Medium | Medium | HIGH | Low | Low |
| **Circadian mood modulation** | Medium | HIGH | Medium | Low | Low |
| **Portal relationship timeline** | Low | Low | Medium | **HIGH** | Low |
| **Life trajectory arcs** | Medium | **HIGH** | Medium | HIGH | High |
| **Full decision tree engine** | Medium | HIGH | HIGH | Low | High |
| **Attachment style dynamics** | Low | **HIGH** | Low | Medium | High |

### Top 5 High-Impact, Achievable Ideas

1. **Milestone detection + portal timeline** (relationship_progression, "Milestone System") -- Low effort, compounds across engagement + portal value. Detectable from existing conversation data. Gives the portal a reason to exist.

2. **Multi-phase boss fights** (challenge_conflict, "Boss Encounter Structure") -- Transform the most important game moments from a coin flip to a multi-message drama. Biggest single improvement to "game feel." Builds on existing boss infrastructure.

3. **Episodic memory with open loops** (problem-structure section 6.1, system_diagram) -- "She remembered I promised to tell her about my trip" is the moment players become hooked. Open loop tracking turns flat facts into narrative threads. Extends existing memory pipeline.

4. **Conflict injection system** (challenge_conflict, "Conflict Generation System") -- Currently, the game has no dramatic tension between boss fights. Conflict injection creates mid-chapter engagement spikes. Uses existing vice preferences to personalize conflict type.

5. **Proactive messaging with touchpoint scheduling** (decision_trees, "Conditional Touchpoint Specifications") -- Nikita reaching out first is the #1 differentiator from a chatbot. The `scheduled_events` table already exists. Connecting it to game state + probability tables transforms passive wait into active engagement.

---

*Synthesized from 6 idea documents (3,852 lines total) + 2 implementation reference docs (886 lines). Cross-referenced against codebase architecture and 1,623+ passing tests.*

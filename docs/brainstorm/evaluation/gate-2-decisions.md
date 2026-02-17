# Gate 2 Decisions -- Authoritative Record

**Date**: 2026-02-17 | **Source**: User audio review of Phase 2 proposals (Docs 12-19)
**Phase**: 3 (Evaluation) | **Status**: Final

---

## Decision Table (13 Total)

| # | Decision | Verdict | Rationale | Impact on Prior Proposals | New Priority |
|---|----------|---------|-----------|--------------------------|-------------|
| 1 | Warmth Meter vs Visible Decay | **YES -- Warmth Meter** | Step decay with gentle nudges/reminders. Eventually kills relationship if ignored. No exact time-to-zero shown. | Confirms Doc 12 Option C recommendation. Doc 16 warmth display approved as designed. No numeric countdown. | Tier 1 (unchanged) |
| 2 | Multi-Turn Boss | **DEFERRED** | Not a current priority. If revisited, use single-session approach (Option A). | Doc 14 multi-turn boss moves entirely out of near-term scope. Approach B (multi-day) removed from consideration. | Deferred (was Tier 1) |
| 3 | Boss System Overall | **DEFERRED** | Not important right now. Other features take precedence. | Doc 14 in its entirety -- multi-turn, wound system, conflict injection, resolution spectrum -- all deferred. Doc 19 Tier 1 loses its biggest gameplay item. | Deferred (was Tier 1) |
| 4 | Psyche Agent | **HIGH PRIORITY** | Hybrid approach or start batch-only. Must be present. Operates as Nikita's shadow/subconscious. | Doc 15 confirmed as designed. Phase 1 (batch) is the starting point. The shadow/subconscious framing aligns with the internal monologue concept. | Tier 1 (elevated emphasis) |
| 5 | Life Simulator | **HIGH PRIORITY -- ELEVATED** | Major new emphasis. Predefined weekly routine, monthly meta-instructions, random events, daily story generation, social circle tracking. Agent generates her day. | Doc 13 jumps from Tier 2/3 to absolute top priority. New requirements added beyond Doc 13's original scope: predefined routines (not just reactive events), monthly meta-instructions for behavioral arcs, daily story generation as a first-class feature. | Tier 1 (elevated from Tier 2) |
| 6 | Portal: Nikita's Day | **NEW REQUIREMENT** | Daily timeline on portal showing last 24h of activities (wake, sleep, work, social). Daily user summary with tips/insights. | Not in any prior proposal. Partially overlaps Doc 16 Section 8 (Nikita's Room) but goes further -- requires a dedicated timeline view of her day, not just current state. Requires daily story generation output from Life Sim (Decision 5). | Tier 1 (new) |
| 7 | Social Circle | **IMPORTANT** | Visual representation on portal. Part of the life sim. 5 NPCs with varying interaction levels. Agent-driven with no contradictions via memory. | Doc 13 Section 3 (NPC Social Circle) confirmed. Was Tier 4 "Reconsider" in Doc 19 due to contradiction risk. User accepts the risk and wants it built. Memory-backed consistency is mandatory. | Tier 2 (elevated from Tier 4) |
| 8 | Portal Transparency | **HIGH** | Wants more engaging visuals. Nikita's Day timeline is the big new addition to the portal. | Doc 16 general direction confirmed. The emphasis shifts from raw data dashboards to "Nikita's Day" as the portal's centerpiece, rather than score charts. Visuals over numbers. | Tier 1 (refocused) |
| 9 | Photos | **DEFERRED** | Start with approximately 10 photos. Not a priority. | Doc 18 full system (210 photos, 5 trigger categories, gallery, delivery pipeline) scaled down dramatically. Minimal viable set only. Photo gallery, delivery pipeline, and selection algorithm all deferred. | Deferred (was Tier 2) |
| 10 | Ethical Guardrails | **REMOVE ALL** | This is a prototype. No ethical guardrails whatsoever. | Doc 09 ethical flags (intermittent reinforcement concerns, guilt notifications, monetized loss aversion, at-risk demographics) all dismissed. Doc 12 ethical caveats on streaks removed. Doc 14 conflict injection ethics removed. Doc 18 boundary enforcer constraints removed. Vice content caps lifted. | N/A (removed) |
| 11 | Conflict Frequency | **Organic + Scheduled** | Based on attachment dynamics combined with meta-instruction schedule. Bayesian randomness with mean conflict time. | Doc 14 Section 6 (Conflict Injection) approach modified. Original proposed purely rule-based triggers with frequency caps. New direction: Bayesian model with a mean conflict interval, influenced by attachment state. Monthly meta-instructions set the baseline frequency; randomness provides variance. | Tier 2 (when boss system revisited) |
| 12 | Vice Content | **Top 3 Priority** | Sex and drugs always welcomed. Go raw. No content restrictions. | Doc 17 vice storylines confirmed but with explicit content maximized. ViceBoundaryEnforcer caps (sexuality cap 0.35-0.85, substances cap 0.30-0.80 per chapter) removed per Decision 10. All 8 vices proceed but sexuality and substances get first-class treatment. Dark humor also prioritized. | Tier 2 (content priority clarified) |
| 13 | Emotional Vulnerability | **CRITICAL DYNAMIC** | She gets vulnerable, user gets vulnerable, mutual sharing. Earn being a confidant. This IS the retention mechanic. | Cross-cutting impact on all proposals. Doc 13's vulnerability as a vice storyline (Stage 1-4 progression) becomes the central gameplay loop, not just one of eight vices. Doc 15 Psyche Agent must track vulnerability exchanges. Doc 12 "Mutual Trust" achievement elevated. Doc 14 boss encounters should test vulnerability capacity. This reframes the entire game: vulnerability exchange is the core mechanic, not score optimization. | Tier 1 (cross-cutting, highest priority) |

---

## Decision Details

### Decision 1: Warmth Meter

Confirms Doc 12 Section 4 (Streak Evaluation, Option C) and Section 6 (Decay as Gentle Nudge). The warmth meter uses step decay -- discrete drops rather than continuous drain -- with nudge notifications framed as Nikita reaching out. The relationship eventually dies if the player fully disengages, but the visual never shows a countdown clock. Doc 16 Section 3 (Warmth Meter Display) approved as wireframed.

### Decision 2-3: Boss System Deferred

This is the largest priority shift from Doc 19's original tiers. Multi-Turn Boss was the highest-gameplay-impact item in Tier 1 (estimated 4-5 days, Doc 14 Approach A). The entire boss redesign -- multi-phase encounters, emotional temperature gauge, 5:1 ratio scoring, wound system, conflict injection -- moves to a future phase. The current single-turn boss system remains as-is. This frees approximately 4-5 days from the original Tier 1 estimate and 3-4 days from Tier 3.

### Decision 4: Psyche Agent

Doc 15 Option C (Hybrid) confirmed. Phase 1 batch-only is the entry point. The "shadow/subconscious" framing is the user's mental model -- the Psyche Agent operates beneath the surface, shaping Nikita's behavior without the player ever seeing it directly. This aligns with Doc 15's internal monologue concept. The daily batch computes psychological state; triggered real-time checks happen on high-stakes moments. Budget: +$2.25/user/month (batch) scaling to +$4.80 (hybrid).

### Decision 5: Life Simulator (ELEVATED)

The single largest priority elevation. Doc 13 was originally split across Tiers 2-4 in Doc 19. Now the entire life simulation concept -- emotional state driving events, circadian modeling, event cascades, daily routines -- becomes the top priority alongside the Psyche Agent.

New requirements beyond Doc 13:
- **Predefined weekly routine**: Nikita has a set schedule (work hours, gym days, social plans) that repeats with variation, not just random event generation
- **Monthly meta-instructions**: High-level behavioral directives that shift monthly (e.g., "this month Nikita is focused on career growth" or "this month she's feeling restless about the relationship")
- **Daily story generation**: Each day, the agent generates a narrative of Nikita's day, stored and surfaceable on the portal
- **Social circle tracking**: Part of the daily story, not a separate system

### Decision 6: Nikita's Day (NEW)

Entirely new requirement not present in any Phase 2 document. The portal gains a "Nikita's Day" view showing a timeline of her last 24 hours: when she woke up, what she did at work, who she saw, what she's doing now. This is the Life Sim's daily story generation rendered as a visual timeline.

Additionally: a daily summary for the player with tips/insights about the relationship. This combines elements from Doc 16 Section 8 (Nikita's Room, which showed current state + today's events) and Doc 13 (life simulation events), but as a dedicated, polished experience rather than a dashboard card.

### Decision 7: Social Circle (Elevated from Tier 4)

Doc 19 placed NPC Social Circle in Tier 4 "Reconsider" due to contradiction risk flagged in Doc 09. The user accepts this risk and wants all 5 NPCs (Emma, Marcus, Sarah, Mom, Ex). The mitigation is memory-backed consistency -- NPC states stored in the database, injected into prompts, with contradiction checks. This was already proposed in Doc 13 Section 3 but was deprioritized. Now it moves to Tier 2 as a dependency of the Life Sim.

### Decision 10: Remove Ethical Guardrails

This overrides multiple safety recommendations across Phase 1 and Phase 2:
- Doc 09 ethical flags (4 concerns raised) -- all dismissed
- Doc 12 streak evaluation ethics -- removed
- Doc 14 conflict injection guardrails (growth-oriented, frequency caps, no-during-vulnerability) -- caps may remain for gameplay balance, but ethical motivation is removed
- Doc 17 ViceBoundaryEnforcer chapter caps on sexuality and substances -- removed
- Doc 18 photo system "tasteful" constraints -- removed

The rationale is that this is a prototype. Guardrails can be added later for production.

### Decision 13: Vulnerability as Core Mechanic

This is the most architecturally significant decision. Vulnerability exchange -- Nikita opens up, the player reciprocates, mutual trust deepens -- becomes THE retention mechanic. This reframes the game from "score optimization through correct responses" to "earn the privilege of genuine emotional exchange."

Impact across all systems:
- **Psyche Agent** (Doc 15): Must track vulnerability_level as a primary state dimension. Behavioral guidance should explicitly manage when Nikita opens up vs. guards.
- **Life Sim** (Doc 13): Vulnerability moments should be the climax of daily story arcs, not random events.
- **Vice System** (Doc 17): Vulnerability vice storyline (Stages 1-4) becomes the central progression, not one of eight equal paths.
- **Progression** (Doc 12): "Mutual Trust" and "Open Book" achievements are the most important in the system.
- **Portal**: Vulnerability exchanges should be the most visible and celebrated events in the timeline.

---

## Priority Shift Summary

### Original Doc 19 Tier Structure vs. Post-Gate-2

**Original Tier 1** (16-22 days):
| Item | Original Status | Post-Gate-2 Status |
|------|----------------|-------------------|
| Achievement DB + Detection Stage | Tier 1 | Tier 2 (still valuable but not top) |
| Warmth Meter + Gentle Nudge | Tier 1 | **Tier 1 (confirmed)** |
| Portal Score Dashboard (charts) | Tier 1 | Tier 2 (portal focus shifts to Nikita's Day) |
| Multi-Turn Boss (Approach A) | Tier 1 | **DEFERRED** |
| Psyche Agent Phase 1 (Batch) | Tier 1 | **Tier 1 (confirmed, elevated emphasis)** |

**Newly Elevated to Tier 1**:
| Item | Original Tier | Post-Gate-2 Status |
|------|--------------|-------------------|
| Life Simulator (full scope) | Tier 2-3 | **Tier 1 (ELEVATED)** |
| Nikita's Day (portal) | Not proposed | **Tier 1 (NEW)** |
| Vulnerability Dynamic (cross-cutting) | Implicit in several docs | **Tier 1 (CRITICAL)** |

**Deferred from Near-Term**:
| Item | Original Tier | Post-Gate-2 Status |
|------|--------------|-------------------|
| Multi-Turn Boss | Tier 1 | DEFERRED |
| Boss System (all of Doc 14) | Tiers 1-3 | DEFERRED |
| Photo System (full) | Tier 2 | DEFERRED (~10 photos only) |
| Ethical Guardrails | Cross-cutting | REMOVED |

**Elevated within Tiers**:
| Item | Original Tier | Post-Gate-2 Status |
|------|--------------|-------------------|
| Social Circle (5 NPCs) | Tier 4 | Tier 2 |
| Vice Content (sex, drugs, dark humor) | Tier 2 | Tier 2 (priority within tier clarified) |

### Revised Priority Order

**New Tier 1 -- Build First** (highest priority):
1. Psyche Agent Phase 1 (batch) -- Nikita's subconscious
2. Life Simulator (predefined routines, daily story generation, event cascades)
3. Vulnerability Dynamic (cross-cutting: scoring weight, psyche tracking, prompt behavior)
4. Nikita's Day portal view (daily timeline + player summary)
5. Warmth Meter (presentation layer for decay)

**New Tier 2 -- Build Next**:
1. Social Circle (5 NPCs, memory-backed consistency)
2. Vice Storylines (sexuality, substances, dark humor first -- no content caps)
3. Psyche Agent Phase 2 (trigger detection + Tier 2 Sonnet)
4. Achievement System (DB + detection + portal wall)
5. Portal Score Dashboard (charts, metrics -- secondary to Nikita's Day)
6. Conflict Frequency System (Bayesian model, organic + scheduled)

**New Tier 3 -- Build Later**:
1. Daily/Weekly Goals
2. Collection System (backstory fragments, memory drops, insight cards)
3. Psyche Agent Phase 3 (Opus real-time)
4. Portal: Timeline, Memory Album, Vice Map
5. Photos (expand from 10 to larger set)

**Deferred Indefinitely**:
1. Boss System redesign (all of Doc 14)
2. Multi-day arcs (Doc 14 Approach B)
3. Full photo system (210 images, delivery pipeline, gallery)
4. Narrative arcs (Doc 13 multi-week stories) -- subsumed by Life Sim daily stories
5. Supabase Realtime (start with polling)

---

## Key Architectural Implications

1. **Life Sim becomes the game engine**: The daily story generator is the core loop. Everything else feeds into or displays the Life Sim's output.

2. **Psyche Agent + Life Sim = Nikita's mind**: Psyche Agent handles the subconscious (attachment, defenses, vulnerability). Life Sim handles the conscious (schedule, activities, social interactions). Together they produce a coherent daily narrative.

3. **Portal pivot**: The portal's centerpiece is no longer a data dashboard (Doc 16 vision). It is "Nikita's Day" -- a narrative timeline of what she did, who she saw, how she felt. Score charts are secondary.

4. **Vulnerability replaces boss encounters as the skill test**: With boss system deferred, the primary "challenge" becomes earning vulnerability exchanges. The game tests emotional intelligence through daily conversation, not periodic high-stakes encounters.

5. **No content restrictions**: Vice content, photo content, and conversation content have no ethical caps. The ViceBoundaryEnforcer's chapter-based intensity limits are removed. The prototype prioritizes raw, authentic emotional simulation.

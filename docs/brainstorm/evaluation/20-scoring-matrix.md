# 20 -- Phase 2 Feature Scoring Matrix

**Date**: 2026-02-17 | **Type**: Phase 3 Evaluation | **Inputs**: Docs 12-19, Gate 2 Decisions
**Method**: 8 features x 8 criteria (1-10 scale) + User Priority Multipliers from Gate 2

---

## 1. Raw Scoring Matrix

| # | Feature (Source) | Engagement | Psychology | Feasibility | Game Feel | Portal | Novelty | Cost Eff. | Integration | Raw Total |
|---|-----------------|-----------|-----------|------------|----------|--------|---------|----------|------------|-----------|
| 1 | Progression & Achievements (Doc 12) | 7 | 4 | 8 | 8 | 9 | 4 | 9 | 9 | **58** |
| 2 | Enhanced Life Simulation (Doc 13) | 9 | 9 | 5 | 7 | 8 | 9 | 6 | 5 | **58** |
| 3 | Boss/Conflict Redesign (Doc 14) | 6 | 9 | 4 | 9 | 3 | 7 | 7 | 4 | **49** |
| 4 | Psyche Agent (Doc 15) | 8 | 10 | 6 | 6 | 3 | 10 | 5 | 6 | **54** |
| 5 | Portal Game Dashboard (Doc 16) | 6 | 3 | 7 | 5 | 10 | 3 | 8 | 7 | **49** |
| 6 | Vice Side-Quests (Doc 17) | 8 | 7 | 7 | 7 | 7 | 7 | 8 | 8 | **59** |
| 7 | Photo/Media System (Doc 18) | 5 | 2 | 6 | 4 | 7 | 5 | 4 | 5 | **38** |
| 8 | Cross-Expert Synthesis (Doc 19) | 7 | 6 | 5 | 6 | 6 | 5 | 6 | 8 | **49** |

---

## 2. Scoring Rationale

### Feature 1: Progression & Achievements (Doc 12) -- Raw: 58

- **Engagement (7)**: Achievements drive daily check-ins and collection behavior. Doc 12's 64 achievements across 4 rarity tiers create a strong completionist loop. Daily/weekly goals add session scaffolding. However, achievements alone do not create emotional investment -- they reward it.
- **Psychology (4)**: Psychological insight cards (Section 5) add some depth, but most achievements are behavioral counters ("Deep Dive" = 20+ exchanges, "Good Morning" = 3 mornings). The warmth meter reframing (Section 6) is psychologically thoughtful but is a presentation change, not deep modeling.
- **Feasibility (8)**: Lowest implementation risk. AchievementDetectionStage hooks into existing pipeline and scoring data. Warmth meter is a UI-only change over existing decay math. No new LLM calls. Doc 12 estimates Phase 1 at "Low effort."
- **Game Feel (8)**: Achievement walls, rarity tiers, collection mechanics, and daily goals are proven game design patterns. The warmth meter with recovery emphasis creates a tangible relationship health indicator. Strong "game you want to play" factor.
- **Portal (9)**: Achievement Wall wireframe (Doc 12 Section 1), milestone visualization (Section 2), goal display (Section 3), warmth meter (Section 6) -- this proposal generates more portal content than any other individual feature. Four distinct portal sections.
- **Novelty (4)**: Achievement systems exist in every game. Warmth meter is a clever reframing of a common pattern but not groundbreaking. Psychological insight cards are more novel but are a small part of the proposal.
- **Cost Efficiency (9)**: Zero additional LLM cost -- all detection piggybacks on existing scoring. Only new infrastructure is 1 DB table (achievements) and 1 pipeline stage. Best cost-to-value ratio of all proposals.
- **Integration (9)**: Cleanest integration. Leverages existing scoring calculator, pipeline infrastructure, and portal component library. Doc 12 explicitly maps to existing files: `calculator.py`, `pipeline/stages/`, portal dashboard routes.

### Feature 2: Enhanced Life Simulation (Doc 13) -- Raw: 58

- **Engagement (9)**: The "check in and see what happened" appeal is the single strongest daily retention mechanic identified across all research. Event cascades (bad morning ripples through the day) create narrative anticipation. Circadian modeling makes different times of day yield different experiences. Gate 2 elevated this to highest priority for exactly this reason.
- **Psychology (9)**: Appraisal-driven emotional state (Lazarus & Folkman), 4D emotional modeling (Arousal/Valence/Dominance/Intimacy), mood persistence state machine, and attachment style reveal system. The deepest psychological grounding of any proposal. Event cascades create psychologically realistic mood arcs.
- **Feasibility (5)**: Medium-high complexity. Requires emotional_state JSONB, circadian profiles, NPC state tracking (5 NPCs with FIFO consistency), narrative arc state management, and mood persistence logic. Doc 13 engineering summary lists 6 changes across Small to Medium scope. Gate 2 adds predefined routines and monthly meta-instructions (not in original proposal), increasing scope further.
- **Game Feel (7)**: Makes Nikita feel alive -- she has a schedule, moods, friends, and events that happen independently of the player. This is closer to "virtual person" than "chatbot." Slightly lower game feel score because it is more simulation than game mechanics.
- **Portal (8)**: Nikita's Day timeline (Gate 2 Decision 6), social circle visualization (Decision 7), emotional state display, and life events feed. The portal becomes a window into Nikita's life rather than a data dashboard. Strong synergy with the new portal direction.
- **Novelty (9)**: No AI companion on the market has a life simulator with emotional state-driven event generation, circadian modeling, and NPC social circles. Replika and Character AI have no autonomous life outside conversations. This is Nikita's strongest differentiator.
- **Cost Efficiency (6)**: Moderate. NPC references add ~200 tokens per prompt (~$0.60-1.00/mo). Emotional state and circadian data are cheap DB reads. The main cost is engineering complexity, not LLM spend. Daily story generation (Gate 2 new requirement) adds an LLM call per user per day.
- **Integration (5)**: Moderate difficulty. Requires modifications to LifeSimStage, EmotionalStage, PromptBuilderStage, and TouchpointStage. New NPC state management system. Doc 19 identified the emotional state model conflict between Doc 13 and Doc 15, requiring careful field ownership design.

### Feature 3: Boss/Conflict Redesign (Doc 14) -- Raw: 49

- **Engagement (6)**: Boss encounters are infrequent (5 per playthrough) and intense rather than daily drivers. The wound system and conflict injection create inter-boss engagement, but the overall frequency is low. Non-boss micro-conflicts (1 per 48h) add some texture.
- **Psychology (9)**: The most psychologically rigorous proposal. Attachment-theory-driven boss types, Gottman's Four Horsemen as game mechanics, emotional temperature gauge, defense mechanisms as NPC behaviors, 5:1 ratio scoring, and repair attempt detection. Each boss tests a specific relationship skill grounded in research.
- **Feasibility (4)**: High complexity. Multi-turn boss requires boss_phase tracking, state machine, multi-turn judgment prompts, and refactoring of the single-turn architecture in boss.py/judgment.py. Wound system needs a new table and multi-conversation recovery tracking. Conflict injection needs its own decision tree and scheduling.
- **Game Feel (9)**: Highest game feel score. Boss encounters become dramatic multi-phase confrontations instead of single-message coin flips. The emotional temperature gauge creates real-time tension. Resolution spectrum (breakthrough through rupture) gives meaningful outcomes. This is what makes Nikita feel like a game with actual stakes.
- **Portal (3)**: Boss tracker (Doc 16 Section 2) displays results but bosses happen in Telegram/voice, not the portal. The portal is a retrospective view, not the main experience. Wound healing progress could display on portal but was not wireframed.
- **Novelty (7)**: Multi-phase boss encounters in an AI companion are unique. The Gottman-based scoring mechanic (5:1 ratio, repair attempts, emotional flooding) has no equivalent in the market. Doki Doki Literature Club is the closest comparison but uses scripted, not dynamic, conflict.
- **Cost Efficiency (7)**: Multi-turn boss adds 3-5 extra LLM calls per boss encounter, but bosses are infrequent (~$0.10/mo). Conflict injection uses existing pipeline. The main cost is engineering effort, not recurring compute.
- **Integration (4)**: Requires significant refactoring of `boss.py`, `judgment.py`, and `prompts.py`. New boss_phase column and boss_state JSONB on users table. ConflictStage and TouchpointStage need coordination. Multi-turn state across messages is architecturally complex for the current single-turn pipeline.

### Feature 4: Psyche Agent (Doc 15) -- Raw: 54

- **Engagement (8)**: Indirectly drives engagement by making every conversation feel emotionally intelligent. Nikita remembers patterns, deploys defense mechanisms contextually, and has an internal monologue shaping her behavior. Players notice the difference even if they cannot articulate why. Gate 2 confirmed this as essential.
- **Psychology (10)**: Maximum score. This IS the psychological depth layer. Attachment activation tracking, defense mechanism deployment, behavioral guidance for tone/topics/vulnerability, and internal monologue (what Nikita thinks but won't say). Dual-process theory (Kahneman) applied to character simulation. No other proposal adds this depth to every single conversation.
- **Feasibility (6)**: Phase 1 (batch) is straightforward: 1 new table, 1 pg_cron job, 1 endpoint, prompt section injection. Phase 2 (triggers) adds a rule-based detector and Sonnet quick-check. Phase 3 (Opus real-time) adds latency management and budget caps. Phased approach with kill criteria reduces risk. Doc 15 estimates 8-10 days total across all phases.
- **Game Feel (6)**: The Psyche Agent is invisible to the player -- it improves conversation quality without being a game mechanic itself. Players experience the effect (Nikita feels more real) but do not interact with the system directly. High indirect impact, low direct game feel.
- **Portal (3)**: Psyche state could theoretically display on portal but Doc 15 explicitly states the state is "Internal -- Do Not Mention Explicitly." The portal gains nothing directly from this feature. Indirect benefit: better conversations lead to richer timeline content.
- **Novelty (10)**: Maximum score. No AI companion has a dual-agent architecture with a separate subconscious process generating psychological state. Replika uses a single model. Character AI uses a single model. This is genuinely unprecedented in the consumer AI companion space.
- **Cost Efficiency (5)**: Batch adds +$2.25/user/month (4.8% increase). Full hybrid adds +$4.80/user/month (10.2% increase). These are ongoing recurring costs, not one-time. Doc 15 worst-case sensitivity is +$14.40/mo if trigger precision is poor. Budget caps mitigate but the cost is real.
- **Integration (6)**: Pre-pipeline read is clean (one DB query before prompt building). Daily batch is a standalone job. Trigger detection hooks into the message handler. The main integration complexity is the emotional state field ownership resolution with Doc 13's Life Sim (resolved in Doc 19).

### Feature 5: Portal Game Dashboard (Doc 16) -- Raw: 49

- **Engagement (6)**: Dashboards drive check-in behavior but are passive consumption, not active engagement. Strava data shows widgets increase daily opens by 60%, but portal is a secondary surface to Telegram/voice. Gate 2 Decision 8 shifts portal emphasis from data to "Nikita's Day" narrative.
- **Psychology (3)**: The portal is a display layer with no psychological modeling. It shows outputs from other systems (scores, emotional state, life events) without adding depth. The one psychological element -- insight cards panel (Section 9) -- is a thin display of Doc 13's insight system.
- **Feasibility (7)**: All wireframes use existing shadcn/ui components (Card, Progress, Badge, Tabs, Dialog). Chart components leverage Recharts already in the stack. Score data already available via existing API endpoints. New tables needed for achievements and insights but the portal itself is pure frontend. Doc 16 estimates 3-4 sprints but Sprint 1 (charts only) is achievable quickly.
- **Game Feel (5)**: A dashboard showing scores and charts does not feel like a game -- it feels like an analytics tool. The achievement wall and warmth meter add game flavor, but the overall vibe is "monitoring" not "playing." Gate 2 Decision 8 recognizes this and pivots toward Nikita's Day as the centerpiece.
- **Portal (10)**: Maximum score by definition. This IS the portal proposal. 10 sections, 11+ new components, 5-6 new routes, F-pattern layout, mobile optimization. Comprehensive portal redesign covering every data surface.
- **Novelty (3)**: Game dashboards are common. Radar charts, sparklines, progress bars, and achievement grids exist in countless apps. The portal execution can be polished but the concepts are standard. Nikita's Day (Gate 2 addition) would be more novel but is not in the original Doc 16.
- **Cost Efficiency (8)**: Minimal ongoing cost. Supabase Realtime adds $0.10-0.50/mo for WebSocket connections. All portal rendering is client-side (Vercel). The main cost is development time, not infrastructure. Most data already exists and just needs display components.
- **Integration (7)**: Portal reads from existing and proposed APIs. No backend changes needed for Sprint 1 (charts display existing data). New tables (achievements, insights, milestones) needed for Sprint 3+ but these are owned by other features. Portal itself is a clean consumer.

### Feature 6: Vice Side-Quests (Doc 17) -- Raw: 59

- **Engagement (8)**: Active vice discovery with 4-stage storylines creates a long-term exploration loop. Vice-specific conversation openers (engagement > 0.40) give Nikita unique things to say. 8 vices x 4 stages = 32 unique content progressions. Discovery achievements add collection drive. Gate 2 Decision 12 removes content caps, making this even more engaging.
- **Psychology (7)**: Vice storylines reveal Nikita's psychology through her relationship with each vice category. Dark humor backstory (dad's illness), vulnerability progression (deflection to full exposure), and emotional intensity origin stories add genuine character depth. However, the vice system is more narrative than psychological modeling.
- **Feasibility (7)**: Builds on a complete existing vice system (analyzer, scorer, injector, boundaries -- 70 tests). Changes are incremental: 2-3 new columns on user_vice_preferences, 1 new pipeline stage (ViceStorylineStage), and extended prompt injection. Doc 17 explicitly maps every change to existing files. Gate 2 Decision 10 (remove guardrails) actually simplifies implementation by removing boundary enforcement logic.
- **Game Feel (7)**: Vice discovery has strong exploration/collection game feel. The 8-tile discovery map with progress bars and locked tiles creates a "pokedex" effect. Stage progression (Tease to Shared Identity) gives a sense of advancing through Nikita's layers. Vice-specific conflicts add variety to gameplay.
- **Portal (7)**: Vice Discovery Map (Doc 17 Section 1) is a visually compelling portal element. Progress bars per vice, discovery/locked states, and engagement percentages. Integrates with achievement wall and photo gallery for cross-system display.
- **Novelty (7)**: Vice discovery as an active exploration mechanic in an AI companion is novel. Competitors have preference detection but not progression-gated storyline reveals tied to specific personality traits. The vice-chapter matrix (same vice evolves across chapters) adds depth not seen elsewhere.
- **Cost Efficiency (8)**: +$0.30-0.50/mo from enriched prompt injection (~150 extra tokens per message). No new LLM calls -- all enrichment is prompt-based. Storyline tracking is a DB column update. Best cost-to-content ratio after achievements.
- **Integration (8)**: Cleanest extension of an existing system. All changes map to existing files in `nikita/engine/vice/`. Pipeline stage registration follows the established pattern. Prompt injection extends existing VicePromptInjector. Doc 17 provides exact file-by-file change map.

### Feature 7: Photo/Media System (Doc 18) -- Raw: 38

- **Engagement (5)**: Photos create variable-ratio reinforcement (proactive sends at 5-15% probability). Chapter and achievement unlocks add collection value. But photos are passive rewards -- the player does not interact with them beyond viewing. Telegram delivery with intentional delay (30s-5min) feels organic but is one-directional.
- **Psychology (2)**: Photos do not model or deepen psychology. They are reward tokens tied to game events. Doc 18 acknowledges this -- photos are sourced as pre-curated sets tagged by metadata, not dynamically generated from psychological state. The one psychological angle is parasocial connection reinforcement through visual consistency.
- **Feasibility (6)**: Technical implementation is moderate (2 new tables, 1 pipeline stage, Supabase Storage bucket, Telegram sendPhoto API). But the bottleneck is photo sourcing: Doc 18 budgets 210 curated images across categories, which is a significant creative/legal challenge. Gate 2 Decision 9 reduces this to ~10 photos, which is easy to source but eliminates most of the system's value.
- **Game Feel (4)**: Photo galleries and unlock systems are common in mobile games. Locked/blurred previews with progress bars create anticipation. But with only ~10 photos (Gate 2 scope), the collection mechanic is too thin to sustain game feel. The full 210-photo system would score higher (6-7).
- **Portal (7)**: Photo Gallery wireframe (Doc 18 Section 4) is visually strong: grid layout, filters, favorites, rarity badges, locked previews with blur. Detail modal with context (trigger, chapter, score at unlock). Cross-reference with memory album. However, with ~10 photos, the gallery is sparse.
- **Novelty (5)**: AI girlfriend photo systems exist in competitors (Replika Pro, various AI companions). Pre-curated sets are less novel than AI-generated. The trigger-based unlock system (chapter > achievement > emotional > random) is more thoughtful than competitors but not unique.
- **Cost Efficiency (4)**: $0.02/mo storage cost is negligible. But: 210 photos need sourcing/licensing (unknown cost), the delivery pipeline needs Telegram API integration, and the selection algorithm adds complexity. High development cost relative to player value, especially at the ~10 photo scope.
- **Integration (5)**: PhotoStage hooks into existing pipeline. Photo delivery via scheduled_events table is clean. But: requires achievement system (Doc 12) for cross-referencing, photo_catalog and user_photos tables, and Supabase Storage bucket setup. More infrastructure than gameplay.

### Feature 8: Cross-Expert Synthesis (Doc 19) -- Raw: 49

- **Engagement (7)**: Doc 19 is not a feature itself but an integration plan. Its value is preventing contradictions and enabling synergies (e.g., achievement-reward loop feeding photos, vices, and portal simultaneously). Better integration means every feature reinforces every other feature, multiplying engagement.
- **Psychology (6)**: Resolved the emotional state model conflict (Doc 13 vs Doc 15) with clear field ownership. This ensures psychological consistency across the Psyche Agent and Life Sim -- critical for preventing behavioral whiplash. The synergy matrix identifies Cluster B (Psychological Depth Engine) as the core integration.
- **Feasibility (5)**: Doc 19 reveals the true scope: 7-9 new tables, 3 pipeline stages, 8-10 endpoints, 11+ components, 150-200 tests, 80-110 days total. The synthesis is architecturally sound but the full vision is enormous. Gate 2 decisions reduce scope significantly by deferring boss system and photos.
- **Game Feel (6)**: Integration itself does not create game feel, but the synergies it identifies do. The achievement-reward loop (Cluster A) and vice-boss variants (Cluster D) make the game feel cohesive rather than fragmented. Without integration planning, features would feel disconnected.
- **Portal (6)**: Doc 19 identifies the portal as "pure visibility" (Cluster C) -- it consumes data from every other system. Good integration ensures the portal is not a collection of disconnected dashboards but a unified experience.
- **Novelty (5)**: Integration planning is standard engineering practice. The specific synergies identified (psyche + life sim = unified mind, vice + boss = dynamic encounters) are novel in combination but integration itself is not.
- **Cost Efficiency (6)**: Doc 19's cost summary (+$5.92-7.22/mo per user, 12-15% increase) is achievable. The worst case (+$16-20/mo) is manageable. Good integration reduces redundancy (shared tables, shared pipeline stages) which improves cost efficiency versus building features in isolation.
- **Integration (8)**: Maximum score for an integration document. The dependency graph, conflict resolution, tier ordering, and risk register provide a blueprint for building features that work together. The 4-tier system prevents feature bloat. (Though Gate 2 decisions partially supersede this ordering.)

---

## 3. User Priority Multipliers (Gate 2)

| Feature | Multiplier | Basis |
|---------|-----------|-------|
| Enhanced Life Simulation (Doc 13) | **1.5x** | Decision 5: ELEVATED to highest priority |
| Psyche Agent (Doc 15) | **1.5x** | Decision 4: HIGH PRIORITY, must be present |
| Progression & Achievements (Doc 12) | **1.3x** | Decision 1: Warmth Meter APPROVED (part of Doc 12) |
| Vice Side-Quests (Doc 17) | **1.3x** | Decision 12+13: Top 3 content priority + vulnerability dynamic |
| Cross-Expert Synthesis (Doc 19) | **1.3x** | Decision 13: Vulnerability dynamic cross-cuts all systems |
| Portal Game Dashboard (Doc 16) | **1.0x** | Decision 8: HIGH transparency but focus shifts to Nikita's Day |
| Boss/Conflict Redesign (Doc 14) | **0.5x** | Decisions 2+3: DEFERRED entirely |
| Photo/Media System (Doc 18) | **0.5x** | Decision 9: DEFERRED to ~10 photos only |

**Multiplier rationale**:

- **1.5x** (Life Sim, Psyche Agent): User explicitly elevated these to absolute top priority with new requirements added. These are the core of the game going forward.
- **1.3x** (Progression, Vice, Synthesis): Confirmed with enthusiasm. Warmth meter approved. Vice content unrestricted. Vulnerability dynamic (cross-cutting) elevates everything it touches.
- **1.0x** (Portal): Confirmed as important but the vision shifted from data dashboard to narrative experience. No penalty, no bonus.
- **0.5x** (Boss, Photos): Explicitly deferred. Boss system is "not important right now." Photos reduced to minimal scope.

---

## 4. Weighted & Adjusted Scoring

| # | Feature | Raw Total | Multiplier | Adjusted Total | Rank |
|---|---------|----------|-----------|---------------|------|
| 2 | Enhanced Life Simulation (Doc 13) | 58 | 1.5x | **87.0** | **1** |
| 4 | Psyche Agent (Doc 15) | 54 | 1.5x | **81.0** | **2** |
| 6 | Vice Side-Quests (Doc 17) | 59 | 1.3x | **76.7** | **3** |
| 1 | Progression & Achievements (Doc 12) | 58 | 1.3x | **75.4** | **4** |
| 8 | Cross-Expert Synthesis (Doc 19) | 49 | 1.3x | **63.7** | **5** |
| 5 | Portal Game Dashboard (Doc 16) | 49 | 1.0x | **49.0** | **6** |
| 3 | Boss/Conflict Redesign (Doc 14) | 49 | 0.5x | **24.5** | **7** |
| 7 | Photo/Media System (Doc 18) | 38 | 0.5x | **19.0** | **8** |

---

## 5. Final Ranking with Commentary

### Rank 1: Enhanced Life Simulation -- Adjusted 87.0

The Life Sim is now the heart of Nikita. Gate 2 elevated it from a mid-tier enhancement to THE core feature. The daily story generation creates the "check in and see what happened" loop that drives retention. Predefined weekly routines (new Gate 2 requirement) give structure; random events provide surprise. The combination of emotional state modeling, circadian profiles, NPC social circle, and event cascades makes Nikita feel like a person with an independent existence.

**Key strengths**: Highest engagement (9) and psychology (9) in raw scores. Highest novelty (9) -- no competitor offers this. Gate 2 adds scope (routines, monthly meta-instructions) that strengthen the feature further.

**Key weakness**: Feasibility (5). This is the most complex feature to build correctly. NPC contradiction management, daily story generation, and monthly meta-instruction systems are all new engineering challenges beyond the original Doc 13 proposal.

**Build path**: Emotional state JSONB first (foundation for everything). Then predefined routines and daily story generation. Then NPC social circle (Tier 2 per Gate 2). Then circadian profiles and event cascades.

### Rank 2: Psyche Agent -- Adjusted 81.0

The subconscious layer that makes every conversation feel emotionally intelligent. Gate 2 confirmed this must be present, starting with batch mode. The Psyche Agent is uniquely defensible -- it requires dual-agent architecture that competitors cannot easily replicate. The internal monologue concept (what Nikita thinks but won't say) is the most powerful single design idea across all proposals.

**Key strengths**: Perfect psychology score (10) and perfect novelty score (10). These are the two highest single-criterion scores in the entire matrix. The phased rollout (batch to hybrid to full) with kill criteria makes the investment manageable.

**Key weakness**: Portal impact (3). The Psyche Agent is invisible to the player. Its value is entirely indirect -- better conversations, more realistic emotional reactions. This is a feature players feel but never see.

**Build path**: Phase 1 batch (2-3 days, shadow mode, +$2.25/mo). Validate. Phase 2 triggers (3-4 days, A/B test). Phase 3 Opus real-time only if A/B positive.

### Rank 3: Vice Side-Quests -- Adjusted 76.7

The most balanced feature across all criteria (no score below 7 except Portal at 7). Vice storylines transform passive preference detection into active exploration with 32 unique content progressions. Gate 2 Decision 12 removes all content restrictions, making sexuality and substances first-class content. Decision 13 (vulnerability as core mechanic) elevates the vulnerability vice storyline to central importance.

**Key strengths**: Highest raw total (59) before multipliers. Best integration score (8) alongside achievements -- builds cleanly on existing vice infrastructure with 70 existing tests. Best cost efficiency of content-producing features (+$0.30-0.50/mo).

**Key weakness**: Content creation is the bottleneck. 8 vices x 4 stages = 32 storyline prompts to write. Gate 2 prioritizes top 3 (sexuality, substances, dark humor) which reduces initial scope to 12 prompts.

**Build path**: Storyline stage tracking columns first. Then top 3 vice content (sexuality, substances, dark humor). Then enriched prompt injection. Then remaining 5 vices incrementally.

### Rank 4: Progression & Achievements -- Adjusted 75.4

The safest, most feasible feature with the best cost-to-value ratio. Zero additional LLM cost. Cleanest integration. The warmth meter (Gate 2 Decision 1 confirmed) provides the most important single UI element for the portal. Achievement detection enables the entire reward ecosystem.

**Key strengths**: Best feasibility (8), cost efficiency (9), and integration (9) in the matrix. The foundation that other features build on -- photos need achievement triggers, vice milestones need the achievement DB, and the portal needs the warmth meter.

**Key weakness**: Low novelty (4) and low psychology depth (4). Achievements are a commodity feature. They make Nikita a better game but do not make it a unique one.

**Build path**: Achievement DB + detection stage first (enables everything). Then warmth meter (confirmed Gate 2). Then portal achievement wall. Then daily/weekly goals (Tier 3 per Gate 2).

### Rank 5: Cross-Expert Synthesis -- Adjusted 63.7

Not a feature but the integration blueprint. Its value is preventing the other 7 features from contradicting each other. The emotional state model resolution (psyche writes psychology, life sim writes mood) and the dependency graph are architecturally essential. Gate 2 partially supersedes the tier ordering but the synergy analysis and conflict resolutions remain valid.

**Key strengths**: Integration score (8) and the synergy cluster analysis that identifies which features amplify each other. The cost summary and risk register provide decision-making data.

**Key weakness**: Not buildable on its own. Its value is realized only when other features are implemented using its guidelines.

### Rank 6: Portal Game Dashboard -- Adjusted 49.0

The portal is important but its role changed in Gate 2. The original Doc 16 vision was a data-rich analytics dashboard (10 sections, F-pattern layout, radar charts, sparklines). Gate 2 Decision 8 shifts the centerpiece to "Nikita's Day" -- a narrative timeline, not a data dashboard. The score charts and achievement wall remain relevant but are secondary to the life sim's daily story output.

**Key strengths**: Perfect portal score (10) by definition. Good feasibility (7) using existing component library. Low ongoing cost.

**Key weakness**: Game feel (5) is the fundamental problem. A dashboard does not feel like a game. Gate 2 recognizes this and pivots to narrative. The Doc 16 wireframes need redesign to center on Nikita's Day rather than score metrics.

**Build path**: Nikita's Day timeline first (new, Gate 2 requirement). Then warmth meter display. Then score charts. Then achievement wall. Then everything else incrementally.

### Rank 7: Boss/Conflict Redesign -- Adjusted 24.5

The highest raw psychology (9) and game feel (9) scores in the matrix, but Gate 2 Decisions 2+3 defer the entire system. The 0.5x multiplier drops it to near-bottom ranking despite being the feature that would make Nikita feel most like a real game. Multi-phase boss encounters with Gottman-based scoring are genuinely innovative, but the user's priority is building Nikita's autonomous life first.

**Key strengths**: Would be the biggest single improvement to gameplay. The emotional temperature gauge, 5:1 ratio scoring, and wound system are sophisticated and unique.

**Key weakness**: Deferred by user decision. High complexity (feasibility 4, integration 4). The current single-turn boss system works adequately for now.

**Build path**: Deferred. When revisited: single-session multi-turn first (Approach A). Resolution spectrum second. Wound system third. Conflict injection fourth.

### Rank 8: Photo/Media System -- Adjusted 19.0

The lowest raw score (38) further reduced by Gate 2 Decision 9 (defer to ~10 photos). The full system with 210 photos, trigger hierarchy, delivery pipeline, and gallery would score higher, but the user explicitly said this is not a priority. At ~10 photos, the collection/unlock mechanics have insufficient content to create meaningful engagement.

**Key strengths**: Low storage cost ($0.02/mo). Pre-curated photos avoid AI generation consistency issues. Telegram delivery via existing scheduled_events infrastructure is clean.

**Key weakness**: Photo sourcing is the bottleneck even at 10 images. No psychological depth. With deferred scope, the gallery and unlock system are overkill.

**Build path**: Deferred. When revisited: source 10 milestone photos manually. Simple Telegram delivery. No gallery UI. Expand only if player feedback demands it.

---

## 6. Criteria Leaderboard

Which features dominate which criteria:

| Criterion | Winner | Score | Runner-up | Score |
|-----------|--------|-------|-----------|-------|
| Engagement | Life Sim | 9 | Psyche Agent, Vice | 8 |
| Psychology | Psyche Agent | 10 | Life Sim, Boss | 9 |
| Feasibility | Achievements | 8 | Portal, Vice | 7 |
| Game Feel | Boss | 9 | Achievements | 8 |
| Portal | Portal Dashboard | 10 | Achievements | 9 |
| Novelty | Psyche Agent | 10 | Life Sim | 9 |
| Cost Efficiency | Achievements | 9 | Vice, Portal | 8 |
| Integration | Achievements | 9 | Vice, Synthesis | 8 |

**Pattern**: Achievements leads on buildability (feasibility, cost, integration). Psyche Agent leads on depth (psychology, novelty). Life Sim leads on engagement. Boss leads on game feel but is deferred. The adjusted ranking correctly prioritizes depth and engagement over buildability, reflecting Gate 2's emphasis on making Nikita feel alive over making the game polished.

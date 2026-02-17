# Bayesian Inference for Nikita — Master Research Index

> **Created**: 2026-02-16
> **Total Documents**: 27
> **Total Lines**: ~27,000
> **Team**: researcher-bayesian, researcher-behavioral, researcher-integration
> **Status**: COMPLETE — All 5 phases finished
> **Roadmap priority**: LATER — This research is for a future optimization cycle, not the current implementation focus. The main brainstorming session (Phases 3-4 at `../INDEX.md`) takes priority.

---

## Phase 1: Research (11 documents)

Foundational research across Bayesian mathematics, psychology, game AI, and computational infrastructure.

| # | Document | Author | Lines | Summary |
|---|----------|--------|-------|---------|
| 01 | [Bayesian Fundamentals](research/01-bayesian-fundamentals.md) | bayesian | 1,352 | Beta-Bernoulli conjugacy, prior selection, posterior updating, conjugate families, narrative-anchored priors for game metrics |
| 02 | [Patient Modeling](research/02-patient-modeling.md) | bayesian | 1,478 | Healthcare Bayesian approaches adapted for player modeling: personalized treatment → personalized game experience, longitudinal tracking |
| 03 | [Bayesian Personality](research/03-bayesian-personality.md) | behavioral | 915 | Big Five as distributions, Fleeson density distributions, within-person variability, attachment theory formalization |
| 04 | [HMM Emotional States](research/04-hmm-emotional-states.md) | bayesian | 1,480 | Hidden Markov Models for mood tracking, forward-backward algorithm, Viterbi decoding, emission models for text observations |
| 05 | [Particle Filters](research/05-particle-filters.md) | behavioral | 1,141 | Sequential Monte Carlo for non-linear state estimation, particle degeneracy, resampling strategies, continuous emotional dimensions |
| 06 | [Thompson Sampling](research/06-thompson-sampling.md) | integration | 1,579 | Multi-armed bandits, Beta-Bernoulli TS, contextual bandits, discounted TS, direct Nikita applications (skip, timing, events, vices) |
| 07 | [Bayesian Networks](research/07-bayesian-networks.md) | integration | 1,535 | DAGs, CPTs, d-separation, DBN 2-time-slice structure, pgmpy API, variable elimination, junction tree, scaling analysis |
| 08 | [Game AI Personality](research/08-game-ai-personality.md) | behavioral | 708 | Dwarf Fortress, RimWorld, CK3 personality systems, emergent behavior from trait distributions, NPC depth patterns |
| 09 | [Beta/Dirichlet Modeling](research/09-beta-dirichlet-modeling.md) | bayesian | 1,721 | Comprehensive Beta/Dirichlet math, decay-as-forgetting, observation weighting, chapter-specific priors, vice Dirichlet |
| 10 | [Efficient Inference](research/10-efficient-inference.md) | bayesian | 1,522 | NumPy benchmarks, memory budget, JSONB serialization, Cloud Run cold start, cost comparison, scaling to 100K players |
| 11 | [Computational Attachment](research/11-computational-attachment.md) | behavioral | 1,077 | Bowlby formalized, Internal Working Models as Bayesian priors, attachment activation sequence, defense mechanism taxonomy |

---

## Phase 2: Ideas (8 documents)

Concrete design proposals applying research to Nikita's game systems.

| # | Document | Author | Lines | Summary |
|---|----------|--------|-------|---------|
| 12 | [Bayesian Player Model](ideas/12-bayesian-player-model.md) | bayesian | 1,212 | Unified BayesianPlayerModel dataclass, Beta metrics, Dirichlet vices, HMM mood, observation pipeline, cold start, decay, serialization |
| 13 | [Nikita DBN](ideas/13-nikita-dbn.md) | behavioral | 950 | Full causal graph: perceived_threat → attachment → defense → emotion → response, 12 nodes, inter-slice temporal deps |
| 14 | [Event Generation](ideas/14-event-generation.md) | integration | 1,200 | Two-phase: Bayesian selection (<1ms) + LLM narration, Thompson Sampling over event categories, Bayesian surprise as conflict trigger |
| 15 | [Integration Architecture](ideas/15-integration-architecture.md) | integration | 1,019 | nikita/bayesian/ package (14 files), pre-stage pipeline integration, BayesianContext, feature flags, API endpoints |
| 16 | [Emotional Contagion](ideas/16-emotional-contagion.md) | behavioral | 887 | Belief divergence (KL) as conflict metric, bidirectional emotion transfer, repair mechanics, divergence thresholds |
| 17 | [Controlled Randomness](ideas/17-controlled-randomness.md) | behavioral | 824 | Surprise budget, tail sampling from personality distributions, coherence constraints, 70/20/10 ratio |
| 18 | [Bayesian Vice Discovery](ideas/18-bayesian-vice-discovery.md) | bayesian | 977 | Dirichlet posterior over 8 vice categories, observation sources, discovery mechanics, Thompson Sampling for vice exploration |
| 19 | [Unified Architecture](ideas/19-unified-bayesian-architecture.md) | integration | 823 | Complete BayesianPlayerState schema (~1.8 KB), end-to-end data flow, 4-phase migration, risk assessment, cost-benefit (17% savings) |

---

## Phase 3: Expert Evaluations (4 documents)

Critical evaluation from four expert personas. Each evaluates all Phase 2 proposals.

| # | Document | Persona | Lines | Score | Key Recommendation |
|---|----------|---------|-------|-------|--------------------|
| 20 | [Game Designer](evaluation/20-game-designer-evaluation.md) | Sr. Game Designer (15y) | 317 | 7.2/10 | Narrative Accountability Rule: every visible change needs a perceivable cause |
| 21 | [Psychology Expert](evaluation/21-psychology-evaluation.md) | Clinical Psychologist & AI Ethics | 544 | 6.8/10 | Rename clinical constructs to behavioral; Secure Base Constraint; trauma bonding prevention |
| 22 | [ML Engineer](evaluation/22-ml-engineer-evaluation.md) | Sr. ML Engineer (10y) | 785 | 7.0/10 | Replace DBN with Bayesian state machine; custom NumPy over pgmpy; LLM observation extraction |
| 23 | [Cost/Performance](evaluation/23-cost-performance-evaluation.md) | Technical PM & Infra Economist | 576 | 7.5/10 | Actual savings 12% not 17%; build Phase 1 only; gate rest on DAU milestones |

**Consensus score**: 7.1/10 — Ship with guardrails. Strong foundation, needs simplification and safety constraints.

---

## Phase 4: Synthesis (3 documents)

Final integrated design incorporating all evaluation feedback.

| # | Document | Lines | Summary |
|---|----------|-------|---------|
| 24 | [Integrated Architecture](synthesis/24-integrated-architecture.md) | 638 | System diagram, Bayesian state machine (6 states), safety module, narrative filter, 10-file package (~1,200 lines), latency budget |
| 25 | [Implementation Roadmap](synthesis/25-implementation-roadmap.md) | 406 | 4-phase rollout with decision gates: Beta metrics (2wk) → TS skip/timing (2wk) → State machine (4wk) → Full (5wk). $65K total |
| 26 | [Database Schema](synthesis/26-database-schema.md) | 601 | bayesian_states (JSONB, ~2KB/player), shadow_log, ab_assignments. RLS, GIN index, optimistic locking, migration strategy |

---

## Phase 5: Audio Summary (1 document)

| # | Document | Lines | Summary |
|---|----------|-------|---------|
| 27 | [Complete Audio Summary](audio/27-complete-audio-summary.md) | 255 | TTS-ready conversational prose (~7,300 words, ~48 min). Covers problem → research → ideas → evaluations → final plan |

---

## Key Design Decisions (Final)

| Decision | Original Proposal | Expert Feedback | Final Design |
|----------|------------------|-----------------|-------------|
| Emotional model | Full DBN, 12 variables | Overengineered (Doc 22) | Bayesian state machine, 6 states |
| Defense mechanisms | 10 categorical | Too granular (Doc 21) | Absorbed into 6 emotional states |
| Attachment construct | "attachment_style" | Clinical overreach (Doc 21) | "engagement_pattern" |
| Surprise direction | Bidirectional | Symmetry flaw (Doc 20) | Negative directional only for bosses |
| Surprise ratio | 70/20/10 | Too aggressive (Doc 20) | 85/12/3 |
| Cold start | Full-weight updates | Too volatile (Doc 20) | Half-weight for first 10 messages |
| Personality traits | Beta distributions | Should be fixed (Doc 21) | Fixed traits, contextual expression |
| Skip/timing | Thompson Sampling | Defer to Phase 2 (Doc 22) | Fixed probabilities initially |
| Observation model | Rules only | Weakest link (Doc 22) | Rules + optional Haiku extraction |
| Cost framing | 17% token savings | Actually 12% (Doc 23) | Architecture modernization, not cost project |
| Investment strategy | Build all at once | Phase 1 only, then gate (Doc 23) | 4-phase with decision gates |

---

## Directory Structure

```
docs/brainstorm/bayesian-inference/
├── 00-research-index.md          (this file)
├── research/                      (Phase 1: 11 documents)
│   ├── 01-bayesian-fundamentals.md
│   ├── 02-patient-modeling.md
│   ├── 03-bayesian-personality.md
│   ├── 04-hmm-emotional-states.md
│   ├── 05-particle-filters.md
│   ├── 06-thompson-sampling.md
│   ├── 07-bayesian-networks.md
│   ├── 08-game-ai-personality.md
│   ├── 09-beta-dirichlet-modeling.md
│   ├── 10-efficient-inference.md
│   └── 11-computational-attachment.md
├── ideas/                         (Phase 2: 8 documents)
│   ├── 12-bayesian-player-model.md
│   ├── 13-nikita-dbn.md
│   ├── 14-event-generation.md
│   ├── 15-integration-architecture.md
│   ├── 16-emotional-contagion.md
│   ├── 17-controlled-randomness.md
│   ├── 18-bayesian-vice-discovery.md
│   └── 19-unified-bayesian-architecture.md
├── evaluation/                    (Phase 3: 4 documents)
│   ├── 20-game-designer-evaluation.md
│   ├── 21-psychology-evaluation.md
│   ├── 22-ml-engineer-evaluation.md
│   └── 23-cost-performance-evaluation.md
├── synthesis/                     (Phase 4: 3 documents)
│   ├── 24-integrated-architecture.md
│   ├── 25-implementation-roadmap.md
│   └── 26-database-schema.md
└── audio/                         (Phase 5: 1 document)
    └── 27-complete-audio-summary.md
```

---

## Reading Order

**Quick overview**: Doc 27 (audio summary — 48 min TTS)

**Technical deep dive**:
1. Start with Doc 19 (unified architecture) for the complete picture
2. Read Docs 20-23 (evaluations) for critical feedback
3. Read Docs 24-26 (synthesis) for the final plan
4. Dive into specific research docs (01-11) for mathematical foundations
5. Read idea docs (12-18) for detailed component designs

**Implementation start**: Doc 25 (roadmap) → Doc 26 (schema) → Doc 24 (architecture)

---

## Glossary of Key Bayesian Terms

| Term | Definition | Primary Documents |
|------|-----------|-------------------|
| **Alpha/Beta (α, β)** | Parameters of the Beta distribution. α counts "successes," β counts "failures." Higher values = more confident distribution. | 01, 09, 12 |
| **Bayesian Surprise** | KL divergence between prior and posterior after an observation. Measures how much a single event shifts beliefs. Used as conflict/escalation trigger. | 09, 14, 16, 24 |
| **Bayesian State Machine** | Finite state machine where transition probabilities are Bayesian-updated from observations. Replaces the full DBN in final design. 6 states: secure, anxious, avoidant, conflicted, repair, growth. | 22, 24 |
| **Beta Distribution** | Continuous probability distribution on [0, 1], parameterized by α and β. Conjugate prior for Bernoulli/binomial likelihoods. Models each relationship metric (intimacy, passion, trust, secureness). | 01, 09, 12 |
| **Conjugate Prior** | A prior distribution that, when combined with a specific likelihood, yields a posterior in the same distribution family. Enables closed-form updates (no MCMC needed). | 01, 09 |
| **Cold Start** | The period before sufficient observations accumulate (first ~10 messages). Half-weight updates prevent volatile early swings. | 12, 20, 24 |
| **CPT (Conditional Probability Table)** | Table specifying P(child | parents) in a Bayesian network. Each node's distribution conditioned on its parent nodes. | 07, 13 |
| **d-separation** | Graphical criterion for conditional independence in a DAG. If X and Y are d-separated given Z, they are conditionally independent. | 07 |
| **DBN (Dynamic Bayesian Network)** | Bayesian network with temporal structure: intra-slice (same timestep) and inter-slice (across timesteps) edges. Originally proposed with 12 nodes; replaced by state machine. | 07, 13, 22 |
| **Decay-as-Forgetting** | Technique where α and β are multiplied by a decay factor (0 < λ < 1) each time step, making old observations count less. Models recency bias. | 09, 12 |
| **Dirichlet Distribution** | Multivariate generalization of Beta distribution. Conjugate prior for categorical/multinomial likelihoods. Used for vice categories (8-dimensional) and timing buckets. | 09, 12, 18 |
| **Emission Model** | In an HMM, the probability distribution P(observation | hidden state). Maps unobservable emotional states to observable text features. | 04 |
| **Engagement Pattern** | Renamed from "attachment_style" per psychology evaluation. Categories: responsive, hyperactive, withdrawn, inconsistent. Describes how player interacts over time. | 11, 21, 24 |
| **Forward-Backward Algorithm** | HMM inference algorithm computing P(hidden state | all observations). Forward pass accumulates evidence; backward pass propagates future information. | 04 |
| **GIN Index** | Generalized Inverted Index in PostgreSQL. Enables efficient queries into JSONB columns (the bayesian_states storage). | 10, 26 |
| **HMM (Hidden Markov Model)** | Probabilistic model with hidden states that evolve via Markov transitions and produce observable emissions. Proposed for mood tracking. | 04, 12 |
| **KL Divergence** | Kullback-Leibler divergence: asymmetric measure of how one distribution differs from another. Used for Bayesian surprise and belief divergence (conflict detection). | 09, 14, 16 |
| **Narrative Accountability Rule** | Design constraint: every player-visible behavioral change must have a perceivable in-game cause. Prevents "magical" personality shifts. | 20, 24 |
| **Observation Weighting** | Assigning different weights to observations based on signal strength. Strong signals (explicit statements) get weight 1.0; weak signals (emoji usage) get 0.3. | 09, 12, 22 |
| **Optimistic Locking** | Concurrency control using a version counter. UPDATE succeeds only if version matches expected value, preventing lost updates on bayesian_states. | 26 |
| **Particle Filter (SMC)** | Sequential Monte Carlo method using weighted samples ("particles") to approximate non-Gaussian posteriors. Alternative to HMMs for continuous state spaces. | 05 |
| **Posterior** | Updated belief distribution after incorporating observations: P(θ | data) ∝ P(data | θ) * P(θ). In conjugate models, stays in same family as prior. | 01, 09 |
| **Prior** | Initial belief distribution before seeing data. "Narrative-anchored priors" encode Nikita's personality (e.g., trust starts skeptical: Beta(3, 7)). | 01, 09, 12 |
| **RLS (Row-Level Security)** | Supabase/PostgreSQL feature restricting row access per user. Each player can only read/write their own bayesian_states row. | 26 |
| **Secure Base Constraint** | Safety rule: Nikita always models secure attachment patterns regardless of player behavior. Prevents reinforcing insecure attachment styles. | 21, 24 |
| **Shadow Mode** | Running Bayesian system alongside existing pipeline without affecting game output. Logs predictions for comparison. Phase 1 validation strategy. | 19, 23, 25 |
| **Thompson Sampling** | Bandit algorithm: sample from each arm's posterior, play the arm with highest sample. Naturally balances exploration/exploitation. Applied to skip rate, timing, event selection, vice discovery. | 06, 14, 18 |
| **Three-Tier Escalation** | Inference complexity tiers: Tier 1 (pure math, <1ms, 85-90%), Tier 2 (Sonnet LLM, 5-15ms, 8-12%), Tier 3 (Opus LLM, 300ms+, 2-3%). Most decisions stay in Tier 1. | 10, 22, 24 |
| **Viterbi Decoding** | Algorithm finding the most likely sequence of hidden states in an HMM. Used for reconstructing emotional trajectories. | 04 |

---

## Cross-Reference Map

Shows which documents reference or build upon each other. Arrows indicate dependency direction (A → B means A builds on B).

### Research → Ideas

| Research Doc | Feeds Into | Relationship |
|-------------|-----------|--------------|
| 01 Bayesian Fundamentals | 12, 18, 19 | Beta/conjugate math used in player model, vice discovery, unified schema |
| 02 Patient Modeling | 12 | Healthcare personalization patterns adapted for player modeling |
| 03 Bayesian Personality | 13, 17 | Personality distributions inform DBN design and randomness constraints |
| 04 HMM Emotional States | 12, 13 | HMM mood tracking integrated into player model and causal graph |
| 05 Particle Filters | 13 | Alternative inference method considered for continuous emotional dimensions |
| 06 Thompson Sampling | 14, 18 | TS applied directly to event generation and vice exploration |
| 07 Bayesian Networks | 13, 15 | DAG/DBN theory underlies causal graph; pgmpy analysis informs architecture |
| 08 Game AI Personality | 17 | RimWorld/CK3 patterns inform controlled randomness design |
| 09 Beta/Dirichlet Modeling | 12, 14, 16, 18 | Core math for all Beta/Dirichlet components across ideas |
| 10 Efficient Inference | 15, 19 | Performance benchmarks and cost analysis shape architecture decisions |
| 11 Computational Attachment | 13, 16 | Bowlby formalization feeds emotional contagion and DBN attachment node |

### Ideas → Evaluations

All Phase 2 documents (12-19) are evaluated by all four expert evaluations (20-23). Key targeted critiques:

| Idea Doc | Strongest Critique From | Key Issue Raised |
|----------|------------------------|-----------------|
| 12 Bayesian Player Model | 20 (Game Designer) | Cold start volatility; half-weight first 10 messages |
| 13 Nikita DBN | 22 (ML Engineer) | Overengineered; replace with Bayesian state machine |
| 14 Event Generation | 20 (Game Designer) | Bidirectional surprise is flawed; negative-only for bosses |
| 15 Integration Architecture | 23 (Cost/Performance) | 14 files too many for Phase 1; incremental build |
| 16 Emotional Contagion | 21 (Psychology) | Bidirectional transfer risks trauma bonding |
| 17 Controlled Randomness | 20 (Game Designer) | 70/20/10 ratio too aggressive; reduce to 85/12/3 |
| 18 Bayesian Vice Discovery | 22 (ML Engineer) | TS for vices solid; observation extraction is weak link |
| 19 Unified Architecture | 23 (Cost/Performance) | 17% savings claim is 12% when Stage 9 included |

### Evaluations → Synthesis

| Evaluation Doc | Key Contributions to Synthesis |
|---------------|-------------------------------|
| 20 Game Designer → 24 | Narrative Accountability Rule, directional surprise, 85/12/3 ratio, NarrativeFilter class |
| 21 Psychology → 24 | Secure Base Constraint, engagement_pattern rename, EmotionalSafetyGuard, fixed personality traits |
| 22 ML Engineer → 24, 25 | Bayesian state machine (6 states), custom NumPy, three-tier escalation, phased testing |
| 23 Cost/Performance → 25, 26 | 4-phase gated rollout, corrected ROI, shadow mode validation, DAU-gated milestones |

### Synthesis Internal Dependencies

```
Doc 25 (Roadmap) ──references──→ Doc 24 (Architecture) for component scope
Doc 26 (Schema)  ──references──→ Doc 24 (Architecture) for state structure
Doc 26 (Schema)  ──references──→ Doc 25 (Roadmap) for migration phasing
Doc 27 (Audio)   ──summarizes──→ All documents (01-26)
```

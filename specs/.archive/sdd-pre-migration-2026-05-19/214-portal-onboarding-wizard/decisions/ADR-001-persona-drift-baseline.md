# ADR-001: Persona Drift Baseline for /converse Conversation Agent

**Status**: ACCEPTED
**Date**: 2026-04-19
**Deciders**: Simon (solo dev)
**Spec**: 214 / FR-11d / GH #356

## Context

Spec 214 introduces a second Pydantic AI agent (`get_conversation_agent`)
that shares the main text agent's `NIKITA_PERSONA` verbatim. The risk
is a silent drift: the wizard agent's system prompt adds a wizard
framing layer that, over time or under revision, could push replies
away from Nikita's canonical voice. Without a falsifiable metric, we
cannot tell a benign framing tweak from a persona regression in CI.

The main text agent has no such baseline because it IS the canonical
voice. The conversation + handoff agents must be measured against it.

## Decision

Pin a persona-drift baseline using TF-IDF cosine similarity + three
structural features. Activate a CI test that fails the build when drift
exceeds the gates.

### Baseline generation (one-shot per persona bump)

Run `scripts/persona_baseline_generate.py` with:

- **Source agent**: the main text agent (`nikita.agents.text.agent.get_nikita_agent`).
- **Seeds**: 3 pinned seeds (e.g. `seed=42`, `seed=1729`, `seed=8128`).
- **Samples per seed**: `PERSONA_DRIFT_SEED_SAMPLES = 20` → 60 total rows.
- **Temperature**: 0.0 (deterministic per seed; run twice to confirm
  the model's own drift is under noise floor).
- **Prompts**: a 20-prompt fixture covering the wizard's topic set
  (location / scene / darkness / identity / backstory / phone) at
  varying message counts. Prompts live in
  `scripts/persona_baseline_prompts.yaml`.

Output: `tests/fixtures/persona_baseline_v1.csv` with columns:

| seed | sample_index | prompt | reply |

### Drift gates

- `PERSONA_DRIFT_COSINE_MIN = 0.70` — TF-IDF cosine between candidate
  agent output and the pinned baseline corpus.
- `PERSONA_DRIFT_FEATURE_TOLERANCE = 0.15` — each of the three features
  must land within ±15% of the baseline mean:
  - mean sentence length (characters)
  - lowercase-ratio (fraction of alpha chars lowercased)
  - canonical-phrase count (count of persona-identifying substrings per
    100 tokens)

### Bump trigger

Bump `v1 → v2` baseline when:

- `NIKITA_PERSONA` is edited AND the CI drift test fails.
- The conversation framing layer is materially restructured (e.g., new
  top-level rule added).

A baseline bump requires:

1. A new ADR (ADR-002, etc.) summarizing the change.
2. Regenerating the CSV with the same 3 seeds × 20 samples × 20 prompts
   recipe.
3. Committing the new CSV alongside the persona change in the same PR.

## Alternatives Considered

- **Embedding-based drift**: OpenAI text-embedding-3-large cosine. Rejected
  because it (a) adds a runtime API dependency, (b) obscures which
  feature drifted, and (c) requires an extra vendor budget for CI.
- **LLM-as-judge**: Gemini or Claude scoring "is this Nikita?" on each
  candidate reply. Rejected for flakiness + cost; kept as a
  supplementary signal for the tone-filter (AC-T2.5.8), not drift.
- **Single-feature drift**: mean sentence length alone. Rejected because
  one feature is too easy to game with a prompt tweak.

## Consequences

- Drift detection is reproducible and auditable — the CSV is the
  single source of truth.
- Baseline generation is expensive (60 live model calls) but
  infrequent (≤ once per persona bump). Run manually, not in CI.
- Three structural features are heuristic — they catch common
  regressions (customer-service register, overly long replies) but
  miss subtle tone shifts. The TF-IDF cosine guards against those.
- We deliberately generate the baseline from the MAIN text agent
  (not the wizard agent). The wizard inherits Nikita's voice; the test
  checks it has not drifted FROM the main text agent's reference
  distribution.

## References

- Tech spec: `specs/214-portal-onboarding-wizard/technical-spec.md` §7.1
  "persona-drift metric"
- `.claude/rules/tuning-constants.md` (all drift constants named + pinned)
- Tuning constants: `nikita/onboarding/tuning.py` (PERSONA_DRIFT_*)
- Generator: `scripts/persona_baseline_generate.py` (Phase A one-shot)

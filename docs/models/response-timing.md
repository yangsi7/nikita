# Response Timing Model

> **Stub — detailed documentation in progress.**
> This file is a placeholder created by the portal parallel track (Spec 210 PR #210-portal).
> The main Spec 210 track will overwrite this file with full documentation including
> the complete model formulation, Monte Carlo validation results, and references.

## Overview

The Response Timing Model controls how long Nikita waits before replying to a user message.
It combines a log-normal base distribution with per-chapter scaling coefficients, per-chapter
hard caps, and an EWMA momentum layer that adapts to the user's own messaging cadence.

## Key Parameters (preliminary)

| Parameter | Value | Description |
|---|---|---|
| μ (log-normal mean) | 2.996 | Controls median delay |
| σ (log-normal std) | 1.714 | Controls tail heaviness |
| Chapter coefficients | [0.15, 0.30, 0.50, 0.75, 1.00] | Ch1..Ch5 multipliers |
| Chapter caps (s) | [10, 60, 300, 900, 1800] | Per-chapter hard ceilings |
| Momentum α | 0.35 | EWMA smoothing factor |
| M bounds | [0.1, 5.0] | Momentum clamp range |

## Implementation

See [`nikita/agents/text/timing.py`](../../nikita/agents/text/timing.py) for the implementation.

See [`specs/210-kill-skip-variable-response/spec.md`](../../specs/210-kill-skip-variable-response/spec.md) for the full specification.

---

*Full documentation (model derivation, Bayesian interpretation, Monte Carlo validation, citations) will be populated by the main Spec 210 implementation track.*

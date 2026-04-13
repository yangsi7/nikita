# Stochastic Model Workflow

When introducing any stochastic behavior (sampling, random delay, decay curve, probabilistic gate):

## Required Steps

1. **Choose a named distribution** with documented rationale. Log-normal for response times, exponential for memoryless, Weibull for hazard. Never use `random.random()` bare — wrap in a named function with parameters.

2. **Define constants as module-level `Final` values** with docstrings. Include the mathematical formula in the module docstring. Link to `docs/models/<model-name>.md`.

3. **Write a Monte Carlo validator** at `scripts/models/<model-name>_mc.py`:
   - Import constants from the production module (single source of truth)
   - Produce percentile CSV + histogram/CDF PNGs under `docs/models/`
   - Include sanity assertions (monotonicity, boundedness, unbiasedness)
   - Exit 0 on pass, 1 on fail. Runtime < 30 s.
   - Run via `uv run python scripts/models/<model-name>_mc.py`

4. **Document the model** at `docs/models/<model-name>.md`:
   - Problem statement, formula, parameters, MC results (linked plots)
   - Citations to academic literature
   - Pitfalls section (feedback loops, boundary conditions, sensitivity)
   - Code cross-references with `file:line`

5. **Build an interactive artifact** — either:
   - Portal page under `portal/src/app/admin/research-lab/` (preferred for React/Recharts)
   - Standalone HTML at `docs/models/<model-name>-explorer.html` (CDN-loaded, single file)

6. **Feature-flag the behavior** in `nikita/config/settings.py` with env-var override. Rollback = flag off, no deploy needed.

## Anti-Patterns

- Bare `random.random()` without named distribution or parameter documentation
- Hard-coded magic numbers in business logic (extract to `Final` constants)
- Stochastic behavior without MC validation (untested distributions drift)
- Missing cap/bound on sampled values (tail risk)
- Mixing timezone-aware and timezone-naive timestamps in delta computation

## Reference Implementation

- `nikita/agents/text/timing.py` — ResponseTimer (log-normal × chapter × momentum)
- `nikita/agents/text/conversation_rhythm.py` — EWMA momentum
- `scripts/models/response_timing_mc.py` — MC validator
- `docs/models/response-timing.md` — model documentation

#!/usr/bin/env python3
"""Regenerate tests/fixtures/persona_baseline_v1.csv (Spec 214 / ADR-001).

One-shot script. Runs 3 seeds × PERSONA_DRIFT_SEED_SAMPLES samples
against the main text agent at temperature 0.0 and writes the CSV.
Requires ``ANTHROPIC_API_KEY`` in the environment.

Usage:

    uv run python scripts/persona_baseline_generate.py [--out PATH]

Not invoked from CI. Maintainer re-runs this after any NIKITA_PERSONA
edit per ADR-001 "Bump trigger".
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import os
import sys
from pathlib import Path

# Deliberately small prompt seed for Phase A scaffold. Full 20-prompt
# fixture lands in a follow-up commit before the drift test is
# activated in CI.
_PROMPTS: tuple[str, ...] = (
    "hey, where are you right now?",
    "nice. what do you like to do when you go out?",
    "1-5, how dark does the night get?",
    "who's asking? name, age, what you do?",
    "pick the backstory that fits best.",
    "voice or text from here on?",
)

_SEEDS: tuple[int, ...] = (42, 1729, 8128)


async def _generate_sample(prompt: str, seed: int) -> str:
    """Call the main text agent once. Returns the reply text.

    Import is deferred so the script fails gracefully when
    ANTHROPIC_API_KEY is missing (rather than crashing at import).
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY required; aborting.")
    from nikita.agents.text.agent import get_nikita_agent

    agent = get_nikita_agent()
    # Pydantic AI does not expose a per-call seed parameter — temperature
    # 0.0 + stable prompts gives sufficient determinism for the baseline
    # purpose (ADR-001 "Alternatives Considered" — we accept small
    # intra-run variance).
    result = await agent.run(prompt)
    return str(result.output)


async def main(out_path: Path) -> None:
    rows: list[dict[str, object]] = []
    from nikita.onboarding.tuning import PERSONA_DRIFT_SEED_SAMPLES

    for seed in _SEEDS:
        for sample_index in range(PERSONA_DRIFT_SEED_SAMPLES):
            prompt = _PROMPTS[sample_index % len(_PROMPTS)]
            reply = await _generate_sample(prompt, seed)
            rows.append(
                {
                    "seed": seed,
                    "sample_index": sample_index,
                    "prompt": prompt,
                    "reply": reply,
                }
            )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["seed", "sample_index", "prompt", "reply"]
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default="tests/fixtures/persona_baseline_v1.csv",
        help="Output CSV path (default: tests/fixtures/persona_baseline_v1.csv)",
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(main(Path(args.out))))

#!/usr/bin/env python3
"""Measure /converse ``source="llm"`` rate against a preview deployment.

Spec 214 FR-11d rollout gate (AC-11d.9 / AC-T2.11.1/2).

Runs ``LLM_SOURCE_RATE_GATE_N`` simulated turns against the preview
endpoint and prints the observed ``source="llm"`` percentage. Exits
non-zero if the rate is below ``LLM_SOURCE_RATE_GATE_MIN`` — paste the
output into PR 3 description as the ship gate evidence.

Usage:

    PORTAL_JWT=... CONVERSE_URL=https://nikita-api-preview.../onboarding/converse \\
        uv run python scripts/converse_source_rate_measurement.py

This is a manual dry-run tool. It is not wired into CI because it hits
a live preview endpoint and spends real LLM tokens.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

# Deferred import so --help works without network libs.

_SAMPLE_PROMPTS = (
    "I live in Zurich",
    "techno",
    "3",
    "Simon, 30, engineer",
    "voice",
    "the second one looks cool",
)


async def _one_turn(
    client, url: str, token: str, prompt: str
) -> tuple[str, int]:
    """POST one turn. Return ``(source, status_code)``."""
    payload = {
        "conversation_history": [],
        "user_input": prompt,
        "turn_id": str(uuid4()),
        "locale": "en",
    }
    r = await client.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=10.0,
    )
    try:
        body = r.json()
    except Exception:
        body = {"source": "unknown"}
    return body.get("source", "unknown"), r.status_code


async def main(url: str, token: str, n: int) -> int:
    import httpx

    llm_count = 0
    fallback_count = 0
    other_count = 0
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[{ts}] Running N={n} turns against {url}")
    async with httpx.AsyncClient() as client:
        for i in range(n):
            prompt = _SAMPLE_PROMPTS[i % len(_SAMPLE_PROMPTS)]
            source, status = await _one_turn(client, url, token, prompt)
            if source == "llm":
                llm_count += 1
            elif source == "fallback":
                fallback_count += 1
            else:
                other_count += 1
            if (i + 1) % 10 == 0:
                print(f"  {i + 1}/{n}  llm={llm_count} fb={fallback_count} other={other_count}")

    llm_rate = llm_count / n if n else 0.0
    print(f"\nllm={llm_count} fallback={fallback_count} other={other_count}")
    print(f"source=llm rate: {llm_rate:.2%}")

    from nikita.onboarding.tuning import LLM_SOURCE_RATE_GATE_MIN

    if llm_rate < LLM_SOURCE_RATE_GATE_MIN:
        print(
            f"FAIL: rate {llm_rate:.2%} < LLM_SOURCE_RATE_GATE_MIN "
            f"({LLM_SOURCE_RATE_GATE_MIN:.0%})"
        )
        return 1
    print(f"PASS: rate {llm_rate:.2%} >= {LLM_SOURCE_RATE_GATE_MIN:.0%}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        default=os.getenv("CONVERSE_URL"),
        help="Full /converse URL (env: CONVERSE_URL)",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("PORTAL_JWT"),
        help="Portal user Bearer JWT (env: PORTAL_JWT)",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=None,
        help="Sample size override; default is LLM_SOURCE_RATE_GATE_N (100)",
    )
    args = parser.parse_args()

    if not args.url or not args.token:
        parser.error("--url + --token (or env CONVERSE_URL + PORTAL_JWT) required")

    from nikita.onboarding.tuning import LLM_SOURCE_RATE_GATE_N

    n = args.n or LLM_SOURCE_RATE_GATE_N
    sys.exit(asyncio.run(main(args.url, args.token, n)))

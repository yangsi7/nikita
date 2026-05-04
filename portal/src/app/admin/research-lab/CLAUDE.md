# portal/src/app/admin/research-lab/ — Self-Contained Research Artifacts

## Purpose

Admin-only "research lab" surface for interactive decision artifacts (Monte Carlo simulators, parameter explorers, design briefs). Each sub-page is a SELF-CONTAINED React port of a standalone HTML artifact (e.g., `docs/models/*-explorer.html`). These are NOT regular portal feature surfaces — they intentionally bypass the shared design system to preserve the artifact's own identity.

## Key Files

- `response-timing/page.tsx` — Spec 210 v2 decision brief. 9 sections: problem recap, proposed log-normal × chapter × momentum model, Monte Carlo simulator, Ch1 floor, momentum (EWMA + feedback-spiral demo), Bayesian equivalence (EWMA ↔ Normal-Normal posterior), old-vs-new comparison, why log-normal + excitement-fades, citations. Uses `recharts` for plots; inline `T` design tokens object at the top of file (scoped).
- `heartbeat/page.tsx` — Spec 215 heartbeat-engine artifact (interactive curves + thresholds).

Both pages mark `"use client"` because they ship local state for Monte Carlo runs / slider control.

## Callers

- Admin nav (when wired) under `/admin/research-lab/<topic>`.
- Direct linking from spec-decision artifacts (e.g., `specs/210-*/spec.md`, `specs/215-*/spec.md`) for spec reviewers.
- Source HTML artifacts at `docs/models/*-explorer.html` — the React versions are 1:1 ports kept in lockstep.

## Gotchas

- **Inline styles preserved intentionally**. Do NOT migrate to Tailwind/shadcn — this is the documented design exception in `nikita/.claude/rules/stochastic-models.md` step 5 (research lab artifacts can ship as standalone HTML or native-port React; both are valid).
- **No design-system cross-bleed**: the local `const T = { ... }` token object is scoped to the component subtree. Imported shadcn primitives are NOT used here on purpose.
- **Constants must mirror production**. The model parameters (e.g., log-normal μ/σ, momentum α) MUST be imported from the production module (`nikita/agents/text/timing.py`, etc.) where possible, OR have a clear comment + test guard noting the mirror. Per `.claude/rules/stochastic-models.md`, drifted artifacts are anti-patterns.
- **Recharts SSR**: `recharts` doesn't render at build time; if SSR-mode prerender breaks the page, wrap chart subtrees in `<ClientOnly>` or use `next/dynamic({ ssr: false })`.
- **Monte Carlo budget**: simulators run thousands of iterations on each parameter change. Throttle slider events; avoid sync setState storms.

## Navigation

- Parent: [`portal/src/app/admin/`](../) (W7b will add admin/CLAUDE.md)
- Spec 210 (response timing): [`specs/210-kill-skip-variable-response/`](../../../../../specs/210-kill-skip-variable-response/)
- Spec 215 (heartbeat): [`specs/215-heartbeat-engine/`](../../../../../specs/215-heartbeat-engine/)
- Stochastic-model rule: [`.claude/rules/stochastic-models.md`](../../../../../.claude/rules/stochastic-models.md)
- Source HTML artifacts: `docs/models/*-explorer.html`

Last verified: 2026-05-05

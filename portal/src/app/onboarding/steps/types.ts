/**
 * Shared step-component types for Spec 214 PR 214-B.
 *
 * Every step (3-11) receives a thin prop surface from the orchestrator:
 *   - `values` — current form state (read-only snapshot)
 *   - `onAdvance` — called with a partial patch when the step's CTA fires
 *   - `onPatch` (optional) — called for mid-step writes (e.g. scene select
 *     → advance, but darkness slider drag → patch without advancing)
 *
 * Steps with API side-effects (BackstoryReveal, PipelineGate, HandoffStep)
 * receive additional hooks/values as explicit typed props — keeping the
 * contract narrow so unit tests can mock exactly what each step uses.
 */

import type { WizardFormValues } from "@/app/onboarding/types/wizard"

/**
 * Common step props — every step receives at least this shape.
 */
export interface StepProps {
  /** Current wizard form state (snapshot, not mutable). */
  values: WizardFormValues
  /** Commit the step's collected fields and advance to the next step. */
  onAdvance: (patch: Partial<WizardFormValues>) => void
}

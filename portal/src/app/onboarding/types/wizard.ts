/**
 * Wizard-internal types: step enum, persisted state schema, form-value shape.
 *
 * These are portal-only types (no backend mirror). The persisted-state schema
 * is versioned via `WIZARD_STATE_VERSION` in `WizardPersistence.ts`; bumping
 * the version clears stale payloads on read.
 */

import type { LifeStage, SocialScene } from "./contracts"

/**
 * Wizard steps (3..11).
 *
 * Steps 1-2 are pre-wizard (landing + auth). Step 3 is the authenticated
 * dossier-header entry point. Steps 4-9 collect profile fields. Step 10 is
 * the pipeline-ready gate (POST /profile). Step 11 is the handoff screen.
 */
export type WizardStep = 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11

/**
 * Snapshot of wizard progress persisted to localStorage for abandon-and-resume.
 *
 * See spec §NR-1 for the canonical schema. The `cache_key` field MUST be
 * written alongside `chosen_option_id` (step 8) so the subsequent PUT to
 * /onboarding/profile/chosen-option can echo it back for server-side
 * ownership validation (FR-10.1).
 */
export interface WizardPersistedState {
  user_id: string
  /** Last completed step (3-10). Step 11 triggers a clear. */
  last_step: WizardStep
  location_city: string | null
  social_scene: SocialScene | null
  drug_tolerance: number | null
  life_stage: LifeStage | null
  interest: string | null
  name: string | null
  age: number | null
  occupation: string | null
  phone: string | null
  chosen_option_id: string | null
  /** From BackstoryPreviewResponse; required for PUT /profile/chosen-option. */
  cache_key: string | null
  /** ISO-8601 timestamp of last write. */
  saved_at: string
}

/**
 * In-memory form-state shape the wizard components share.
 *
 * Separate from the persisted shape because (a) user_id is derived from the
 * auth context, not form input; (b) saved_at is a persistence-layer concern.
 */
export interface WizardFormValues {
  location_city: string | null
  social_scene: SocialScene | null
  drug_tolerance: number | null
  life_stage: LifeStage | null
  interest: string | null
  name: string | null
  age: number | null
  occupation: string | null
  phone: string | null
  chosen_option_id: string | null
  cache_key: string | null
}

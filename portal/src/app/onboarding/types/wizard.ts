/**
 * Wizard-internal types: form-value shape shared across step components.
 *
 * These are portal-only types (no backend mirror).
 *
 * EM-4 (2026-05-05): `WizardStep` and `WizardPersistedState` removed
 * alongside `WizardStateMachine.ts` + `WizardPersistence.ts` per FR-11d
 * (server `/state` GET is the single source of truth).
 */

import type { LifeStage, SocialScene } from "./contracts"

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

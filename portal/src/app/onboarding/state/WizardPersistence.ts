/**
 * Wizard state persistence — localStorage RWX with user-scoped key + version byte.
 *
 * Spec 214 NR-1: partial profile + current step persist in localStorage keyed
 * by `nikita_wizard_{user_id}`. Version-byte mismatch → clear and start fresh
 * (defends against legacy cinematic-onboarding payloads without the byte).
 *
 * Per AC-NR1.5, reads MUST occur inside `useEffect` (never during render) to
 * avoid SSR hydration mismatch. This module exposes plain functions; the
 * useEffect discipline is enforced by the caller.
 */

import type { WizardPersistedState } from "@/app/onboarding/types/wizard"

/**
 * Persisted-state schema version. Bump when the shape of
 * WizardPersistedState changes in a backwards-incompatible way. On mismatch
 * `readPersistedState` clears the key and returns null.
 *
 * Current value: 1 (initial Spec 214 schema)
 * History: — (no prior versions)
 * Rationale: Legacy `OnboardingCinematic` wrote an unrelated key; the version
 *   byte distinguishes this wizard's payloads from any accidental older data.
 */
export const WIZARD_STATE_VERSION = 1

interface PersistedEnvelope {
  version: number
  data: WizardPersistedState
}

/**
 * Returns the localStorage key used for the given user. Exported for tests
 * and for clearPersistedState callers.
 */
export function persistedStateKey(userId: string): string {
  return `nikita_wizard_${userId}`
}

/**
 * Reads and deserializes the persisted state for `userId`.
 *
 * Returns null (and clears the key) if:
 *   - nothing is stored for this user
 *   - the payload is not valid JSON
 *   - the envelope `version` differs from WIZARD_STATE_VERSION
 *   - the envelope is missing a `data` field
 *
 * SSR-safety: returns null when `window` is undefined. AC-NR1.5 requires
 * callers to invoke this inside `useEffect`, not during render.
 */
export function readPersistedState(userId: string): WizardPersistedState | null {
  if (typeof window === "undefined") return null

  const key = persistedStateKey(userId)
  const raw = window.localStorage.getItem(key)
  if (raw === null) return null

  let parsed: unknown
  try {
    parsed = JSON.parse(raw)
  } catch {
    window.localStorage.removeItem(key)
    return null
  }

  if (!isEnvelope(parsed) || parsed.version !== WIZARD_STATE_VERSION) {
    window.localStorage.removeItem(key)
    return null
  }

  // Extra guard: reject state whose embedded user_id doesn't match the key
  // (catches tampering or cross-tenant leakage in shared browsers).
  if (parsed.data.user_id !== userId) {
    window.localStorage.removeItem(key)
    return null
  }

  return parsed.data
}

/**
 * Serializes and writes `state` to localStorage under its embedded `user_id`.
 * SSR-safe no-op when `window` is undefined. Best-effort: silently swallows
 * QuotaExceededError (iOS Safari Private Mode, Chrome Incognito) and other
 * setItem failures so the wizard never crashes mid-step. Persistence is a
 * resume convenience; in-memory state is authoritative until commit.
 */
export function writePersistedState(state: WizardPersistedState): void {
  if (typeof window === "undefined") return
  const envelope: PersistedEnvelope = {
    version: WIZARD_STATE_VERSION,
    data: state,
  }
  try {
    window.localStorage.setItem(persistedStateKey(state.user_id), JSON.stringify(envelope))
  } catch (err) {
    // Quota exceeded / Safari Private Mode / corrupted storage — best-effort
    // per AC-NR1.5. Caller treats persistence as advisory; do not throw.
    if (typeof console !== "undefined" && console.warn) {
      console.warn("[wizard-persistence] setItem failed; continuing without persistence", err)
    }
  }
}

/**
 * Removes the persisted state for `userId`. Called on wizard completion
 * (step 11) per AC-NR1.3 to prevent stale resume. SSR-safe no-op.
 */
export function clearPersistedState(userId: string): void {
  if (typeof window === "undefined") return
  window.localStorage.removeItem(persistedStateKey(userId))
}

function isEnvelope(value: unknown): value is PersistedEnvelope {
  if (typeof value !== "object" || value === null) return false
  const v = value as Record<string, unknown>
  if (typeof v.version !== "number") return false
  if (typeof v.data !== "object" || v.data === null) return false
  const d = v.data as Record<string, unknown>
  if (typeof d.user_id !== "string") return false
  return true
}

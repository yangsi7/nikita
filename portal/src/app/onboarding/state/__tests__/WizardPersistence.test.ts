import { describe, it, expect, beforeEach } from "vitest"

import {
  clearPersistedState,
  persistedStateKey,
  readPersistedState,
  writePersistedState,
  WIZARD_STATE_VERSION,
} from "@/app/onboarding/state/WizardPersistence"
import type { WizardPersistedState } from "@/app/onboarding/types/wizard"

// Spec 214 PR 214-A — T101 (RED)
// Tests AC-NR1.1 (resume mid-wizard), AC-NR1.2 (write on advance),
// AC-NR1.4 (user-scoped key — never read other users' state).
//
// Persistence is keyed by `nikita_wizard_{user_id}` and includes a version
// byte so legacy cinematic-onboarding payloads (without the byte) get
// silently cleared instead of mis-deserialized.

const USER_A = "11111111-1111-1111-1111-111111111111"
const USER_B = "22222222-2222-2222-2222-222222222222"

const baseState = (overrides: Partial<WizardPersistedState> = {}): WizardPersistedState => ({
  user_id: USER_A,
  last_step: 6,
  location_city: "Berlin",
  social_scene: "techno",
  drug_tolerance: 4,
  life_stage: "tech",
  interest: null,
  name: null,
  age: null,
  occupation: null,
  phone: null,
  chosen_option_id: null,
  cache_key: null,
  saved_at: "2026-04-16T08:00:00.000Z",
  ...overrides,
})

describe("WizardPersistence — key scoping (spec NR-1, AC-NR1.4)", () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it("scopes the key by user_id", () => {
    expect(persistedStateKey(USER_A)).toBe(`nikita_wizard_${USER_A}`)
    expect(persistedStateKey(USER_B)).toBe(`nikita_wizard_${USER_B}`)
    expect(persistedStateKey(USER_A)).not.toBe(persistedStateKey(USER_B))
  })

  it("ignores another user's persisted state when reading", () => {
    writePersistedState(baseState({ user_id: USER_A, location_city: "Berlin" }))
    expect(readPersistedState(USER_B)).toBeNull()
  })

  it("returns null when no key has been written for this user", () => {
    expect(readPersistedState(USER_A)).toBeNull()
  })
})

describe("WizardPersistence — round-trip (spec NR-1, AC-NR1.1, AC-NR1.2)", () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it("round-trips all collected fields, including cache_key + chosen_option_id", () => {
    const state = baseState({
      last_step: 8,
      name: "Jane",
      age: 28,
      occupation: "designer",
      phone: "+15551234567",
      chosen_option_id: "abc123def456",
      cache_key: "v1:berlin:techno:4:tech:0:0:designer",
    })
    writePersistedState(state)
    const read = readPersistedState(USER_A)
    expect(read).not.toBeNull()
    expect(read).toEqual(state)
  })

  it("writes a fresh saved_at timestamp on each call", () => {
    const a = baseState({ saved_at: "2026-04-16T08:00:00.000Z" })
    writePersistedState(a)
    const b = baseState({ saved_at: "2026-04-16T08:05:00.000Z", last_step: 7 })
    writePersistedState(b)
    expect(readPersistedState(USER_A)).toEqual(b)
  })
})

describe("WizardPersistence — version byte (spec NR-1)", () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it("declares WIZARD_STATE_VERSION = 1", () => {
    // Regression guard: bumping requires a CHANGELOG note + migration path
    expect(WIZARD_STATE_VERSION).toBe(1)
  })

  it("clears and returns null when the persisted version differs", () => {
    const wrongVersion = JSON.stringify({
      version: 999,
      data: baseState(),
    })
    window.localStorage.setItem(persistedStateKey(USER_A), wrongVersion)
    expect(readPersistedState(USER_A)).toBeNull()
    expect(window.localStorage.getItem(persistedStateKey(USER_A))).toBeNull()
  })

  it("clears and returns null when the persisted payload is corrupt JSON", () => {
    window.localStorage.setItem(persistedStateKey(USER_A), "{not-json")
    expect(readPersistedState(USER_A)).toBeNull()
    expect(window.localStorage.getItem(persistedStateKey(USER_A))).toBeNull()
  })

  it("clears and returns null when the persisted shape lacks a data field", () => {
    window.localStorage.setItem(
      persistedStateKey(USER_A),
      JSON.stringify({ version: WIZARD_STATE_VERSION })
    )
    expect(readPersistedState(USER_A)).toBeNull()
  })
})

describe("WizardPersistence — clearPersistedState (spec NR-1, AC-NR1.3)", () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it("removes the user's key on completion", () => {
    writePersistedState(baseState())
    clearPersistedState(USER_A)
    expect(window.localStorage.getItem(persistedStateKey(USER_A))).toBeNull()
    expect(readPersistedState(USER_A)).toBeNull()
  })

  it("does not touch other users' keys", () => {
    writePersistedState(baseState({ user_id: USER_A }))
    writePersistedState(baseState({ user_id: USER_B }))
    clearPersistedState(USER_A)
    expect(readPersistedState(USER_B)).not.toBeNull()
  })
})

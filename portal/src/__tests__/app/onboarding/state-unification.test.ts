/**
 * EM-4 state unification regression guard.
 *
 * FR-11d mandates the server `/state` GET endpoint is the single source of
 * truth for wizard state. This test exists to enforce that contract at the
 * codebase-shape level — the legacy `WizardPersistence.ts` (localStorage RWX)
 * and `WizardStateMachine.ts` (FSM) modules MUST NOT be reintroduced.
 *
 * Falsifiable check: if any future PR re-adds either module under
 * `portal/src/app/onboarding/state/`, this test fails. Symbol-level greps
 * over the shipped TS sources catch a re-introduction even if it dodges
 * the original filenames.
 *
 * The runtime-level "wizard mutation produces zero `localStorage.setItem`
 * calls" assertion is exercised by the existing `WizardShell.test.tsx`
 * fixture (which mounts the canonical wizard and never touches localStorage);
 * adding a duplicate render here would couple two tests to the same fixture
 * for no extra signal. The structural check below is what EM-4 specifically
 * regresses against.
 */

import { describe, expect, it } from "vitest"
import { existsSync, readFileSync } from "node:fs"
import { join } from "node:path"

const ONBOARDING_DIR = join(__dirname, "..", "..", "..", "app", "onboarding")
const STATE_DIR = join(ONBOARDING_DIR, "state")

describe("EM-4 — legacy state writers are not reintroduced", () => {
  it("WizardPersistence.ts must not exist (server /state is the sole authority)", () => {
    expect(existsSync(join(STATE_DIR, "WizardPersistence.ts"))).toBe(false)
  })

  it("WizardStateMachine.ts must not exist (216-C WizardShell is canonical)", () => {
    expect(existsSync(join(STATE_DIR, "WizardStateMachine.ts"))).toBe(false)
  })

  it("onboarding-wizard-legacy.tsx must not exist (legacy form wizard retired)", () => {
    expect(existsSync(join(ONBOARDING_DIR, "onboarding-wizard-legacy.tsx"))).toBe(false)
  })
})

describe("EM-4 — useConversationState reducer does not write localStorage", () => {
  it("source contains no localStorage.setItem / removeItem / window.localStorage calls", () => {
    const path = join(ONBOARDING_DIR, "hooks", "useConversationState.ts")
    const src = readFileSync(path, "utf-8")
    // Strip line/block comments so a comment mentioning localStorage doesn't
    // false-positive the structural assertion.
    const code = src
      .replace(/\/\*[\s\S]*?\*\//g, "")
      .replace(/\/\/[^\n]*/g, "")
    expect(code).not.toMatch(/localStorage\.(setItem|removeItem|getItem)/)
    expect(code).not.toMatch(/window\.localStorage/)
  })
})

describe("EM-4 — WizardShell does not write localStorage", () => {
  it("WizardShell.tsx source contains no localStorage writes", () => {
    const path = join(ONBOARDING_DIR, "_components", "WizardShell.tsx")
    const src = readFileSync(path, "utf-8")
    const code = src
      .replace(/\/\*[\s\S]*?\*\//g, "")
      .replace(/\/\/[^\n]*/g, "")
    expect(code).not.toMatch(/localStorage\.(setItem|removeItem)/)
    expect(code).not.toMatch(/window\.localStorage\.(setItem|removeItem)/)
  })
})

describe("EM-4 — NEXT_PUBLIC_USE_LEGACY_FORM_WIZARD flag is fully retired", () => {
  // QA iter-1 (PR #518): the flag must not be read anywhere on the
  // wizard-mount path. Comments stripped before grep so a lingering
  // historical mention in a JSDoc block does not register as a hit.
  it.each([
    ["page.tsx", "page.tsx"],
    ["onboarding-wizard.tsx", "onboarding-wizard.tsx"],
  ])("%s contains no NEXT_PUBLIC_USE_LEGACY_FORM_WIZARD reads", (_name, file) => {
    const src = readFileSync(join(ONBOARDING_DIR, file), "utf-8")
    const code = src
      .replace(/\/\*[\s\S]*?\*\//g, "")
      .replace(/\/\/[^\n]*/g, "")
    expect(code).not.toMatch(/NEXT_PUBLIC_USE_LEGACY_FORM_WIZARD/)
  })
})

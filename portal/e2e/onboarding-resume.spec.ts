import { test, expect } from "@playwright/test"
import { mockApiRoutes } from "./fixtures"

/**
 * Spec 214 — Onboarding resume (PR 214-C, T301)
 *
 * US-3: Mid-wizard abandonment + resume.
 *
 * Pre-populates localStorage with a Spec 214 `WizardPersistedState` envelope
 * (see `portal/src/app/onboarding/types/wizard.ts` + `WizardPersistence.ts`).
 * Then reloads `/onboarding?resume=true` and asserts the wizard opens on the
 * persisted step.
 *
 * The persisted key is `nikita_wizard_{user_id}` (see
 * `WizardPersistence.persistedStateKey`). The user_id under E2E auth bypass
 * is `e2e-player-id` (see `portal/src/lib/supabase/middleware.ts`).
 */

const USER_ID = "e2e-player-id"
const STATE_KEY = `nikita_wizard_${USER_ID}`
const WIZARD_STATE_VERSION = 1

test.describe("Onboarding resume — US-3 (Spec 214)", () => {
  test("abandon on step 7 then reload with ?resume=true resumes exact step", async ({ page }) => {
    await mockApiRoutes(page)

    // Seed localStorage BEFORE the page script runs so the wizard sees it.
    // page.addInitScript is evaluated on every navigation on this context.
    await page.addInitScript(
      ({ key, version, userId }) => {
        const payload = {
          version,
          data: {
            user_id: userId,
            last_step: 7,
            location_city: "Zurich",
            social_scene: "techno",
            drug_tolerance: 3,
            life_stage: "tech",
            interest: null,
            name: null,
            age: null,
            occupation: null,
            phone: null,
            chosen_option_id: null,
            cache_key: null,
            saved_at: new Date().toISOString(),
          },
        }
        window.localStorage.setItem(key, JSON.stringify(payload))
      },
      { key: STATE_KEY, version: WIZARD_STATE_VERSION, userId: USER_ID }
    )

    await page.goto("/onboarding?resume=true", { waitUntil: "domcontentloaded" })

    // AC-3.x: Wizard resumes on step 7 (the last-persisted step), NOT step 3.
    const step7 = page.locator('[data-testid="wizard-step-7"]')
    await expect(step7).toBeVisible({ timeout: 10_000 })

    // Verify that step 3 (dossier header) is NOT mounted — one-step-at-a-time
    // discipline per spec AC-1.1.
    await expect(page.locator('[data-testid="wizard-step-3"]')).toHaveCount(0)
  })

  test("missing resume param with persisted state still resumes (soft resume)", async ({ page }) => {
    await mockApiRoutes(page)

    await page.addInitScript(
      ({ key, version, userId }) => {
        const payload = {
          version,
          data: {
            user_id: userId,
            last_step: 5,
            location_city: "Berlin",
            social_scene: "techno",
            drug_tolerance: null,
            life_stage: null,
            interest: null,
            name: null,
            age: null,
            occupation: null,
            phone: null,
            chosen_option_id: null,
            cache_key: null,
            saved_at: new Date().toISOString(),
          },
        }
        window.localStorage.setItem(key, JSON.stringify(payload))
      },
      { key: STATE_KEY, version: WIZARD_STATE_VERSION, userId: USER_ID }
    )

    await page.goto("/onboarding", { waitUntil: "domcontentloaded" })

    // Soft-resume: without the explicit ?resume=true, the wizard still honors
    // localStorage (spec NR-1 — persistence is authoritative when present).
    const step5 = page.locator('[data-testid="wizard-step-5"]')
    await expect(step5).toBeVisible({ timeout: 10_000 })
  })
})

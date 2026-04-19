import { test, expect, type Page } from "@playwright/test"
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

interface SeedOptions {
  lastStep: number
  version?: number
  overrides?: Record<string, unknown>
}

/**
 * Seeds `nikita_wizard_{user_id}` localStorage with a Spec 214 envelope.
 *
 * Called via `page.addInitScript` so the payload lands BEFORE any page
 * script runs and the wizard's on-mount `readPersistedState` sees it.
 * Defaults emit a minimal valid envelope; `overrides` replaces top-level
 * `data` fields (user_id, last_step, etc) for per-test variants.
 */
async function seedWizardState(page: Page, opts: SeedOptions): Promise<void> {
  const version = opts.version ?? WIZARD_STATE_VERSION
  await page.addInitScript(
    ({ key, version, userId, lastStep, overrides }) => {
      const baseData = {
        user_id: userId,
        last_step: lastStep,
        location_city: null,
        social_scene: null,
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
      }
      const payload = {
        version,
        data: { ...baseData, ...overrides },
      }
      window.localStorage.setItem(key, JSON.stringify(payload))
    },
    {
      key: STATE_KEY,
      version,
      userId: USER_ID,
      lastStep: opts.lastStep,
      overrides: opts.overrides ?? {},
    }
  )
}

// SKIPPED: legacy form wizard specs superseded by PR #363 chat-first wizard.
// Tracked in GH #364 for rewrite against chat UI or deletion with PR 5 cleanup.
test.describe.skip("Onboarding resume — US-3 (Spec 214)", () => {
  test("abandon on step 7 then reload with ?resume=true resumes exact step", async ({ page }) => {
    await mockApiRoutes(page)

    await seedWizardState(page, {
      lastStep: 7,
      overrides: {
        location_city: "Zurich",
        social_scene: "techno",
        drug_tolerance: 3,
        life_stage: "tech",
      },
    })

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

    await seedWizardState(page, {
      lastStep: 5,
      overrides: {
        location_city: "Berlin",
        social_scene: "techno",
      },
    })

    await page.goto("/onboarding", { waitUntil: "domcontentloaded" })

    // Soft-resume: without the explicit ?resume=true, the wizard still honors
    // localStorage (spec NR-1 — persistence is authoritative when present).
    const step5 = page.locator('[data-testid="wizard-step-5"]')
    await expect(step5).toBeVisible({ timeout: 10_000 })
  })

  test("envelope with mismatched version byte is cleared and wizard fresh-starts on step 3", async ({ page }) => {
    await mockApiRoutes(page)

    // Seed an envelope whose `version` field does NOT match the current
    // WIZARD_STATE_VERSION (1). Per WizardPersistence.readPersistedState,
    // mismatched envelopes are silently cleared and `null` returned — so the
    // wizard mounts with EMPTY_VALUES on its first-step default (step 3).
    //
    // Security-relevant: the version guard defends against forged legacy
    // payloads and cinematic-onboarding leakage (see NR-1, WizardPersistence
    // docblock). This test is the regression guard for that branch.
    await seedWizardState(page, {
      lastStep: 7,
      version: 999, // mismatch vs WIZARD_STATE_VERSION = 1
      overrides: {
        location_city: "TamperedCity",
      },
    })

    await page.goto("/onboarding", { waitUntil: "domcontentloaded" })

    // Wizard fresh-starts on step 3 (DossierHeader / FIRST_WIZARD_STEP), NOT
    // the tampered step 7.
    const step3 = page.locator('[data-testid="wizard-step-3"]')
    await expect(step3).toBeVisible({ timeout: 10_000 })
    await expect(page.locator('[data-testid="wizard-step-7"]')).toHaveCount(0)

    // Envelope was cleared (post-conditions). Readback should be null. Uses
    // expect.poll because `readPersistedState` runs inside the wizard's
    // mount-time `useEffect` (AC-NR1.5) — step 3 can render BEFORE the
    // effect fires, so a direct evaluate can race the cleanup. Poll until
    // the useEffect has had a chance to run.
    await expect
      .poll(
        async () =>
          page.evaluate((key) => window.localStorage.getItem(key), STATE_KEY),
        { timeout: 5_000 }
      )
      .toBeNull()
  })
})

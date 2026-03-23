import { test, expect } from "@playwright/test"
import { mockApiRoutes } from "./fixtures"

/**
 * Onboarding cinematic E2E tests.
 *
 * The /onboarding page is a server component that:
 * 1. Checks Supabase auth (bypassed via E2E_AUTH_BYPASS=true)
 * 2. Fetches /portal/stats server-side to check onboarded_at
 *    (fails gracefully in E2E since NEXT_PUBLIC_API_URL is a dummy URL,
 *     so the page always falls through to show the onboarding cinematic)
 *
 * The client-side OnboardingCinematic renders 5 snap-scroll sections:
 *   section-score, section-chapters, section-rules, section-profile, section-mission
 *
 * Form submission POSTs to /api/v1/onboarding/profile (mocked in api-mocks.ts).
 */

// ────────────────────────────────────────────────────────
// Group 1: Desktop (1280x720 — default viewport)
// ────────────────────────────────────────────────────────

test.describe("Onboarding — Desktop Sections", () => {
  test("renders all 5 sections", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/onboarding", { waitUntil: "networkidle" })

    const sections = ["section-score", "section-chapters", "section-rules", "section-profile", "section-mission"]
    for (const id of sections) {
      await expect(
        page.locator(`[data-testid="${id}"]`),
        `Section [data-testid="${id}"] should be attached`
      ).toBeAttached({ timeout: 10_000 })
    }
  })

  test("score section shows heading and ScoreRing SVG", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/onboarding", { waitUntil: "networkidle" })

    const scoreSection = page.locator('[data-testid="section-score"]')
    await expect(scoreSection).toBeVisible({ timeout: 10_000 })
    // The SectionHeader renders "The Score" text
    await expect(scoreSection).toContainText("The Score")
    // ScoreRing renders an SVG
    const svg = scoreSection.locator("svg").first()
    await expect(svg).toBeAttached()
  })

  test("chapter stepper is visible after scroll", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/onboarding", { waitUntil: "networkidle" })

    const chaptersSection = page.locator('[data-testid="section-chapters"]')
    await chaptersSection.scrollIntoViewIfNeeded()
    await expect(chaptersSection).toBeVisible({ timeout: 10_000 })

    const stepper = page.locator('[data-testid="onboarding-chapter-stepper"]')
    await expect(stepper).toBeVisible({ timeout: 10_000 })
  })

  test("rules section shows 4 rule cards", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/onboarding", { waitUntil: "networkidle" })

    const rulesSection = page.locator('[data-testid="section-rules"]')
    await rulesSection.scrollIntoViewIfNeeded()
    await expect(rulesSection).toBeVisible({ timeout: 10_000 })
    await expect(rulesSection).toContainText("The Rules")

    // 4 rule cards: "How You Score", "Time Matters", "Boss Encounters", "Your Vices"
    for (const title of ["How You Score", "Time Matters", "Boss Encounters", "Your Vices"]) {
      await expect(rulesSection.getByText(title)).toBeVisible({ timeout: 5_000 })
    }
  })

  test("profile form has city input and scene selector", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/onboarding", { waitUntil: "networkidle" })

    const profileSection = page.locator('[data-testid="section-profile"]')
    await profileSection.scrollIntoViewIfNeeded()
    await expect(profileSection).toBeVisible({ timeout: 10_000 })

    // City input
    const cityInput = profileSection.locator('input[placeholder="City, Country"]')
    await expect(cityInput).toBeVisible({ timeout: 5_000 })

    // Scene selector — "Techno" option text
    await expect(profileSection.getByText("Techno")).toBeVisible({ timeout: 5_000 })
  })

  test("MoodOrb renders in mission section", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/onboarding", { waitUntil: "networkidle" })

    const missionSection = page.locator('[data-testid="section-mission"]')
    await missionSection.scrollIntoViewIfNeeded()
    await expect(missionSection).toBeVisible({ timeout: 10_000 })

    const moodOrb = page.locator('[data-testid="onboarding-mood-orb"]')
    await expect(moodOrb).toBeVisible({ timeout: 5_000 })
  })

  test("submit with valid data shows transition overlay", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/onboarding", { waitUntil: "networkidle" })

    // Scroll to profile section and fill form
    const profileSection = page.locator('[data-testid="section-profile"]')
    await profileSection.scrollIntoViewIfNeeded()
    await expect(profileSection).toBeVisible({ timeout: 10_000 })

    // Fill city
    const cityInput = profileSection.locator('input[placeholder="City, Country"]')
    await cityInput.fill("Zurich, Switzerland")

    // Select "Techno" scene (click the radio button that contains "Techno")
    await profileSection.getByText("Techno").click()

    // Scroll to submit button and click
    const submitBtn = page.locator('[data-testid="onboarding-submit-btn"]')
    await submitBtn.scrollIntoViewIfNeeded()
    await expect(submitBtn).toBeVisible({ timeout: 5_000 })
    await submitBtn.click()

    // After successful submit, the transition overlay renders with "Opening Telegram..."
    // Scope to section-mission to avoid strict mode violation (toast also contains this text)
    const missionSection = page.locator('[data-testid="section-mission"]')
    await expect(missionSection.getByText("Opening Telegram...")).toBeVisible({ timeout: 10_000 })
  })

  test("submit without required fields scrolls to profile section", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/onboarding", { waitUntil: "networkidle" })

    // Scroll directly to the mission/submit section without filling form
    const missionSection = page.locator('[data-testid="section-mission"]')
    await missionSection.scrollIntoViewIfNeeded()
    await expect(missionSection).toBeVisible({ timeout: 10_000 })

    const submitBtn = page.locator('[data-testid="onboarding-submit-btn"]')
    await expect(submitBtn).toBeVisible({ timeout: 5_000 })
    await submitBtn.click()

    // The onError handler scrolls to section-profile
    // After clicking, profile section should become visible (scrolled into view)
    const profileSection = page.locator('[data-testid="section-profile"]')
    await expect(profileSection).toBeInViewport({ timeout: 10_000 })
  })
})

// ────────────────────────────────────────────────────────
// Group 2: Mobile (375x812)
// ────────────────────────────────────────────────────────

test.describe("Onboarding — Mobile Layout", () => {
  test.use({ viewport: { width: 375, height: 812 } })

  test("mobile layout renders all sections", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/onboarding", { waitUntil: "networkidle" })

    const sections = ["section-score", "section-chapters", "section-rules", "section-profile", "section-mission"]
    for (const id of sections) {
      await expect(
        page.locator(`[data-testid="${id}"]`),
        `Section [data-testid="${id}"] should be attached on mobile`
      ).toBeAttached({ timeout: 10_000 })
    }
  })

  test("scene selector cards visible on mobile", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/onboarding", { waitUntil: "networkidle" })

    const profileSection = page.locator('[data-testid="section-profile"]')
    await profileSection.scrollIntoViewIfNeeded()
    await expect(profileSection).toBeVisible({ timeout: 10_000 })

    // "Techno" scene card should be visible on mobile
    await expect(profileSection.getByText("Techno")).toBeVisible({ timeout: 5_000 })
  })
})

// ────────────────────────────────────────────────────────
// Group 3: Auth Redirects
// ────────────────────────────────────────────────────────

test.describe("Onboarding — Auth Behavior", () => {
  /**
   * KNOWN LIMITATION: The "already onboarded" redirect cannot be tested in E2E.
   *
   * page.tsx fetches /portal/stats SERVER-SIDE using the real
   * NEXT_PUBLIC_API_URL (a dummy URL in E2E env). This fetch happens inside
   * the Next.js server process, not in the browser, so page.route() mocks
   * cannot intercept it. The fetch fails, the catch block runs, and the
   * page falls through to show onboarding regardless of onboarded_at.
   *
   * To properly test this, we would need:
   * - A real backend or MSW (node) to intercept server-side fetches
   * - Or modifying page.tsx to accept an env-based override for testing
   *
   * For now, we verify that the page renders successfully when the
   * server-side stats fetch fails (the graceful fallback path).
   */
  test("page renders onboarding when server-side stats fetch fails (graceful fallback)", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/onboarding", { waitUntil: "networkidle" })

    // The page should show the onboarding cinematic (not redirect)
    const scoreSection = page.locator('[data-testid="section-score"]')
    await expect(scoreSection).toBeAttached({ timeout: 10_000 })
    expect(page.url()).toContain("/onboarding")
  })
})

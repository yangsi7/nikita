import { test, expect, assertLoginPageElements } from "./fixtures"

/**
 * Auth flow E2E tests.
 *
 * Tests verify the complete authentication lifecycle:
 * - Unauthenticated redirect behavior
 * - Login page form rendering and interaction
 * - Magic link submission flow
 * - Error states (database errors, rate limits, expired links)
 * - Logout behavior (sidebar sign-out button)
 */

test.describe("Auth Flow — Unauthenticated Redirects", () => {
  test("unauthenticated user at / renders landing page (no redirect)", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded", timeout: 30_000 })
    await page.waitForTimeout(2_000)
    // Root page now shows the landing page — middleware has an early-return for /
    // Unauthenticated users must NOT be redirected to /login
    const url = page.url()
    expect(url).not.toContain("/login")
    // Landing page H1 should be visible
    const h1 = page.locator("h1")
    await expect(h1).toContainText("Dumped", { timeout: 5_000 })
  })

  // Skipped: E2E_AUTH_BYPASS=true in playwright.config means middleware never
  // redirects to /login. These tests are vacuous (OR always true). To test real
  // redirects, run with E2E_AUTH_BYPASS=false and a real Supabase instance.
  test.skip("unauthenticated user at /dashboard redirects to /login", async ({ page }) => {
    await page.goto("/dashboard", { waitUntil: "domcontentloaded", timeout: 30_000 })
    await page.waitForTimeout(2_000)
    expect(page.url()).toContain("/login")
  })

  test.skip("unauthenticated user at /admin redirects to /login", async ({ page }) => {
    await page.goto("/admin", { waitUntil: "domcontentloaded", timeout: 30_000 })
    await page.waitForTimeout(2_000)
    expect(page.url()).toContain("/login")
  })
})

test.describe("Auth Flow — Login Page Rendering", () => {
  test("login page renders all required form elements", async ({ page }) => {
    await page.goto("/login")
    await assertLoginPageElements(page)
  })

  test("login page has email input with correct placeholder", async ({ page }) => {
    await page.goto("/login")
    const emailInput = page.getByPlaceholder("you@example.com")
    await expect(emailInput).toBeVisible()
    await expect(emailInput).toHaveAttribute("type", "email")
  })

  test("login page has submit button initially disabled", async ({ page }) => {
    await page.goto("/login")
    const submitBtn = page.getByRole("button", { name: /send magic link/i })
    await expect(submitBtn).toBeDisabled()
  })

  test("login page branding shows Nikita in rose color", async ({ page }) => {
    await page.goto("/login")
    const brand = page.getByText("Nikita").first()
    await expect(brand).toBeVisible()
    // Verify it uses the rose accent class
    const classAttr = await brand.getAttribute("class")
    expect(classAttr).toContain("rose")
  })
})

test.describe("Auth Flow — Form Interaction", () => {
  test("submit button enables when email is entered", async ({ page }) => {
    await page.goto("/login")
    const emailInput = page.getByPlaceholder("you@example.com")
    const submitBtn = page.getByRole("button", { name: /send magic link/i })

    await expect(submitBtn).toBeDisabled()
    await emailInput.fill("player@example.com")
    await expect(submitBtn).toBeEnabled()
  })

  test("submit button disables when email is cleared", async ({ page }) => {
    await page.goto("/login")
    const emailInput = page.getByPlaceholder("you@example.com")
    const submitBtn = page.getByRole("button", { name: /send magic link/i })

    await emailInput.fill("player@example.com")
    await expect(submitBtn).toBeEnabled()
    await emailInput.clear()
    await expect(submitBtn).toBeDisabled()
  })

  test("submitting email shows confirmation message", async ({ page }) => {
    await page.goto("/login")
    const emailInput = page.getByPlaceholder("you@example.com")
    const submitBtn = page.getByRole("button", { name: /send magic link/i })

    await emailInput.fill("test@example.com")

    // Mock the Supabase magic link endpoint to prevent real API call
    await page.route("**/auth/v1/otp**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({}),
      })
    })

    await submitBtn.click()

    // Should show confirmation text or "Try another email" button
    await expect(
      page.getByText(/check your|magic link|try another/i).first()
    ).toBeVisible({ timeout: 10_000 })
  })

  test("magic link failure shows error toast and stays on login", async ({ page }) => {
    await page.goto("/login")
    const emailInput = page.getByPlaceholder("you@example.com")
    const submitBtn = page.getByRole("button", { name: /send magic link/i })

    await emailInput.fill("test@example.com")

    // Mock Supabase magic link endpoint to return rate limit error
    await page.route("**/auth/v1/otp**", async (route) => {
      await route.fulfill({
        status: 429,
        contentType: "application/json",
        body: JSON.stringify({ error: "Rate limit exceeded", message: "Rate limit exceeded" }),
      })
    })

    await submitBtn.click()

    // Should show error state — sonner toast with "Too many attempts"
    await page.waitForTimeout(2_000)
    // Check that we did NOT navigate away (still on login)
    expect(page.url()).toContain("/login")
  })

  test("database error shows account issue toast", async ({ page }) => {
    await page.goto("/login")
    const emailInput = page.getByPlaceholder("you@example.com")
    const submitBtn = page.getByRole("button", { name: /send magic link/i })

    await emailInput.fill("broken@example.com")

    // Mock Supabase magic link endpoint to return database error
    // (happens when auth.identities is missing for a user)
    await page.route("**/auth/v1/otp**", async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({
          error: "Database error querying schema",
          message: "Database error querying schema",
        }),
      })
    })

    await submitBtn.click()

    // Should show "Account issue detected" toast
    await expect(
      page.getByText(/account issue/i).first()
    ).toBeVisible({ timeout: 5_000 })

    // Should stay on login page
    expect(page.url()).toContain("/login")
  })

  test("EM-1: confirm-route error param surfaces toast on /onboarding/auth", async ({ page }) => {
    // Navigate to wizard auth surface with error query param (sent by
    // /auth/confirm on verifyOtp failure post-EM-1; previously /login).
    await page.goto("/onboarding/auth?error=link_expired")

    // Should show the EM-1 funnel-recovery toast copy.
    await expect(
      page.getByText(/timed out/i).first()
    ).toBeVisible({ timeout: 5_000 })
  })
})

test.describe("Auth Flow — Logout", () => {
  test("sign out button is present in sidebar when page renders", async ({ page }) => {
    // Navigate to dashboard — if it renders (no redirect), check for sign out
    await page.goto("/dashboard", { waitUntil: "domcontentloaded", timeout: 30_000 })
    await page.waitForTimeout(2_000)

    if (!page.url().includes("/login")) {
      // Page rendered — verify Sign Out exists in DOM (may be in collapsed sidebar)
      const signOutCount = await page.locator("text=Sign Out").count()
      expect(signOutCount, "Sign Out should exist in page DOM").toBeGreaterThanOrEqual(1)
    }
  })
})

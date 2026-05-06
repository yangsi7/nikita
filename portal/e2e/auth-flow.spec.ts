import { test, expect, assertLoginPageElements } from "./fixtures"

/**
 * Auth flow E2E — Spec 216-G TG-first canonical.
 *
 * Verifies:
 * - Unauthenticated users land on the marketing page (no redirect to /login)
 * - /login renders TG-first surface (no email form)
 * - /auth/confirm error redirects surface toast on /login
 * - Sidebar sign-out button is present on dashboard
 *
 * Email-form interaction tests removed: portal-side magic-link form was
 * deleted in PR #537 (216-G). Bot signup_handler FSM is now the single
 * canonical signup path.
 */

test.describe("Auth Flow — Unauthenticated Redirects", () => {
  test("unauthenticated user at / renders landing page (no redirect)", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded", timeout: 30_000 })
    await page.waitForTimeout(2_000)
    const url = page.url()
    expect(url).not.toContain("/login")
    const h1 = page.locator("h1")
    await expect(h1).toContainText("Dumped", { timeout: 5_000 })
  })

  // Skipped: E2E_AUTH_BYPASS=true in playwright.config means middleware never
  // redirects. To test real redirects, run with E2E_AUTH_BYPASS=false.
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

test.describe("Auth Flow — Login Page (TG-first)", () => {
  test("login page renders TG-first surface", async ({ page }) => {
    await page.goto("/login")
    await assertLoginPageElements(page)
  })

  test("login page CTA links to Telegram bot", async ({ page }) => {
    await page.goto("/login")
    const cta = page.locator('[data-testid="login-telegram-cta"]')
    await expect(cta).toHaveAttribute("href", "https://t.me/Nikita_my_bot")
  })

  test("login page has no email input (regression guard)", async ({ page }) => {
    await page.goto("/login")
    await expect(page.locator('input[type="email"]')).toHaveCount(0)
  })

  test("login page branding shows Nikita in rose color", async ({ page }) => {
    await page.goto("/login")
    const brand = page.getByText("Nikita").first()
    await expect(brand).toBeVisible()
    const classAttr = await brand.getAttribute("class")
    expect(classAttr).toContain("rose")
  })
})

test.describe("Auth Flow — Confirm Error Recovery", () => {
  test("confirm-route error param surfaces toast on /login", async ({ page }) => {
    // Post-216-G: /auth/confirm failures redirect to /login?error=... (was /onboarding/auth?error=...)
    await page.goto("/login?error=link_expired")
    await expect(page.getByText(/expired/i).first()).toBeVisible({ timeout: 5_000 })
  })

  test("telegram_conflict error surfaces toast on /login", async ({ page }) => {
    await page.goto("/login?error=telegram_conflict")
    await expect(
      page.getByText(/already linked/i).first()
    ).toBeVisible({ timeout: 5_000 })
  })
})

test.describe("Auth Flow — Logout", () => {
  test("sign out button is present in sidebar when page renders", async ({ page }) => {
    await page.goto("/dashboard", { waitUntil: "domcontentloaded", timeout: 30_000 })
    await page.waitForTimeout(2_000)

    if (!page.url().includes("/login")) {
      const signOutCount = await page.locator("text=Sign Out").count()
      expect(signOutCount, "Sign Out should exist in page DOM").toBeGreaterThanOrEqual(1)
    }
  })
})

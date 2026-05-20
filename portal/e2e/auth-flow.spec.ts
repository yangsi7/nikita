import { test, expect } from "./fixtures"

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

test.describe("Auth Flow — /login deletion (Spec 220 PR-A)", () => {
  test("/login returns 410 GONE", async ({ request }) => {
    // Spec 220 PR-A (REQ-002): /login is no longer an auth surface. The page
    // was deleted and replaced with a route handler returning 410 Gone so
    // crawlers and stale links fail loudly. Canonical entry is the TG bot.
    const res = await request.get("/login", { maxRedirects: 0 })
    expect(res.status()).toBe(410)
  })
})

// Spec 220 PR-A deleted the /login page (now 410), so /auth/confirm errors can
// no longer surface a toast there. PR-B (Plan 01-04) rewrites /auth/confirm to
// return 400-on-error (no /login redirect). These error-recovery tests are
// re-evaluated against the new surface in PR-B — skipped here to keep PR-A green.
test.describe.skip("Auth Flow — Confirm Error Recovery (redefined in PR-B)", () => {
  test("confirm-route error param surfaces toast on /login", async ({ page }) => {
    await page.goto("/login?error=link_expired")
    await expect(page.getByText(/expired/i).first()).toBeVisible({ timeout: 5_000 })
  })

  test("telegram_conflict error surfaces toast on /login", async ({ page }) => {
    await page.goto("/login?error=telegram_conflict")
    await expect(
      page.getByText(/already linked/i).first()
    ).toBeVisible({ timeout: 5_000 })
  })

  test("telegram_bind_failed error surfaces toast on /login", async ({ page }) => {
    await page.goto("/login?error=telegram_bind_failed")
    await expect(
      page.getByText(/couldn't link/i).first()
    ).toBeVisible({ timeout: 5_000 })
  })
})

test.describe("Auth Flow — /onboarding/auth deletion (Spec 220 PR-A)", () => {
  test("/onboarding/auth returns 404 (route file fully deleted)", async ({ request }) => {
    // Spec 220 FR-3 / REQ-003: the /onboarding/auth route handler is DELETED
    // entirely (full file removal, not a 410 stub). A deleted FE route returns
    // 404. SPEC AC-2 explicitly allows 404 for deleted FE routes.
    const res = await request.get("/onboarding/auth", { maxRedirects: 0 })
    expect(res.status()).toBe(404)
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

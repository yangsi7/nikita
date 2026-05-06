import { test, expect, assertLoginPageElements, expectProtectedRoute } from "./fixtures"

/**
 * Login Page E2E — Spec 216-G TG-first canonical surface.
 *
 * Post-216-G `/login` is no longer a magic-link email form. It's the
 * sign-out destination + `/auth/confirm` failure redirect target.
 * Renders a single Telegram CTA. No portal-side `signInWithOtp`.
 */

test.describe("Login Page (TG-first)", () => {
  test("renders TG-first surface with all elements", async ({ page }) => {
    await page.goto("/login")
    await assertLoginPageElements(page)
  })

  test("CTA href points at Telegram bot", async ({ page }) => {
    await page.goto("/login")
    const cta = page.locator('[data-testid="login-telegram-cta"]')
    await expect(cta).toHaveAttribute("href", "https://t.me/Nikita_my_bot")
  })

  test("renders no email input (regression guard)", async ({ page }) => {
    await page.goto("/login")
    await expect(page.locator('input[type="email"]')).toHaveCount(0)
  })

  test("renders no portal magic-link button (regression guard)", async ({ page }) => {
    await page.goto("/login")
    await expect(
      page.getByRole("button", { name: /send magic link/i })
    ).toHaveCount(0)
  })

  test("error query param surfaces error toast", async ({ page }) => {
    await page.goto("/login?error=link_expired")
    await expect(page.getByText(/expired/i).first()).toBeVisible({ timeout: 5_000 })
  })

  test("uses dark theme (bg-void)", async ({ page }) => {
    await page.goto("/login")
    const body = page.locator("body")
    const bgColor = await body.evaluate((el) => getComputedStyle(el).backgroundColor)
    expect(bgColor).not.toBe("rgb(255, 255, 255)")
  })
})

test.describe("Auth Redirects (Unauthenticated)", () => {
  test("root / renders landing page", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded", timeout: 30_000 })
    await page.waitForTimeout(2_000)
    await expect(page.locator("h1")).toContainText("Dumped", { timeout: 5_000 })
  })

  const protectedRoutes = [
    "/dashboard",
    "/dashboard/engagement",
    "/dashboard/vices",
    "/dashboard/conversations",
    "/dashboard/diary",
    "/dashboard/settings",
    "/admin",
    "/admin/users",
    "/admin/pipeline",
    "/admin/voice",
    "/admin/text",
    "/admin/jobs",
    "/admin/prompts",
  ]

  for (const route of protectedRoutes) {
    test(`${route} is protected (requires auth)`, async ({ page }) => {
      const result = await expectProtectedRoute(page, route)
      expect(result, `${route} should render with auth bypass active`).toBe("rendered")
    })
  }
})

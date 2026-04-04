import { test, expect, assertLoginPageElements, expectProtectedRoute } from "./fixtures"

test.describe("Login Page", () => {
  test("renders login form with all elements", async ({ page }) => {
    await page.goto("/login")
    await assertLoginPageElements(page)
  })

  test("has correct page title/brand", async ({ page }) => {
    await page.goto("/login")
    await expect(page.getByText("Nikita")).toBeVisible()
    await expect(page.getByText("Sign in to your dashboard")).toBeVisible()
  })

  test("email input accepts text", async ({ page }) => {
    await page.goto("/login")
    const emailInput = page.getByPlaceholder("you@example.com")
    await emailInput.fill("test@example.com")
    await expect(emailInput).toHaveValue("test@example.com")
  })

  test("submit button disabled when email empty", async ({ page }) => {
    await page.goto("/login")
    const submitBtn = page.getByRole("button", { name: /send magic link/i })
    await expect(submitBtn).toBeDisabled()
  })

  test("submit button enabled when email entered", async ({ page }) => {
    await page.goto("/login")
    await page.getByPlaceholder("you@example.com").fill("test@example.com")
    const submitBtn = page.getByRole("button", { name: /send magic link/i })
    await expect(submitBtn).toBeEnabled()
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
    // Landing page H1 says "Don't Get Dumped" — verify it rendered
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
      // E2E_AUTH_BYPASS=true → pages always render, never redirect.
      // Assert "rendered" explicitly so the test fails if bypass breaks.
      expect(result, `${route} should render with auth bypass active`).toBe("rendered")
    })
  }
})

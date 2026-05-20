import { test, expect, expectProtectedRoute } from "./fixtures"

/**
 * Auth redirects + protected-route E2E.
 *
 * Spec 220 PR-A deleted the `/login` page (now 410 GONE — see auth-flow.spec.ts
 * for the 410 assertion). The TG-first surface tests that previously lived here
 * are obsolete; this file now covers landing render + protected-route gating.
 */

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

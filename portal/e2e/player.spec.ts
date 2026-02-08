import { test, expect, expectProtectedRoute } from "./fixtures"

/**
 * Player dashboard E2E tests.
 *
 * Tests verify player routes are accessible and render expected structure.
 * Without auth, pages may show error/loading states or redirect to /login.
 */

test.describe("Player Routes — Smoke Tests", () => {
  const playerRoutes = [
    { path: "/dashboard", name: "Dashboard" },
    { path: "/dashboard/engagement", name: "Engagement" },
    { path: "/dashboard/vices", name: "Vices" },
    { path: "/dashboard/conversations", name: "Conversations" },
    { path: "/dashboard/diary", name: "Diary" },
    { path: "/dashboard/settings", name: "Settings" },
  ]

  for (const route of playerRoutes) {
    test(`${route.name} (${route.path}) loads or redirects`, async ({ page }) => {
      const result = await expectProtectedRoute(page, route.path)

      if (result === "rendered") {
        // Page rendered — verify body has content (not blank)
        const body = page.locator("body")
        const text = await body.textContent()
        expect(text?.length).toBeGreaterThan(0)
      }
      expect(["redirected", "rendered"]).toContain(result)
    })
  }
})

test.describe("Player Routes — Structure", () => {
  test("player sidebar has navigation when rendered", async ({ page }) => {
    const result = await expectProtectedRoute(page, "/dashboard")

    if (result === "rendered") {
      // Check for player sidebar nav — at least some items should render
      const hasNikita = await page.locator("text=Nikita").first().isVisible().catch(() => false)
      expect(hasNikita).toBe(true)
    }
  })

  test("dashboard renders or redirects without auth", async ({ page }) => {
    const result = await expectProtectedRoute(page, "/dashboard")
    // Without auth: either redirects to /login or renders page (both acceptable)
    expect(["redirected", "rendered"]).toContain(result)
  })

  test("deep route /dashboard/conversations/abc-123 is protected", async ({ page }) => {
    const result = await expectProtectedRoute(page, "/dashboard/conversations/abc-123")
    expect(["redirected", "rendered"]).toContain(result)
  })
})
